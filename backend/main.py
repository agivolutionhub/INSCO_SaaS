from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import time
from rich.console import Console

# Consola para logs
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

# Directorios de almacenamiento básicos
TMP_DIR = BASE_DIR / "tmp"
STORAGE_DIR = BASE_DIR / "storage"

# Crear directorios
TMP_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
console.print(f"Directorio temporal: {TMP_DIR}")
console.print(f"Directorio de almacenamiento: {STORAGE_DIR}")

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
        "version": "1.0.0"
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
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        return JSONResponse(status_code=500, content=health_status)
    
    return health_status

# Mostrar información de inicio
console.print("[bold green]API INSCO mínima iniciada correctamente[/bold green]")
console.print(f"[green]Endpoints disponibles:[/green]")
console.print(f"  • [bold]/api/root[/bold] - Endpoint principal")
console.print(f"  • [bold]/health[/bold] - Verificación de salud") 