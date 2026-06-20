import os
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager, asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
import qrcode
from io import BytesIO
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# ==============================================================================
# CONFIGURACIÓN INICIAL Y ENTORNO
# ==============================================================================
# Carga las variables de entorno desde la ruta absoluta del archivo de configuración.
load_dotenv("/app/config.env")

# Asigna la clave API del servidor, usando un valor de respaldo por seguridad.
API_KEY = os.getenv("API_KEY", "cambia_esta_clave")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
FERNET = None

# Inicialización segura del objeto de encriptación Fernet.
# Si la clave no es válida, captura la excepción para evitar el colapso del servidor.
if ENCRYPTION_KEY:
    try:
        FERNET = Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        print(f"Advertencia: Clave ENCRYPTION_KEY inválida ({e}). La encriptación de URL estará deshabilitada.")
        FERNET = None

# Rutas persistentes dentro del volumen compartido del contenedor.
DATABASE = "/app/datos/nodos.db"
TUNNEL_URL_FILE = "/app/datos/tunnel_url.txt"
TUNNEL_URL_ENC_FILE = "/app/datos/tunnel_url_encrypted.txt"

# ==============================================================================
# MODELOS DE DATOS (PYDANTIC)
# ==============================================================================
# Define las estructuras y validaciones de datos para las peticiones HTTP entrantes.

class NodePing(BaseModel):
    uuid: str

class NodeAdd(BaseModel):
    uuid: str
    ip: str
    puerto: int
    base_folio: str

    # Validador de campo para asegurar que el puerto esté dentro del rango TCP/IP estándar.
    @field_validator('puerto')
    def puerto_valido(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError('Puerto debe estar entre 1 y 65535')
        return v

class NodeAct(NodeAdd):
    pass

# Nuevo modelo para la eliminación de nodos, requiere uuid y base_folio
class NodeDel(BaseModel):
    uuid: str
    base_folio: str

# ==============================================================================
# GESTIÓN DE LA BASE DE DATOS (SQLITE3)
# ==============================================================================

# Administrador de contexto para las conexiones a la base de datos.
# Garantiza el cierre de los descriptores de archivos incluso ante excepciones de ejecución.
@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30.0, check_same_thread=False)
    # Habilita el modo WAL (Write-Ahead Logging) para permitir lecturas y escrituras concurrentes sin bloqueos.
    conn.execute("PRAGMA journal_mode=WAL")
    # Configura el retorno de registros como diccionarios accesibles por clave de columna.
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Inicializa la estructura relacional si el archivo .db se encuentra vacío.
# Actualización: la identificación de nodos se hace ahora por uuid + base_folio.
# Con esto, cualquier nodo puede estar vinculado a cualquier base y viceversa.
def init_db():
    with get_db() as conn:
        # Eliminar la tabla si existe (para empezar desde cero)
        conn.execute('DROP TABLE IF EXISTS nodos')
        # Crear la tabla con la nueva estructura
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nodos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL,
                ip TEXT NOT NULL,
                puerto INTEGER NOT NULL,
                base_folio TEXT NOT NULL,
                ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activo BOOLEAN DEFAULT 1,
                UNIQUE(uuid, base_folio)
            )
        ''')
        # Crear índices
        conn.execute('CREATE INDEX idx_base ON nodos(base_folio)')
        conn.execute('CREATE INDEX idx_uuid ON nodos(uuid)')

# ==============================================================================
# CICLO DE VIDA DE LA APLICACIÓN (LIFESPAN)
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Acciones de inicio: Inicializa la base de datos antes de escuchar peticiones.
    init_db()
    yield
    # Acciones de apagado.
    pass

# Instanciación de la API FastAPI.
app = FastAPI(title="SGM Signal Server", lifespan=lifespan)

# ==============================================================================
# DEPENDENCIAS DE AUTENTICACIÓN
# ==============================================================================
# Intercepta los encabezados HTTP para validar las llaves de acceso de los nodos.
def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# ==============================================================================
# ENDPOINTS DE GESTIÓN DE NODOS
# ==============================================================================

@app.post("/api/ping", dependencies=[Depends(verify_api_key)])
def ping(p: NodePing):
    return {"status": "pong", "uuid": p.uuid}

@app.post("/api/add", dependencies=[Depends(verify_api_key)])
def add(node: NodeAdd):
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO nodos (uuid, ip, puerto, base_folio, ultima_actualizacion) VALUES (?, ?, ?, ?, ?)",
                (node.uuid, node.ip, node.puerto, node.base_folio, datetime.now(timezone.utc))
            )
            conn.commit()
            return {"status": "added", "id": cur.lastrowid}
        except sqlite3.IntegrityError:
            # Captura conflictos de clave única  en caso de que el (UUID + base_folio) ya esté registrado.
            raise HTTPException(status_code=409, detail="Node with same UUID and base_folio already exists")

@app.post("/api/del", dependencies=[Depends(verify_api_key)])
# Cambio de modelo de datos de <<NodePing>> a <<NodeDel>>
def delete(node: NodeDel):
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM nodos WHERE uuid = ? AND base_folio = ?",
            (node.uuid, node.base_folio)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "deleted"}

@app.post("/api/act", dependencies=[Depends(verify_api_key)])
def update(node: NodeAct):
    with get_db() as conn:
        # Actualizar el nodo que coincide con uuid y base_folio
        cur = conn.execute(
            "UPDATE nodos SET ip = ?, puerto = ?, base_folio = ?, ultima_actualizacion = ? WHERE uuid = ? AND base_folio = ?",
            (node.ip, node.puerto, node.base_folio, datetime.now(timezone.utc), node.uuid, node.base_folio)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "updated"}

# Cambio de endpoint de <<show>> a <<show_by_folio>>
@app.get("/api/show_by_folio", dependencies=[Depends(verify_api_key)])
def show(base_folio: str):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT uuid, ip, puerto, base_folio, ultima_actualizacion FROM nodos WHERE base_folio = ? AND activo = 1",
            (base_folio,)
        )
        nodes = [dict(row) for row in cur.fetchall()]
    return {"nodes": nodes}

# Nuevo endpoint para listar nodos por UUID por medio de <<show_by_uuid>>
@app.get("/api/show_by_uuid", dependencies=[Depends(verify_api_key)])
def show_by_uuid(uuid: str):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT uuid, ip, puerto, base_folio, ultima_actualizacion FROM nodos WHERE uuid = ? AND activo = 1",
            (uuid,)
        )
        nodes = [dict(row) for row in cur.fetchall()]
    return {"nodes": nodes}

# ==============================================================================
# ENDPOINTS DE INFORMACIÓN GENERAL DEL SERVIDOR
# ==============================================================================

@app.get("/api/get_server_url", dependencies=[Depends(verify_api_key)])
def get_server_url():
    try:
        with open(TUNNEL_URL_FILE, "r") as f:
            url = f.read().strip()
        return {"server_url": url}
    except:
        raise HTTPException(status_code=404, detail="URL not available")

@app.get("/api/get_encrypted_url", dependencies=[Depends(verify_api_key)])
def get_encrypted_url():
    try:
        with open(TUNNEL_URL_ENC_FILE, "r") as f:
            encrypted = f.read().strip()
        return {"encrypted_url": encrypted}
    except:
        raise HTTPException(status_code=404, detail="Encrypted URL not available")

@app.get("/api/qr", dependencies=[Depends(verify_api_key)])
def qr_code():
    url_data = get_server_url()
    url = url_data["server_url"]
    # Genera la matriz de código QR a partir de la cadena de texto plano.
    img = qrcode.make(url)
    # Inicializa un flujo de bytes en memoria para no requerir almacenamiento temporal en disco físico.
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    # Transmite la imagen binaria directamente a través de HTTP streaming.
    return StreamingResponse(buf, media_type="image/png")

@app.get("/api/qr_encrypted", dependencies=[Depends(verify_api_key)])
def qr_encrypted():
    enc_data = get_encrypted_url()
    encrypted = enc_data["encrypted_url"]
    img = qrcode.make(encrypted)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.get("/api/status", dependencies=[Depends(verify_api_key)])
def status():
    tunnel_active = False
    try:
        with open(TUNNEL_URL_FILE, "r") as f:
            if f.read().strip():
                tunnel_active = True
    except:
        pass
    return {
        "server_time": datetime.now(timezone.utc).isoformat(),
        "tunnel_active": tunnel_active,
        "api_version": "1.0"
    }
