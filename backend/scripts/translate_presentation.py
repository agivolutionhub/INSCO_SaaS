#!/usr/bin/env python3
"""
Traductor de presentaciones PowerPoint (.pptx).

Utiliza la API de OpenAI para traducir el contenido textual
de archivos PPTX manteniendo el formato y estructura original.
"""
import argparse
import sys
import time
import os
from pathlib import Path
import logging

# Ajustar path para importar servicios
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.translation_service import Translator, PPTXEditor

# Configurar logger
logger = logging.getLogger("translate-pptx-cli")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Traductor de presentaciones PPTX")
    parser.add_argument("input_file", type=str, help="Archivo PPTX de entrada")
    parser.add_argument("-o", "--output", type=str, help="Ruta del archivo de salida")
    parser.add_argument("-l", "--language", type=str, default="en", 
                        choices=["en", "es", "fr", "de", "it", "pt"],
                        help="Idioma destino (por defecto: en)")
    parser.add_argument("--no-cache", action="store_true", help="Desactivar caché de traducciones")
    
    return parser.parse_args()

def validate_input(input_path):
    """Valida el archivo de entrada."""
    if not input_path.exists():
        logger.error(f"Error: No se encuentra el archivo {input_path}")
        return False
        
    if not input_path.is_file() or input_path.suffix.lower() != '.pptx':
        logger.error(f"Error: El archivo debe ser PPTX: {input_path}")
        return False
    
    return True

def print_stats(elapsed, editor, translator, result_path):
    """Muestra estadísticas del proceso de traducción."""
    if not result_path or not os.path.exists(result_path):
        logger.error(f"\n❌ Error: No se generó el archivo de salida")
        return
        
    logger.info(f"\n✅ Traducción completada en {elapsed:.2f} segundos")
    logger.info(f"Archivo generado: {result_path}")
    
    # Estadísticas básicas
    logger.info(f"\nEstadísticas:")
    logger.info(f"- Diapositivas procesadas: {editor.slides_processed}")
    logger.info(f"- Textos traducidos: {editor.total_texts}")
    
    # Estadísticas de caché si está habilitada
    if hasattr(translator, 'cache') and translator.cache:
        cache_hits = translator.cache_hits
        cache_misses = translator.cache_misses
        total = cache_hits + cache_misses
        hit_rate = cache_hits / total * 100 if total > 0 else 0
        logger.info(f"- Caché: {cache_hits} hits, {cache_misses} misses ({hit_rate:.1f}% aciertos)")

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        input_path = Path(args.input_file)
        if not validate_input(input_path):
            return 1
        
        output_path = args.output
        if not output_path:
            output_path = input_path.with_name(f"{input_path.stem}_translated_{args.language}{input_path.suffix}")
        else:
            output_path = Path(output_path)
        
        logger.info(f"Iniciando traducción de {input_path.name} a {args.language}")
        logger.info(f"Archivo de salida: {output_path}")
        
        # Crear instancia del traductor
        translator = Translator(target_language=args.language, use_cache=not args.no_cache)
        editor = PPTXEditor(translator)
        
        # Medir tiempo
        start_time = time.time()
        
        # Procesar el archivo
        result_path = editor.process_pptx(input_path, output_path)
        
        # Mostrar resultado
        elapsed = time.time() - start_time
        print_stats(elapsed, editor, translator, result_path)
        
        return 0 if result_path and os.path.exists(result_path) else 1
            
    except Exception as e:
        logger.error(f"\n❌ Error durante la traducción: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 