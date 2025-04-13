#!/bin/bash
# setup_server.sh - Script de instalación de dependencias para INSCO API
# Uso: sudo bash setup_server.sh

# Verificar que se está ejecutando como root
if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse como root (usar sudo)"
  exit 1
fi

# Función para mostrar mensajes con formato
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

success() {
  echo "✅ $1"
}

error() {
  echo "❌ $1"
  exit 1
}

warning() {
  echo "⚠️ $1"
}

log "Iniciando instalación de dependencias para INSCO API en Ubuntu"
log "=============================================================="

# Variables
TEMP_DIR="/tmp/insco_setup"
mkdir -p $TEMP_DIR

# Actualizar repositorios
log "Actualizando repositorios..."
apt-get update || error "Error al actualizar repositorios"

# Instalar herramientas básicas
log "Instalando herramientas básicas..."
apt-get install -y curl wget software-properties-common apt-transport-https ca-certificates gnupg || \
  error "Error instalando herramientas básicas"

#======================================
# BLOQUE 1: Instalación de LibreOffice
#======================================
log "Instalando LibreOffice y dependencias para generación de snapshots..."

# Instalar LibreOffice y unoconv
apt-get install -y libreoffice libreoffice-script-provider-python python3-uno unoconv || \
  error "Error al instalar LibreOffice"

# Instalar poppler-utils (necesario para pdf2image)
apt-get install -y poppler-utils || warning "Error al instalar poppler-utils, la funcionalidad de snapshots podría no funcionar"

# Verificar instalación LibreOffice
if command -v libreoffice &> /dev/null; then
  LIBREOFFICE_VERSION=$(libreoffice --version | head -n 1)
  success "LibreOffice instalado: $LIBREOFFICE_VERSION"
else
  error "LibreOffice no está disponible"
fi

# Verificar instalación unoconv
if command -v unoconv &> /dev/null; then
  UNOCONV_VERSION=$(unoconv --version | head -n 1)
  success "unoconv instalado: $UNOCONV_VERSION"
else
  error "unoconv no está disponible"
fi

#======================================
# BLOQUE 2: Instalación de FFmpeg
#======================================
log "Instalando FFmpeg y herramientas de procesamiento multimedia..."

# Agregar repositorio para versión completa de FFmpeg (si es necesario)
add-apt-repository -y universe || warning "Error al añadir repositorio universe"

# Instalar FFmpeg completo
apt-get install -y ffmpeg || error "Error al instalar FFmpeg"

# Verificar instalación FFmpeg
if command -v ffmpeg &> /dev/null; then
  FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
  success "FFmpeg instalado: $FFMPEG_VERSION"
  
  # Verificar codecs importantes
  CODECS=$(ffmpeg -codecs)
  echo "$CODECS" | grep -q "libx264" && success "Codec H.264 disponible" || warning "Codec H.264 no disponible"
  echo "$CODECS" | grep -q "libx265" && success "Codec H.265 disponible" || warning "Codec H.265 no disponible"
  echo "$CODECS" | grep -q "aac" && success "Codec AAC disponible" || warning "Codec AAC no disponible"
else
  error "FFmpeg no está disponible"
fi

#======================================
# BLOQUE 3: Verificaciones adicionales
#======================================
log "Realizando verificaciones adicionales..."

# Probar unoconv con un documento simple
log "Probando conversión básica con unoconv..."
echo "Texto de prueba" > $TEMP_DIR/test.txt
if unoconv -f pdf $TEMP_DIR/test.txt; then
  success "unoconv funciona correctamente"
  rm -f $TEMP_DIR/test.txt $TEMP_DIR/test.pdf
else
  warning "La prueba de unoconv falló, podría ser necesario reiniciar el servidor"
fi

# Probar FFmpeg con una conversión simple
log "Probando FFmpeg con una conversión simple..."
if ffmpeg -f lavfi -i testsrc=duration=1:size=640x360:rate=30 -c:v libx264 -y $TEMP_DIR/test.mp4 &> /dev/null; then
  success "FFmpeg funciona correctamente"
  rm -f $TEMP_DIR/test.mp4
else
  warning "La prueba de FFmpeg falló"
fi

#======================================
# BLOQUE 4: Optimizaciones
#======================================
log "Aplicando optimizaciones..."

# 1. Configurar LibreOffice para entorno sin interfaz (headless)
echo '' > /etc/profile.d/insco_libreoffice.sh
echo 'export UNO_PATH="/usr/lib/libreoffice/program"' >> /etc/profile.d/insco_libreoffice.sh
echo 'export URE_BOOTSTRAP="file:///usr/lib/libreoffice/program/fundamental.ini"' >> /etc/profile.d/insco_libreoffice.sh
echo 'export PYTHONPATH="/usr/lib/libreoffice/program:$PYTHONPATH"' >> /etc/profile.d/insco_libreoffice.sh
chmod +x /etc/profile.d/insco_libreoffice.sh
success "Configuración de entorno LibreOffice completada"

# 2. Ajustar parámetros del sistema para mejor rendimiento
echo 'vm.overcommit_memory=1' >> /etc/sysctl.d/99-insco.conf
sysctl -p /etc/sysctl.d/99-insco.conf

#======================================
# Finalización
#======================================
log "Limpiando archivos temporales..."
rm -rf $TEMP_DIR

log "=============================================================="
log "✅ INSTALACIÓN COMPLETADA"
log "Todas las dependencias necesarias para INSCO API están instaladas:"
log "• LibreOffice (para generación de capturas de diapositivas)"
log "• FFmpeg (para procesamiento de audio y video)"
log "• Herramientas auxiliares (poppler, python-uno, etc.)"
log ""
log "Es recomendable reiniciar el servidor para asegurar que todo funcione correctamente:"
log "  sudo reboot"
log ""
log "Después del reinicio, la API estará lista para ser desplegada."
log "==============================================================" 