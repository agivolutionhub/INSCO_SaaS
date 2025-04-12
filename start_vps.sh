#!/bin/bash

# Script para iniciar los servidores de backend y frontend del proyecto INSCO en el VPS

# IP del servidor VPS
VPS_IP="147.93.85.32"

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Iniciando servidores del proyecto INSCO en VPS ($VPS_IP) ===${NC}"

# Función para verificar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar dependencias
if ! command_exists node || ! command_exists npm; then
    echo -e "${YELLOW}Se requieren Node.js y npm para ejecutar este proyecto.${NC}"
    exit 1
fi

# Comprobar que estamos en el directorio correcto
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${YELLOW}Error: Este script debe ejecutarse desde el directorio raíz del proyecto INSCO.${NC}"
    exit 1
fi

# Función para manejar la terminación del script
cleanup() {
    echo -e "\n${YELLOW}Deteniendo servidores...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit 0
}

# Capturar señales para limpiar procesos al salir
trap cleanup SIGINT SIGTERM

# Configurar URL de API para el frontend
echo -e "${GREEN}Configurando URL de la API para el frontend...${NC}"
echo "VITE_API_URL=http://$VPS_IP:8088/api" > frontend/.env
echo -e "${GREEN}✓ API URL configurada: http://$VPS_IP:8088/api${NC}"

# Iniciar el backend
echo -e "${GREEN}Iniciando el servidor backend...${NC}"
cd backend
# Activar el entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi
# Iniciar el backend usando Python con la IP externa
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8088 &
BACKEND_PID=$!
cd ..

# Verificar que el backend haya iniciado correctamente
sleep 3
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${YELLOW}Error: No se pudo iniciar el servidor backend.${NC}"
    exit 1
fi

echo -e "${GREEN}Servidor backend iniciado en http://$VPS_IP:8088${NC}"

# Iniciar el frontend
echo -e "${GREEN}Iniciando el servidor frontend...${NC}"
cd frontend
npm install
# Iniciar en modo producción con la IP del VPS
npm run build
npx serve -s dist -l 3001 --cors &
FRONTEND_PID=$!

# Verificar que el frontend haya iniciado correctamente
sleep 5
if ! ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${YELLOW}Error: No se pudo iniciar el servidor frontend.${NC}"
    kill $BACKEND_PID
    exit 1
fi

cd ..

echo -e "${GREEN}Servidor frontend iniciado en http://$VPS_IP:3001${NC}"
echo -e "${GREEN}=== Ambos servidores están funcionando en el VPS ===${NC}"
echo -e "Backend: http://$VPS_IP:8088/api/root"
echo -e "Frontend: http://$VPS_IP:3001"
echo -e "Presiona Ctrl+C para detener ambos servidores"

# Guardar PIDs para referencia
echo $BACKEND_PID > backend.pid
echo $FRONTEND_PID > frontend.pid
echo -e "${GREEN}PIDs guardados en backend.pid y frontend.pid${NC}"

# Mantener el script ejecutándose
wait $BACKEND_PID $FRONTEND_PID 