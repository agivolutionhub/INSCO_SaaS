#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path
from openai import OpenAI

def check_openai_connection():
    """Verifica la conexión con OpenAI siguiendo la estructura oficial de la documentación"""
    
    print("Verificando conexión con OpenAI...")
    
    # Configuración directa tal como se muestra en la documentación
    # CREDENCIALES EMBEBIDAS
    API_KEY = "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"
    ASSISTANT_ID = "asst_mBShBt93TIVI0PKE7zsNO0eZ"
    
    try:
        # Crear cliente tal como se muestra en la documentación oficial
        client = OpenAI(api_key=API_KEY)
        print(f"Cliente OpenAI inicializado con API key: {API_KEY[:8]}...{API_KEY[-4:]}")
        
        # 1. Verificar que podemos acceder al asistente
        print(f"Verificando acceso al asistente ID: {ASSISTANT_ID}")
        try:
            assistant = client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
            print(f"✅ Asistente encontrado: {assistant.name}")
        except Exception as e:
            print(f"❌ Error al acceder al asistente: {str(e)}")
            return False
        
        # 2. Crear thread según la documentación oficial
        print("\nCreando nuevo thread...")
        thread = client.beta.threads.create()
        print(f"Thread creado: {thread.id}")
        
        # 3. Añadir mensaje al thread según la documentación
        print("Añadiendo mensaje al thread...")
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Traduce el siguiente texto de español a inglés: 'Hola mundo'"
        )
        
        # 4. Ejecutar el asistente según la documentación
        print("Ejecutando asistente...")
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        # 5. Esperar a que se complete
        print("Esperando respuesta...")
        while run.status not in ["completed", "failed", "cancelled", "expired"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            
        if run.status != "completed":
            print(f"❌ Error en la ejecución del asistente: {run.status}")
            if hasattr(run, 'last_error'):
                print(f"Detalles del error: {run.last_error}")
            return False
        
        # 6. Obtener mensajes según la documentación
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        
        # Buscar mensaje del asistente
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        if not assistant_messages:
            print("❌ No se recibió respuesta del asistente")
            return False
            
        # Extraer texto de la respuesta
        try:
            content = assistant_messages[0].content[0].text.value
            print(f"\n✅ Traducción exitosa: {content}")
            return True
        except (IndexError, AttributeError) as e:
            print(f"❌ Error al extraer respuesta: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

if __name__ == "__main__":
    check_openai_connection() 