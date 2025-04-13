from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import time
import sys
import os

# Añadir directorio actual al path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Importar el script de configuración de entorno
from scripts.setup_env import setup_env

# Obtener directorio base
BASE_DIR = Path(__file__).resolve().parent

# Función para verificar acceso a un directorio
def verify_directory_access(directory):
    """Verifica que un directorio sea accesible para lectura/escritura"""
    try:
        test_file = directory / "test.txt"
        with open(test_file, "w") as f:
            f.write("test")
        test_file.unlink()
        return True, None
    except Exception as e:
        return False, str(e)

def create_app():
    """Crea y configura la aplicación FastAPI"""
    # Configurar variables de entorno
    env_vars = setup_env()
    
    # Crear una instancia de FastAPI
    app = FastAPI(
        title="INSCO API",
        description="API para el proyecto INSCO",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # Configurar CORS
    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3001",
        "http://147.93.85.32:3001",
        "http://147.93.85.32:8088",
        # Añadir dominios de producción si es necesario
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Directorios de almacenamiento
    TMP_DIR = BASE_DIR / "tmp"
    STORAGE_DIR = BASE_DIR / "storage"
    
    # Crear directorios
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Directorio temporal: {TMP_DIR}")
    print(f"Directorio de almacenamiento: {STORAGE_DIR}")
    
    # Montar directorios estáticos
    app.mount("/tmp", StaticFiles(directory=TMP_DIR), name="temp")
    app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")
    
    @app.get("/api/root")
    async def root():
        return {"message": "Bienvenido a la API de INSCO"}
    
    @app.get("/health")
    async def health_check():
        """Endpoint para verificar la salud del servicio (usado por Docker healthcheck)"""
        health_status = {
            "status": "healthy",
            "time": time.time(),
            "version": "1.0.0",
            "openai_configured": bool(env_vars.get("variables", {}).get("OPENAI_API_KEY"))
        }
        
        # Verificar que los directorios críticos sean accesibles
        storage_ok, storage_error = verify_directory_access(STORAGE_DIR)
        tmp_ok, tmp_error = verify_directory_access(TMP_DIR)
        
        if not (storage_ok and tmp_ok):
            health_status["status"] = "unhealthy"
            health_status["error"] = storage_error or tmp_error
            return JSONResponse(status_code=500, content=health_status)
        
        return health_status
    
    # Mostrar información de inicio
    print("API INSCO iniciada correctamente")
    print("Endpoints disponibles:")
    print("  • /api/root - Endpoint principal")
    print("  • /health - Verificación de salud")
    print(f"OpenAI configurado: {'Sí' if env_vars.get('variables', {}).get('OPENAI_API_KEY') else 'No'}")
    
    return app

# Crear aplicación
app = create_app() 