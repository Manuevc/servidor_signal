#!/bin/bash

# ==============================================================================
# SCRIPT DE ARRANQUE NATIVO PARA EL SERVIDOR DE SEÑALIZACIÓN SGM
# ==============================================================================
# Este script actúa como el orquestador principal dentro del contenedor Docker.
# Su función es garantizar que se establezca un túnel SSH inverso persistente
# mediante Serveo, capturar la URL pública asignada dinámicamente, escribirla
# en un archivo de texto accesible para el backend de FastAPI y, finalmente,
# ceder el control del contenedor al servidor Uvicorn bajo el PID principal.
# ==============================================================================

# Detiene la ejecución del script inmediatamente si algún comando falla (retorna un estado distinto de cero).
set -e

echo "Iniciando script start.sh"

# Función de limpieza que se ejecuta al recibir señales de terminación del contenedor.
cleanup() {
    echo "Recibida señal de terminación. Matando proceso SSH..."
    # Intenta terminar el proceso del bucle del túnel SSH en segundo plano si existe.
    # Se redirige el error a /dev/null para evitar mensajes innecesarios si el proceso ya murió.
    kill $SSH_PID 2>/dev/null
    exit 0
}

# Registra la función cleanup para que intercepte las señales SIGTERM y SIGINT enviadas por Docker.
trap cleanup SIGTERM SIGINT

# Asegura la existencia del directorio persistente para almacenar los registros de auditoría.
mkdir -p /app/datos/logs
echo "Directorio de logs creado"

# Limpia el archivo de URL anterior para evitar confusiones
> /app/datos/tunnel_url.txt

# Función interna que encapsula el bucle infinito encargado de mantener el túnel activo.
run_tunnel() {
    while true; do
        echo "Intentando establecer túnel Serveo..."
        
        # Inicia la conexión SSH inversa hacia Serveo en segundo plano.
        # -o StrictHostKeyChecking=no: Evita la confirmación interactiva de la huella digital del servidor.
        # -o UserKnownHostsFile=/dev/null: No almacena la llave del host remoto en el sistema local.
        # -o ServerAliveInterval=60: Envía un paquete de control cada 60 segundos para mantener vivo el socket.
        # -R 80:localhost:8000: Mapea el puerto remoto 80 de Serveo al puerto local 8000 de FastAPI.
        # 2>&1: Redirige el flujo de error estándar (stderr) hacia la salida estándar (stdout) para poder procesarlo en la tubería.
        ssh -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -o ServerAliveInterval=60 \
            -R 80:localhost:8000 \
            serveo.net 2>&1 | while IFS= read -r line; do
                
                # Imprime en la consola del contenedor cada línea recibida de la conexión SSH.
                echo "$line"
                
                # Evalúa mediante una expresión regular si la línea contiene la URL pública asignada por Serveo.
		if [[ "$line" =~ Forwarding\ HTTP\ traffic\ from\ (https://[^[:space:]]+) ]]; then
                    # Almacena en la variable la coincidencia exacta encontrada por la expresión regular.
                    url="${BASH_REMATCH[1]}"
                    
                    # Sobrescribe el archivo de texto con la nueva URL pública para que esté disponible para los nodos.
                    echo "$url" > /app/datos/tunnel_url.txt
                    echo "URL encontrada: $url"
                fi
            done
            
        # Si el flujo de la tubería se rompe, significa que el comando SSH ha finalizado por desconexión.
        # Se registra el evento con fecha y hora en el archivo de historial de fallas.
        echo "Túnel caído, reintentando en 5 segundos..." >> /app/datos/tunnel.log
        
        # Pausa de cortesía obligatoria antes de iniciar una nueva solicitud para evitar saturar el procesador y el servidor remoto.
        sleep 5
    done
}

# Lanza la función del túnel de forma asíncrona en un hilo separado en segundo plano.
run_tunnel &

# Captura inmediatamente el Identificador de Proceso (PID) del último subproceso lanzado en segundo plano.
SSH_PID=$!
echo "Túnel lanzado con PID $SSH_PID"

echo "Esperando URL..."

# Bucle de sincronización: detiene el script principal hasta que el archivo contenga una URL válida.
# grep -q: Opera en modo silencioso, devolviendo éxito (estado 0) en cuanto encuentra el patrón.
while ! grep -qE "https://[a-f0-9]{16}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}\.(serveo\.net|serveousercontent\.com)" /app/datos/tunnel_url.txt 2>/dev/null; do
    # Espera un segundo entre verificaciones para no saturar las operaciones de lectura/escritura en disco.
    sleep 1
done

# Recupera la URL verificada del archivo de texto para confirmarla en la salida de consola.
URL=$(cat /app/datos/tunnel_url.txt)
echo "Túnel listo. URL: $URL"

# Reemplaza el proceso actual del intérprete de comandos Bash por el servidor Uvicorn.
# Esto convierte a Uvicorn en el PID 1, permitiéndole recibir directamente las señales del ciclo de vida de Docker.
exec uvicorn servidor:app --host 0.0.0.0 --port 8000
