FROM python:3.12-slim

WORKDIR /app

# Instalar autossh y beep (para sonido)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    autossh \
    beep \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servidor.py tunnel_manager.py start.sh .
COPY config.env .

RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
