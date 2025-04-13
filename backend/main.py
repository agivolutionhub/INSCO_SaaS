from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys, os
import time
from rich.console import Console

# Obtener el directorio base
BASE_DIR = Path(__file__).resolve().parent

# Añadir directorio de scripts al path
sys.path.insert(0, str(BASE_DIR))

# Importar el módulo setup_env
from scripts.setup_env import setup_env

# Importar el router de autofit
from scripts.diapos_autofit import get_autofit_router

# Configurar entorno
env_config = setup_env()
console = Console()

# Crear una instancia de FastAPI
app = FastAPI(title="INSCO API", description="API minificada para el proyecto INSCO")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorios de almacenamiento (versión mínima)
STORAGE_DIR = BASE_DIR / "storage"
TMP_DIR = BASE_DIR / "tmp"

# Crear directorios básicos
for directory in [STORAGE_DIR, TMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    console.print(f"Directorio creado: {directory}")

# Verificar configuración de OpenAI
api_key = os.getenv('OPENAI_API_KEY')
console.print(f"OpenAI API Key configurada: {bool(api_key)}")

# Montar directorios estáticos
app.mount("/tmp", StaticFiles(directory=TMP_DIR), name="temp")
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# Comprobar si existe el directorio static en la ruta del contenedor o usar una ruta local
static_dir = Path("/app/static")
if not static_dir.exists():
    static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if not static_dir.exists():
        static_dir = BASE_DIR.parent / "frontend" / "dist"
        
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    console.print(f"Frontend montado desde: {static_dir}")
else:
    console.print("[bold red]⚠️ No se encontró el directorio static del frontend[/bold red]")

# Incluir router de autofit
app.include_router(get_autofit_router())

@app.get("/api/root")
async def root():
    return {"message": "Bienvenido a la API minificada de INSCO"}

@app.get("/health")
async def health_check():
    """Endpoint para verificar la salud del servicio (usado por Docker healthcheck)"""
    # Verificar los servicios críticos
    health_status = {
        "status": "healthy",
        "time": time.time(),
        "version": "1.0.0-min",
        "services": {
            "storage": True,
            "tmp": True
        }
    }
    
    # Verificar que los directorios críticos sean accesibles
    try:
        # Comprobar directorio de almacenamiento
        storage_test = STORAGE_DIR / "test.txt"
        with open(storage_test, "w") as f:
            f.write("test")
        os.unlink(storage_test)
        
        # Comprobar directorio temporal
        tmp_test = TMP_DIR / "test.txt"
        with open(tmp_test, "w") as f:
            f.write("test")
        os.unlink(tmp_test)
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        return JSONResponse(status_code=500, content=health_status)
    
    # Verificar que tenemos la clave API si está configurada para usar OpenAI
    if os.getenv('OPENAI_API_KEY'):
        health_status["services"]["openai"] = True
    else:
        health_status["status"] = "degraded"
        health_status["services"]["openai"] = False
        health_status["openai_error"] = "API Key no configurada"
    
    return health_status

# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8088))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 