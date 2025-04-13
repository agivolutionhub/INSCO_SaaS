#!/bin/bash

# Script para instalar INSCO como servicio systemd

# Verificar permisos de superusuario
if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse como root (usa sudo)"
  exit 1
fi

# Obtener directorio de la instalación
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Instalando desde: $SCRIPT_DIR"

# Crear archivo de servicio
cat > /etc/systemd/system/insco.service << EOL
[Unit]
Description=INSCO SaaS Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
ExecStart=/bin/bash -c "$SCRIPT_DIR/start_background.sh"
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOL

# Dar permisos al script de inicio
chmod +x "$SCRIPT_DIR/start_background.sh"

# Recargar configuración de systemd
systemctl daemon-reload

echo "Servicio instalado correctamente como insco.service"
echo "Para iniciarlo: sudo systemctl start insco"
echo "Para habilitarlo al inicio: sudo systemctl enable insco"
echo "Para ver su estado: sudo systemctl status insco" 