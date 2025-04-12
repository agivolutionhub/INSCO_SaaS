#!/bin/bash
# deploy-manual.sh - Script para desplegar INSCO_SaaS manualmente
# Separando frontend y backend para mayor control

set -e

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DESPLIEGUE MANUAL DE INSCO_SaaS ===${NC}"

# Obtener IP pública (o usar la proporcionada)
if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s ifconfig.me)
    echo -e "${YELLOW}IP detectada: $PUBLIC_IP${NC}"
    echo -e "${YELLOW}Si esta IP no es correcta, cancela y ejecuta: PUBLIC_IP=tu-ip-real ./deploy-manual.sh${NC}"
    sleep 3
fi

# Verificar requisitos
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker no está instalado${NC}"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo -e "${RED}Error: Docker Compose no está instalado${NC}"; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e "${RED}Error: Node.js no está instalado${NC}"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo -e "${RED}Error: npm no está instalado${NC}"; exit 1; }

# 1. Actualizar repositorio
echo -e "\n${GREEN}1. Actualizando repositorio...${NC}"
git pull

# 2. Crear directorios necesarios si no existen
echo -e "\n${GREEN}2. Creando directorios necesarios...${NC}"
mkdir -p storage data config
mkdir -p backend/config/cache

# 3. Verificar archivos de configuración
echo -e "\n${GREEN}3. Verificando archivos de configuración...${NC}"
CREDENCIALES_FILE="backend/config/auth_credentials.json"
if [ ! -f "$CREDENCIALES_FILE" ]; then
    echo -e "${YELLOW}ADVERTENCIA: No se encontró $CREDENCIALES_FILE${NC}"
    echo -e "${YELLOW}Asegúrate de copiar tus archivos de configuración en la carpeta backend/config/${NC}"
fi

# 4. Configurar CORS en backend para permitir solicitudes del frontend
echo -e "\n${GREEN}4. Configurando CORS en el backend...${NC}"
sed -i "s|allow_origins=\[\(.*\)\]|allow_origins=[\"http://localhost:5173\", \"http://localhost:5174\", \"http://localhost:3000\", \"http://$PUBLIC_IP:3000\"]|g" backend/main.py

# 5. Crear docker-compose para backend solamente
echo -e "\n${GREEN}5. Creando configuración para desplegar solo el backend...${NC}"
cat > docker-compose.backend.yml <<EOL
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: insco-backend
    restart: always
    ports:
      - "8088:8088"
    volumes:
      - ./storage:/app/storage
      - ./data:/app/data
      - ./config:/app/config
      - ./backend/config/auth_credentials.json:/app/config/auth_credentials.json
      - ./backend/config/openapi.json:/app/config/openapi.json
      - ./backend/config/sttapi.json:/app/config/sttapi.json
      - ./backend/config/ttsapi.json:/app/config/ttsapi.json
      - ./backend/config/translator.json:/app/config/translator.json
      - /tmp:/tmp
      - /tmp/conversions:/tmp/conversions
    environment:
      - ENVIRONMENT=production
      - TZ=Europe/Madrid
      - PYTHONUNBUFFERED=1
      - DEBIAN_FRONTEND=noninteractive
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  mongodb_data:
EOL

# 6. Desplegar backend
echo -e "\n${GREEN}6. Desplegando backend con Docker...${NC}"
docker compose -f docker-compose.backend.yml down
docker compose -f docker-compose.backend.yml up --build -d

# 7. Esperar a que el backend esté listo
echo -e "\n${GREEN}7. Esperando a que el backend esté listo...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8088/api/root >/dev/null; then
        echo -e "${GREEN}✓ Backend iniciado correctamente${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${YELLOW}⚠️ El backend aún no responde, pero continuaremos...${NC}"
    fi
    echo "Esperando... ($i/10)"
    sleep 5
done

# 8. Configurar URL del backend para el frontend
echo -e "\n${GREEN}8. Configurando URL del backend para el frontend...${NC}"
echo "VITE_API_URL=http://$PUBLIC_IP:8088/api" > frontend/.env
echo -e "${GREEN}✓ URL del backend configurada: http://$PUBLIC_IP:8088/api${NC}"

# 9. Construir y servir frontend
echo -e "\n${GREEN}9. Construyendo y sirviendo frontend...${NC}"
cd frontend
npm install
npm run build

# 10. Verificar si serve está instalado globalmente, sino instalarlo
if ! command -v serve &> /dev/null; then
    echo -e "${YELLOW}Instalando 'serve' para servir el frontend...${NC}"
    npm install -g serve
fi

# 11. Detener cualquier instancia anterior del frontend
pkill -f "serve -s dist" || true

# 12. Servir frontend en segundo plano
echo -e "\n${GREEN}10. Iniciando servidor frontend en puerto 3000...${NC}"
nohup serve -s dist -l 3000 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
echo -e "${GREEN}✓ Frontend desplegado con PID: $FRONTEND_PID (guardado en frontend.pid)${NC}"

cd ..

# 13. Verificar puertos
echo -e "\n${GREEN}11. Verificando puertos...${NC}"
command -v ufw >/dev/null 2>&1 && {
    echo -e "${YELLOW}Verificando firewall (ufw)...${NC}"
    ufw status | grep "8088" || echo -e "${YELLOW}⚠️ Puede que necesites abrir el puerto 8088: sudo ufw allow 8088${NC}"
    ufw status | grep "3000" || echo -e "${YELLOW}⚠️ Puede que necesites abrir el puerto 3000: sudo ufw allow 3000${NC}"
}

# 14. Instrucciones finales
echo -e "\n${GREEN}=== DESPLIEGUE COMPLETADO ===${NC}"
echo -e "${GREEN}✓ Backend: http://$PUBLIC_IP:8088/api/root${NC}"
echo -e "${GREEN}✓ Frontend: http://$PUBLIC_IP:3000${NC}"
echo -e ""
echo -e "${YELLOW}Para detener el frontend:${NC} kill \$(cat frontend.pid)"
echo -e "${YELLOW}Para detener el backend:${NC} docker compose -f docker-compose.backend.yml down"
echo -e "${YELLOW}Para ver logs del frontend:${NC} tail -f frontend.log"
echo -e "${YELLOW}Para ver logs del backend:${NC} docker logs -f insco-backend"
echo -e ""
echo -e "${GREEN}Si encuentras problemas:${NC}"
echo -e "1. Verifica que los puertos 3000 y 8088 estén abiertos en el firewall"
echo -e "2. Comprueba que los archivos de configuración estén en backend/config/"
echo -e "3. Revisa los logs de ambos servicios"

# Script para detener todo
cat > stop-manual.sh <<EOL
#!/bin/bash
# Detener despliegue manual

echo "Deteniendo frontend..."
if [ -f frontend.pid ]; then
    kill \$(cat frontend.pid) 2>/dev/null || true
    rm frontend.pid
fi

echo "Deteniendo backend..."
docker compose -f docker-compose.backend.yml down

echo "Despliegue manual detenido"
EOL

chmod +x stop-manual.sh
echo -e "\n${GREEN}✓ Script de detención creado: ./stop-manual.sh${NC}" 