#!/usr/bin/env python3
import logging
from pathlib import Path
import os, shutil, tempfile, zipfile
from typing import Dict, Optional, Union
import requests
import json

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
            
            # Añadir timeout para evitar esperas infinitas
            response = requests.post(
                MICROREST_URL,
                files=files,
                timeout=MICROREST_TIMEOUT
            )
        
        response.raise_for_status()
        
        # Determinar el tipo de respuesta basado en el Content-Type
        content_type = response.headers.get("Content-Type")
        logger.info(f"Respuesta recibida del microservicio. Content-Type: {content_type}")
        
        if content_type == "application/zip":
            # La respuesta es un ZIP con múltiples imágenes
            temp_zip = output_dir / "slides.zip"
            
            # Guardar el archivo ZIP
            with open(temp_zip, "wb") as f:
                f.write(response.content)
            
            # Extraer las imágenes del ZIP
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
            
            # Eliminar el ZIP temporal
            temp_zip.unlink()
            
            # Listar y renombrar las imágenes extraídas
            for i, img_file in enumerate(sorted(output_dir.glob("*.png")), 1):
                new_name = output_dir / f"slide_{i:03d}.{format}"
                img_file.rename(new_name)
                stats["generated_files"].append(str(new_name))
                stats["slides"] += 1
                
        elif content_type == "image/png":
            # La respuesta es una única imagen
            output_file = output_dir / f"slide_001.{format}"
            
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            stats["generated_files"].append(str(output_file))
            stats["slides"] = 1
            
        else:
            logger.error(f"Tipo de contenido inesperado: {content_type}")
            raise ValueError(f"Tipo de contenido inesperado del microservicio: {content_type}")
            
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