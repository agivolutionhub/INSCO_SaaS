#!/usr/bin/env python3
"""
Script para dividir presentaciones PowerPoint en archivos más pequeños.

Permite fragmentar presentaciones PPTX grandes en múltiples archivos con un número
específico de diapositivas por archivo.
"""
import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

# Ajustar path para importar servicios
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar servicio
from services.pptx_service import split_presentation

# Configurar logger
logger = logging.getLogger("split-pptx-cli")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Divide presentaciones PPTX en archivos más pequeños")
    parser.add_argument("input", type=Path, help="Archivo PPTX a dividir")
    parser.add_argument("-o", "--output-dir", type=Path, help="Directorio para guardar los archivos resultantes")
    parser.add_argument("-s", "--slides", type=int, default=20, 
                      help="Número de diapositivas por archivo (default: 20)")
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        input_file = args.input
        
        # Validar archivo de entrada
        if not input_file.exists():
            logger.error(f"Error: No se encuentra el archivo {input_file}")
            return 1
        
        if input_file.suffix.lower() != '.pptx':
            logger.error(f"Error: El archivo debe ser PPTX: {input_file}")
            return 1
        
        output_dir = args.output_dir or input_file.parent / f"{input_file.stem}_partes"
        slides_per_chunk = args.slides
        
        logger.info(f"Dividiendo presentación: {input_file}")
        logger.info(f"Diapositivas por archivo: {slides_per_chunk}")
        logger.info(f"Directorio de salida: {output_dir}")
        
        # Dividir la presentación
        output_files = split_presentation(
            input_file=str(input_file),
            output_dir=str(output_dir),
            slides_per_chunk=slides_per_chunk
        )
        
        # Mostrar resultados
        logger.info("\nArchivos generados:")
        for i, file_path in enumerate(output_files, 1):
            file = Path(file_path)
            file_size = file.stat().st_size / (1024 * 1024)  # Tamaño en MB
            logger.info(f"  {i}. {file.name} ({file_size:.1f} MB)")
        
        logger.info(f"\nProceso completado. Se generaron {len(output_files)} archivos en {output_dir}")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 