#!/bin/bash

# Script para diagnosticar problemas de despliegue en el VPS

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Test de diagnóstico para despliegue de INSCO ===${NC}"

# Verificar estado de los contenedores
echo -e "${GREEN}Verificando estado de los contenedores:${NC}"
docker ps -a

# Verificar logs del backend
echo -e "\n${GREEN}Logs del backend (últimas 30 líneas):${NC}"
docker logs insco-app --tail 30

# Verificar si el backend está respondiendo
echo -e "\n${GREEN}Probando endpoint de health del backend:${NC}"
curl -v http://localhost:8088/health || echo -e "${RED}No se pudo conectar al backend${NC}"

# Verificar estructura de archivos estáticos
echo -e "\n${GREEN}Verificando archivos estáticos en el contenedor:${NC}"
docker exec insco-app ls -la /app/static/ || echo -e "${RED}No se puede acceder a los archivos estáticos${NC}"

# Verificar credenciales de OpenAI
echo -e "\n${GREEN}Verificando configuración de OpenAI:${NC}"
docker exec insco-app bash -c "cat /app/config/auth_credentials.json | grep -v api_key | grep -v assistant_id" || echo -e "${RED}No se encontró el archivo de credenciales${NC}"

# Verificar puertos abiertos en el host
echo -e "\n${GREEN}Puertos en escucha en el servidor:${NC}"
netstat -tulpn | grep LISTEN

# Verificar variables de entorno
echo -e "\n${GREEN}Variables de entorno en el contenedor:${NC}"
docker exec insco-app env | grep -E 'OPEN|ENVIRONMENT|PYTHON'

echo -e "\n${GREEN}Pruebas de diagnóstico completadas.${NC}"
echo -e "${YELLOW}Si el frontend sigue sin funcionar, verifica:${NC}"
echo -e "1. Que los archivos estáticos estén correctamente ubicados en /app/static"
echo -e "2. Que el backend esté sirviendo la ruta '/' correctamente (app.mount('/') en main.py)"
echo -e "3. Que las etiquetas de Traefik estén configuradas correctamente en docker-compose.yml"
echo -e "4. Que no haya problemas de CORS o certificados SSL en el navegador"
echo -e "5. Que el puerto 8088 esté accesible y las reglas de firewall lo permitan" 