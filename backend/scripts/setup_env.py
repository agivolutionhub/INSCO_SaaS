#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from rich.console import Console

console = Console()

def setup_env():
    """Configura las variables de entorno de OpenAI desde diferentes fuentes"""
    
    console.print("[bold green]Configurando variables de entorno para OpenAI...[/bold green]")
    
    # Posibles ubicaciones del archivo .env
    env_paths = [
        Path("/app/.env"),
        Path("/app/config/.env"),
        Path("/app/backend/config/.env"),
        Path(__file__).parent.parent / "config" / ".env",
    ]
    
    # Posibles ubicaciones de los archivos JSON de configuración
    json_configs = {
        "openapi": [
            Path("/app/config/openapi.json"),
            Path("/app/backend/config/openapi.json"),
            Path(__file__).parent.parent / "config" / "openapi.json",
        ],
        "sttapi": [
            Path("/app/config/sttapi.json"),
            Path("/app/backend/config/sttapi.json"),
            Path(__file__).parent.parent / "config" / "sttapi.json",
        ],
        "ttsapi": [
            Path("/app/config/ttsapi.json"),
            Path("/app/backend/config/ttsapi.json"),
            Path(__file__).parent.parent / "config" / "ttsapi.json",
        ],
        "translator": [
            Path("/app/config/translator.json"),
            Path("/app/backend/config/translator.json"),
            Path(__file__).parent.parent / "config" / "translator.json",
        ]
    }
    
    # Variables a buscar
    variables = {
        "OPENAI_API_KEY": None,
        "OPENAI_ASSISTANT_ID": None
    }
    
    # 1. Verificar si ya están en el entorno
    for var in variables:
        if value := os.environ.get(var):
            console.print(f"✅ Variable {var} ya configurada en el entorno")
            variables[var] = value
    
    # 2. Buscar en archivos .env
    for env_path in env_paths:
        if not env_path.exists():
            continue
        
        console.print(f"📄 Leyendo archivo: {env_path}")
        try:
            with open(env_path, "r") as f:
                for line in f:
                    if not line.strip() or line.strip().startswith("#"):
                        continue
                    
                    try:
                        key, value = line.strip().split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        if key in variables and not variables[key]:
                            variables[key] = value
                            os.environ[key] = value
                            console.print(f"✅ Variable {key} configurada desde {env_path}")
                    except ValueError:
                        console.print(f"⚠️ Línea mal formateada: {line.strip()}")
        except Exception as e:
            console.print(f"❌ Error leyendo {env_path}: {str(e)}")
    
    # 3. Buscar en archivos JSON de configuración
    console.print("\n[bold green]Buscando claves API en archivos JSON de configuración...[/bold green]")
    
    # Comprobar openapi.json primero para OPENAI_API_KEY
    if not variables["OPENAI_API_KEY"]:
        for config_path in json_configs["openapi"]:
            if not config_path.exists():
                continue
            
            try:
                console.print(f"📄 Leyendo configuración: {config_path}")
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                
                if "openai" in config_data and "api_key" in config_data["openai"]:
                    api_key = config_data["openai"]["api_key"]
                    if api_key:
                        variables["OPENAI_API_KEY"] = api_key
                        os.environ["OPENAI_API_KEY"] = api_key
                        console.print(f"✅ OPENAI_API_KEY configurada desde {config_path}")
                        break
            except Exception as e:
                console.print(f"❌ Error leyendo {config_path}: {str(e)}")
    
    # Comprobar sttapi.json para STT API key
    api_key_found = False
    for config_type, paths in json_configs.items():
        if config_type == "openapi":
            continue  # Ya procesado
            
        for config_path in paths:
            if not config_path.exists():
                continue
                
            try:
                console.print(f"📄 Leyendo configuración: {config_path}")
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                
                # Extraer clave API según el tipo de archivo
                api_key = None
                if config_type == "sttapi" and "stt" in config_data and "api_key" in config_data["stt"]:
                    api_key = config_data["stt"]["api_key"]
                    env_var = "STT_API_KEY"
                elif config_type == "ttsapi" and "tts" in config_data and "api_key" in config_data["tts"]:
                    api_key = config_data["tts"]["api_key"]
                    env_var = "TTS_API_KEY"
                
                if api_key:
                    os.environ[env_var] = api_key
                    console.print(f"✅ {env_var} configurada desde {config_path}")
                    
                    # Si OPENAI_API_KEY no está configurada, usar esta clave como fallback
                    if not variables["OPENAI_API_KEY"]:
                        variables["OPENAI_API_KEY"] = api_key
                        os.environ["OPENAI_API_KEY"] = api_key
                        console.print(f"✅ OPENAI_API_KEY configurada desde {config_path} (fallback)")
                        api_key_found = True
            except Exception as e:
                console.print(f"❌ Error leyendo {config_path}: {str(e)}")
    
    # Mostrar estado final
    console.print("\n[bold green]Estado final de variables de entorno:[/bold green]")
    for var, value in variables.items():
        if value:
            # Mostrar solo parcialmente para mantener la seguridad
            masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "****"
            console.print(f"[green]✓ {var} = {masked}[/green]")
        else:
            console.print(f"[red]✗ {var} no configurada[/red]")
    
    # Verificar variables de APIs adicionales
    for env_var in ["STT_API_KEY", "TTS_API_KEY"]:
        if value := os.environ.get(env_var):
            # Mostrar solo parcialmente para mantener la seguridad
            masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "****"
            console.print(f"[green]✓ {env_var} = {masked}[/green]")
    
    # Verificar si tenemos las variables mínimas necesarias
    if not variables["OPENAI_API_KEY"]:
        console.print("[bold red]⚠️ ADVERTENCIA: No se encontró la API key de OpenAI[/bold red]")
        console.print("Las funciones de IA no estarán disponibles.")
    else:
        console.print("[bold green]✅ Configuración de OpenAI completada[/bold green]")

if __name__ == "__main__":
    setup_env() 