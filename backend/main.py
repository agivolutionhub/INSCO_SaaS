from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys, os

# Obtener el directorio base
BASE_DIR = Path(__file__).resolve().parent

# Añadir directorio de scripts al path
sys.path.insert(0, str(BASE_DIR))

# Importar los routers
from scripts.diapos_autofit import get_autofit_router
from scripts.diapos_split import create_api

# Crear una instancia de FastAPI
app = FastAPI(
    title="INSCO Tools API", 
    description="API minificada para el proyecto INSCO: Herramientas de procesamiento de diapositivas",
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

# Montar directorios estáticos para archivos procesados
app.mount("/tmp", StaticFiles(directory=TMP_DIR), name="temp")
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# Ya no montamos el frontend aquí, ya que se sirve separadamente en el puerto 3001
# Dejamos solamente la API en este puerto 8088

# Incluir routers
app.include_router(get_autofit_router())

# Obtenemos el router de diapos_split (la función create_api devuelve una app FastAPI) 
# y obtenemos su router para incluirlo en nuestra app principal
split_app = create_api()
for router in split_app.routes:
    if hasattr(router, "include_in_schema") and router.include_in_schema:
        app.routes.append(router)

@app.get("/root")
async def root():
    return {"message": "INSCO Tools API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Endpoint para verificar la salud del servicio"""
    return {
        "status": "healthy",
        "service": "insco-tools",
        "storage": STORAGE_DIR.exists()
    }

# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8088))
    print(f"Iniciando servidor en puerto {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 