# Servidor de Señalización SGM con Serveo

Servidor central para la red SGM (Sistema de Gestión Multipropósito). Permite el registro y descubrimiento de nodos, y expone su propia URL pública mediante un túnel inverso **Serveo** con reconexión automática, alertas visuales y soporte para encriptación de la URL.

## 🚀 Características

- API REST para registrar, actualizar, eliminar y consultar nodos.
- Túnel inverso persistente con **autossh** (reconexión automática).
- Detección y notificación de cambios de URL (alertas visuales y sonoras en la consola).
- Endpoints para que los nodos obtengan la URL pública actual (texto plano, encriptada y código QR).
- Base de datos SQLite con soporte para concurrencia (modo WAL).
- Dockerizado para fácil despliegue.
- Manejo limpio de señales de terminación (SIGTERM) en contenedores.

## 📋 Requisitos previos

- Docker y Docker Compose instalados.
- El servidor debe tener **salida a internet** (puertos 22 o 443 abiertos para conexiones salientes).
- El puerto 8000 del host debe estar libre (para monitoreo local).

## 🔧 Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/servidor-signal-sgm.git
   cd servidor-signal-sgm
