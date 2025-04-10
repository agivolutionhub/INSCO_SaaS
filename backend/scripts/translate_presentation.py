#!/usr/bin/env python3
import argparse, sys, time, os
from pathlib import Path

# Añadir directorio base al path para importar el servicio
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.translation_service import Translator, PPTXEditor

def main():
    parser = argparse.ArgumentParser(description="Traductor de presentaciones PPTX")
    parser.add_argument("input_file", type=str, help="Archivo PPTX de entrada")
    parser.add_argument("-o", "--output", type=str, help="Ruta del archivo de salida")
    parser.add_argument("-l", "--language", type=str, default="en", 
                        choices=["en", "es", "fr", "de", "it", "pt"],
                        help="Idioma destino (por defecto: en)")
    parser.add_argument("--no-cache", action="store_true", help="Desactivar caché de traducciones")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: No se encuentra el archivo {input_path}")
        return 1
        
    if not input_path.is_file() or input_path.suffix.lower() != '.pptx':
        print(f"Error: El archivo debe ser PPTX: {input_path}")
        return 1
    
    output_path = args.output
    if not output_path:
        output_path = input_path.with_name(f"{input_path.stem}_translated_{args.language}{input_path.suffix}")
    else:
        output_path = Path(output_path)
    
    print(f"Iniciando traducción de {input_path.name} a {args.language}")
    print(f"Archivo de salida: {output_path}")
    
    try:
        # Crear instancia del traductor
        translator = Translator(target_language=args.language, use_cache=not args.no_cache)
        editor = PPTXEditor(translator)
        
        # Medir tiempo
        start_time = time.time()
        
        # Procesar el archivo
        result_path = editor.process_pptx(input_path, output_path)
        
        # Mostrar resultado
        elapsed = time.time() - start_time
        
        if result_path and os.path.exists(result_path):
            print(f"\n✅ Traducción completada en {elapsed:.2f} segundos")
            print(f"Archivo generado: {result_path}")
            
            # Estadísticas básicas
            print(f"\nEstadísticas:")
            print(f"- Diapositivas procesadas: {editor.slides_processed}")
            print(f"- Textos traducidos: {editor.total_texts}")
            
            # Estadísticas de caché si está habilitada
            if not args.no_cache:
                cache_hits = translator.cache_hits
                cache_misses = translator.cache_misses
                total = cache_hits + cache_misses
                hit_rate = cache_hits / total * 100 if total > 0 else 0
                print(f"- Caché: {cache_hits} hits, {cache_misses} misses ({hit_rate:.1f}% aciertos)")
            
            return 0
        else:
            print(f"\n❌ Error: No se generó el archivo de salida")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error durante la traducción: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 