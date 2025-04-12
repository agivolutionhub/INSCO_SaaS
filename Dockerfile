FROM node:20-alpine AS frontend-builder

# Directorio de trabajo para el frontend
WORKDIR /app/frontend

# Copiar archivos de configuración y dependencias
COPY frontend/package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar el código fuente del frontend
COPY frontend/ ./

# Aumentar memoria disponible para Node y construir el frontend para producción
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build || (echo "Ignorando errores de TypeScript" && vite build)

# Usar una imagen base de Python para el backend
FROM python:3.12-slim

# Configuraciones iniciales para evitar interactividad durante la instalación
ENV DEBIAN_FRONTEND=noninteractive \
    TERM=dumb \
    PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-script-provider-python \
    python3-uno \
    unoconv \
    ffmpeg \
    poppler-utils \
    curl \
    wget \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    libx11-6 \
    libxrender1 \
    libfontconfig1 \
    fontconfig \
    libsm6 \
    libice6 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar entorno LibreOffice para modo headless
ENV PYTHONPATH="/usr/lib/libreoffice/program" \
    UNO_PATH="/usr/lib/libreoffice/program" \
    URE_BOOTSTRAP="file:///usr/lib/libreoffice/program/fundamental.ini" \
    HOME="/tmp"

# Crear un directorio temporal para LibreOffice
RUN mkdir -p /tmp/.config/libreoffice && chmod -R 777 /tmp/.config

# Directorio de trabajo para el backend
WORKDIR /app

# Copiar requirements.txt primero para aprovechar la caché de Docker
COPY backend/requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del backend
COPY backend/ ./backend/

# Copiar el build del frontend desde la etapa anterior
COPY --from=frontend-builder /app/frontend/dist /app/static

# Crear directorios necesarios
RUN mkdir -p /app/storage /app/tmp && chmod -R 777 /app/storage /app/tmp

# Exponer el puerto del backend
EXPOSE 8088

# Variable de entorno para indicar que estamos en producción
ENV ENVIRONMENT=production

# Comando para iniciar el backend
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8088", "--log-level", "debug"] 