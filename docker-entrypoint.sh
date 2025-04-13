#!/bin/bash
set -e

# Función para mostrar logs
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Iniciando INSCO SaaS en Docker..."

# Configurar variables de entorno
export BACKEND_PORT=${BACKEND_PORT:-8088}
export FRONTEND_PORT=${FRONTEND_PORT:-3001}

# Crear rutas iniciales
mkdir -p /app/storage/transcripts \
    /app/storage/audio \
    /app/storage/autofit \
    /app/storage/translations \
    /app/tmp/uploads \
    /app/tmp/processed \
    /app/tmp/captures \
    /app/tmp/audio \
    /app/tmp/videos

# Comprobar el archivo de credenciales
if [ ! -f "/app/config/auth_credentials.json" ]; then
    log "ADVERTENCIA: No se encontró el archivo de credenciales"
    log "Las funciones de IA podrían no estar disponibles"
fi

# Verificar la instalación de FFmpeg
if command -v ffmpeg &> /dev/null; then
    log "FFmpeg disponible: $(ffmpeg -version | head -n 1)"
else
    log "ADVERTENCIA: FFmpeg no está disponible"
fi

# Iniciar el frontend en segundo plano
log "Iniciando frontend en puerto $FRONTEND_PORT..."
cd /app/frontend
nohup http-server -p $FRONTEND_PORT dist --cors -a 0.0.0.0 > /app/frontend.log 2>&1 &
FRONTEND_PID=$!
cd /app

# Verificar que el frontend responde
log "Verificando frontend..."
for i in {1..10}; do
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null; then
        log "Frontend disponible en puerto $FRONTEND_PORT"
        break
    fi
    sleep 1
    if [ $i -eq 10 ]; then
        log "ADVERTENCIA: No se pudo verificar el frontend. Continuando de todos modos..."
    fi
done

# Iniciar el backend
log "Iniciando backend en puerto $BACKEND_PORT..."
cd /app
exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port $BACKEND_PORT --log-level info
