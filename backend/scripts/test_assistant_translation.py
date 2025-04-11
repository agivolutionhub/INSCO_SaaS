#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión con la API de asistentes de OpenAI.
Traduce un texto simple para comprobar que la configuración es correcta.
"""

import os
import time
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Añadir directorio padre al path para poder importar desde módulos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Cargar variables de entorno
config_path = Path(__file__).parent.parent / "config" / ".env"
load_dotenv(config_path)

# Configurar cliente OpenAI
client = OpenAI()
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "asst_mBShBt93TIVI0PKE7zsNO0eZ")
OPENAI_BETA_HEADER = {"OpenAI-Beta": "assistants=v2"}

def translate_test(text="Hola mundo", target_language="English"):
    """
    Función de prueba para traducir un texto usando la API de asistentes.
    """
    print(f"Probando traducción de: '{text}' al {target_language}")
    print(f"Usando asistente ID: {ASSISTANT_ID}")
    print(f"API Key configurada: {bool(os.getenv('OPENAI_API_KEY'))}")
    print("-" * 40)
    
    try:
        # Crear un thread
        start_time = time.time()
        thread = client.beta.threads.create(
            extra_headers=OPENAI_BETA_HEADER
        )
        print(f"✓ Thread creado: {thread.id}")
        
        # Añadir mensaje
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Traduce este texto al {target_language}: {text}",
            extra_headers=OPENAI_BETA_HEADER
        )
        print(f"✓ Mensaje añadido")
        
        # Ejecutar asistente
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            extra_headers=OPENAI_BETA_HEADER
        )
        print(f"✓ Ejecución iniciada: {run.id}")
        
        # Esperar respuesta
        print("Esperando respuesta:", end="", flush=True)
        while run.status in ["queued", "in_progress"]:
            print(".", end="", flush=True)
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
                extra_headers=OPENAI_BETA_HEADER
            )
        print()
        
        # Verificar estado
        if run.status != "completed":
            print(f"❌ Error: La ejecución terminó con estado {run.status}")
            if hasattr(run, "last_error"):
                print(f"   Detalles del error: {run.last_error}")
            return False
        
        # Obtener mensajes
        messages = client.beta.threads.messages.list(
            thread_id=thread.id,
            extra_headers=OPENAI_BETA_HEADER
        )
        
        # Buscar respuesta del asistente
        for msg in messages.data:
            if msg.role == "assistant":
                for content in msg.content:
                    if content.type == "text":
                        translation = content.text.value
                        duration = time.time() - start_time
                        print(f"✓ Traducción recibida en {duration:.2f} segundos")
                        print(f"Original: '{text}'")
                        print(f"Traducción: '{translation}'")
                        return True
        
        print("❌ No se encontró respuesta del asistente")
        return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Probar con diferentes textos
    test_texts = [
        ("Hola mundo", "English"),
        ("El cielo es azul", "French"),
        ("Máquina de traducción", "German")
    ]
    
    success = True
    for text, lang in test_texts:
        print("\n" + "=" * 50)
        if not translate_test(text, lang):
            success = False
        print("=" * 50)
    
    if success:
        print("\n✅ Todas las pruebas completadas con éxito")
        sys.exit(0)
    else:
        print("\n❌ Algunas pruebas fallaron")
        sys.exit(1) 