# Informe Optimizado de Refactorización: Archivo `/main.py`

## 1. Estructura Actual

El análisis del archivo `main.py` muestra la siguiente estructura y características:

### 📊 Visión General

El archivo `main.py` actúa como punto de entrada principal de la aplicación FastAPI. Actualmente contiene:

- **Importaciones**: Módulos del sistema, librerías externas y módulos internos.
- **Configuración básica**: Inicialización de FastAPI, configuración CORS y creación de directorios.
- **Importación de scripts**: Funciones directas desde scripts (`scripts/*.py`).
- **Importación de routers**: Routers desde módulos de rutas (`routes/*.py`).
- **Registro de routers**: Inclusión de blueprints en la aplicación principal.
- **Endpoints directos**: Algunos endpoints definidos directamente en el archivo principal.
- **Código de inicialización**: Para ejecutar la aplicación con uvicorn.

## 2. Inconsistencias Detectadas

- **Mezcla de patrones de organización**: Algunos endpoints definidos directamente en `main.py`, otros en routers.
- **Duplicación de funcionalidad**: Endpoints similares entre `main.py` y routers.
- **Configuración manual de directorios**: Creación repetitiva de múltiples directorios.
- **Configuración hardcodeada**: Valores codificados directamente como URLs CORS o puertos.
- **Manejo inconsistente de archivos**: Código duplicado para procesar archivos.

## 3. Propuesta Optimizada de Refactorización

### 3.1. Enfoque Principal: Simplificación y Delegación

La propuesta se centra en simplificar `main.py` para que actúe exclusivamente como punto de entrada, delegando toda la funcionalidad específica a módulos especializados:

```python
"""
Punto de entrada principal para la API de INSCO.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
from pathlib import Path
import uvicorn

# Configuración básica
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "tmp/uploads"
PROCESSED_DIR = BASE_DIR / "tmp/processed"
CAPTURES_DIR = BASE_DIR / "tmp/captures"
AUDIO_DIR = BASE_DIR / "tmp/audio"
TRANSCRIPTS_DIR = BASE_DIR / "storage/transcripts"
VIDEO_DIR = BASE_DIR / "tmp/videos"
AUDIO_OUTPUT_DIR = BASE_DIR / "storage/audio"
AUTOFIT_DIR = BASE_DIR / "storage/autofit"

# Crear directorios necesarios
for directory in [UPLOAD_DIR, PROCESSED_DIR, CAPTURES_DIR, AUDIO_DIR, 
                 TRANSCRIPTS_DIR, VIDEO_DIR, AUDIO_OUTPUT_DIR, AUTOFIT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Crear la aplicación FastAPI
app = FastAPI(title="INSCO API")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar routers
from routes.translate_pptx import router as translate_pptx_router
from routes.split_pptx import router as split_pptx_router
from routes.snapshot import router as snapshot_router
from routes.autofit import router as autofit_router
from routes.transcript import router as transcript_router
from routes.text_to_speech import router as text_to_speech_router

# Registrar routers
for router in [
    translate_pptx_router,
    split_pptx_router,
    snapshot_router,
    autofit_router,
    transcript_router,
    text_to_speech_router
]:
    app.include_router(router)

# Mover endpoints específicos a un nuevo router
from routes.common import router as common_router
app.include_router(common_router)

@app.get("/")
async def root():
    return {"message": "INSCO API está funcionando"}

# Ejecución directa
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8088))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
```

### 3.2. Creación de `routes/common.py` para Endpoints Existentes

Mover los endpoints definidos directamente en `main.py` a un nuevo router específico:

```python
# routes/common.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import shutil, uuid
from pathlib import Path

# Importar servicios
from scripts.snapshot import extract_pptx_slides

router = APIRouter(prefix="/api", tags=["common"])

# Obtener BASE_DIR
from main import BASE_DIR, UPLOAD_DIR, PROCESSED_DIR, CAPTURES_DIR

@router.post("/upload-pptx-for-captures")
async def upload_pptx_for_captures(file: UploadFile = File(...)):
    """Sube un archivo PPTX para generar capturas."""
    try:
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem
        file_extension = Path(filename).suffix
        
        if file_extension.lower() != '.pptx':
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PPTX")
        
        file_location = UPLOAD_DIR / f"{file_id}{file_extension}"
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@router.post("/process-captures")
async def process_captures(file_id: str = Form(...), original_name: str = Form(None)):
    """Procesa un archivo PPTX para generar capturas."""
    try:
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        file_path = files[0]
        
        capture_dir = CAPTURES_DIR / file_id
        capture_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            stats = extract_pptx_slides(
                pptx_path=file_path,
                output_dir=capture_dir,
                format="png",
                dpi=300
            )
            
            image_urls = []
            for img_path in sorted(capture_dir.glob("*.png")):
                rel_path = img_path.relative_to(BASE_DIR)
                image_urls.append(f"/{str(rel_path)}")
            
            return {
                "status": "success",
                "file_id": file_id,
                "original_name": original_name or Path(file_path).stem,
                "slides_count": stats["slides"],
                "image_urls": image_urls
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al generar capturas: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Descarga un archivo procesado."""
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename
    )
```

### 3.3. Creación de Archivo para Configuración (opcional)

Si se desea una configuración más flexible, se puede crear un archivo de configuración simple:

```python
# config.py
import os
from pathlib import Path

# Directorio base
BASE_DIR = Path(__file__).resolve().parent

# Configuración del servidor
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8088))
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

# Configuración CORS
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

# Directorios
DIRS = {
    "UPLOAD": BASE_DIR / "tmp/uploads",
    "PROCESSED": BASE_DIR / "tmp/processed",
    "CAPTURES": BASE_DIR / "tmp/captures",
    "AUDIO": BASE_DIR / "tmp/audio",
    "TRANSCRIPTS": BASE_DIR / "storage/transcripts",
    "VIDEO": BASE_DIR / "tmp/videos",
    "AUDIO_OUTPUT": BASE_DIR / "storage/audio",
    "AUTOFIT": BASE_DIR / "storage/autofit",
}

# Crear directorios
def create_directories():
    """Crea todos los directorios necesarios."""
    for directory in DIRS.values():
        directory.mkdir(parents=True, exist_ok=True)
```

### 3.4. Estrategia de Compatibilidad Durante la Transición

Para asegurar que la refactorización no rompa la integración con el frontend:

1. **Middleware de compatibilidad incorporado en FastAPI**:
   ```python
   # En main.py, después de crear la app
   
   # Lista de endpoints críticos usados por el frontend
   LEGACY_ENDPOINTS = [
       "/api/autofit/upload-pptx", 
       "/api/autofit/process",
       # Añadir otros endpoints críticos
   ]
   
   @app.middleware("http")
   async def compatibility_middleware(request, call_next):
       # Procesar la solicitud normalmente
       response = await call_next(request)
       
       # Solo para endpoints legacy y respuestas JSON
       if (request.url.path in LEGACY_ENDPOINTS and 
           response.headers.get("content-type") == "application/json"):
           try:
               # Verificar si la respuesta tiene el nuevo formato con "data"
               body = await response.body()
               data = json.loads(body)
               
               if isinstance(data, dict) and "status" in data and "data" in data:
                   # Adaptar al formato esperado por el frontend
                   from fastapi.responses import JSONResponse
                   return JSONResponse(content=data["data"])
           except:
               # Si hay error en la transformación, devolver respuesta original
               pass
               
       return response
   ```

2. **Pruebas antes de implementar**:
   - Documentar y probar cada endpoint usado por el frontend
   - Verificar estructura de respuesta antes y después de refactorizar
   - Implementar cambios gradualmente, validando cada ruta

### 3.5. Documentación de Compatibilidad API

Crear un documento simple en el repositorio para registrar contratos API:

```
# api_contracts.md (en la raíz del proyecto)

## Contratos API para Frontend

Los siguientes endpoints son consumidos directamente por el frontend y deben mantener su estructura de respuesta:

### POST /api/autofit/upload-pptx
Respuesta:
```json
{
  "file_id": "string",
  "filename": "string",
  "original_name": "string"
}
```

### POST /api/autofit/process
Respuesta:
```json
{
  "file_id": "string",
  "output_filename": "string",
  "download_url": "string"
}
```
```

Este documento servirá como referencia durante refactorizaciones para evitar romper contratos API.

## 4. Implementación Pragmática

### Fase 1: Extraer Endpoints a Router (1 día)
- Crear `routes/common.py`
- Mover endpoints específicos desde `main.py`
- Verificar funcionalidad

### Fase 2: Simplificar `main.py` (1/2 día)
- Limpiar importaciones innecesarias
- Estandarizar registro de routers
- Mejorar creación de directorios

### Fase 3: Opcional - Extraer Configuración (1/2 día)
- Crear `config.py` para valores configurables
- Ajustar `main.py` para usar la configuración

## 5. Comparación con Enfoque Original

| Área | Enfoque Original | Enfoque Optimizado |
|------|------------------|-------------------|
| **Complejidad** | Alta (patrón Factory, múltiples módulos) | Baja (extracción simple de endpoints) |
| **Tiempo** | 2-3 días | 1-2 días |
| **Riesgo** | Alto (cambios estructurales significativos) | Bajo (cambios mínimos) |
| **Compatibilidad** | Requiere adaptaciones en otros módulos | Mantiene compatibilidad casi total |

## 6. Conclusión

Este enfoque optimizado proporciona una mejora significativa en la organización del código sin introducir complejidad innecesaria. Al mover los endpoints específicos a un router dedicado y simplificar la configuración, se logra un archivo `main.py` más limpio y centrado en su función principal como punto de entrada.

La propuesta es pragmática y puede implementarse de forma rápida y con bajo riesgo, manteniendo la compatibilidad con el código existente y sentando las bases para mejoras futuras. 