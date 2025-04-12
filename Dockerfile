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
RUN npm run build

# Usar una imagen base de Python para el backend
FROM python:3.12-slim

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    ffmpeg \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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
RUN mkdir -p /app/storage /app/tmp

# Exponer el puerto del backend
EXPOSE 8088

# Variable de entorno para indicar que estamos en producción
ENV ENVIRONMENT=production

# Comando para iniciar el backend
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8088"] 