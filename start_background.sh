#!/bin/bash
# =============================================================================
# Script para iniciar los servidores de INSCO en segundo plano 
# Diseñado para funcionar con systemd o de forma independiente
# =============================================================================

# ========================= CONFIGURACIÓN GENERAL =============================
# IP del servidor VPS (configurable mediante variable de entorno SERVER_IP)
VPS_IP=${SERVER_IP:-"147.93.85.32"}

# Puertos de servicios (configurables mediante variables de entorno)
BACKEND_PORT=${BACKEND_PORT:-8088}
FRONTEND_PORT=${FRONTEND_PORT:-3001}

# Obtener directorio de instalación
INSCO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Archivo de logs
BACKEND_LOG="$INSCO_DIR/backend.log"
FRONTEND_LOG="$INSCO_DIR/frontend.log"

# Archivos PID
BACKEND_PID_FILE="$INSCO_DIR/backend.pid"
FRONTEND_PID_FILE="$INSCO_DIR/frontend.pid"

# ========================= FUNCIONES AUXILIARES ==============================

# Función para mostrar mensajes con formato
log() {
    local msg_type=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $msg_type in
        "INFO")  echo -e "$timestamp [INFO] $message" ;;
        "WARN")  echo -e "$timestamp [WARN] $message" ;;
        "ERROR") echo -e "$timestamp [ERROR] $message" ;;
        *)       echo -e "$timestamp $message" ;;
    esac
}

# Función para liberar un puerto matando cualquier proceso que lo esté usando
liberar_puerto() {
    local puerto=$1
    log "INFO" "Verificando si el puerto $puerto está en uso..."
    
    # Obtener PIDs de procesos usando el puerto especificado
    local pid_list=$(lsof -i:$puerto -t 2>/dev/null)
    
    if [ -n "$pid_list" ]; then
        log "WARN" "Puerto $puerto ocupado por los siguientes procesos: $pid_list"
        log "INFO" "Matando procesos para liberar el puerto..."
        for pid in $pid_list; do
            log "INFO" "Matando proceso $pid"
            kill -9 $pid 2>/dev/null
        done
        # Esperar a que se libere el puerto
        sleep 2
        log "INFO" "Puerto $puerto liberado."
    else
        log "INFO" "Puerto $puerto disponible."
    fi
}

# Función para verificar que un servicio esté respondiendo
verificar_servicio() {
    local nombre=$1
    local url=$2
    local intentos=$3
    local tiempo_espera=${4:-1}
    
    log "INFO" "Verificando que el servicio $nombre esté disponible..."
    for i in $(seq 1 $intentos); do
        if curl -s "$url" > /dev/null; then
            log "INFO" "$nombre disponible"
            return 0
        fi
        
        if [ $i -eq $intentos ]; then
            log "ERROR" "$nombre no disponible después de $intentos intentos"
            return 1
        fi
        sleep $tiempo_espera
    done
}

# Función para iniciar el backend
iniciar_backend() {
    log "INFO" "Iniciando backend..."
    cd "$INSCO_DIR/backend"
    
    # Activar entorno virtual si existe
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Comprobar dependencias
    pip install -r requirements.txt
    
    # Iniciar uvicorn con nohup
    log "INFO" "Iniciando backend con nohup en puerto $BACKEND_PORT..."
    nohup python -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$BACKEND_PID_FILE"
    log "INFO" "Backend iniciado con PID: $BACKEND_PID"
    
    cd "$INSCO_DIR"
    
    # Verificar que el backend esté funcionando
    if ! verificar_servicio "Backend" "http://localhost:$BACKEND_PORT/api/root" 30; then
        return 1
    fi
    
    return 0
}

# Función para iniciar el frontend
iniciar_frontend() {
    log "INFO" "Iniciando frontend..."
    cd "$INSCO_DIR/frontend"
    
    log "INFO" "Instalando dependencias del frontend..."
    npm install
    
    # Asegurarse de que TypeScript esté instalado globalmente
    log "INFO" "Verificando instalación de TypeScript..."
    if ! command -v tsc &> /dev/null; then
        log "INFO" "TypeScript no encontrado, instalando globalmente..."
        npm install -g typescript
    fi
    
    # Construir el frontend
    log "INFO" "Construyendo el frontend..."
    npm run build
    
    # Crear un archivo de configuración para serve para forzar el puerto 3001
    log "INFO" "Creando archivo de configuración para serve..."
    cat > serve.json << EOL
{
  "port": $FRONTEND_PORT,
  "trailingSlash": true,
  "cleanUrls": true,
  "rewrites": []
}
EOL
    
    # Iniciar el servidor con nohup forzando el puerto especificado
    # El archivo serve.json en el directorio actual fuerza el uso del puerto
    log "INFO" "Iniciando servidor de frontend con nohup en puerto $FRONTEND_PORT..."
    nohup npx serve -s dist --no-clipboard > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$FRONTEND_PID_FILE"
    log "INFO" "Frontend iniciado con PID: $FRONTEND_PID"
    
    cd "$INSCO_DIR"
    
    # Verificar que el frontend esté en el puerto correcto
    if ! verificar_servicio "Frontend" "http://localhost:$FRONTEND_PORT" 10; then
        log "WARN" "Frontend no responde en puerto $FRONTEND_PORT. Verificando puerto real..."
        # Intentar detectar en qué puerto está realmente
        puerto_real=$(netstat -tlnp 2>/dev/null | grep "$FRONTEND_PID" | awk '{print $4}' | awk -F: '{print $NF}')
        if [ -n "$puerto_real" ]; then
            log "WARN" "Frontend está usando el puerto $puerto_real en lugar de $FRONTEND_PORT"
            log "WARN" "Frontend: http://$VPS_IP:$puerto_real (PUERTO INCORRECTO)"
            log "ERROR" "Matando el proceso en puerto incorrecto y reintentando..."
            kill -9 $FRONTEND_PID 2>/dev/null
            sleep 2
            
            # Volver a intentar una vez más con énfasis en el puerto
            log "INFO" "Reintentando iniciar frontend forzando puerto $FRONTEND_PORT..."
            cd "$INSCO_DIR/frontend"
            liberar_puerto $FRONTEND_PORT
            nohup NODE_OPTIONS="--max-old-space-size=512" npx serve -s dist -p $FRONTEND_PORT --no-clipboard > "$FRONTEND_LOG" 2>&1 &
            FRONTEND_PID=$!
            echo $FRONTEND_PID > "$FRONTEND_PID_FILE"
            log "INFO" "Frontend reiniciado con PID: $FRONTEND_PID"
            cd "$INSCO_DIR"
            
            # Verificar de nuevo
            if ! verificar_servicio "Frontend" "http://localhost:$FRONTEND_PORT" 10; then
                log "ERROR" "No se puede iniciar el frontend en el puerto correcto después de reintentar"
                return 1
            fi
            return 0
        } else {
            log "ERROR" "No se puede determinar en qué puerto está el frontend"
            return 1
        }
    fi
    
    return 0
}

# ========================= PROGRAMA PRINCIPAL ===============================

main() {
    log "INFO" "======= Iniciando INSCO SaaS ======="
    
    # Configurar directorio
    cd "$INSCO_DIR"
    
    # Configurar URL de API para el frontend
    log "INFO" "Configurando API URL: http://$VPS_IP:$BACKEND_PORT/api"
    echo "VITE_API_URL=http://$VPS_IP:$BACKEND_PORT/api" > frontend/.env
    
    # Liberar puertos antes de iniciar servicios
    liberar_puerto $BACKEND_PORT
    liberar_puerto $FRONTEND_PORT
    
    # Iniciar backend
    iniciar_backend
    if [ $? -ne 0 ]; then
        log "ERROR" "Fallo al iniciar el backend"
        exit 1
    fi
    
    # Iniciar frontend
    iniciar_frontend
    if [ $? -ne 0 ]; then
        log "ERROR" "Fallo al iniciar el frontend"
        exit 1
    fi
    
    # Verificar que ambos servicios están activos
    if ! ps -p $BACKEND_PID > /dev/null || ! ps -p $FRONTEND_PID > /dev/null; then
        log "ERROR" "Al menos uno de los servicios no está funcionando"
        exit 1
    fi
    
    # Mostrar información sobre los servicios iniciados
    log "INFO" "======= INSCO SaaS iniciado correctamente ======="
    log "INFO" "Backend: http://$VPS_IP:$BACKEND_PORT/api/root"
    log "INFO" "Frontend: http://$VPS_IP:$FRONTEND_PORT"
    log "INFO" "Backend log: $BACKEND_LOG"
    log "INFO" "Frontend log: $FRONTEND_LOG"
    
    # Si se ejecuta manualmente (no a través de systemd), salir
    if [[ -z "${INVOCATION_ID}" ]]; then  # Esta variable solo existe en contexto systemd
        log "INFO" "Servicios iniciados en segundo plano. Puedes cerrar la terminal."
        log "INFO" "Para detener los servicios: kill $BACKEND_PID $FRONTEND_PID"
        exit 0
    fi
    
    # Si se ejecuta a través de systemd, mantener el proceso en primer plano
    log "INFO" "Ejecutándose en modo systemd, vigilando servicios..."
    touch "$INSCO_DIR/insco.running"
    
    # Bucle de monitoreo para systemd
    while true; do
        # Verificar backend
        if ! ps -p $BACKEND_PID > /dev/null; then
            log "WARN" "Backend caído, reiniciando..."
            liberar_puerto $BACKEND_PORT
            iniciar_backend
        fi
        
        # Verificar frontend
        if ! ps -p $FRONTEND_PID > /dev/null; then
            log "WARN" "Frontend caído, reiniciando..."
            liberar_puerto $FRONTEND_PORT
            iniciar_frontend
        else
            # Verificar que el frontend sigue en el puerto correcto
            if ! curl -s --connect-timeout 2 "http://localhost:$FRONTEND_PORT" > /dev/null; then
                log "WARN" "Frontend activo pero no responde en puerto $FRONTEND_PORT. Reiniciando..."
                kill -9 $FRONTEND_PID 2>/dev/null
                liberar_puerto $FRONTEND_PORT
                iniciar_frontend
            fi
        fi
        
        sleep 30
    done
}

# Iniciar el programa
main 