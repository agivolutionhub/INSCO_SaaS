#!/bin/bash

# Script para preparar el frontend para despliegue con Docker
# Este script compila el frontend y copia los archivos a nginx/www

echo "🚀 Preparando el frontend para despliegue..."

# Crear directorios necesarios
mkdir -p nginx/www
mkdir -p nginx/ssl

# Si no existen certificados SSL, crear unos autofirmados
if [ ! -f nginx/ssl/insco.crt ] || [ ! -f nginx/ssl/insco.key ]; then
    echo "📜 Generando certificados SSL autofirmados..."
    mkdir -p nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/insco.key -out nginx/ssl/insco.crt \
        -subj "/C=ES/ST=Madrid/L=Madrid/O=INSCO/CN=insco.local"
fi

# Compilar el frontend si no está ya compilado
if [ ! -d frontend/dist ]; then
    echo "🔨 Compilando el frontend..."
    cd frontend
    npm install
    npm run build
    cd ..
fi

# Copiar los archivos compilados a nginx/www
echo "📋 Copiando archivos compilados a nginx/www..."
cp -r frontend/dist/* nginx/www/

echo "✅ Frontend preparado para despliegue"
echo ""
echo "Para iniciar los contenedores, ejecuta:"
echo "docker-compose up -d"
echo ""
echo "Para ver los logs, ejecuta:"
echo "docker-compose logs -f" 