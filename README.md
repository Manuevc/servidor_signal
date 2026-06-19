# Servidor de Señalización con Serveo para SGM (Sistema de Gestión Multipropósito)

Este proyecto provee una API centralizada basada en FastAPI para coordinar y registrar la comunicación entre múltiples nodos de una red para un sistema propio llamado (SGM). Además, incluye un mecanismo automatizado en segundo plano que expone el servidor local a internet mediante un túnel seguro y gratuito de Serveo, generando accesos directos y códigos QR dinámicos.

---

## Requisitos Previos

Antes de comenzar, asegúrese de tener instaladas las siguientes herramientas en su sistema operativo:

1. Sistema operativo Linux basado en Ubuntu.
2. Docker: Plataforma para empaquetar y ejecutar aplicaciones en contenedores aislados.
3. Docker Compose: Herramienta para definir y correr aplicaciones Docker de múltiples contenedores.
4. Python: Lenguaje de programación de alto nivel. Se requiere para acciones mínimas de configuración (por defecto Linux tiene una versión de Python instalada).

### ¿Cómo saber si tengo Docker instalado?

Abra una terminal y ejecute los siguientes comandos. Ambos deberían devolverte una versión de texto (ej. Docker version 24.0).

```
docker --version
docker compose version
```

Por ejemplo, le debería entregar algunos resultados similares a los siguientes:

```
usuario@maquina ~ docker --version
Docker version 29.5.3, build d1c06ef
usuario@maquina ~ docker compose version
Docker Compose version v5.1.4
```

Si no los tiene le recomendamos visitar la página oficial de docker para instalar los repositorios más recientes.

---

## Guía de Configuración

Siga estas instrucciones en orden secuencial para configurar el servidor en su máquina.

### Paso 1. Descargue los archivos del proyecto.

1. Descargue los archivos comprimidos (.zip) del proyecto desde: [https://github.com/Manuevc/servidor_signal.git](https://github.com/Manuevc/servidor_signal.git).
2. Guarde los archivos en el directorio de su preferencia.
3. Descomprima los archivos por medio de su Explorador de Archivos.

Se recomienda nombrar el directorio como: *servidor_signal*, pero puede elegir el nombre de su preferencia. A partir de este punto nos referiremos al directorio creado como *directorio local*.

### Paso 2. Abra el directorio local del proyecto en la terminal.

1. Abra una terminal.
2. Diríjase al directorio local. Utilice los comandos
```
ls
```
para ver el contenido del directorio y
```
cd nombre_carpeta
```
para entrar en los directorios. Para retroceder, utilice el comando
```
cd ..
```
(con dos puntos seguidos).

En la terminal debe ser capaz de ver el conjunto de archivos que descargó (no el archivo comprimido porque en el Paso 1 ya los descomprimió).

### Paso 3. Crear y configurar el archivo de configuración (config.env).

1. Ejecute el comando 
```
ls
```
para que observe el contenido del directorio local. En éste podrá observar un archivo llamado *config.env.example*.

2. Copie el archivo ejecutando el siguiente comando: 
```
cp config.env.example config.env
```
. Si vuelve a ejecutar el comando
```
ls
```
podrá observar que se creó el archivo *config.env*.

3. Genere una API_KEY aleatoria ejecutando el siguiente comando:
```
python -c "import secrets; print(secrets.token_hex(32))"
```

4. Genere una ENCRIPTION_KEY aleatoria ejecuntando el siguiente comando:
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

5. Edite el archivo de configuración. Abra la interfaz de *nano* para editar el archivo ejecutando el comando:
```
nano config.env
```

6. Una vez abierto el archivo de configuración *config.env* en la interfaz de *nano*, copie el API_KEY generado anteriormente en el campo de mismo nombre.
7. También copie el ENCRIPTION_KEY generado anteriormente en el campo de mismo nombre, o en su defecto déjelo vacío. Se recomienda agregar la clave de encriptación para comunicación encriptada, pero puede probar sin encriptación.
8. Guarde el archivo de configuración presionando la combinación de teclas 
```
Ctrl + o
```
para guardar (presione Enter para confirmar el nombre del archivo) y 
```
Ctrl + x
```
para cerrar la interfaz de nano.

---

## Guía de Despliegue del Servidor

Siga estas instrucciones en orden secuencial para levantar el contenedor y desplegar el servidor.

### Paso 4. Levantar el contenedor.

1. Ejecute el siguiente comando para levantar el contenedor: 
```
docker compose up -d --build
```

Podrá observar que Docker descargará la imagen base de Python e instalará las librerías necesarias a partir de las versiones especificadas en *requirements.txt*. El parámetro *-d* garantiza que el servicio corra en modo asíncrono para liberar la terminal inmediatamente.

### Paso 5. Verificar la URL Pública Asignada.

1. Ejecute el siguiente comando para ver los logs del contenedor:
```
docker logs -f sgm-signal
```
2. Cierre los logs cuando ya no necesite verlos ejecutando la combinación de teclas:
```
Ctrl + c
```

El contenedor iniciará un proceso SSH nativo en segundo plano que solicitará un túnel dinámico hacia los servidores de Serveo (serveo.net). Para visualizar la URL pública que se ha asignado al servidor, puede inspeccionar los logs desplegados en el comando anterior. Verá un mensaje similar al siguiente:

```
Iniciando script start.sh
Directorio de logs creado
Túnel lanzado con PID 7
Esperando URL...
Intentando establecer túnel Serveo...
Túnel listo. URL: https://9cc624897225fc85-177-226-169-30.serveousercontent.com
Pseudo-terminal will not be allocated because stdin is not a terminal.
Warning: Permanently added 'serveo.net' (RSA) to the list of known hosts.
Forwarding HTTP traffic from https://bb4d6b616adb4502-177-226-169-30.serveousercontent.com
URL encontrada: https://bb4d6b616adb4502-177-226-169-30.serveousercontent.com
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

```

---

## Algunos comandos de utilidad.

### Detener el servidor.

* Ejecute el siguiente comando: 
```
docker compose down
```

### Ver los contenedores levantados.

* Ejecute el siguiente comando: 
```
docker ps
```

### Limpiar la terminal.
 
* Ejecute el siguiente comando:
```
clear
```

---

## Estructura de Endpoints de la API

Todas las peticiones (salvo que se indique lo contrario) requieren obligatoriamente incluir un encabezado HTTP de autenticación llamado X-API-Key provisto con el valor exacto de su variable API_KEY.

### Gestión de Nodos (POST).

* **/api/ping**: Comprobación básica de latencia para verificar el estado de conexión de un nodo.
* **/api/add**: Registra un nuevo nodo en la base de datos interna SQLite (nodos.db). Almacena su uuid, dirección ip, puerto y base_folio. La combinación **uuid + base_folio** debe ser única.
* **/api/act**: Actualiza los parámetros de red o folios de un nodo existente. Para identificar el nodo, se requiere enviar tanto el **uuid** como el **base_folio** actuales.
* **/api/del**: Remueve permanentemente a un nodo del directorio activo de señalización. Para eliminar, se requiere enviar tanto el **uuid** como el **base_folio** del nodo.

### Consultas e información (GET).

* **/api/show_by_folio?base_folio=VALOR**: Retorna la lista de todos los nodos activos vinculados a un `base_folio` específico (puede haber varios con el mismo base_folio pero distinto uuid).
* **/api/show_by_uuid?uuid=VALOR**: Retorna la lista de todos los nodos activos que coinciden con un `uuid` dado (puede haber varios con el mismo uuid pero distinto base_folio).
* **/api/status**: Devuelve métricas generales del estado del servidor, la hora del sistema en formato UTC y si el túnel inverso permanece activo.
* **/api/get_server_url**: Devuelve la URL pública actual del túnel en formato de texto plano.
* **/api/get_encrypted_url**: Devuelve la URL pública encriptada de forma simétrica a través del algoritmo Fernet (requiere haber configurado una ENCRYPTION_KEY válida).

## Ejemplos explícitos de uso.

Para los siguientes ejemplos de uso, supóngase los siguientes valores aleatorios. *Nota: NO UTILICE ESTOS VALORES EN SU ARCHIVO DE CONFIGURACIÓN*.

* URL: https://abcd1234.serveousercontent.com.
* API_KEY: MiApiKeySecreta123456 (puede ser cualquiera, o una generada aleatoriamente).
* ENCRIPTION_KEY: MiEncriptionKey123456 (solamente pueden ser aquellas generadas por el código del Paso 3, o en su defecto deje vacío este campo en el archivo de configuración).

Nota: Si se está probando localmente (sin túnel) en el mismo servidor, puede sustituir la URL por http://localhost:8000. Si está utilizando una máquina externa pero en la misma red que el servidor, entonces puede sustituir la URL por la IP del servidor, por ejemplo http://192.168.1.2:8000. En ambos casos de prueba local, mantenga el puerto 8000 o cámbielo dentro del archivo start.sh de acuerdo a sus necesidades.

### Ejemplos básicos de autenticación (sólo API_KEY):

Todos estos endpoints requieren el encabezado **X-API-Key**.

#### Comprobación de respuesta del servidor (/api/ping):

Ejecute:

```
curl -X POST https://abcd1234.serveousercontent.com/api/ping \
  -H "X-API-Key: mi_api_key_secreta_123456" \
  -H "Content-Type: application/json" \
  -d '{"uuid": "nodo_001"}'
```

Respuesta esperada:

```
{"status":"pong","uuid":"nodo_001"}
```

#### Registrar un nuevo nodo (/api/add):

Ejecute:

```
curl -X POST https://abcd1234.serveousercontent.com/api/add \
  -H "X-API-Key: mi_api_key_secreta_123456" \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "nodo_001",
    "ip": "192.168.1.100",
    "puerto": 8080,
    "base_folio": "FOLIO_A"
  }'
```

Respuesta esperada:

```
{"status":"added","id":1}
```

#### Actualizar los datos de un nodo existente (/api/act):

Ejecute:

```
curl -X POST https://abcd1234.serveousercontent.com/api/act \
  -H "X-API-Key: mi_api_key_secreta_123456" \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "nodo_001",
    "ip": "192.168.1.200",
    "puerto": 9090,
    "base_folio": "FOLIO_B"
  }'
```

Respuesta esperada:

```
{"status":"updated"}
```


**Nota**: Si se cambia el `base_folio`, la nueva combinación `(uuid, base_folio)` debe ser única; de lo contrario, se producirá un error de conflicto (409).

#### Eliminar un nodo (/api/del):

Ejecute:

```
curl -X POST https://abcd1234.serveousercontent.com/api/del \
  -H "X-API-Key: mi_api_key_secreta_123456" \
  -H "Content-Type: application/json" \
  -d '{"uuid": "nodo_001", "base_folio": "FOLIO_B"}'
```

Respuesta esperada:

```
{"status":"deleted"}
```

#### Consultar nodos activos por base_folio (/api/show_by_folio)

Devuelve todos los nodos activos que tengan el `base_folio` especificado (puede haber varios con el mismo uuid pero distinto base_folio).

Ejecute:

```
curl -X GET "https://abcd1234.serveousercontent.com/api/show_by_folio?base_folio=FOLIO_B" \
  -H "X-API-Key: mi_api_key_secreta_123456"
```

Respuesta esperada:

```
{
  "nodes": [
    {
      "uuid": "nodo_001",
      "ip": "192.168.1.200",
      "puerto": 9090,
      "base_folio": "FOLIO_B",
      "ultima_actualizacion": "2026-06-16 10:30:00"
    }
  ]
}
```

#### Consultar nodos activos por UUID (/api/show_by_uuid)

Devuelve todos los nodos activos que tengan el `uuid` especificado (puede haber varios con el mismo uuid pero distinto base_folio).

Ejecute:

```
curl -X GET "https://abcd1234.serveousercontent.com/api/show_by_uuid?uuid=nodo_001" \
  -H "X-API-Key: mi_api_key_secreta_123456"
```

Respuesta esperada:
```
{
  "nodes": [
    {
      "uuid": "nodo_001",
      "ip": "192.168.1.200",
      "puerto": 9090,
      "base_folio": "FOLIO_B",
      "ultima_actualizacion": "2026-06-16 10:30:00"
    }
  ]
}
```


#### Obtener estado del servidor (/api/status):

Ejecute:

```
curl -X GET https://abcd1234.serveousercontent.com/api/status \
  -H "X-API-Key: mi_api_key_secreta_123456"
```

Respuesta esperada:

```
{
  "server_time": "2026-06-16T10:30:00+00:00",
  "tunnel_active": true,
  "api_version": "1.0"
}
```

#### Obtener la URL pública del túnel (/api/get_server_url):

Ejecute:

```
curl -X GET https://abcd1234.serveousercontent.com/api/get_server_url \
  -H "X-API-Key: mi_api_key_secreta_123456"
```

Respuesta esperada:

```
{"server_url":"https://abcd1234.serveousercontent.com"}
```

#### Generar un código QR con la URL pública (/api/qr):

Este endpoint devuelve una imagen PNG. Puede guardarla con el comando siguiente

```
curl -X GET https://abcd1234.serveousercontent.com/api/qr \
  -H "X-API-Key: mi_api_key_secreta_123456" \
  --output qr_server.png
```

### Ejemplos con encriptación de la URL (requiere ENCRIPTION_KEY):

Si se configura una clave de encriptación simétrica, el servidor puede entregar la URL pública cifrada, de modo que solo los clientes que posean la misma clave puedan descifrarla.

#### Obtener la URL encriptada (/api/get_encrypted_url):

Ejecute:

```
curl -X GET https://abcd1234.serveousercontent.com/api/get_encrypted_url \
  -H "X-API-Key: mi_api_key_secreta_123456"
```

Respuesta esperada:

```
{"encrypted_url":"gAAAAABm... (cadena larga encriptada)"}
```

#### Generar un código QR con la URL encriptada (/api/qr_encrypted):

Este QR contiene la URL cifrada. Al escanearlo, el cliente deberá descifrarla con la misma clave.

```
curl -X GET https://abcd1234.serveousercontent.com/api/qr_encrypted \
  -H "X-API-Key: mi_api_key_secreta_123456" \
  --output qr_encrypted.png
```

### ¿Cómo descifrar la URL del cliente?

Si el cliente está escrito en Python, puedes usar cryptography para descifrar:

```
from cryptography.fernet import Fernet

encrypted_url = "gAAAAABm..."   # cadena obtenida del endpoint
key = "clave_simetrica_generada"   # la misma ENCRYPTION_KEY

cipher = Fernet(key.encode())
decrypted_url = cipher.decrypt(encrypted_url.encode()).decode()
print(decrypted_url)  # Muestra la URL pública real
```

Esto permite distribuir la URL de forma segura, por ejemplo, a través de un código QR que solo los nodos autorizados puedan interpretar.

### Notas:

* Todas las peticiones deben incluir el encabezado X-API-Key. Sin él, el servidor responde con *401 Unauthorized*.
* La URL pública cambia cada vez que el túnel se reinicia (por ejemplo, al levantar el contenedor). Por eso es importante que los nodos consulten periódicamente /api/get_server_url o /api/get_encrypted_url para conocer la dirección actual. Esto solamente ocurre en la versión gratuita. Si está pagando por usar Serveo, entonces no sucederá.
* El puerto del nodo debe estar en el rango 1‑65535, validado automáticamente por Pydantic.
* * Los campos `uuid` y `base_folio` son textos libres. **La combinación de ambos debe ser única**; es decir, no puede haber dos nodos con el mismo `uuid` y el mismo `base_folio` simultáneamente. Esto permite que un mismo `uuid` pueda aparecer en diferentes `base_folio` sin conflicto.

---

## Resolución de problemas frecuentes

Si el sistema no arranca o si se experimentan anomalías en los flujos de red, localiza el origen del inconveniente según las siguientes categorías:

### 1. Errores de Red y Desconexiones del Túnel (serveo.net).

* **Síntoma**: Los logs muestran constantemente el mensaje "Túnel caído, reintentando en 5 segundos..." o la conexión tarda demasiado en establecerse.
* **Causa**: Serveo es un servicio gratuito de uso compartido. Si solicitas el puerto remoto 80 de manera reiterada, el balanceador de carga del servidor remoto puede bloquear temporalmente tu IP pública por exceso de peticiones o conflicto de sockets.
* **Solución**: El archivo start.sh está diseñado para reintentar la conexión de forma infinita y automática. Si el bloqueo persiste, puedes detener por completo los contenedores con "docker compose down", esperar unos minutos para que expire tu sesión en los servidores remotos de Serveo y volver a levantarlo.

### 2. Fallos del Entorno de Contenedores (Docker / Compose)

* **Síntoma**: El comando "docker compose up" arroja errores de sintaxis, problemas con los demonios o fallos al compilar el volumen "./datos".
* **Solución**: Estos problemas son ajenos al código fuente de este proyecto y competen a la instalación de Docker en tu sistema anfitrión.
   * Para problemas relacionados con permisos de sockets, volúmenes de Linux o instalación de Docker de escritorio, dirígete directamente a la Documentación Oficial de Soporte de Docker (https://docs.docker.com/).
   * Si experimentas errores de sintaxis en las directivas del archivo de orquestación, acude a la Guía de Referencia de Docker Compose (https://docs.docker.com/compose/).

### 3. Excepciones de Código y Módulos de Python.

* **Síntoma**: Excepciones internas en el manejo de peticiones asíncronas, validaciones fallidas de modelos Pydantic o errores de bases de datos relacionales en el archivo servidor.py.
* **Solución**: Si necesitas validar el comportamiento nativo de los módulos integrados que componen el backend, puedes consultar sus respectivos portales de soporte comunitario:
   * Para el ruteo de la API, lifespans y dependencias: Documentación de FastAPI (https://fastapi.tiangolo.com/).
   * Para esquemas de validación de puertos y campos binarios: Soporte de Pydantic (https://docs.pydantic.dev/).
   * Para la suite de servidores ASGI que procesa la aplicación: Portal de Uvicorn (https://www.uvicorn.org/).


