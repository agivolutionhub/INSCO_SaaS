#!/usr/bin/env python3
"""
Script para traducir transcripciones de vídeo a diferentes idiomas.
Utiliza la API de OpenAI Assistant para realizar las traducciones.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('translate_video')

# Añadir directorio padre al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importar servicio
from services.video_translate_service import translate_file

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Traduce transcripciones de vídeo a diferentes idiomas"
    )
    
    parser.add_argument(
        "input_file",
        help="Archivo de texto a traducir"
    )
    
    parser.add_argument(
        "-l", "--language",
        default="English",
        help="Idioma al que traducir (por defecto: English)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Ruta del archivo de salida (opcional)"
    )
    
    parser.add_argument(
        "--source-language",
        help="Idioma original del texto (opcional, se autodetecta)"
    )
    
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        # Traducir archivo
        result = translate_file(
            file_path=args.input_file,
            target_language=args.language,
            output_path=args.output,
            original_language=args.source_language
        )
        
        # Verificar resultado
        if result.get("status") == "error":
            logger.error(f"Error en la traducción: {result.get('error', 'Error desconocido')}")
            return 1
        
        # Mostrar resultado
        logger.info(f"Traducción completada en {result.get('processing_time', 0):.2f} segundos")
        logger.info(f"Archivo de entrada: {result.get('input_file')}")
        logger.info(f"Archivo de salida: {result.get('output_file')}")
        
        return 0
    
    except KeyboardInterrupt:
        logger.warning("Operación cancelada por el usuario")
        return 130
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 