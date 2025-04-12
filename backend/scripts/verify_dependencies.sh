#!/bin/bash
# Script para verificar que las dependencias críticas estén correctamente instaladas

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Verificando dependencias del sistema para INSCO...${NC}"

# Verificar FFmpeg
if command -v ffmpeg &> /dev/null; then
  FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
  echo -e "${GREEN}✅ FFmpeg instalado: $FFMPEG_VERSION${NC}"
  
  # Verificar codecs importantes
  CODECS=$(ffmpeg -codecs)
  echo "$CODECS" | grep -q "libx264" && echo -e "${GREEN}  ✅ Codec H.264 disponible${NC}" || echo -e "${YELLOW}  ⚠️ Codec H.264 no disponible${NC}"
  echo "$CODECS" | grep -q "libx265" && echo -e "${GREEN}  ✅ Codec H.265 disponible${NC}" || echo -e "${YELLOW}  ⚠️ Codec H.265 no disponible${NC}"
  echo "$CODECS" | grep -q "aac" && echo -e "${GREEN}  ✅ Codec AAC disponible${NC}" || echo -e "${YELLOW}  ⚠️ Codec AAC no disponible${NC}"
else
  echo -e "${RED}❌ ERROR: FFmpeg no está disponible${NC}"
  exit 1
fi

# Verificar poppler-utils
if command -v pdftoppm &> /dev/null; then
  PDFTOPPM_VERSION=$(pdftoppm -v 2>&1 | head -n 1)
  echo -e "${GREEN}✅ poppler-utils instalado: $PDFTOPPM_VERSION${NC}"
else
  echo -e "${RED}❌ ERROR: poppler-utils no está disponible${NC}"
  exit 1
fi

echo -e "${GREEN}Verificación completada. El sistema está listo para ejecutar INSCO.${NC}" 