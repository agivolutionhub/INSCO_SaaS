#!/usr/bin/env python3
"""
Script para probar la comunicación con el microservicio de conversión PPTX
"""
import requests
import sys
from pathlib import Path

def test_microservice_api():
    """Prueba las capacidades del microservicio para descubrir los endpoints disponibles"""
    print("Probando conexión al microservicio...")
    
    base_url = "http://147.93.85.32:8090"
    
    # Intentar obtener la documentación OpenAPI
    try:
        response = requests.get(f"{base_url}/openapi.json")
        response.raise_for_status()
        api_spec = response.json()
        
        print("\n✅ Conexión exitosa")
        print("\nEndpoints disponibles:")
        
        for path, methods in api_spec.get("paths", {}).items():
            for method, details in methods.items():
                print(f"  • {method.upper()} {path}")
                if details.get("parameters"):
                    print("    Parámetros:")
                    for param in details.get("parameters", []):
                        required = "obligatorio" if param.get("required") else "opcional"
                        print(f"      - {param.get('name')} ({param.get('in', 'query')}, {required})")
        
        return True
    except Exception as e:
        print(f"❌ Error al conectar con el microservicio: {str(e)}")
        return False

def test_file_upload(file_path):
    """Prueba la subida de archivos al microservicio"""
    if not Path(file_path).exists():
        print(f"❌ Error: El archivo {file_path} no existe")
        return False
    
    print(f"\nProbando subida de archivo {file_path}...")
    
    try:
        # Intentar con el endpoint para subir y convertir
        with open(file_path, "rb") as file:
            files = {'file': (Path(file_path).name, file, 'application/vnd.openxmlformats-officedocument.presentationml.presentation')}
            data = {
                'output_dir': '/tmp/output',
                'format': 'png',
                'dpi': '300'
            }
            
            response = requests.post(
                "http://147.93.85.32:8090/upload_and_convert",
                files=files,
                data=data
            )
        
        # Verificar si la respuesta fue exitosa (código 2xx)
        if response.ok:
            print("✅ Subida exitosa")
            print(f"Respuesta: {response.json()}")
            return True
        else:
            print(f"❌ Error en la respuesta: {response.status_code}")
            print(f"Detalle: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error al subir archivo: {str(e)}")
        return False

if __name__ == "__main__":
    # Probar conexión al API
    test_microservice_api()
    
    # Si se proporciona un archivo, probar la subida
    if len(sys.argv) > 1:
        test_file_path = sys.argv[1]
        test_file_upload(test_file_path)
    else:
        print("\nPara probar la subida de un archivo, ejecute:")
        print(f"python {sys.argv[0]} ruta/al/archivo.pptx") 