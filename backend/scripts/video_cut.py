#!/usr/bin/env python3
"""
Script para cortar segmentos de un archivo de vídeo usando FFmpeg.

Permite extraer una porción específica de un vídeo definiendo tiempos de inicio y fin.
"""
import argparse
import sys
import logging
from pathlib import Path

# Ajustar path para importar servicios
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar servicio
from services.video_service import cut_video, get_video_info

# Configurar logger
logger = logging.getLogger("video-cut-cli")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Cortar segmentos de vídeo usando FFmpeg")
    parser.add_argument("input", help="Archivo de vídeo de entrada")
    parser.add_argument("output", help="Archivo de vídeo de salida")
    parser.add_argument("--start", type=float, default=0, help="Tiempo de inicio en segundos")
    parser.add_argument("--end", type=float, required=True, help="Tiempo final en segundos")
    parser.add_argument("--format", help="Formato de salida (opcional)")
    
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        input_file = Path(args.input)
        output_file = Path(args.output)
        
        # Validar archivo de entrada
        if not input_file.exists():
            logger.error(f"Error: No se encuentra el archivo {input_file}")
            return 1
        
        # Obtener información del vídeo original
        video_info = get_video_info(input_file)
        duration = video_info.get("duration", 0)
        
        if duration > 0 and args.end > duration:
            logger.warning(f"El tiempo final ({args.end}s) excede la duración del vídeo ({duration:.2f}s)")
            logger.warning(f"Se ajustará al final del vídeo")
            end_time = duration
        else:
            end_time = args.end
        
        logger.info(f"Cortando vídeo: {input_file}")
        logger.info(f"Desde {args.start}s hasta {end_time}s")
        logger.info(f"Archivo de salida: {output_file}")
        
        # Cortar vídeo
        result = cut_video(
            video_path=input_file,
            output_path=output_file,
            start_time=args.start,
            end_time=end_time,
            output_format=args.format
        )
        
        # Mostrar resultados
        logger.info(f"Vídeo cortado exitosamente: {result['output_file']}")
        logger.info(f"Duración: {result['duration']:.2f} segundos")
        logger.info(f"Tamaño: {result['size']/1024/1024:.2f} MB")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 