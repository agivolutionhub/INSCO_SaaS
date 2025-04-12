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
ENV DEBIAN_FRONTEND=noninteractive \
    TERM=dumb \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    poppler-utils \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist /app/static
RUN mkdir -p /app/storage /app/tmp && chmod -R 777 /app/storage /app/tmp

# Copiar el archivo .env (será sobrescrito por el volume mount en docker-compose)
COPY backend/config/.env /app/.env

# Configurar variables de entorno para OpenAI
ENV OPENAI_API_KEY=""
ENV OPENAI_ASSISTANT_ID=""

EXPOSE 8088
ENV ENVIRONMENT=production

# Hacer ejecutable el script de configuración de entorno
RUN chmod +x /app/backend/scripts/setup_env.py

# Ejecutar el script de configuración de entorno antes de iniciar la aplicación
CMD python3 /app/backend/scripts/setup_env.py && python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8088 --log-level debug 