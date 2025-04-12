# Configuración para integrar el backend con el servicio MicroREST

## Detalles del servicio MicroREST
El servicio MicroREST está corriendo en el VPS para manejar la conversión de archivos PPTX a imágenes PNG usando LibreOffice. Aquí están las configuraciones para integrarlo con tu backend:

- **URL del servicio MicroREST**:
  - Dirección: http://147.93.85.32:8090
  - Endpoint: /convert_pptx_to_png
  - Método: POST
  - Cuerpo esperado (JSON):
    {
        "input_path": "/tmp/conversions/your_file.pptx",
        "output_dir": "/tmp/conversions/output"
    }
  - Respuesta esperada (JSON):
    {
        "status": "success",
        "output_files": ["slide1.png", "slide2.png", ...],
        "output_dir": "/tmp/conversions/output"
    }

- **Rutas compartidas**:
  - Usa /tmp/conversions en el VPS para guardar los archivos PPTX.
  - Usa /tmp/conversions/output para las imágenes PNG generadas.
  - Asegúrate de que tu docker-compose.yml monta este directorio:
    volumes:
      - /tmp/conversions:/tmp/conversions

- **Ejemplo de integración en tu backend**:
  Modifica backend/main.py para reemplazar la lógica actual de conversión con LibreOffice por una solicitud al servicio MicroREST. Aquí va un ejemplo de código:

  import requests

  def convert_pptx_to_png(input_pptx_path, output_dir):
      response = requests.post(
          "http://147.93.85.32:8090/convert_pptx_to_png",
          json={
              "input_path": input_pptx_path,  # Ejemplo: "/tmp/conversions/myfile.pptx"
              "output_dir": output_dir         # Ejemplo: "/tmp/conversions/output"
          }
      )
      response.raise_for_status()
      return response.json()

## Actualizar el Dockerfile
Dado que LibreOffice ya no estará en el contenedor (se usa el servicio MicroREST externo), actualiza el Dockerfile para eliminar las dependencias relacionadas con LibreOffice:

FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build || vite build

FROM python:3.10-slim
ENV DEBIAN_FRONTEND=noninteractive \
    TERM=dumb \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    poppler-utils \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist /app/static
RUN mkdir -p /app/storage /app/tmp && chmod -R 777 /app/storage /app/tmp
EXPOSE 8088
ENV ENVIRONMENT=production
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8088", "--log-level", "debug"]

## Siguientes pasos
1. Implementa el código de integración en backend/main.py usando el ejemplo proporcionado.
2. Actualiza el Dockerfile en el repositorio con el contenido proporcionado.
3. Asegúrate de que docker-compose.yml incluye el volumen /tmp/conversions:/tmp/conversions.
4. Redeploy en EasyPanel.
5. Verifica los resultados con:
   docker ps
   docker logs tools
   curl http://localhost:8088/health