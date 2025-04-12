# INSCO SaaS

Sistema SaaS para procesamiento y optimización de presentaciones, audio y video para la industria del cartón ondulado.

## Componentes

- **Backend**: API REST desarrollada con FastAPI
- **Frontend**: Interfaz de usuario desarrollada con React y Tailwind CSS

## Módulos principales

- **AutoFit**: Ajuste automático de textos en diapositivas PowerPoint
- **Transcripción**: Conversión de audio a texto usando IA
- **Traducción**: Traducción automática de presentaciones
- **Montaje de vídeo**: Generación automática de vídeos a partir de imágenes y audio
- **Captura de diapositivas**: Exportación de diapositivas a imágenes de alta calidad

## Requisitos

- Python 3.9+
- FFmpeg
- LibreOffice
- Node.js 18+

## Desarrollado por

[AGIVOLUTION](https://www.agivolution.com) - Soluciones tecnológicas para la industria del cartón ondulado

## Despliegue con Docker

Para desplegar el proyecto con Docker, sigue estos pasos:

1. Prepara el frontend para el despliegue:
   ```bash
   ./deploy-frontend.sh
   ```
   Este script:
   - Crea los directorios necesarios para nginx
   - Genera certificados SSL autofirmados si no existen
   - Compila el frontend si no está compilado
   - Copia los archivos compilados al directorio nginx/www

2. Inicia los contenedores:
   ```bash
   docker-compose up -d
   ```

3. Para ver los logs:
   ```bash
   docker-compose logs -f
   ```

4. Para detener los contenedores:
   ```bash
   docker-compose down
   ```

5. La aplicación estará disponible en:
   - https://localhost (o la IP del servidor donde esté desplegado)
   - El backend API: https://localhost/api/ 