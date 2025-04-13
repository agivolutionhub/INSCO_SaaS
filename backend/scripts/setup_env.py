#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

def setup_env():
    """Configura las variables de entorno de OpenAI desde diferentes fuentes"""
    
    print("Configurando variables de entorno para OpenAI...")
    
    # Posibles ubicaciones del archivo de credenciales
    credentials_paths = [
        Path("/app/config/auth_credentials.json"),
        Path("/app/backend/config/auth_credentials.json"),
        Path(__file__).parent.parent / "config" / "auth_credentials.json",
    ]
    
    # Variables a buscar
    variables = {
        "OPENAI_API_KEY": None,
        "OPENAI_ASSISTANT_ID": None,
        "OPENAI_MODEL": None,
        "OPENAI_TRANSCRIPTION_MODEL": None,
        "OPENAI_TTS_MODEL": None
    }
    
    # Configuración adicional
    config = {
        "models": {},
        "params": {},
        "tts_voices": []
    }
    
    # 1. Verificar si ya están en el entorno
    for var in variables:
        if value := os.environ.get(var):
            variables[var] = value
    
    # 2. Buscar en archivo auth_credentials.json
    for credentials_path in credentials_paths:
        if not credentials_path.exists():
            continue
        
        try:
            print(f"Leyendo credenciales desde: {credentials_path}")
            with open(credentials_path, "r") as f:
                credentials = json.load(f)
            
            # Cargar API key y Assistant ID desde la sección openai
            if "openai" in credentials:
                _load_openai_credentials(credentials, variables)
            
            # Cargar modelos si están definidos
            if "models" in credentials:
                config["models"] = credentials["models"]
                _load_model_configs(credentials["models"], variables)
            
            # Cargar parámetros y voces TTS
            if "params" in credentials:
                config["params"] = credentials["params"]
            
            if "tts_voices" in credentials:
                config["tts_voices"] = credentials["tts_voices"]
            
            if variables["OPENAI_API_KEY"] and variables["OPENAI_ASSISTANT_ID"]:
                break
        except Exception as e:
            print(f"Error leyendo {credentials_path}: {str(e)}")
    
    # Verificar si tenemos las variables mínimas necesarias
    if not variables["OPENAI_API_KEY"]:
        print("ADVERTENCIA: No se encontró la API key de OpenAI")
        print("Las funciones de IA no estarán disponibles.")
    
    return {
        "variables": variables,
        "config": config
    }

def _load_openai_credentials(credentials, variables):
    """Carga credenciales de OpenAI desde el diccionario de configuración"""
    if "api_key" in credentials["openai"] and not variables["OPENAI_API_KEY"]:
        variables["OPENAI_API_KEY"] = credentials["openai"]["api_key"]
        os.environ["OPENAI_API_KEY"] = credentials["openai"]["api_key"]
    
    if "assistant_id" in credentials["openai"] and not variables["OPENAI_ASSISTANT_ID"]:
        variables["OPENAI_ASSISTANT_ID"] = credentials["openai"]["assistant_id"]
        os.environ["OPENAI_ASSISTANT_ID"] = credentials["openai"]["assistant_id"]

def _load_model_configs(models, variables):
    """Configura variables de entorno para los modelos de IA"""
    model_mappings = {
        "chat": "OPENAI_MODEL",
        "transcription": "OPENAI_TRANSCRIPTION_MODEL",
        "tts": "OPENAI_TTS_MODEL"
    }
    
    for model_type, env_var in model_mappings.items():
        if model_type in models and not variables[env_var]:
            variables[env_var] = models[model_type]
            os.environ[env_var] = models[model_type]

if __name__ == "__main__":
    setup_env() 