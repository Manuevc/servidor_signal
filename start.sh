#!/bin/bash
set -e

cleanup() {
    echo "Recibida señal de terminación. Deteniendo procesos..."
    kill $TUNNEL_PID 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT

mkdir -p /app/datos/logs
python /app/tunnel_manager.py &
TUNNEL_PID=$!

# Esperar a que el túnel esté listo (archivo URL creado y con contenido)
echo "Esperando que el túnel esté listo..."
while ! grep -q "https://" /app/datos/tunnel_url.txt 2>/dev/null; do
    sleep 1
done
echo "Túnel listo. URL: $(cat /app/datos/tunnel_url.txt)"

exec uvicorn servidor:app --host 0.0.0.0 --port 8000
