FROM node:20-alpine AS frontend-builder

# Directorio de trabajo para el frontend
WORKDIR /app/frontend

# Copiar archivos de configuración y dependencias
COPY frontend/package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar el código fuente del frontend
COPY frontend/ ./

# Construir el frontend para producción
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

FROM python:3.10-slim

# Variables de entorno para la construcción
ENV DEBIAN_FRONTEND=noninteractive \
    TERM=dumb \
    PYTHONUNBUFFERED=1

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    poppler-utils \
    ffmpeg \
    fonts-liberation \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    # Herramientas de diagnóstico adicionales
    procps \
    net-tools \
    wget \
    nano \
    vim \
    htop \
    iputils-ping \
    telnet \
    netcat-openbsd \
    lsof \
    traceroute \
    dnsutils \
    iproute2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g http-server

# Directorio de trabajo
WORKDIR /app

# Copiar y instalar dependencias de Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY backend/ ./backend/

# Copiar frontend construido
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Crear solo los directorios necesarios para AutoFit
RUN mkdir -p /app/storage/autofit \
    /app/tmp \
    /app/config \
    && chmod -R 777 /app/storage /app/tmp /app/config

# Copiar script de inicio
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8088 3001
ENV ENVIRONMENT=production

# Usar script de entrada personalizado que inicia tanto frontend como backend
ENTRYPOINT ["/app/docker-entrypoint.sh"] 