#!/bin/bash

# Script para iniciar los servidores de INSCO en segundo plano (optimizado para systemd)

# IP del servidor VPS
VPS_IP="147.93.85.32"

# Obtener directorio de instalación
INSCO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Configurar directorio
cd "$INSCO_DIR"

# Función para liberar un puerto matando cualquier proceso que lo esté usando
liberar_puerto() {
    local puerto=$1
    echo "Verificando si el puerto $puerto está en uso..."
    
    # Obtener PIDs de procesos usando el puerto especificado
    local pid_list=$(lsof -i:$puerto -t 2>/dev/null)
    
    if [ -n "$pid_list" ]; then
        echo "Puerto $puerto ocupado por los siguientes procesos: $pid_list"
        echo "Matando procesos para liberar el puerto..."
        for pid in $pid_list; do
            echo "Matando proceso $pid"
            kill -9 $pid 2>/dev/null
        done
        # Esperar a que se libere el puerto
        sleep 2
        echo "Puerto $puerto liberado."
    else
        echo "Puerto $puerto disponible."
    fi
}

# Configurar URL de API para el frontend
echo "VITE_API_URL=http://$VPS_IP:8088/api" > frontend/.env
echo "Configurada API URL: http://$VPS_IP:8088/api"

# Liberar puerto del backend
liberar_puerto 8088

# Iniciar el backend
cd backend
# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Comprobar dependencias
pip install -r requirements.txt

# Iniciar uvicorn para el backend usando nohup para que sobreviva al cierre de la terminal
echo "Iniciando backend con nohup..."
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8088 > "$INSCO_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend iniciado con PID: $BACKEND_PID"
echo $BACKEND_PID > "$INSCO_DIR/backend.pid"
cd ..

# Esperar a que el backend esté disponible
echo "Esperando a que el backend esté disponible..."
for i in {1..30}; do
    if curl -s http://localhost:8088/api/root > /dev/null; then
        echo "Backend disponible"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Backend no disponible después de 30 intentos"
        exit 1
    fi
    sleep 1
done

# Liberar puerto del frontend
liberar_puerto 3001

# Iniciar el frontend
cd frontend
echo "Instalando dependencias del frontend..."
npm install

# Asegurarse de que TypeScript esté instalado globalmente
echo "Verificando instalación de TypeScript..."
if ! command -v tsc &> /dev/null; then
    echo "TypeScript no encontrado, instalando globalmente..."
    npm install -g typescript
fi

# Construir el frontend
echo "Construyendo el frontend..."
npm run build

# Iniciar el servidor de frontend con nohup y forzar el puerto 3001
echo "Iniciando servidor de frontend con nohup en puerto 3001..."
nohup npx serve -s dist -l 3001 --no-port-switching --cors > "$INSCO_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend iniciado con PID: $FRONTEND_PID"
echo $FRONTEND_PID > "$INSCO_DIR/frontend.pid"
cd ..

# Verificar que ambos servicios están activos
if ! ps -p $BACKEND_PID > /dev/null || ! ps -p $FRONTEND_PID > /dev/null; then
    echo "ERROR: Al menos uno de los servicios no está funcionando"
    exit 1
fi

# Verificar específicamente que el frontend está escuchando en el puerto 3001
echo "Verificando que el frontend esté escuchando en el puerto 3001..."
for i in {1..10}; do
    if curl -s http://localhost:3001 > /dev/null; then
        echo "Frontend disponible en puerto 3001"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "ADVERTENCIA: Frontend no responde en puerto 3001. Verificando puerto real..."
        # Intentar detectar en qué puerto está realmente
        puerto_real=$(netstat -tlnp 2>/dev/null | grep "$FRONTEND_PID" | awk '{print $4}' | awk -F: '{print $NF}')
        if [ -n "$puerto_real" ]; then
            echo "ADVERTENCIA: Frontend está usando el puerto $puerto_real en lugar de 3001"
            echo "Frontend: http://$VPS_IP:$puerto_real (PUERTO INCORRECTO)"
        else
            echo "ERROR: No se puede determinar en qué puerto está el frontend"
        fi
    fi
    sleep 1
done

echo "INSCO SaaS iniciado correctamente en modo servicio"
echo "Backend: http://$VPS_IP:8088/api/root"
echo "Frontend: http://$VPS_IP:3001"
echo "Backend log: $INSCO_DIR/backend.log"
echo "Frontend log: $INSCO_DIR/frontend.log"

# Si se ejecuta manualmente (no a través de systemd), podemos salir aquí
if [[ -z "${INVOCATION_ID}" ]]; then  # Esta variable solo existe en contexto systemd
    echo "Servicios iniciados en segundo plano. Puedes cerrar la terminal."
    echo "Para detener los servicios: kill $BACKEND_PID $FRONTEND_PID"
    exit 0
fi

# Si llegamos aquí, es porque se está ejecutando a través de systemd
# Mantenerse en primer plano para systemd
# Crear un archivo para indicar que está corriendo
touch "$INSCO_DIR/insco.running"

# Bucle infinito con comprobación de estado
while true; do
    if ! ps -p $BACKEND_PID > /dev/null; then
        echo "ADVERTENCIA: Backend caído, reiniciando..."
        cd backend
        # Liberar puerto antes de reiniciar
        liberar_puerto 8088
        nohup python -m uvicorn main:app --host 0.0.0.0 --port 8088 > "$INSCO_DIR/backend.log" 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > "$INSCO_DIR/backend.pid"
        cd ..
    fi
    
    if ! ps -p $FRONTEND_PID > /dev/null; then
        echo "ADVERTENCIA: Frontend caído, reiniciando..."
        cd frontend
        # Liberar puerto antes de reiniciar
        liberar_puerto 3001
        nohup npx serve -s dist -l 3001 --no-port-switching --cors > "$INSCO_DIR/frontend.log" 2>&1 &
        FRONTEND_PID=$!
        echo $FRONTEND_PID > "$INSCO_DIR/frontend.pid"
        cd ..
    fi
    
    sleep 30
done 