#!/usr/bin/env python3
import argparse, sys, json
from pathlib import Path

# Añadir el directorio base al path para importaciones
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.snapshot_service import extract_pptx_slides, DEFAULT_DPI, DEFAULT_FORMAT, DEFAULT_OUTPUT_DIR

def load_config(config_file=None):
    """Carga la configuración desde un archivo JSON"""
    config = {
        "dpi": DEFAULT_DPI,
        "format": DEFAULT_FORMAT,
        "output_dir": str(DEFAULT_OUTPUT_DIR)
    }
    
    if config_file and Path(config_file).exists():
        try:
            with open(config_file) as f:
                config.update(json.load(f))
        except: pass
    
    return config

def main():
    parser = argparse.ArgumentParser(description="Convertir presentaciones PPTX a imágenes")
    parser.add_argument("pptx_file", help="Archivo PPTX a convertir")
    parser.add_argument("-o", "--output-dir", help="Directorio de salida")
    parser.add_argument("-f", "--format", choices=["png", "jpg"], default=DEFAULT_FORMAT, 
                      help="Formato de imagen (png o jpg)")
    parser.add_argument("-d", "--dpi", type=int, default=DEFAULT_DPI, help="Resolución en DPI")
    parser.add_argument("--config", help="Archivo de configuración JSON")
    
    args = parser.parse_args()
    
    try:
        cfg = load_config(args.config)
        result = extract_pptx_slides(
            args.pptx_file,
            args.output_dir or cfg.get("output_dir"),
            args.format or cfg.get("format"),
            args.dpi or cfg.get("dpi")
        )
        
        print(f"\n✓ Convertidas {result['slides']} diapositivas")
        print(f"✓ Guardadas en: {result['output_dir']}")
        print(f"✓ Formato: {result['format']} @ {result['dpi']}dpi")
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())