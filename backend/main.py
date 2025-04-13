from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys, os

# Obtener el directorio base
BASE_DIR = Path(__file__).resolve().parent

# Añadir directorio de scripts al path
sys.path.insert(0, str(BASE_DIR))

# Importar el router de autofit
from scripts.diapos_autofit import get_autofit_router

# Crear una instancia de FastAPI
app = FastAPI(
    title="INSCO Autofit", 
    description="API minificada para el proyecto INSCO: Herramienta Autofit",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", 
                  "https://tools.inscoia.es"],
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
    print(f"Directorio creado: {directory}")

# Montar directorios estáticos
app.mount("/tmp", StaticFiles(directory=TMP_DIR), name="temp")
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# Detectar frontend
static_dir = Path("/app/static")
if not static_dir.exists():
    static_dir = BASE_DIR.parent / "frontend" / "dist"
        
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    print(f"Frontend montado desde: {static_dir}")
else:
    print("⚠️ Frontend no encontrado. Solo API disponible")

# Incluir router de autofit
app.include_router(get_autofit_router())

@app.get("/api/root")
async def root():
    return {"message": "INSCO Autofit API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Endpoint para verificar la salud del servicio"""
    return {
        "status": "healthy",
        "service": "autofit",
        "storage": STORAGE_DIR.exists()
    }

# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8088))
    print(f"Iniciando servidor en puerto {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 