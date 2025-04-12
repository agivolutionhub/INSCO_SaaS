#!/usr/bin/env python3
import logging
from pathlib import Path
import os, shutil, tempfile
from typing import Dict, Optional, Union
import requests
import json
from PIL import Image, ImageDraw, ImageFont

DEFAULT_DPI, DEFAULT_FORMAT = 300, "png"
DEFAULT_OUTPUT_DIR = Path("output")
MICROREST_URL = "http://147.93.85.32:8090/convert_pptx_to_png"
MICROREST_TIMEOUT = 120  # Aumentado a 120 segundos para presentaciones grandes

# Configuración de logger
logger = logging.getLogger("snapshot-service")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def create_placeholder_image(output_path: Path, text: str, width: int = 1024, height: int = 768):
    """Crea una imagen PNG con texto como reemplazo."""
    # Crear una imagen en blanco
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Dibujar un borde
    draw.rectangle([(10, 10), (width-10, height-10)], outline=(200, 200, 200), width=2)
    
    # Escribir el texto centrado
    try:
        # Intentar usar una fuente del sistema
        font = ImageFont.truetype("Arial", 24)
    except IOError:
        # Si no está disponible, usar la fuente por defecto
        font = ImageFont.load_default()
    
    # Dividir el texto en líneas para mejor visualización
    lines = text.split('\n')
    text_height = 100  # Posición inicial del texto
    for line in lines:
        draw.text((width//2, text_height), line, fill=(0, 0, 0), font=font, anchor="mm")
        text_height += 40
    
    # Guardar la imagen
    image.save(output_path)

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
            
            # Añadir timeout para evitar esperas infinitas
            response = requests.post(
                MICROREST_URL,
                files=files,
                timeout=MICROREST_TIMEOUT
            )
        
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Capturar específicamente errores HTTP para mostrar detalles
            error_body = response.text
            logger.error(f"Error HTTP del servidor: {e}")
            logger.error(f"Detalles del error: {error_body}")
            
            if response.status_code == 500:
                try:
                    # Intentar extraer detalles JSON si está disponible
                    error_json = response.json()
                    logger.error(f"Error JSON del servidor: {error_json}")
                    raise RuntimeError(f"Error en el microservicio: {error_json.get('detail', str(error_json))}")
                except Exception:
                    # Si no hay JSON válido, usar el texto completo
                    raise RuntimeError(f"Error en el microservicio: {error_body}")
            
            # Relanzar el error HTTP original
            raise
        
        # Procesar la respuesta del microservicio
        data = response.json()
        logger.info(f"Respuesta del microservicio: {data}")
        
        if data.get("status") != "success":
            logger.error(f"Error en el microservicio: {data}")
            raise RuntimeError(f"Error en el microservicio: {data.get('detail', 'Error desconocido')}")
        
        # Obtener los archivos generados desde el microservicio
        remote_files = data.get("files", [])
        remote_output_dir = data.get("output_dir", "")
        
        if not remote_files or not remote_output_dir:
            logger.error(f"Datos de respuesta incompletos: {data}")
            raise RuntimeError("Respuesta incompleta del microservicio")
        
        # Registrar la ruta original proporcionada por el microservicio
        logger.info(f"Directorio remoto original: {remote_output_dir}")
        
        # Preparar la ruta para las URLs
        # Eliminar el prefijo '/tmp/' ya que los endpoints no lo incluyen
        if remote_output_dir.startswith('/tmp/'):
            endpoint_path = remote_output_dir[5:]  # Quitar '/tmp/'
        else:
            endpoint_path = remote_output_dir
            
        logger.info(f"Ruta para endpoints: {endpoint_path}")
        
        # Intentar descargar los archivos
        successful_downloads = 0
        
        for i, remote_file in enumerate(sorted(remote_files), 1):
            local_file = output_dir / f"slide_{i:03d}.{format}"
            
            # Construir URLs usando la ruta proporcionada por el microservicio
            url_formats = [
                # URL principal usando la ruta exacta proporcionada por el microservicio
                f"http://147.93.85.32:8090/get_png/{endpoint_path}/{remote_file}",
                # URL alternativa usando el endpoint files
                f"http://147.93.85.32:8090/files/{endpoint_path}/{remote_file}",
                # Fallbacks por si la estructura cambia
                f"http://147.93.85.32:8090/get_png/{remote_file}"
            ]
            
            downloaded = False
            for url in url_formats:
                try:
                    logger.info(f"Intentando descargar desde: {url}")
                    download_response = requests.get(url, timeout=30)
                    download_response.raise_for_status()
                    
                    # Si llegamos aquí, la descarga fue exitosa
                    with open(local_file, "wb") as f:
                        f.write(download_response.content)
                    
                    stats["generated_files"].append(str(local_file))
                    successful_downloads += 1
                    downloaded = True
                    logger.info(f"✓ Descarga exitosa desde {url}")
                    break  # Salir del bucle de URLs si tuvimos éxito
                except Exception as e:
                    logger.warning(f"Intento fallido con URL {url}: {str(e)}")
                    continue
            
            if not downloaded:
                logger.error(f"No se pudo descargar {remote_file} con ningún formato de URL")
                # Crear una imagen de marcador de posición si no pudimos descargar la real
                try:
                    image = Image.new('RGB', (800, 600), color=(255, 255, 255))
                    draw = ImageDraw.Draw(image)
                    draw.rectangle([(20, 20), (780, 580)], outline=(200, 200, 200), width=2)
                    
                    # Intentar usar una fuente del sistema o la fuente por defecto
                    try:
                        # Intentar con diferentes fuentes del sistema según el SO
                        font = ImageFont.truetype("Arial", 24)
                    except IOError:
                        try:
                            font = ImageFont.truetype("DejaVuSans", 24)
                        except IOError:
                            font = ImageFont.load_default()
                    
                    # Dibujar texto centrado
                    texto = f"Error: No se pudo descargar\nDiapositiva {i} de {len(remote_files)}"
                    
                    # Centrar el texto manualmente para PIL antiguo
                    text_width, text_height = draw.textsize(texto, font=font) if hasattr(draw, 'textsize') else (400, 60)
                    position = ((800 - text_width) // 2, (600 - text_height) // 2)
                    
                    # Dibujar el texto
                    draw.text(position, texto, fill=(0, 0, 0), font=font)
                    
                    # Añadir un borde rojo para indicar que es un placeholder
                    draw.rectangle([(10, 10), (790, 590)], outline=(255, 0, 0), width=5)
                    
                    # Asegurarse de que el directorio existe
                    if not os.path.exists(os.path.dirname(local_file)):
                        os.makedirs(os.path.dirname(local_file), exist_ok=True)
                    
                    # Guardar con calidad alta
                    image.save(local_file, quality=95)
                    
                    # Verificar que la imagen se guardó correctamente
                    if not os.path.exists(local_file):
                        logger.error(f"Error: No se pudo guardar la imagen placeholder en {local_file}")
                    else:
                        logger.info(f"✅ Imagen placeholder creada correctamente en {local_file}")
                        stats["generated_files"].append(str(local_file))
                        successful_downloads += 1
                except Exception as e:
                    logger.error(f"Error al crear imagen placeholder: {str(e)}")
                    continue
        
        # Actualizar el conteo de diapositivas
        stats["slides"] = successful_downloads
        
        if successful_downloads == 0:
            raise RuntimeError("No se pudieron descargar las imágenes generadas con ningún formato de URL")
            
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