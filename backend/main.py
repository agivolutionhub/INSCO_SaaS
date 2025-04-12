from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import time
import sys
from rich.console import Console

# Añadir el directorio actual al path de Python
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Importar utilidades propias
from scripts.utils import setup_logger, ensure_dir

# Configurar logger
logger = setup_logger("main")

# Consola para logs enriquecidos
console = Console()

# Crear una instancia de FastAPI
app = FastAPI(title="INSCO API", description="API mínima para el proyecto INSCO")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3001", "http://147.93.85.32:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Obtener directorio base
BASE_DIR = Path(__file__).resolve().parent

# Directorios de almacenamiento
TMP_DIR = ensure_dir(BASE_DIR / "tmp")
STORAGE_DIR = ensure_dir(BASE_DIR / "storage")
CONFIG_DIR = ensure_dir(BASE_DIR / "config")

# Log de directorios creados
console.print(f"[green]Directorio temporal:[/green] {TMP_DIR}")
console.print(f"[green]Directorio de almacenamiento:[/green] {STORAGE_DIR}")
console.print(f"[green]Directorio de configuración:[/green] {CONFIG_DIR}")

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
        "environment": "development"
    }
    
    # Verificar que los directorios críticos sean accesibles
    try:
        # Comprobar directorio de almacenamiento
        storage_test = STORAGE_DIR / "test.txt"
        with open(storage_test, "w") as f:
            f.write("test")
        storage_test.unlink()  # Eliminar archivo de prueba
        
        # Comprobar directorio temporal
        tmp_test = TMP_DIR / "test.txt"
        with open(tmp_test, "w") as f:
            f.write("test")
        tmp_test.unlink()  # Eliminar archivo de prueba
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        return JSONResponse(status_code=500, content=health_status)
    
    return health_status

# Mostrar información de inicio
console.print("[bold green]API INSCO iniciada correctamente[/bold green]")
console.print("[green]Endpoints disponibles:[/green]")
console.print("  • [bold]/api/root[/bold] - Endpoint principal")
console.print("  • [bold]/health[/bold] - Verificación de salud") 