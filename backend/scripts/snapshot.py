#!/usr/bin/env python3
"""
Script para convertir presentaciones PPTX a imágenes.

Extrae cada diapositiva como una imagen individual en formatos PNG o JPG.
Permite configurar la resolución (DPI) y el directorio de salida.
"""
import argparse, sys, json, logging
from pathlib import Path

# Configurar logger
logger = logging.getLogger("snapshot-cli")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Añadir el directorio base al path para importaciones
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.snapshot_service import extract_pptx_slides, DEFAULT_DPI, DEFAULT_FORMAT, DEFAULT_OUTPUT_DIR

def load_config(config_file=None):
    """Carga la configuración desde un archivo JSON."""
    config = {
        "dpi": DEFAULT_DPI,
        "format": DEFAULT_FORMAT,
        "output_dir": str(DEFAULT_OUTPUT_DIR)
    }
    
    if config_file and Path(config_file).exists():
        try:
            logger.debug(f"Cargando configuración desde {config_file}")
            with open(config_file) as f:
                config.update(json.load(f))
        except Exception as e:
            logger.warning(f"Error al cargar configuración: {str(e)}")
    
    return config

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Convertir presentaciones PPTX a imágenes")
    parser.add_argument("pptx_file", help="Archivo PPTX a convertir")
    parser.add_argument("-o", "--output-dir", help="Directorio de salida")
    parser.add_argument("-f", "--format", choices=["png", "jpg"], default=DEFAULT_FORMAT, 
                      help="Formato de imagen (png o jpg)")
    parser.add_argument("-d", "--dpi", type=int, default=DEFAULT_DPI, help="Resolución en DPI")
    parser.add_argument("--config", help="Archivo de configuración JSON")
    
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        pptx_path = Path(args.pptx_file)
        
        if not pptx_path.exists():
            logger.error(f"El archivo no existe: {pptx_path}")
            return 1
            
        if pptx_path.suffix.lower() != '.pptx':
            logger.error(f"El archivo debe ser PPTX: {pptx_path}")
            return 1
        
        cfg = load_config(args.config)
        output_dir = args.output_dir or cfg.get("output_dir")
        format_type = args.format or cfg.get("format")
        dpi_value = args.dpi or cfg.get("dpi")
        
        logger.info(f"Procesando {pptx_path.name} ({format_type}, {dpi_value}dpi)")
        
        result = extract_pptx_slides(
            pptx_path,
            output_dir,
            format_type,
            dpi_value
        )
        
        logger.info(f"\n✓ Convertidas {result['slides']} diapositivas")
        logger.info(f"✓ Guardadas en: {result['output_dir']}")
        logger.info(f"✓ Formato: {result['format']} @ {result['dpi']}dpi")
        return 0
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())