#!/bin/bash

# Script para iniciar los servidores de INSCO en segundo plano (optimizado para systemd)

# IP del servidor VPS
VPS_IP="147.93.85.32"

# Configurar directorio
cd /INSCO_SaaS

# Configurar URL de API para el frontend
echo "VITE_API_URL=http://$VPS_IP:8088/api" > frontend/.env
echo "Configurada API URL: http://$VPS_IP:8088/api"

# Iniciar el backend
cd backend
# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Comprobar dependencias
pip install -r requirements.txt

# Iniciar uvicorn para el backend
python -m uvicorn main:app --host 0.0.0.0 --port 8088 &
BACKEND_PID=$!
echo "Backend iniciado con PID: $BACKEND_PID"
echo $BACKEND_PID > /INSCO_SaaS/backend.pid
cd ..

# Esperar a que el backend esté disponible
echo "Esperando a que el backend esté disponible..."
for i in {1..30}; do
    if curl -s http://localhost:8088/api/root > /dev/null; then
        echo "Backend disponible"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Backend no disponible después de 30 intentos"
        exit 1
    fi
    sleep 1
done

# Iniciar el frontend
cd frontend
npm install
npm run build
npx serve -s dist -l 3001 --cors &
FRONTEND_PID=$!
echo "Frontend iniciado con PID: $FRONTEND_PID"
echo $FRONTEND_PID > /INSCO_SaaS/frontend.pid
cd ..

# Verificar que ambos servicios están activos
if ! ps -p $BACKEND_PID > /dev/null || ! ps -p $FRONTEND_PID > /dev/null; then
    echo "ERROR: Al menos uno de los servicios no está funcionando"
    exit 1
fi

echo "INSCO SaaS iniciado correctamente en modo servicio"
echo "Backend: http://$VPS_IP:8088/api/root"
echo "Frontend: http://$VPS_IP:3001"

# Mantenerse en primer plano para systemd
# No usar wait, ya que systemd necesita que el proceso principal se mantenga
# Crear un archivo para indicar que está corriendo
touch /INSCO_SaaS/insco.running

# Bucle infinito con comprobación de estado
while true; do
    if ! ps -p $BACKEND_PID > /dev/null; then
        echo "ADVERTENCIA: Backend caído, reiniciando..."
        cd backend
        python -m uvicorn main:app --host 0.0.0.0 --port 8088 &
        BACKEND_PID=$!
        echo $BACKEND_PID > /INSCO_SaaS/backend.pid
        cd ..
    fi
    
    if ! ps -p $FRONTEND_PID > /dev/null; then
        echo "ADVERTENCIA: Frontend caído, reiniciando..."
        cd frontend
        npx serve -s dist -l 3001 --cors &
        FRONTEND_PID=$!
        echo $FRONTEND_PID > /INSCO_SaaS/frontend.pid
        cd ..
    fi
    
    sleep 30
done 