#!/usr/bin/env python3
from pathlib import Path
import sys, re, argparse

# Añadir directorio de servicios al path
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.autofit_service import procesar_pptx, procesar_lote, DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR

def mostrar_menu_carpetas(directorio=DEFAULT_INPUT_DIR):
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    subcarpetas = [d for d in directorio.iterdir() if d.is_dir()]
    
    if not subcarpetas:
        print(f"No se encontraron subcarpetas en {directorio}")
        return None
    
    subcarpetas.sort(key=lambda c: int(re.match(r'^(\d+)\.?\s*', c.name).group(1)) 
                    if re.match(r'^(\d+)\.?\s*', c.name) else float('inf'))
    
    print("\nCarpetas disponibles:")
    print("0. [TODAS LAS CARPETAS]")
    for i, carpeta in enumerate(subcarpetas, 1):
        print(f"{i}. {carpeta.name} ({len(list(carpeta.glob('*.pptx')))} archivos PPTX)")
    
    while True:
        try:
            opcion = int(input("\nSelecciona carpeta a procesar [0]: ") or "0")
            if 0 <= opcion <= len(subcarpetas):
                return None if opcion == 0 else subcarpetas[opcion - 1]
            print(f"Opción inválida. Selecciona entre 0 y {len(subcarpetas)}")
        except ValueError:
            print("Ingresa un número válido")

def main():
    parser = argparse.ArgumentParser(description="Aplica autofit a presentaciones PPTX usando python-pptx")
    parser.add_argument("pptx_file", nargs="?", type=Path, help="Archivo PPTX a procesar (opcional)")
    parser.add_argument("-o", "--output", type=Path, help="Ruta de salida para el archivo procesado")
    parser.add_argument("-i", "--input-dir", type=Path, default=DEFAULT_INPUT_DIR, help="Directorio de búsqueda de archivos PPTX")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-b", "--batch", action="store_true", help="Procesar todos los archivos")
    group.add_argument("--interactive", action="store_true", help="Modo interactivo para seleccionar carpeta")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directorio para archivos de salida")
    
    args = parser.parse_args()
    
    try:
        if args.interactive or len(sys.argv) <= 1:
            carpeta = mostrar_menu_carpetas(args.input_dir)
            if carpeta is None:
                if input("¿Procesar TODAS las carpetas? (s/N): ").lower() == 's':
                    procesar_lote(args.input_dir, args.output_dir)
                else:
                    print("Operación cancelada")
            elif input(f"¿Procesar la carpeta {carpeta.name}? (S/n): ").lower() != 'n':
                procesar_lote(carpeta, args.output_dir / carpeta.name)
            else:
                print("Operación cancelada")
        elif args.pptx_file or (not args.batch and len(sys.argv) > 1):
            archivo = args.pptx_file or Path(sys.argv[1])
            salida = args.output or (Path(sys.argv[2]) if len(sys.argv) > 2 else None)
            procesar_pptx(archivo, salida)
        else:
            procesar_lote(args.input_dir, args.output_dir)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
