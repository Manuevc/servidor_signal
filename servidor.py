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

load_dotenv("/app/config.env")

API_KEY = os.getenv("API_KEY", "cambia_esta_clave")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
FERNET = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None
DATABASE = "/app/datos/nodos.db"
TUNNEL_URL_FILE = "/app/datos/tunnel_url.txt"
TUNNEL_URL_ENC_FILE = "/app/datos/tunnel_url_encrypted.txt"

# ---------- Modelos ----------
class NodePing(BaseModel):
    uuid: str

class NodeAdd(BaseModel):
    uuid: str
    ip: str
    puerto: int
    base_folio: str

    @field_validator('puerto')
    def puerto_valido(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError('Puerto debe estar entre 1 y 65535')
        return v

class NodeAct(NodeAdd):
    pass

# ---------- Base de datos ----------
@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nodos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                ip TEXT NOT NULL,
                puerto INTEGER NOT NULL,
                base_folio TEXT NOT NULL,
                ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activo BOOLEAN DEFAULT 1
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_base ON nodos(base_folio)')

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (opcional)
    pass

# ---------- App ----------
app = FastAPI(title="SGM Signal Server", lifespan=lifespan)

# ---------- Autenticación ----------
def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# ---------- Endpoints de nodos ----------
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
            raise HTTPException(status_code=409, detail="UUID already exists")

@app.post("/api/del", dependencies=[Depends(verify_api_key)])
def delete(node: NodePing):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM nodos WHERE uuid = ?", (node.uuid,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "deleted"}

@app.post("/api/act", dependencies=[Depends(verify_api_key)])
def update(node: NodeAct):
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE nodos SET ip = ?, puerto = ?, base_folio = ?, ultima_actualizacion = ? WHERE uuid = ?",
            (node.ip, node.puerto, node.base_folio, datetime.now(timezone.utc), node.uuid)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"status": "updated"}

@app.get("/api/show", dependencies=[Depends(verify_api_key)])
def show(base_folio: str):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT uuid, ip, puerto, ultima_actualizacion FROM nodos WHERE base_folio = ? AND activo = 1",
            (base_folio,)
        )
        nodes = [dict(row) for row in cur.fetchall()]
    return {"nodes": nodes}

# ---------- Endpoints de información del servidor ----------
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
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
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
