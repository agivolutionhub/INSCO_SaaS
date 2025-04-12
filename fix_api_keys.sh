#!/bin/bash

# Script para diagnosticar y reparar problemas relacionados con las claves API

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Diagnóstico de Claves API - INSCO ===${NC}"

# Verificar estructura de archivos de configuración
echo -e "\n${GREEN}Verificando archivos de configuración...${NC}"
CONFIG_DIR="./backend/config"

# Lista de archivos importantes
declare -a CONFIG_FILES=(".env" "openapi.json" "sttapi.json" "ttsapi.json" "translator.json")

# Verificar existencia y validez de cada archivo
for file in "${CONFIG_FILES[@]}"; do
    file_path="${CONFIG_DIR}/${file}"
    if [ ! -f "$file_path" ]; then
        echo -e "${RED}❌ Archivo no encontrado: ${file_path}${NC}"
        if [[ "$file" == ".env" ]]; then
            echo -e "${YELLOW}⚠️ El archivo .env es necesario para las variables de entorno${NC}"
            echo -e "${YELLOW}   Puedes crear uno a partir del archivo .env.example${NC}"
        elif [[ "$file" == *.json ]]; then
            echo -e "${YELLOW}⚠️ Archivo de configuración JSON faltante${NC}"
        fi
    else
        # Verificar que el archivo no esté vacío
        if [ ! -s "$file_path" ]; then
            echo -e "${RED}❌ Archivo vacío: ${file_path}${NC}"
        else
            # Hacer verificaciones específicas según el tipo de archivo
            if [[ "$file" == ".env" ]]; then
                if grep -q "OPENAI_API_KEY" "$file_path"; then
                    echo -e "${GREEN}✅ Archivo .env contiene OPENAI_API_KEY${NC}"
                else
                    echo -e "${YELLOW}⚠️ Archivo .env no contiene OPENAI_API_KEY${NC}"
                fi
                
                if grep -q "OPENAI_ASSISTANT_ID" "$file_path"; then
                    echo -e "${GREEN}✅ Archivo .env contiene OPENAI_ASSISTANT_ID${NC}"
                else
                    echo -e "${YELLOW}⚠️ Archivo .env no contiene OPENAI_ASSISTANT_ID${NC}"
                fi
            elif [[ "$file" == "openapi.json" ]]; then
                if grep -q "api_key" "$file_path"; then
                    echo -e "${GREEN}✅ openapi.json contiene api_key${NC}"
                else
                    echo -e "${YELLOW}⚠️ openapi.json no contiene api_key${NC}"
                fi
            elif [[ "$file" == "sttapi.json" || "$file" == "ttsapi.json" ]]; then
                if grep -q "api_key" "$file_path"; then
                    echo -e "${GREEN}✅ ${file} contiene api_key${NC}"
                else
                    echo -e "${YELLOW}⚠️ ${file} no contiene api_key${NC}"
                fi
            fi
        fi
    fi
done

# Verificar configuración en docker-compose.yml
echo -e "\n${GREEN}Verificando docker-compose.yml...${NC}"
if [ -f "docker-compose.yml" ]; then
    # Verificar volúmenes necesarios
    if grep -q "backend/config/.env:/app/.env" "docker-compose.yml"; then
        echo -e "${GREEN}✅ Volumen para .env configurado${NC}"
    else
        echo -e "${RED}❌ Falta volumen para .env en docker-compose.yml${NC}"
        echo -e "${YELLOW}   Añade: - ./backend/config/.env:/app/.env${NC}"
    fi
    
    # Verificar si los archivos JSON están mapeados
    if grep -q "backend/config/openapi.json:/app/config/openapi.json" "docker-compose.yml"; then
        echo -e "${GREEN}✅ Volumen para openapi.json configurado${NC}"
    else
        echo -e "${RED}❌ Falta volumen para openapi.json en docker-compose.yml${NC}"
        echo -e "${YELLOW}   Añade: - ./backend/config/openapi.json:/app/config/openapi.json${NC}"
    fi
    
    # Verificar configuración env_file
    if grep -q "env_file:" "docker-compose.yml" && grep -q "./backend/config/.env" "docker-compose.yml"; then
        echo -e "${GREEN}✅ env_file configurado correctamente${NC}"
    else
        echo -e "${RED}❌ Falta configuración env_file en docker-compose.yml${NC}"
        echo -e "${YELLOW}   Añade:\n  env_file:\n    - ./backend/config/.env${NC}"
    fi
else
    echo -e "${RED}❌ No se encontró el archivo docker-compose.yml${NC}"
fi

# Opción para reparar automáticamente problemas conocidos
echo -e "\n${GREEN}¿Quieres intentar reparar automáticamente los problemas? (s/n)${NC}"
read -r REPAIR

if [[ $REPAIR == "s" || $REPAIR == "S" ]]; then
    echo -e "\n${GREEN}Intentando reparar problemas...${NC}"
    
    # 1. Crear archivo .env si no existe
    if [ ! -f "${CONFIG_DIR}/.env" ] && [ -f ".env.example" ]; then
        echo -e "${YELLOW}Creando archivo .env desde .env.example...${NC}"
        cp ".env.example" "${CONFIG_DIR}/.env"
        echo -e "${YELLOW}⚠️ IMPORTANTE: Edita ${CONFIG_DIR}/.env y añade tus claves API reales${NC}"
    fi
    
    # 2. Asegurarse de que los archivos JSON están correctamente mapeados en docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        NEED_UPDATE=false
        
        if ! grep -q "backend/config/.env:/app/.env" "docker-compose.yml"; then
            NEED_UPDATE=true
        fi
        
        if ! grep -q "backend/config/openapi.json:/app/config/openapi.json" "docker-compose.yml"; then
            NEED_UPDATE=true
        fi
        
        if $NEED_UPDATE; then
            echo -e "${YELLOW}Actualizando docker-compose.yml...${NC}"
            cp docker-compose.yml docker-compose.yml.bak
            echo -e "${GREEN}Copia de seguridad creada: docker-compose.yml.bak${NC}"
            
            # Agregar los volúmenes necesarios - esto es una solución básica y puede requerir ajustes manuales
            awk '
            /volumes:/ && !done {
                print;
                print "      - ./storage:/app/storage";
                print "      - ./data:/app/data";
                print "      - ./config:/app/config";
                print "      - ./backend/config/.env:/app/.env";
                print "      - ./backend/config/openapi.json:/app/config/openapi.json";
                print "      - ./backend/config/sttapi.json:/app/config/sttapi.json";
                print "      - ./backend/config/ttsapi.json:/app/config/ttsapi.json";
                print "      - ./backend/config/translator.json:/app/config/translator.json";
                print "      - /tmp:/tmp";
                print "      - /tmp/conversions:/tmp/conversions";
                done=1;
                next;
            }
            !done || $1 !~ /^[-]/ { print }
            ' docker-compose.yml.bak > docker-compose.yml.tmp
            
            # Verificar si la edición parece válida
            if grep -q "services:" "docker-compose.yml.tmp"; then
                mv docker-compose.yml.tmp docker-compose.yml
                echo -e "${GREEN}✅ docker-compose.yml actualizado correctamente${NC}"
            else
                echo -e "${RED}❌ Error al actualizar docker-compose.yml, utilizando copia de seguridad${NC}"
                mv docker-compose.yml.bak docker-compose.yml
                rm -f docker-compose.yml.tmp
            fi
        fi
    fi
    
    echo -e "\n${GREEN}Reparación completada.${NC}"
    echo -e "${YELLOW}A continuación, ejecuta:${NC}"
    echo -e "${YELLOW}  docker-compose down${NC}"
    echo -e "${YELLOW}  docker-compose up --build -d${NC}"
else
    echo -e "\n${GREEN}Instrucciones para solucionar problemas manualmente:${NC}"
    echo -e "1. Asegúrate de que ${CONFIG_DIR}/.env contiene tus claves API de OpenAI:"
    echo -e "   OPENAI_API_KEY=sk-xxxxxx..."
    echo -e "   OPENAI_ASSISTANT_ID=asst-xxxxx..."
    echo -e "2. Verifica que los archivos JSON en ${CONFIG_DIR} contienen las claves API correctas"
    echo -e "3. Asegúrate de que docker-compose.yml tiene los volúmenes correctamente mapeados:"
    echo -e "   - ./backend/config/.env:/app/.env"
    echo -e "   - ./backend/config/openapi.json:/app/config/openapi.json"
    echo -e "   - ./backend/config/sttapi.json:/app/config/sttapi.json"
    echo -e "   - ./backend/config/ttsapi.json:/app/config/ttsapi.json"
    echo -e "   - ./backend/config/translator.json:/app/config/translator.json"
    echo -e "4. Ejecuta: docker-compose down && docker-compose up --build -d"
fi

echo -e "\n${GREEN}Diagnóstico completado.${NC}" 