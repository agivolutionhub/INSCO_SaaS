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
RUN npm run build || vite build

FROM python:3.10-slim

# Variables de entorno para la construcción
ENV DEBIAN_FRONTEND=noninteractive \
    TERM=dumb \
    PYTHONUNBUFFERED=1

# Instalar dependencias mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar y instalar dependencias de Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY backend/ ./backend/

# Copiar frontend construido
COPY --from=frontend-builder /app/frontend/dist /app/static

# Crear directorios necesarios
RUN mkdir -p /app/storage /app/tmp /app/config && chmod -R 777 /app/storage /app/tmp /app/config

EXPOSE 8088
ENV ENVIRONMENT=production

# Comando de inicio
CMD python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8088 --log-level info 