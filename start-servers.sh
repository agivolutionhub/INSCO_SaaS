#!/bin/bash

# Script para iniciar los servidores de backend y frontend del proyecto INSCO

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Iniciando servidores del proyecto INSCO ===${NC}"

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

# Iniciar el backend con Python 3.12
echo -e "${GREEN}Iniciando el servidor backend...${NC}"
cd backend
# Activar el entorno virtual
source venv/bin/activate
cd ..
python3.12 -m uvicorn backend.main:app --reload --port 8088 &
BACKEND_PID=$!

# Verificar que el backend haya iniciado correctamente
sleep 3
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${YELLOW}Error: No se pudo iniciar el servidor backend.${NC}"
    exit 1
fi

echo -e "${GREEN}Servidor backend iniciado en http://localhost:8088${NC}"

# Iniciar el frontend
echo -e "${GREEN}Iniciando el servidor frontend...${NC}"
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!

# Verificar que el frontend haya iniciado correctamente
sleep 5
if ! ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${YELLOW}Error: No se pudo iniciar el servidor frontend.${NC}"
    kill $BACKEND_PID
    exit 1
fi

echo -e "${GREEN}Servidor frontend iniciado en http://localhost:5173${NC}"
echo -e "${GREEN}=== Ambos servidores están funcionando ===${NC}"
echo -e "Presiona Ctrl+C para detener ambos servidores"

# Mantener el script ejecutándose
wait $BACKEND_PID $FRONTEND_PID 