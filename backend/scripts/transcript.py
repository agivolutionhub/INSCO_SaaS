#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("transcript-cli")

# Añadir directorio base al path para importaciones
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.transcript_service import transcribe_video, find_video_files

def main():
    parser = argparse.ArgumentParser(description="Transcribe vídeos con OpenAI API")
    parser.add_argument("video", nargs="?", type=Path, help="Ruta al archivo de vídeo")
    parser.add_argument("--output", type=Path, help="Directorio de salida")
    parser.add_argument("--model", default="gpt-4o-transcribe", 
                        choices=["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"], 
                        help="Modelo de OpenAI a utilizar")
    parser.add_argument("--formats", nargs="+", default=["all"], 
                        choices=["json","txt","md","all"], help="Formatos de salida")
    args = parser.parse_args()

    try:
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
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())