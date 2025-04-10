#!/usr/bin/env python3
"""
Script para transcribir vídeos a texto usando la API de OpenAI.

Convierte archivos de vídeo a texto transcrito con varios modelos de IA
y permite exportar en múltiples formatos (TXT, JSON, MD).
"""
from pathlib import Path
import argparse
import sys
import logging

# Ajustar path para importar servicios
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importar servicios
from services.transcript_service import transcribe_video, find_video_files

# Configurar logger
logger = logging.getLogger("transcript-cli")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Transcribe vídeos con OpenAI API")
    parser.add_argument("video", nargs="?", type=Path, help="Ruta al archivo de vídeo")
    parser.add_argument("-o", "--output", type=Path, help="Directorio de salida")
    parser.add_argument("-m", "--model", default="gpt-4o-transcribe", 
                        choices=["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"], 
                        help="Modelo de OpenAI a utilizar")
    parser.add_argument("-f", "--formats", nargs="+", default=["all"], 
                        choices=["json","txt","md","all"], help="Formatos de salida")
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        logger.info("-" * 60)
        logger.info("🎬 OpenAI API - TRANSCRIPCIÓN DE VÍDEO A TEXTO")
        logger.info("-" * 60)
        
        # Búsqueda automática si no se especifica video
        if not args.video:
            logger.info("No se especificó archivo de vídeo, buscando en data/input/video/...")
            videos = find_video_files(Path("data/input/video"))
            if not videos:
                raise FileNotFoundError("No se encontraron vídeos en data/input/video/")
            args.video = videos[0]
            logger.info(f"Usando vídeo encontrado: {args.video}")
            
        # Validar que el archivo existe
        if not args.video.exists():
            raise FileNotFoundError(f"No se encuentra el archivo: {args.video}")
        
        # Ejecutar transcripción
        result = transcribe_video(args.video, args.output, args.model, args.formats)
        
        # Mostrar estadísticas
        logger.info("📊 Estadísticas de Transcripción")
        logger.info("-" * 40)
        for key, value in result["stats"].items():
            logger.info(f"✓ {key}: {value}")
        
        logger.info("-" * 60)
        logger.info("✅ PROCESO COMPLETADO CON ÉXITO")
        logger.info("-" * 60)
        
        return 0
    except FileNotFoundError as e:
        logger.error(f"Error: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())