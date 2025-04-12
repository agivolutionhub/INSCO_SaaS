#!/bin/bash

# Script para desplegar el proyecto INSCO en el VPS

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Iniciando despliegue del proyecto INSCO ===${NC}"

# Verificar si Docker y Docker Compose están instalados
if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker y Docker Compose son necesarios para el despliegue.${NC}"
    echo -e "Instala Docker con:"
    echo -e "  curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    echo -e "Instala Docker Compose con:"
    echo -e "  apt-get install docker-compose-plugin"
    exit 1
fi

# Verificar que exista el archivo de credenciales JSON
if [ ! -f "./backend/config/auth_credentials.json" ]; then
    echo -e "${RED}Error: No se encuentra el archivo de configuración en backend/config/auth_credentials.json${NC}"
    echo -e "Crea el archivo con la siguiente estructura:"
    echo -e '{
  "openai": {
    "api_key": "tu_api_key",
    "assistant_id": "tu_assistant_id"
  }
}'
    exit 1
fi

# Crear directorios necesarios
echo -e "${GREEN}Creando directorios necesarios...${NC}"
mkdir -p storage data config

# Limpiar contenedores existentes
echo -e "${GREEN}Deteniendo contenedores existentes...${NC}"
docker-compose down

# Construir y desplegar los contenedores
echo -e "${GREEN}Construyendo y desplegando contenedores...${NC}"
docker-compose up --build -d

# Esperar a que los contenedores estén funcionando
echo -e "${GREEN}Esperando a que los contenedores estén listos...${NC}"
sleep 10

# Verificar que los contenedores estén funcionando
if [ "$(docker ps -q -f name=insco-app)" ]; then
    echo -e "${GREEN}¡Despliegue completado con éxito!${NC}"
    
    # Verificar si OpenAI está configurado
    OPENAI_CONFIGURED=$(docker exec insco-app bash -c "grep -q api_key /app/config/auth_credentials.json && echo 'true' || echo 'false'")
    if [ "$OPENAI_CONFIGURED" = "true" ]; then
        echo -e "${GREEN}✅ API de OpenAI configurada correctamente${NC}"
    else
        echo -e "${YELLOW}⚠️ La API de OpenAI no está configurada. Las funciones de IA no estarán disponibles.${NC}"
    fi
    
    echo -e "${GREEN}La aplicación está disponible en:${NC}"
    echo -e "  http://localhost:8088 (acceso directo)"
    echo -e "  URL de EasyPanel (consulta tu panel de control)"
    
    # Verificar estado de salud del backend
    echo -e "\n${GREEN}Verificando estado de salud del backend...${NC}"
    sleep 5
    curl -s http://localhost:8088/health | grep -q "healthy" && \
        echo -e "${GREEN}✅ Backend funcionando correctamente${NC}" || \
        echo -e "${RED}❌ Backend no responde correctamente${NC}"
else
    echo -e "${RED}Error: El contenedor no se inició correctamente.${NC}"
    echo -e "Comprueba los logs con: docker-compose logs"
fi 