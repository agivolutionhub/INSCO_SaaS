#!/bin/bash

# Script para desplegar el proyecto INSCO en el VPS

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Iniciando despliegue del proyecto INSCO (Versión Mínima) ===${NC}"

# Verificar si Docker y Docker Compose están instalados
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker y Docker Compose son necesarios para el despliegue.${NC}"
    echo -e "Instala Docker con:"
    echo -e "  curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    echo -e "Instala Docker Compose con:"
    echo -e "  apt-get install docker-compose-plugin"
    exit 1
fi

# Verificar que exista el archivo de credenciales JSON o crearlo si no existe
if [ ! -f "./backend/config/auth_credentials.json" ]; then
    echo -e "${YELLOW}No se encuentra el archivo de configuración. Creando uno vacío...${NC}"
    mkdir -p ./backend/config
    echo '{
  "openai": {
    "api_key": "",
    "assistant_id": ""
  }
}' > ./backend/config/auth_credentials.json
    echo -e "${GREEN}Creado archivo de credenciales vacío. Recuerda actualizarlo más tarde.${NC}"
fi

# Crear directorios necesarios
echo -e "${GREEN}Creando directorios necesarios...${NC}"
mkdir -p storage data config

# Limpiar contenedores existentes
echo -e "${GREEN}Deteniendo contenedores existentes...${NC}"
docker compose down

# Construir y desplegar los contenedores
echo -e "${GREEN}Construyendo y desplegando contenedores...${NC}"
docker compose up --build -d

# Esperar a que los contenedores estén funcionando
echo -e "${GREEN}Esperando a que los contenedores estén listos...${NC}"
sleep 10

# Verificar que los contenedores estén funcionando
if [ "$(docker ps -q -f name=insco-app)" ]; then
    echo -e "${GREEN}¡Despliegue completado con éxito!${NC}"
    
    # Verificar estado de salud del backend
    echo -e "\n${GREEN}Verificando estado de salud del backend...${NC}"
    sleep 5
    if curl -s http://localhost:8088/health | grep -q "healthy"; then
        echo -e "${GREEN}✅ Backend funcionando correctamente${NC}"
    else
        echo -e "${RED}❌ Backend no responde correctamente${NC}"
        echo -e "Verifica los logs con: docker logs insco-app"
    fi
    
    echo -e "\n${GREEN}La aplicación está disponible en:${NC}"
    echo -e "  Backend API: http://localhost:8088/api/root"
    echo -e "  Frontend: Configurado con Traefik (consulta tu panel de control)"
else
    echo -e "${RED}Error: El contenedor no se inició correctamente.${NC}"
    echo -e "Comprueba los logs con: docker compose logs"
fi 