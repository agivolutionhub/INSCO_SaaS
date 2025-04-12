#!/bin/bash
# deploy-manual.sh - Script para desplegar INSCO_SaaS manualmente
# Versión minimalista

set -e

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DESPLIEGUE MANUAL DE INSCO_SaaS (Versión mínima) ===${NC}"

# Usar la IP específica del servidor, o permitir sobreescribirla
if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP="147.93.85.32"
    echo -e "${GREEN}IP configurada: $PUBLIC_IP${NC}"
    echo -e "${YELLOW}Para usar otra IP, ejecuta: PUBLIC_IP=tu-ip-real ./deploy-manual.sh${NC}"
fi

# Verificar requisitos
command -v node >/dev/null 2>&1 || { echo -e "${RED}Error: Node.js no está instalado${NC}"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo -e "${RED}Error: npm no está instalado${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Error: Python 3 no está instalado${NC}"; exit 1; }
command -v pip >/dev/null 2>&1 || { echo -e "${RED}Error: pip no está instalado${NC}"; exit 1; }

# 1. Actualizar repositorio
echo -e "\n${GREEN}1. Actualizando repositorio...${NC}"
git pull

# 2. Crear directorios necesarios si no existen
echo -e "\n${GREEN}2. Creando directorios necesarios...${NC}"
mkdir -p storage data config
mkdir -p backend/config backend/tmp backend/storage

# 3. Verificar archivo de credenciales
echo -e "\n${GREEN}3. Verificando archivo de credenciales...${NC}"
CREDENCIALES_FILE="backend/config/auth_credentials.json"
if [ ! -f "$CREDENCIALES_FILE" ]; then
    echo -e "${YELLOW}Creando archivo de credenciales vacío...${NC}"
    echo '{
  "openai": {
    "api_key": "",
    "assistant_id": ""
  }
}' > "$CREDENCIALES_FILE"
    echo -e "${GREEN}✓ Archivo de credenciales creado${NC}"
fi

# 4. Configurar CORS en backend para permitir solicitudes del frontend
echo -e "\n${GREEN}4. Configurando CORS en el backend...${NC}"
sed -i "s|allow_origins=\[\(.*\)\]|allow_origins=[\"http://localhost:5173\", \"http://localhost:5174\", \"http://localhost:3001\", \"http://$PUBLIC_IP:3001\"]|g" backend/main.py

# 5. Instalar dependencias del backend
echo -e "\n${GREEN}5. Instalando dependencias del backend...${NC}"
cd backend
python3 -m pip install -r requirements.txt
cd ..

# 6. Iniciar el backend
echo -e "\n${GREEN}6. Iniciando el backend...${NC}"
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8088 &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✓ Backend iniciado con PID: $BACKEND_PID${NC}"

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

# 8. Configurar URL del backend para el frontend - usando IP específica
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

# 12. Servir frontend en segundo plano en puerto 3001
echo -e "\n${GREEN}10. Iniciando servidor frontend en puerto 3001...${NC}"
nohup serve -s dist -l 3001 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
echo -e "${GREEN}✓ Frontend desplegado con PID: $FRONTEND_PID (guardado en frontend.pid)${NC}"

cd ..

# 13. Guardar PID del backend
echo $BACKEND_PID > backend.pid
echo -e "${GREEN}✓ PID del backend guardado en backend.pid${NC}"

# 14. Verificar puertos
echo -e "\n${GREEN}11. Verificando puertos...${NC}"
command -v ufw >/dev/null 2>&1 && {
    echo -e "${YELLOW}Verificando firewall (ufw)...${NC}"
    ufw status | grep "8088" || echo -e "${YELLOW}⚠️ Puede que necesites abrir el puerto 8088: sudo ufw allow 8088${NC}"
    ufw status | grep "3001" || echo -e "${YELLOW}⚠️ Puede que necesites abrir el puerto 3001: sudo ufw allow 3001${NC}"
}

# 15. Instrucciones finales
echo -e "\n${GREEN}=== DESPLIEGUE COMPLETADO ===${NC}"
echo -e "${GREEN}✓ Backend: http://$PUBLIC_IP:8088/api/root${NC}"
echo -e "${GREEN}✓ Frontend: http://$PUBLIC_IP:3001${NC}"
echo -e ""
echo -e "${YELLOW}Para detener el frontend:${NC} kill \$(cat frontend.pid)"
echo -e "${YELLOW}Para detener el backend:${NC} kill \$(cat backend.pid)"
echo -e "${YELLOW}Para ver logs del frontend:${NC} tail -f frontend.log"

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
if [ -f backend.pid ]; then
    kill \$(cat backend.pid) 2>/dev/null || true
    rm backend.pid
fi

echo "Despliegue manual detenido"
EOL

chmod +x stop-manual.sh
echo -e "\n${GREEN}✓ Script de detención creado: ./stop-manual.sh${NC}" 