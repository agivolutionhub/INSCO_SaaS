#!/bin/bash

# Script para configurar INSCO como servicio systemd

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Configurando INSCO como servicio systemd ===${NC}"

# Verificar si se está ejecutando como root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Por favor, ejecuta este script como root o con sudo${NC}"
  exit 1
fi

# Directorio base del proyecto
INSCO_DIR="/INSCO_SaaS"

# Verificar si el directorio existe
if [ ! -d "$INSCO_DIR" ]; then
  echo -e "${RED}Error: Directorio $INSCO_DIR no encontrado${NC}"
  exit 1
fi

# Verificar que los archivos necesarios existen
if [ ! -f "$INSCO_DIR/insco.service" ] || [ ! -f "$INSCO_DIR/start_background.sh" ]; then
  echo -e "${RED}Error: Archivos de servicio no encontrados${NC}"
  exit 1
fi

# Dar permisos de ejecución
chmod +x "$INSCO_DIR/start_background.sh"
echo -e "${GREEN}✓ Permisos de ejecución configurados${NC}"

# Copiar archivo de servicio a systemd
cp "$INSCO_DIR/insco.service" /etc/systemd/system/
echo -e "${GREEN}✓ Archivo de servicio copiado a /etc/systemd/system/${NC}"

# Recargar systemd
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd recargado${NC}"

# Habilitar y arrancar el servicio
systemctl enable insco.service
echo -e "${GREEN}✓ Servicio habilitado para iniciar con el sistema${NC}"

systemctl start insco.service
echo -e "${GREEN}✓ Servicio iniciado${NC}"

# Verificar estado
echo -e "\n${GREEN}=== Estado del servicio ===${NC}"
systemctl status insco.service

echo -e "\n${GREEN}=== Configuración completada ===${NC}"
echo -e "Comandos útiles:"
echo -e "${YELLOW}Ver logs:${NC} journalctl -u insco.service -f"
echo -e "${YELLOW}Reiniciar servicio:${NC} systemctl restart insco.service"
echo -e "${YELLOW}Detener servicio:${NC} systemctl stop insco.service"
echo -e "${YELLOW}Ver estado:${NC} systemctl status insco.service" 