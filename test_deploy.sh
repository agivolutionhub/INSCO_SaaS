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

# Verificar logs de los contenedores
echo -e "\n${GREEN}Logs del backend (últimas 30 líneas):${NC}"
docker logs insco-app --tail 30

echo -e "\n${GREEN}Logs de nginx (últimas 30 líneas):${NC}"
docker logs insco-nginx --tail 30

# Verificar si el backend está respondiendo
echo -e "\n${GREEN}Probando endpoint de health del backend:${NC}"
curl -v http://localhost:8088/health || echo -e "${RED}No se pudo conectar al backend${NC}"

# Comprobar si nginx puede acceder al backend
echo -e "\n${GREEN}Probando conectividad desde nginx al backend:${NC}"
docker exec insco-nginx curl -v http://insco-app:8088/health || echo -e "${RED}Nginx no puede conectar con el backend${NC}"

# Verificar estructura de archivos en el frontend
echo -e "\n${GREEN}Verificando archivos del frontend en nginx:${NC}"
docker exec insco-nginx ls -la /var/www/html/

# Verificar configuración de nginx
echo -e "\n${GREEN}Verificando configuración de nginx:${NC}"
docker exec insco-nginx nginx -T

# Verificar puertos abiertos en el host
echo -e "\n${GREEN}Puertos en escucha en el servidor:${NC}"
netstat -tulpn | grep LISTEN

echo -e "\n${GREEN}Pruebas de diagnóstico completadas.${NC}"
echo -e "${YELLOW}Si el frontend sigue sin funcionar, verifica:${NC}"
echo -e "1. Que los archivos estáticos estén correctamente ubicados en /var/www/html"
echo -e "2. Que la configuración de nginx esté mapeando correctamente las rutas"
echo -e "3. Que el backend esté respondiendo a las peticiones de la API"
echo -e "4. Que no haya bloqueos de CORS o problemas de certificados SSL"
echo -e "5. Que los puertos 80 y 443 estén abiertos en el firewall del VPS" 