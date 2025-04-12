#!/bin/bash

# Script para diagnosticar problemas de despliegue en el VPS

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Test de diagnóstico para despliegue de INSCO (Versión mínima) ===${NC}"

# Verificar proceso del backend
echo -e "${GREEN}Verificando si el backend está corriendo:${NC}"
if [ -f "backend.pid" ]; then
    PID=$(cat backend.pid)
    if ps -p $PID > /dev/null; then
        echo -e "${GREEN}✓ Backend corriendo con PID $PID${NC}"
    else
        echo -e "${RED}✗ Backend no está corriendo (PID $PID no válido)${NC}"
    fi
else
    echo -e "${RED}✗ No se encontró archivo backend.pid${NC}"
    echo -e "${YELLOW}Buscando procesos uvicorn...${NC}"
    ps aux | grep uvicorn | grep -v grep
fi

# Verificar si el backend está respondiendo
echo -e "\n${GREEN}Probando endpoint de la API:${NC}"
curl -s http://localhost:8088/api/root && echo || echo -e "${RED}No se pudo conectar al backend${NC}"

# Verificar estado de salud
echo -e "\n${GREEN}Probando endpoint de health:${NC}"
curl -s http://localhost:8088/health && echo || echo -e "${RED}No se pudo conectar al endpoint health${NC}"

# Verificar proceso del frontend
echo -e "\n${GREEN}Verificando si el frontend está corriendo:${NC}"
if [ -f "frontend.pid" ]; then
    PID=$(cat frontend.pid)
    if ps -p $PID > /dev/null; then
        echo -e "${GREEN}✓ Frontend corriendo con PID $PID${NC}"
    else
        echo -e "${RED}✗ Frontend no está corriendo (PID $PID no válido)${NC}"
    fi
else
    echo -e "${RED}✗ No se encontró archivo frontend.pid${NC}"
    echo -e "${YELLOW}Buscando procesos serve...${NC}"
    ps aux | grep serve | grep -v grep
fi

# Verificar puertos abiertos en el host
echo -e "\n${GREEN}Puertos en escucha en el servidor:${NC}"
netstat -tulpn 2>/dev/null | grep -E "8088|3001" || echo -e "${YELLOW}No se pudo verificar puertos (netstat no disponible)${NC}"

echo -e "\n${GREEN}Pruebas de diagnóstico completadas.${NC}"
echo -e "${YELLOW}Si el servicio no funciona, verifica:${NC}"
echo -e "1. Que los puertos 8088 y 3001 estén abiertos y accesibles"
echo -e "2. Que no haya problemas en los logs de los servicios"
echo -e "3. Que la URL del backend esté configurada correctamente en frontend/.env" 