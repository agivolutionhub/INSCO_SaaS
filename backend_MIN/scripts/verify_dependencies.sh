#!/bin/bash
# Script para verificar que las dependencias críticas estén correctamente instaladas

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Verificando dependencias básicas para INSCO...${NC}"

# Verificar Python
if command -v python3 &> /dev/null; then
  PYTHON_VERSION=$(python3 --version)
  echo -e "${GREEN}✅ Python instalado: $PYTHON_VERSION${NC}"
else
  echo -e "${RED}❌ ERROR: Python 3 no está disponible${NC}"
  exit 1
fi

# Verificar pip
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
  PIP_VERSION=$(pip --version 2>/dev/null || pip3 --version)
  echo -e "${GREEN}✅ pip instalado: $PIP_VERSION${NC}"
else
  echo -e "${RED}❌ ERROR: pip no está disponible${NC}"
  exit 1
fi

# Verificar curl (para healthchecks)
if command -v curl &> /dev/null; then
  CURL_VERSION=$(curl --version | head -n 1)
  echo -e "${GREEN}✅ curl instalado: $CURL_VERSION${NC}"
else
  echo -e "${YELLOW}⚠️ ADVERTENCIA: curl no está disponible (podría ser necesario para healthchecks)${NC}"
fi

echo -e "${GREEN}Verificación completada. El sistema está listo para ejecutar la versión básica de INSCO.${NC}" 