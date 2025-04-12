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

# Crear directorios necesarios
echo -e "${GREEN}Creando directorios necesarios...${NC}"
mkdir -p storage data config nginx/ssl nginx/www

# Generar certificados SSL autofirmados si no existen
if [ ! -f "nginx/ssl/insco.crt" ] || [ ! -f "nginx/ssl/insco.key" ]; then
    echo -e "${YELLOW}Generando certificados SSL autofirmados...${NC}"
    echo -e "${YELLOW}NOTA: En producción, reemplaza estos por certificados válidos de Let's Encrypt${NC}"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/insco.key -out nginx/ssl/insco.crt \
        -subj "/C=ES/ST=Madrid/L=Madrid/O=INSCO/CN=insco.agivolution.com"
fi

# Construir y desplegar los contenedores
echo -e "${GREEN}Construyendo y desplegando contenedores...${NC}"
docker-compose up --build -d

# Verificar que los contenedores estén funcionando
if [ "$(docker ps -q -f name=insco-app)" ] && [ "$(docker ps -q -f name=insco-nginx)" ]; then
    echo -e "${GREEN}¡Despliegue completado con éxito!${NC}"
    echo -e "${GREEN}La aplicación está disponible en:${NC}"
    echo -e "  https://insco.agivolution.com"
    echo -e "${YELLOW}Nota: Asegúrate de que el dominio apunte a la IP del servidor${NC}"
else
    echo -e "${RED}Error: Uno o más contenedores no se iniciaron correctamente.${NC}"
    echo -e "Comprueba los logs con: docker-compose logs"
fi

# Instrucciones para obtener certificados SSL reales
echo -e "\n${YELLOW}Para obtener certificados SSL válidos con Let's Encrypt:${NC}"
echo -e "1. Instala Certbot: apt-get install certbot"
echo -e "2. Ejecuta: certbot certonly --standalone -d insco.agivolution.com"
echo -e "3. Copia los certificados:"
echo -e "   cp /etc/letsencrypt/live/insco.agivolution.com/fullchain.pem nginx/ssl/insco.crt"
echo -e "   cp /etc/letsencrypt/live/insco.agivolution.com/privkey.pem nginx/ssl/insco.key"
echo -e "4. Reinicia Nginx: docker-compose restart nginx" 