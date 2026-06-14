#!/usr/bin/env python3
import subprocess
import threading
import time
import re
import os
import logging
from datetime import datetime
from cryptography.fernet import Fernet

# Configuración
TUNNEL_URL_FILE = "/app/datos/tunnel_url.txt"
TUNNEL_URL_ENC_FILE = "/app/datos/tunnel_url_encrypted.txt"
LOG_FILE = "/app/datos/logs/signal.log"
SERVEO_URL_PATTERN = r'https://[a-zA-Z0-9\-]+\.(?:serveo\.net|serveousercontent\.com)'
CHECK_INTERVAL = 30
ALERT_COOLDOWN = 300

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

last_alert_time = 0
current_url = None

def alerta_visual(mensaje):
    print("\n" + "=" * 80)
    print(f"\033[91m\033[5m*** ALERTA: {mensaje} ***\033[0m")
    print("=" * 80 + "\n")
    try:
        subprocess.run(["wall", mensaje], check=False)
    except:
        pass

def alerta_sonido():
    try:
        subprocess.run(["beep", "-f", "1000", "-l", "200", "-r", "3"], check=False)
    except:
        print("\a" * 3, flush=True)

def guardar_url(url):
    global current_url
    if url == current_url:
        return
    current_url = url
    logging.info(f"Nueva URL pública: {url}")
    with open(TUNNEL_URL_FILE, "w") as f:
        f.write(url)
    # Encriptar
    key = os.getenv("ENCRYPTION_KEY")
    if key:
        try:
            fkey = Fernet(key.encode())
            encrypted = fkey.encrypt(url.encode()).decode()
            with open(TUNNEL_URL_ENC_FILE, "w") as ef:
                ef.write(encrypted)
        except Exception as e:
            logging.error(f"Error encriptando: {e}")
    # Alertar si no ha pasado mucho tiempo desde la última alerta
    global last_alert_time
    now = time.time()
    if now - last_alert_time > ALERT_COOLDOWN:
        last_alert_time = now
        alerta_visual(f"Túnel activo. URL: {url}")
        alerta_sonido()

def monitor_tunnel():
    """Lanza autossh y monitorea su salida en un hilo separado."""
    cmd = [
        "autossh", "-M", "0",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-R", "80:localhost:8000",
        "serveo.net"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, bufsize=1)
    
    def read_stderr():
        for line in iter(proc.stderr.readline, ''):
            if not line:
                break
            match = re.search(SERVEO_URL_PATTERN, line)
            if match:
                guardar_url(match.group(0))
        logging.error("El túnel se ha detenido. Se reiniciará...")
        alerta_visual("El túnel se detuvo. Reiniciando...")
        alerta_sonido()
    def read_stdout():
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            logging.debug(f"autossh stdout: {line.strip()}")

    threading.Thread(target=read_stderr, daemon=True).start()
    threading.Thread(target=read_stdout, daemon=True).start()
    return proc

if __name__ == "__main__":
    while True:
        proc = monitor_tunnel()
        proc.wait()
        proc.stdout.close()
        proc.stderr.close()
        logging.info("Reiniciando túnel en 5 segundos...")
        time.sleep(5)
