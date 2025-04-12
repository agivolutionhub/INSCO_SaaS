#!/usr/bin/env python3
import logging
from pathlib import Path
import subprocess, tempfile, platform, os, shutil
from pdf2image import convert_from_path
from typing import Dict, List, Optional, Union
import requests
import json

DEFAULT_DPI, DEFAULT_FORMAT = 300, "png"
DEFAULT_OUTPUT_DIR = Path("output")
LIBREOFFICE_TIMEOUT = 60
MICROREST_URL = "http://147.93.85.32:8090/convert_pptx_to_png"

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
    
    # Preparar rutas para el microservicio
    shared_temp_dir = Path("/tmp/conversions")
    shared_temp_dir.mkdir(parents=True, exist_ok=True)
    
    shared_output_dir = shared_temp_dir / "output"
    shared_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Copiar archivo PPTX al directorio compartido
    shared_pptx_path = shared_temp_dir / pptx_path.name
    shutil.copy2(pptx_path, shared_pptx_path)
    
    try:
        # Llamar al microservicio REST
        logger.info(f"Llamando al microservicio para convertir {shared_pptx_path}")
        
        response = requests.post(
            MICROREST_URL,
            json={
                "input_path": str(shared_pptx_path),
                "output_dir": str(shared_output_dir)
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result["status"] != "success":
            raise RuntimeError(f"Error en el microservicio: {result.get('error', 'Unknown error')}")
            
        # Copiar imágenes generadas al directorio final
        for i, file_name in enumerate(result["output_files"], 1):
            source_file = shared_output_dir / file_name
            if not source_file.exists():
                logger.warning(f"Archivo de origen no encontrado: {source_file}")
                continue
                
            output_file = output_dir / f"slide_{i:03d}.{format}"
            shutil.copy2(source_file, output_file)
            stats["generated_files"].append(str(output_file))
            stats["slides"] += 1
            
        logger.info(f"Generadas {stats['slides']} imágenes en {output_dir}")
    except requests.RequestException as e:
        logger.error(f"Error al comunicarse con el microservicio: {str(e)}")
        raise RuntimeError(f"Error al comunicarse con el microservicio: {str(e)}")
    except Exception as e:
        logger.error(f"Error al extraer diapositivas: {str(e)}")
        raise
    finally:
        try: 
            # Limpiar archivos temporales
            for file in shared_output_dir.glob("*"):
                file.unlink()
            if shared_pptx_path.exists():
                shared_pptx_path.unlink()
        except Exception as e: 
            logger.warning(f"No se pudieron eliminar archivos temporales: {str(e)}")
    
    return {
        "slides": stats["slides"],
        "output_dir": str(output_dir),
        "format": format.upper(),
        "dpi": dpi,
        "generated_files": stats["generated_files"]
    } 