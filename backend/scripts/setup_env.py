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
    
    # Posibles ubicaciones del archivo de credenciales
    credentials_paths = [
        Path("/app/config/auth_credentials.json"),
        Path("/app/backend/config/auth_credentials.json"),
        Path(__file__).parent.parent / "config" / "auth_credentials.json",
    ]
    
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
    
    # 2. Buscar en archivo auth_credentials.json
    if not variables["OPENAI_API_KEY"] or not variables["OPENAI_ASSISTANT_ID"]:
        for credentials_path in credentials_paths:
            if not credentials_path.exists():
                continue
            
            try:
                console.print(f"📄 Leyendo credenciales desde: {credentials_path}")
                with open(credentials_path, "r") as f:
                    credentials = json.load(f)
                
                if "openai" in credentials:
                    if "api_key" in credentials["openai"] and not variables["OPENAI_API_KEY"]:
                        variables["OPENAI_API_KEY"] = credentials["openai"]["api_key"]
                        os.environ["OPENAI_API_KEY"] = credentials["openai"]["api_key"]
                        console.print(f"✅ OPENAI_API_KEY configurada desde {credentials_path}")
                    
                    if "assistant_id" in credentials["openai"] and not variables["OPENAI_ASSISTANT_ID"]:
                        variables["OPENAI_ASSISTANT_ID"] = credentials["openai"]["assistant_id"]
                        os.environ["OPENAI_ASSISTANT_ID"] = credentials["openai"]["assistant_id"]
                        console.print(f"✅ OPENAI_ASSISTANT_ID configurada desde {credentials_path}")
                
                if variables["OPENAI_API_KEY"] and variables["OPENAI_ASSISTANT_ID"]:
                    break
            except Exception as e:
                console.print(f"❌ Error leyendo {credentials_path}: {str(e)}")
    
    # Mostrar estado final
    console.print("\n[bold green]Estado final de variables de entorno:[/bold green]")
    for var, value in variables.items():
        if value:
            # Mostrar solo parcialmente para mantener la seguridad
            masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "****"
            console.print(f"[green]✓ {var} = {masked}[/green]")
        else:
            console.print(f"[red]✗ {var} no configurada[/red]")
    
    # Verificar si tenemos las variables mínimas necesarias
    if not variables["OPENAI_API_KEY"]:
        console.print("[bold red]⚠️ ADVERTENCIA: No se encontró la API key de OpenAI[/bold red]")
        console.print("Las funciones de IA no estarán disponibles.")
    else:
        console.print("[bold green]✅ Configuración de OpenAI completada[/bold green]")
    
    return variables

if __name__ == "__main__":
    setup_env() 