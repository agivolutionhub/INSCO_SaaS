#!/usr/bin/env python3
"""
Script para crear montajes de vídeo a partir de imágenes y audio usando FFmpeg.
Este script genera un slideshow con transiciones basadas en tiempos especificados.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('video_montage')

# Ajustar path para importar servicios
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar servicio
from services.video_montage_service import generate_video_montage

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Crea un montaje de vídeo combinando imágenes y audio"
    )
    parser.add_argument(
        "audio_file", 
        help="Ruta al archivo de audio"
    )
    parser.add_argument(
        "images_json", 
        help="Archivo JSON con lista de {'path': 'ruta/imagen.jpg', 'start_time': 0.0}"
    )
    parser.add_argument(
        "output_path", 
        help="Ruta de salida para el vídeo generado"
    )
    parser.add_argument(
        "--fps", 
        type=int, 
        default=25, 
        help="Fotogramas por segundo (default: 25)"
    )
    parser.add_argument(
        "--transition", 
        type=float, 
        default=0.8, 
        help="Duración de la transición en segundos (default: 0.8)"
    )
    
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        audio_file = args.audio_file
        images_json_file = args.images_json
        output_path = args.output_path
        
        # Validar archivos de entrada
        if not os.path.exists(audio_file):
            logger.error(f"No se encuentra el archivo de audio: {audio_file}")
            return 1
            
        if not os.path.exists(images_json_file):
            logger.error(f"No se encuentra el archivo JSON: {images_json_file}")
            return 1
        
        # Cargar datos de imágenes
        with open(images_json_file, 'r') as f:
            try:
                images_data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"El archivo JSON no es válido: {images_json_file}")
                return 1
        
        # Validar estructura del JSON
        if not isinstance(images_data, list):
            logger.error("El JSON debe contener una lista de imágenes")
            return 1
        
        for item in images_data:
            if not isinstance(item, dict) or 'path' not in item or 'start_time' not in item:
                logger.error("Cada elemento debe tener 'path' y 'start_time'")
                return 1
        
        # Crear directorio de salida si no existe
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Generar montaje
        logger.info(f"Generando montaje de vídeo con {len(images_data)} imágenes")
        result = generate_video_montage(
            audio_path=audio_file,
            image_paths=images_data,
            output_dir=output_dir,
            output_filename=os.path.basename(output_path)
        )
        
        # Mostrar resultado
        print(json.dumps(result, indent=2))
        
        if result['status'] == 'success':
            logger.info(f"Montaje generado exitosamente: {result['output_path']}")
            logger.info(f"Duración: {result['duration']:.2f} segundos")
            logger.info(f"Tamaño: {result['file_size'] / (1024*1024):.2f} MB")
            return 0
        else:
            logger.error(f"Error: {result.get('error', 'Error desconocido')}")
            return 1
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
