FROM python:3.11-slim

# Instalar dependencias esenciales del sistema (por si Rust requiere compilar componentes nativos de C)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV CARGO_HOME=/tmp/.cargo
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usar la variable $PORT que Render inyecta automáticamente
CMD ["uvicorn", "app_couple_endpoints:app", "--host", "0.0.0.0", "--port", "${PORT}"]
