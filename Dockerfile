# ==============================================================================
# DOCKERFILE PARA EL SERVIDOR DE SEÑALIZACIÓN SGM
# ==============================================================================
# Define el entorno de ejecución contenedorizado basado en Debian Slim,
# empaquetando las dependencias del sistema, librerías de Python y scripts.
# ==============================================================================

# Utiliza la imagen oficial de Python minimalista basada en Debian Bookworm.
FROM python:3.12-slim

# Establece el directorio de trabajo principal dentro del contenedor.
WORKDIR /app

# Instala los binarios del sistema requeridos para el túnel y las alertas.
# openssh-client: Cliente nativo de SSH para establecer la comunicación.
# autossh: Monitor encargado de reiniciar el túnel si la conexión cae.
# beep: Herramienta para emitir alertas acústicas a través del hardware del host.
# --no-install-recommends: Evita paquetes secundarios para mantener la imagen ligera.
# rm -rf: Limpia el caché de apt inmediatamente para reducir el tamaño de las capas de Docker.
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    autossh \
    beep \
    && rm -rf /var/lib/apt/lists/*

# Copia la lista de dependencias de Python e instala los paquetes en el entorno global.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia los archivos estrictamente necesarios para el núcleo de la aplicación.
# Se omite tunnel_manager.py y scripts experimentales, consolidando el diseño limpio.
COPY servidor.py start.sh .

# Otorga permisos de ejecución nativos al script orquestador de Bash.
RUN chmod +x start.sh

# Informa a Docker que el contenedor escuchará en el puerto 8000 en tiempo de ejecución.
EXPOSE 8000

# Define el punto de entrada principal que inicializará todo el contenedor al arrancar.
CMD ["./start.sh"]
