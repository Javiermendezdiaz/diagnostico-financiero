FROM python:3.11-slim

# Instalar dependencias esenciales del sistema (por si Rust requiere compilar componentes nativos de C)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pre-crear la ruta de CARGO con permisos para evitar "os error 30" en tiempo de compilación
RUN mkdir -p /tmp/.cargo && chmod 777 /tmp/.cargo

ENV CARGO_HOME=/tmp/.cargo
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usar la variable $PORT que Render inyecta automáticamente (shell format para expansión)
CMD uvicorn app_couple_endpoints:app --host 0.0.0.0 --port $PORT
