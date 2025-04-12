# Informe completo: Implementación y ajuste del microservicio para conversión de PPTX a PNGs

## Resumen
Este informe detalla el proceso de creación, depuración y ajuste de un microservicio (converter_service.py) para convertir archivos PPTX a imágenes PNG, así como las modificaciones necesarias en el backend del proyecto (agivolutionhub/INSCO_SaaS) para integrar esta funcionalidad. El objetivo final es permitir la previsualización de diapositivas en el frontend y la descarga de un archivo ZIP con las imágenes, todo gestionado dentro del contenedor Docker del proyecto.

### Contexto inicial
- **Problema original**: Intentamos instalar LibreOffice dentro del contenedor Docker del proyecto (scripts_tools), pero enfrentamos problemas como DeploymentException y la falta de archivos de configuración (fundamental.ini).
- **Solución inicial**: Creamos un microservicio externo en el VPS (147.93.85.32) para manejar la conversión de PPTX a PNGs, evitando los problemas dentro del contenedor.
- **Evolución**: El microservicio inicialmente intentó generar PNGs y comprimirlos en un ZIP, pero falló en la compresión (FileNotFoundError: No such file or directory: '/tmp/converter_service/<temp_dir>/output.zip'). Decidimos simplificar el microservicio para que solo genere los PNGs y devuelva sus nombres, dejando la compresión ZIP al backend.

## Acciones realizadas

### 1. Creación del microservicio
- **Ubicación**: /opt/converter_service/converter_service.py en el VPS.
- **Objetivo inicial**: Recibir un archivo PPTX, convertirlo a PNGs (uno por diapositiva), comprimir los PNGs en un ZIP, y devolver el ZIP al backend.
- **Implementación inicial**:
  - Usamos LibreOffice para convertir el PPTX a PDF (libreoffice --headless --convert-to pdf).
  - Usamos pdftoppm (de poppler-utils) para convertir el PDF a PNGs (pdftoppm -png -r 300).
  - Usamos shutil.make_archive para crear un archivo ZIP con los PNGs.
  - Devolvíamos el ZIP con FileResponse.

### 2. Depuración y ajustes
- **Problemas encontrados**:
  - **LibreOffice en el contenedor**: Falló con DeploymentException y problemas de dependencias (fundamental.ini no encontrado).
  - **Microservicio inicial**: Falló al crear el ZIP (FileNotFoundError: No such file or directory: '/tmp/converter_service/<temp_dir>/output.zip'), aunque la conversión a PNGs funcionaba manualmente.
  - **Causa del fallo**: El paquete zip no estaba instalado en el VPS, lo que impedía que shutil.make_archive creara el archivo ZIP.

- **Soluciones aplicadas**:
  - Instalamos poppler-utils para usar pdftoppm:
    sudo apt-get update
    sudo apt-get install -y poppler-utils
  - Instalamos zip para permitir la compresión:
    sudo apt install -y zip
  - Ajustamos el microservicio para manejar correctamente el nombre del archivo PDF generado por LibreOffice (test.pdf en lugar de output.pdf).
  - Simplificamos el microservicio para que solo genere los PNGs y devuelva una lista de nombres de archivos, eliminando la compresión ZIP.

### 3. Versión final del microservicio
- **Funcionalidad actual**:
  - Recibe un archivo PPTX a través de una solicitud POST al endpoint /convert_pptx_to_png.
  - Convierte el PPTX a PDF usando LibreOffice.
  - Convierte el PDF a PNGs (uno por diapositiva) usando pdftoppm.
  - Devuelve un JSON con la lista de nombres de archivos PNG generados y el directorio temporal donde están:
    {
        "status": "success",
        "files": ["slide-01.png", "slide-02.png", ..., "slide-21.png"],
        "output_dir": "/tmp/converter_service/<temp_dir>/output"
    }
  - Los archivos PNG se eliminan automáticamente después de la solicitud gracias a tempfile.TemporaryDirectory.

- **Código final** (/opt/converter_service/converter_service.py):
  from fastapi import FastAPI, HTTPException, UploadFile, File
  from fastapi.responses import JSONResponse
  import subprocess
  import os
  import shutil
  import tempfile
  import logging

  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger("converter-service")

  app = FastAPI()

  TEMP_DIR = "/tmp/converter_service"
  os.makedirs(TEMP_DIR, exist_ok=True)

  @app.post("/convert_pptx_to_png")
  async def convert_pptx_to_png(file: UploadFile = File(...)):
      try:
          with tempfile.TemporaryDirectory(dir=TEMP_DIR) as temp_dir:
              logger.info(f"Directorio temporal creado: {temp_dir}")
              input_path = os.path.join(temp_dir, file.filename)
              pdf_path = os.path.join(temp_dir, os.path.splitext(file.filename)[0] + ".pdf")
              output_dir = os.path.join(temp_dir, "output")
              os.makedirs(output_dir, exist_ok=True)

              logger.info(f"Guardando archivo PPTX en: {input_path}")
              with open(input_path, "wb") as buffer:
                  shutil.copyfileobj(file.file, buffer)

              logger.info(f"Convirtiendo PPTX a PDF: {input_path} -> {pdf_path}")
              command_pptx_to_pdf = [
                  "libreoffice",
                  "--headless",
                  "--convert-to",
                  "pdf",
                  input_path,
                  "--outdir",
                  temp_dir
              ]
              result = subprocess.run(command_pptx_to_pdf, capture_output=True, text=True)
              if result.returncode != 0:
                  logger.error(f"Error al convertir a PDF: {result.stderr}")
                  raise HTTPException(status_code=500, detail=f"Conversion to PDF failed: {result.stderr}")

              if not os.path.exists(pdf_path):
                  logger.error(f"Archivo PDF no encontrado: {pdf_path}")
                  raise HTTPException(status_code=500, detail=f"PDF file not found: {pdf_path}")

              logger.info(f"Convirtiendo PDF a PNGs: {pdf_path} -> {output_dir}/slide")
              command_pdf_to_png = [
                  "pdftoppm",
                  "-png",
                  "-r", "300",
                  pdf_path,
                  os.path.join(output_dir, "slide")
              ]
              result = subprocess.run(command_pdf_to_png, capture_output=True, text=True)
              if result.returncode != 0:
                  logger.error(f"Error al convertir a PNG: {result.stderr}")
                  raise HTTPException(status_code=500, detail=f"Conversion to PNG failed: {result.stderr}")

              output_files = [f for f in os.listdir(output_dir) if f.endswith(".png")]
              logger.info(f"Archivos PNG generados: {output_files}")
              if not output_files:
                  logger.error("No se generaron archivos PNG")
                  raise HTTPException(status_code=500, detail="No PNG files were generated")

              return JSONResponse(content={
                  "status": "success",
                  "files": output_files,
                  "output_dir": output_dir
              })

      except Exception as e:
          logger.error(f"Error en el microservicio: {str(e)}")
          raise HTTPException(status_code=500, detail=str(e))
      finally:
          file.file.close()

  if __name__ == "__main__":
      import uvicorn
      uvicorn.run(app, host="0.0.0.0", port=8090)

### 4. Problemas y soluciones
- **Problema 1: LibreOffice en el contenedor**:
  - Falló con DeploymentException y problemas de dependencias.
  - **Solución**: Movimos la conversión a un microservicio externo en el VPS, donde LibreOffice funciona correctamente.
- **Problema 2: Compresión ZIP en el microservicio**:
  - Falló porque el paquete zip no estaba instalado.
  - **Solución**: Instalamos zip, pero luego decidimos mover la compresión al backend para simplificar el microservicio.
- **Problema 3: Desfase de tiempo en los logs**:
  - Los logs del microservicio mostraban un desfase de 2 horas.
  - **Solución pendiente**: Ajustar la zona horaria del VPS a UTC para evitar confusión (no crítico para el funcionamiento).

## Tareas para la IA del editor de código (Cursor IDE)

La IA de tu editor de código (Cursor IDE) debe adaptar los scripts del backend para integrar el nuevo formato del microservicio, que ahora devuelve un JSON con la lista de nombres de archivos PNG y el directorio donde están, en lugar de un archivo ZIP. El backend debe copiar los PNGs al contenedor, permitir previsualización en el frontend, y manejar la compresión ZIP y descarga.

### 1. Ajustar el script extract_pptx_slides (carpeta service)
El script extract_pptx_slides (en la carpeta service) debe ser modificado para:
- Descargar los archivos PNG desde el microservicio usando requests.get, ya que el backend no tiene acceso directo al sistema de archivos del VPS.
- Almacenar los PNGs en output_dir para previsualización.
- Asegurarse de que los PNGs estén disponibles para un endpoint de previsualización y para compresión en un ZIP.

**Código ajustado** (extract_pptx_slides):
#!/usr/bin/env python3
import logging
from pathlib import Path
import os
import shutil
import requests
from typing import Dict, Optional, Union

DEFAULT_DPI, DEFAULT_FORMAT = 300, "png"
DEFAULT_OUTPUT_DIR = Path("output")
MICROREST_URL = "http://147.93.85.32:8090/convert_pptx_to_png"
MICROREST_TIMEOUT = 30  # Timeout en segundos para las solicitudes al microservicio

# Configuración de logger
logger = logging.getLogger("snapshot-service")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def extract_pptx_slides(
    pptx_path: Union[str, Path], 
    output_dir: Optional[Union[str, Path]] = None, 
    format: str = DEFAULT_FORMAT, 
    dpi: int = DEFAULT_DPI
) -> Dict:
    """
    Extrae diapositivas de un archivo PPTX como imágenes usando el servicio MicroREST.
    
    Args:
        pptx_path: Ruta al archivo PPTX
        output_dir: Directorio de salida (opcional)
        format: Formato de imagen ('png' o 'jpg')
        dpi: Resolución en DPI
        
    Returns:
        Dict con estadísticas y rutas de archivos generados
    """
    pptx_path = Path(pptx_path)
    if not pptx_path.exists():
        logger.error(f"No se encuentra el archivo PPTX: {pptx_path}")
        raise FileNotFoundError(f"No se encuentra el archivo PPTX: {pptx_path}")

    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR / pptx_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extrayendo diapositivas de {pptx_path} a {output_dir} ({format.upper()}, {dpi}dpi)")
    
    stats = {"slides": 0, "generated_files": []}
    
    try:
        # Enviar directamente el archivo PPTX al microservicio
        logger.info(f"Enviando archivo PPTX al microservicio: {pptx_path}")
        
        with open(pptx_path, "rb") as file:
            files = {"file": (pptx_path.name, file, 'application/vnd.openxmlformats-officedocument.presentationml.presentation')}
            
            response = requests.post(
                MICROREST_URL,
                files=files,
                timeout=MICROREST_TIMEOUT
            )
        
        response.raise_for_status()
        
        # La respuesta del microservicio es un JSON con la lista de archivos PNG y el directorio
        data = response.json()
        logger.info(f"Respuesta del microservicio: {data}")
        
        remote_files = data["files"]
        remote_output_dir = data["output_dir"]
        
        if not remote_files:
            logger.error("No se recibieron archivos PNG del microservicio")
            raise RuntimeError("No PNG files received from microservice")

        # Copiar los archivos PNG del microservicio al contenedor
        for i, remote_file in enumerate(sorted(remote_files), 1):
            remote_file_path = os.path.join(remote_output_dir, remote_file)
            local_file = output_dir / f"slide_{i:03d}.{format}"
            
            # Descargar el archivo PNG desde el microservicio
            logger.info(f"Descargando archivo PNG: {remote_file_path} -> {local_file}")
            # Usamos requests para descargar el archivo
            with open(local_file, "wb") as local_f:
                local_f.write(open(remote_file_path, "rb").read())
            
            stats["generated_files"].append(str(local_file))
            stats["slides"] += 1

        logger.info(f"Generadas {stats['slides']} imágenes en {output_dir}")

    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout al comunicarse con el microservicio (tiempo límite: {MICROREST_TIMEOUT}s): {str(e)}")
        raise RuntimeError(f"El microservicio no respondió dentro del tiempo límite ({MICROREST_TIMEOUT}s). Podría estar sobrecargado o no disponible.")
    except requests.RequestException as e:
        logger.error(f"Error al comunicarse con el microservicio: {str(e)}")
        raise RuntimeError(f"Error al comunicarse con el microservicio: {str(e)}")
    except Exception as e:
        logger.error(f"Error al extraer diapositivas: {str(e)}")
        raise

    return {
        "slides": stats["slides"],
        "output_dir": str(output_dir),
        "format": format.upper(),
        "dpi": dpi,
        "generated_files": stats["generated_files"]
    }

**Problema actual**:
- El script intenta abrir los archivos PNG directamente desde el sistema de archivos del microservicio (open(remote_file_path, "rb")), lo cual no funcionará porque el backend no tiene acceso directo al sistema de archivos del VPS.
- **Tarea para la IA**:
  - Modificar el script para descargar los PNGs usando requests.get desde una URL proporcionada por el microservicio.
  - Añadir un endpoint en el microservicio para servir los PNGs (por ejemplo, /get_png/<filename>).

### 2. Añadir un endpoint al microservicio para servir los PNGs
El microservicio debe proporcionar un endpoint para que el backend pueda descargar los PNGs. La IA debe añadir este endpoint a converter_service.py.

**Tarea para la IA**:
- Añadir un endpoint /get_png/<filename> al microservicio que permita descargar un archivo PNG desde el output_dir.
- Asegurarse de que el endpoint sea accesible mientras el directorio temporal exista.

**Código ajustado** (converter_service.py):
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import subprocess
import os
import shutil
import tempfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("converter-service")

app = FastAPI()

TEMP_DIR = "/tmp/converter_service"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/convert_pptx_to_png")
async def convert_pptx_to_png(file: UploadFile = File(...)):
    temp_dir = None
    try:
        temp_dir = tempfile.TemporaryDirectory(dir=TEMP_DIR)
        logger.info(f"Directorio temporal creado: {temp_dir.name}")
        input_path = os.path.join(temp_dir.name, file.filename)
        pdf_path = os.path.join(temp_dir.name, os.path.splitext(file.filename)[0] + ".pdf")
        output_dir = os.path.join(temp_dir.name, "output")
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Guardando archivo PPTX en: {input_path}")
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Convirtiendo PPTX a PDF: {input_path} -> {pdf_path}")
        command_pptx_to_pdf = [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            input_path,
            "--outdir",
            temp_dir.name
        ]
        result = subprocess.run(command_pptx_to_pdf, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error al convertir a PDF: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Conversion to PDF failed: {result.stderr}")

        if not os.path.exists(pdf_path):
            logger.error(f"Archivo PDF no encontrado: {pdf_path}")
            raise HTTPException(status_code=500, detail=f"PDF file not found: {pdf_path}")

        logger.info(f"Convirtiendo PDF a PNGs: {pdf_path} -> {output_dir}/slide")
        command_pdf_to_png = [
            "pdftoppm",
            "-png",
            "-r", "300",
            pdf_path,
            os.path.join(output_dir, "slide")
        ]
        result = subprocess.run(command_pdf_to_png, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error al convertir a PNG: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Conversion to PNG failed: {result.stderr}")

        output_files = [f for f in os.listdir(output_dir) if f.endswith(".png")]
        logger.info(f"Archivos PNG generados: {output_files}")
        if not output_files:
            logger.error("No se generaron archivos PNG")
            raise HTTPException(status_code=500, detail="No PNG files were generated")

        return JSONResponse(content={
            "status": "success",
            "files": output_files,
            "output_dir": output_dir
        })

    except Exception as e:
        logger.error(f"Error en el microservicio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()
        # No eliminamos el directorio temporal aquí para permitir la descarga de los PNGs
        # La limpieza se manejará manualmente o por un proceso de limpieza periódica

@app.get("/get_png/{output_dir:path}/{filename}")
async def get_png(output_dir: str, filename: str):
    file_path = os.path.join(output_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="image/png", filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)

### 3. Ajustar extract_pptx_slides para descargar los PNGs
La IA debe modificar extract_pptx_slides para descargar los PNGs desde el microservicio usando el nuevo endpoint /get_png/<output_dir>/<filename>.



**Código ajustado** (extract_pptx_slides):
#!/usr/bin/env python3
import logging
from pathlib import Path
import os
import requests
from typing import Dict, Optional, Union

DEFAULT_DPI, DEFAULT_FORMAT = 300, "png"
DEFAULT_OUTPUT_DIR = Path("output")
MICROREST_URL = "http://147.93.85.32:8090/convert_pptx_to_png"
MICROREST_TIMEOUT = 30  # Timeout en segundos para las solicitudes al microservicio

logger = logging.getLogger("snapshot-service")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def extract_pptx_slides(
    pptx_path: Union[str, Path], 
    output_dir: Optional[Union[str, Path]] = None, 
    format: str = DEFAULT_FORMAT, 
    dpi: int = DEFAULT_DPI
) -> Dict:
    pptx_path = Path(pptx_path)
    if not pptx_path.exists():
        logger.error(f"No se encuentra el archivo PPTX: {pptx_path}")
        raise FileNotFoundError(f"No se encuentra el archivo PPTX: {pptx_path}")

    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR / pptx_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extrayendo diapositivas de {pptx_path} a {output_dir} ({format.upper()}, {dpi}dpi)")
    
    stats = {"slides": 0, "generated_files": []}
    
    try:
        logger.info(f"Enviando archivo PPTX al microservicio: {pptx_path}")
        
        with open(pptx_path, "rb") as file:
            files = {"file": (pptx_path.name, file, 'application/vnd.openxmlformats-officedocument.presentationml.presentation')}
            
            response = requests.post(
                MICROREST_URL,
                files=files,
                timeout=MICROREST_TIMEOUT
            )
        
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Respuesta del microservicio: {data}")
        
        remote_files = data["files"]
        remote_output_dir = data["output_dir"]
        
        if not remote_files:
            logger.error("No se recibieron archivos PNG del microservicio")
            raise RuntimeError("No PNG files received from microservice")

        for i, remote_file in enumerate(sorted(remote_files), 1):
            local_file = output_dir / f"slide_{i:03d}.{format}"
            
            logger.info(f"Descargando archivo PNG: {remote_file} -> {local_file}")
            # Construir la URL para descargar el archivo PNG
            download_url = f"http://147.93.85.32:8090/get_png/{remote_output_dir}/{remote_file}"
            response = requests.get(download_url, timeout=MICROREST_TIMEOUT)
            response.raise_for_status()
            
            with open(local_file, "wb") as local_f:
                local_f.write(response.content)
            
            stats["generated_files"].append(str(local_file))
            stats["slides"] += 1

        logger.info(f"Generadas {stats['slides']} imágenes en {output_dir}")

    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout al comunicarse con el microservicio (tiempo límite: {MICROREST_TIMEOUT}s): {str(e)}")
        raise RuntimeError(f"El microservicio no respondió dentro del tiempo límite ({MICROREST_TIMEOUT}s). Podría estar sobrecargado o no disponible.")
    except requests.RequestException as e:
        logger.error(f"Error al comunicarse con el microservicio: {str(e)}")
        raise RuntimeError(f"Error al comunicarse con el microservicio: {str(e)}")
    except Exception as e:
        logger.error(f"Error al extraer diapositivas: {str(e)}")
        raise

    return {
        "slides": stats["slides"],
        "output_dir": str(output_dir),
        "format": format.upper(),
        "dpi": dpi,
        "generated_files": stats["generated_files"]
    }

### 4. Crear endpoints para previsualización y descarga (carpeta routers)
La IA debe modificar el script en la carpeta routers (probablemente captures.py o main.py) para:
- Añadir un endpoint para previsualizar los PNGs (por ejemplo, /api/preview/<filename>).
- Añadir un endpoint para comprimir los PNGs en un ZIP y ofrecerlo para descarga (por ejemplo, /api/download_zip/<session_id>).

**Código de ejemplo** (routers/captures.py):
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
from pathlib import Path
from .service.snapshot_service import extract_pptx_slides

router = APIRouter()

@router.post("/api/process-captures")
async def process_captures(file: UploadFile = File(...)):
    if not file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PPTX")

    output_dir = Path("tmp/captures") / file.filename.replace(".pptx", "")
    result = extract_pptx_slides(file.file, output_dir=output_dir)
    
    return {
        "status": "success",
        "slides": result["slides"],
        "output_dir": str(result["output_dir"]),
        "files": result["generated_files"]
    }

@router.get("/api/preview/{output_dir:path}/{filename}")
async def preview_slide(output_dir: str, filename: str):
    file_path = Path(output_dir) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Slide not found")
    return FileResponse(file_path, media_type="image/png", filename=filename)

@router.get("/api/download_zip/{output_dir:path}")
async def download_zip(output_dir: str):
    output_dir = Path(output_dir)
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output directory not found")

    zip_path = output_dir.parent / f"{output_dir.name}.zip"
    shutil.make_archive(str(output_dir.parent / output_dir.name), "zip", output_dir)
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{output_dir.name}.zip"
    )

**Tareas para la IA**:
- Implementar los endpoints /api/preview/{output_dir}/{filename} y /api/download_zip/{output_dir} en el script de routers.
- Asegurarse de que el endpoint /api/process-captures devuelva la información necesaria (output_dir y files) para que el frontend pueda previsualizar y descargar.
- Añadir limpieza automática de archivos después de la descarga (por ejemplo, eliminar el ZIP y los PNGs después de un tiempo o al finalizar la sesión).

### 5. Ajustar el frontend para previsualización y descarga
La IA debe modificar el frontend para:
- Usar el endpoint /api/preview/{output_dir}/{filename} para previsualizar las diapositivas.
- Usar el endpoint /api/download_zip/{output_dir} para descargar el ZIP con todas las diapositivas.

**Tareas para la IA**:
- Modificar el frontend para mostrar las diapositivas usando el endpoint /api/preview.
- Añadir un botón de descarga que llame al endpoint /api/download_zip y ofrezca el archivo ZIP al usuario.

## Siguientes pasos
1. La IA debe implementar los cambios en extract_pptx_slides y los endpoints en el script de routers.
2. Redeploy el proyecto en EasyPanel para aplicar los cambios.
3. Prueba la funcionalidad desde el frontend:
   - Sube un archivo PPTX.
   - Verifica que las diapositivas se previsualicen correctamente.
   - Descarga el ZIP y confirma que contiene todos los PNGs.
4. Ajustar la zona horaria del VPS a UTC para evitar el desfase en los logs:
   sudo dpkg-reconfigure tzdata
   # Seleccionar UTC y confirmar