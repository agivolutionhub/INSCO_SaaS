#!/usr/bin/env python3
from pathlib import Path
import sys
import argparse
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("tts-cli")

# Añadir directorio base al path para importaciones
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.text_to_speech_service import generate_speech_from_file, list_available_voices

def main():
    parser = argparse.ArgumentParser(description="Generar audio a partir de texto con pausas entre oraciones")
    parser.add_argument("input", help="Archivo de texto de entrada", type=str)
    parser.add_argument("--output", "-o", help="Archivo de audio de salida", type=str, default=None)
    parser.add_argument("--voice", "-v", help="Voz a utilizar", type=str, default="echo", 
                      choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
    parser.add_argument("--model", "-m", help="Modelo TTS", type=str, default="gpt-4o-mini-tts")
    parser.add_argument("--pause", "-p", help="Duración de pausas entre oraciones (ms)", type=int, default=1300)
    parser.add_argument("--speed", "-s", help="Velocidad de habla (1.0 es normal)", type=float, default=1.0)
    parser.add_argument("--list-voices", "-l", help="Listar voces disponibles", action="store_true")
    args = parser.parse_args()
    
    try:
        if args.list_voices:
            logger.info("Obteniendo información de voces disponibles...")
            voices_info = list_available_voices()
            
            if "error" in voices_info:
                logger.error(f"Error al obtener voces: {voices_info['error']}")
                return 1
                
            logger.info("=== Voces Disponibles ===")
            for voice_id, voice_data in voices_info.get("voices", {}).items():
                logger.info(f"• {voice_id}: {voice_data.get('description', 'Sin descripción')}")
                
            logger.info("\n=== Modelos Disponibles ===")
            for model_id, model_data in voices_info.get("models", {}).items():
                if "tts" in model_id:
                    cost = model_data.get("cost", {}).get("per_minute", "N/A")
                    logger.info(f"• {model_id}: ${cost} por minuto")
            return 0
            
        logger.info("=" * 60)
        logger.info("🔊 GENERACIÓN DE VOZ - TEXTO A AUDIO")
        logger.info("=" * 60)
        
        input_file = Path(args.input)
        
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = input_file.with_suffix('.mp3')
        
        logger.info(f"Procesando archivo: {input_file}")
        logger.info(f"Voz seleccionada: {args.voice}")
        logger.info(f"Modelo: {args.model}")
        logger.info(f"Duración de pausas: {args.pause}ms")
        logger.info(f"Velocidad: {args.speed}x")
        
        stats = generate_speech_from_file(
            input_file=input_file, 
            output_file=output_file, 
            voice=args.voice, 
            model=args.model,
            pause_duration_ms=args.pause,
            speed=args.speed
        )
        
        logger.info("=" * 60)
        logger.info("✅ GENERACIÓN COMPLETADA CON ÉXITO")
        logger.info(f"Archivo generado: {output_file}")
        logger.info(f"Duración: {stats['duration']:.2f}s")
        logger.info(f"Segmentos: {stats['segments_count']}")
        logger.info(f"Caracteres: {stats['characters']}")
        logger.info(f"Coste aproximado: ${stats['cost']:.4f}")
        logger.info("=" * 60)
        
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 