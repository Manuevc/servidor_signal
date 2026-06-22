#!/bin/bash

# ==============================================================================
# SCRIPT DE ARRANQUE NATIVO PARA EL SERVIDOR DE SEÑALIZACIÓN SGM
# ==============================================================================
# Este script actúa como el orquestador principal dentro del contenedor Docker.
# Su función es:
#   1. Cargar la configuración desde /app/config.env.
#   2. Establecer un túnel SSH inverso persistente con Serveo (dominio
#      personalizado o aleatorio según configuración).
#   3. Capturar la URL pública asignada dinámicamente y escribirla en
#      /app/datos/tunnel_url.txt para que el backend de FastAPI la consuma.
#   4. Iniciar el servidor Uvicorn como proceso principal (PID 1).
# ==============================================================================

# Detiene la ejecución si algún comando falla.
set -e

echo "Iniciando script start.sh"

# -----------------------------------------------------------------------------
# CARGA DE VARIABLES DE ENTORNO
# -----------------------------------------------------------------------------
# Carga las variables definidas en /app/config.env (API_KEY, ENCRYPTION_KEY,
# SERVEO_DOMAIN, SERVEO_SSH_KEY_PATH, SERVEO_SSH_KEY_FINGERPRINT).
if [ -f /app/config.env ]; then
    set -a                # Exporta automáticamente las variables asignadas
    source /app/config.env
    set +a
    echo "Archivo config.env cargado correctamente."
else
    echo "ADVERTENCIA: No se encontró /app/config.env. Usando valores por defecto."
fi

# -----------------------------------------------------------------------------
# FUNCIÓN DE LIMPIEZA (para terminación graceful)
# -----------------------------------------------------------------------------
cleanup() {
    echo "Recibida señal de terminación. Matando proceso SSH..."
    # Intenta matar el proceso del túnel; si ya no existe, no falla (|| true)
    kill $SSH_PID 2>/dev/null || true
    exit 0
}
# Registra la función para SIGTERM y SIGINT (señales enviadas por Docker)
trap cleanup SIGTERM SIGINT

# -----------------------------------------------------------------------------
# CREAR DIRECTORIOS Y LIMPIEZA INICIAL
# -----------------------------------------------------------------------------
mkdir -p /app/datos/logs
echo "Directorio de logs creado"

# Limpia el archivo de URL anterior para evitar confusiones
> /app/datos/tunnel_url.txt

# -----------------------------------------------------------------------------
# VALIDACIÓN DE CONFIGURACIÓN INCOMPLETA (ANTES DE DECIDIR MODO)
# -----------------------------------------------------------------------------
if [ -n "$SERVEO_DOMAIN" ] || [ -n "$SERVEO_SSH_KEY_PATH" ]; then
    if [ -z "$SERVEO_DOMAIN" ] || [ -z "$SERVEO_SSH_KEY_PATH" ]; then
        echo "ERROR: Configuración de dominio personalizado incompleta."
        echo "Se requieren SERVEO_DOMAIN y SERVEO_SSH_KEY_PATH."
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE DOMINIO PERSONALIZADO (OPCIONAL)
# -----------------------------------------------------------------------------
# Si se definen SERVEO_DOMAIN y SERVEO_SSH_KEY_PATH, se usa el modo avanzado
# con dominio propio. De lo contrario, se usa el modo gratuito con URL aleatoria.
if [ -n "$SERVEO_DOMAIN" ] && [ -n "$SERVEO_SSH_KEY_PATH" ]; then
    echo "Configuración de dominio personalizado detectada: $SERVEO_DOMAIN"
    echo "Ruta de llave SSH: $SERVEO_SSH_KEY_PATH"

    # Verificar que la llave exista
    if [ ! -f "$SERVEO_SSH_KEY_PATH" ]; then
        echo "ERROR: No se encontró la llave SSH en $SERVEO_SSH_KEY_PATH"
        exit 1
    fi

    # Verificar y FORZAR permisos correctos (600 o 400)
    PERMS=$(stat -c "%a" "$SERVEO_SSH_KEY_PATH" 2>/dev/null || stat -f "%Lp" "$SERVEO_SSH_KEY_PATH" 2>/dev/null)
    if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ]; then
        echo "ADVERTENCIA: La llave SSH tiene permisos $PERMS. Ajustando a 600 automáticamente..."
        chmod 600 "$SERVEO_SSH_KEY_PATH"
    fi

    # Verificar que el fingerprint esté configurado (solo como recordatorio)
    if [ -n "$SERVEO_SSH_KEY_FINGERPRINT" ]; then
        echo "Huella de llave configurada: $SERVEO_SSH_KEY_FINGERPRINT"
    else
        echo "ADVERTENCIA: No se configuró SERVEO_SSH_KEY_FINGERPRINT."
        echo "Asegúrate de agregar el registro TXT en DNS con la huella correcta."
    fi

    # Construir comando SSH para dominio personalizado
    SSH_CMD="ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=30 \
        -i $SERVEO_SSH_KEY_PATH \
        -R $SERVEO_DOMAIN:80:localhost:8000 \
        serveo.net"

    # Patrón de URL para esperar (dominio personalizado, literal)
    URL_PATTERN="https://$SERVEO_DOMAIN"
else
    echo "Usando configuración estándar (dominio aleatorio de Serveo)."

    # Construir comando SSH para dominio aleatorio (plan gratuito)
    SSH_CMD="ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=30 \
        -R 80:localhost:8000 \
        serveo.net"

    # Patrón de URL para esperar (formato hash-IP, expresión regular extendida)
    URL_PATTERN="https://[a-f0-9]{16}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}\.(serveo\.net|serveousercontent\.com)"
fi

# -----------------------------------------------------------------------------
# FUNCIÓN QUE EJECUTA EL TÚNEL (BUCLE INFINITO DE RECONEXIÓN)
# -----------------------------------------------------------------------------
run_tunnel() {
    while true; do
        echo "Intentando establecer túnel Serveo..."

        # Ejecutar el comando SSH y procesar cada línea de salida
        eval "$SSH_CMD" 2>&1 | while IFS= read -r line; do
            echo "$line"

            # Capturar la URL cuando Serveo emita "Forwarding HTTP traffic from"
            if [[ "$line" =~ Forwarding\ HTTP\ traffic\ from\ (https://[^[:space:]]+) ]]; then
                url="${BASH_REMATCH[1]}"
                echo "$url" > /app/datos/tunnel_url.txt
                echo "URL encontrada: $url"
            fi

            # Detectar errores de SSH para salir o reintentar con mensaje claro
            if [[ "$line" =~ "Permission denied" ]] || [[ "$line" =~ "No TXT record" ]] || [[ "$line" =~ "Could not resolve hostname" ]]; then
                echo "ERROR: Fallo en la conexión SSH: $line"
                echo "Revisa tu configuración de llave, DNS o credenciales."
                # Podemos salir con código de error para que Docker reinicie el contenedor
                exit 1
            fi
        done

        # Si el bucle sale (por caída del túnel), registrar el evento y reintentar
        echo "Túnel caído, reintentando en 5 segundos..." >> /app/datos/tunnel.log
        sleep 5
    done
}

# -----------------------------------------------------------------------------
# INICIAR EL TÚNEL EN SEGUNDO PLANO
# -----------------------------------------------------------------------------
run_tunnel &
SSH_PID=$!
echo "Túnel lanzado con PID $SSH_PID"

# -----------------------------------------------------------------------------
# ESPERAR URL VÁLIDA (UNIFICADO)
# -----------------------------------------------------------------------------
echo "Esperando URL..."
TIMEOUT=60
SECONDS=0
if [ -n "$SERVEO_DOMAIN" ] && [ -n "$SERVEO_SSH_KEY_PATH" ]; then
    while ! grep -q "$URL_PATTERN" /app/datos/tunnel_url.txt 2>/dev/null; do
        if [ $SECONDS -ge $TIMEOUT ]; then
            echo "ERROR: Tiempo de espera agotado (${TIMEOUT}s) sin recibir URL."
            echo "Revisa la conexión SSH, DNS o la configuración de Serveo."
            exit 1
        fi
        sleep 1
    done
else
    while ! grep -qE "$URL_PATTERN" /app/datos/tunnel_url.txt 2>/dev/null; do
        if [ $SECONDS -ge $TIMEOUT ]; then
            echo "ERROR: Tiempo de espera agotado (${TIMEOUT}s) sin recibir URL."
            echo "Revisa la conexión SSH o la disponibilidad de Serveo."
            exit 1
        fi
        sleep 1
    done
fi

# -----------------------------------------------------------------------------
# INICIAR EL SERVIDOR FASTAPI (COMO PROCESO PRINCIPAL)
# -----------------------------------------------------------------------------
# Reemplaza el script actual por Uvicorn, convirtiéndolo en PID 1.
exec uvicorn servidor:app --host 0.0.0.0 --port 8000
