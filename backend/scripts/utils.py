from pathlib import Path
import os
import logging
import json
from datetime import datetime

# Configurar logger básico
def setup_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Crear un manejador para la salida en consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Definir el formato del log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Agregar el manejador al logger
    logger.addHandler(console_handler)
    
    return logger

# Obtener el directorio base de la aplicación
def get_base_dir():
    return Path(__file__).resolve().parent.parent

# Cargar contenido de un archivo JSON
def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger = setup_logger("utils")
        logger.error(f"Error loading JSON file {file_path}: {str(e)}")
        return {}

# Guardar contenido en un archivo JSON
def save_json_file(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger = setup_logger("utils")
        logger.error(f"Error saving JSON file {file_path}: {str(e)}")
        return False

# Asegurar que un directorio existe
def ensure_dir(dir_path):
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    return Path(dir_path) 