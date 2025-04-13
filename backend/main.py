from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys, os

# Obtener el directorio base
BASE_DIR = Path(__file__).resolve().parent

# Añadir directorio de scripts al path
sys.path.insert(0, str(BASE_DIR))

# Importar los routers
from scripts.diapos_autofit import get_autofit_router
from scripts.diapos_split import get_router as get_split_router
from scripts.diapos_translate import router as translate_router

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

# Establecer variables de entorno para los scripts
os.environ["STORAGE_DIR"] = str(STORAGE_DIR)
os.environ["CACHE_DIR"] = str(BASE_DIR / "config" / "cache")

# Montar directorios estáticos para archivos procesados
app.mount("/tmp", StaticFiles(directory=TMP_DIR), name="temp")
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

# Ya no montamos el frontend aquí, ya que se sirve separadamente en el puerto 3001
# Dejamos solamente la API en este puerto 8088

# Incluir routers
app.include_router(get_autofit_router())
app.include_router(get_split_router())
app.include_router(translate_router)

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

# Endpoint para manejar rutas del frontend
@app.get("/slides/{rest_of_path:path}")
async def serve_frontend_routes(rest_of_path: str):
    """
    Endpoint para manejar rutas de frontend como /slides/*
    Sirve directamente el archivo index.html del frontend para que React Router funcione
    """
    # Posibles ubicaciones del index.html, en orden de prioridad
    possible_paths = [
        BASE_DIR.parent / "frontend" / "dist" / "index.html",  # ../frontend/dist/index.html
        Path("/app/frontend/dist/index.html"),                 # Docker path
        Path("/frontend/dist/index.html"),                     # Alternative Docker path
    ]
    
    # Log para diagnóstico
    print(f"Buscando index.html para la ruta: /slides/{rest_of_path}")
    
    # Intentar cada ruta posible
    index_path = None
    for path in possible_paths:
        print(f"Comprobando ruta: {path}")
        if path.exists():
            index_path = path
            print(f"¡Encontrado! Usando: {index_path}")
            break
    
    # Verificar que se encontró alguna ruta válida
    if not index_path:
        error_msg = "No se encontró index.html en ninguna ubicación conocida"
        print(f"ERROR: {error_msg}")
        print(f"Directorio actual: {os.getcwd()}")
        print(f"Contenido de posibles directorios padre:")
        
        # Intentar listar contenidos de directorios padre para diagnóstico
        for parent_dir in [BASE_DIR.parent, Path("/app"), Path("/")]:
            if parent_dir.exists():
                print(f"Contenido de {parent_dir}:")
                try:
                    for item in parent_dir.iterdir():
                        print(f"  - {item}")
                except Exception as e:
                    print(f"  Error al listar contenido: {str(e)}")
        
        return {"error": error_msg, "checked_paths": [str(p) for p in possible_paths]}
    
    # Devolver el archivo index.html
    return FileResponse(index_path)

# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8088))
    print(f"Iniciando servidor en puerto {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 