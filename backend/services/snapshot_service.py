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
        
        # Extraer el nombre del directorio de salida (solo el último componente)
        # El output_dir devuelto por el microservicio es una ruta completa como /tmp/converter_service/abc123/output
        # pero para el endpoint necesitamos solo el componente abc123/output
        output_dir_components = remote_output_dir.split('/')
        dir_name = output_dir_components[-2]  # Penúltimo componente (directorio temporal)
        subdir_name = output_dir_components[-1]  # Último componente (generalmente "output")
        endpoint_dir_path = f"{dir_name}/{subdir_name}"
        
        logger.info(f"Descargando archivos desde endpoint /get_png/{endpoint_dir_path}/...")
        
        # Descargar cada archivo PNG desde el nuevo endpoint
        for i, remote_file in enumerate(sorted(remote_files), 1):
            local_file = output_dir / f"slide_{i:03d}.{format}"
            
            # Construir la URL para el endpoint GET /get_png/{output_dir}/{filename}
            download_url = f"http://147.93.85.32:8090/get_png/{endpoint_dir_path}/{remote_file}"
            logger.info(f"Descargando archivo PNG: {download_url} -> {local_file}")
            
            try:
                # Descargar el archivo
                download_response = requests.get(download_url, timeout=30)
                download_response.raise_for_status()
                
                # Guardar el archivo localmente
                with open(local_file, "wb") as f:
                    f.write(download_response.content)
                
                stats["generated_files"].append(str(local_file))
                stats["slides"] += 1
            except Exception as e:
                logger.error(f"Error al descargar {remote_file}: {str(e)}")
                # Continuar con el siguiente archivo si hay error
                continue
        
        if stats["slides"] == 0:
            raise RuntimeError("No se pudieron descargar las imágenes generadas")
            
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