"""
Rutas para procesamiento y manipulación de vídeos.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uuid
import shutil
from pathlib import Path
import os
from typing import Dict, Any, Optional

from services.video_service import cut_video, get_video_info

router = APIRouter(tags=["video"])

# Obtener directorios de almacenamiento desde la configuración principal
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "tmp/uploads"
PROCESSED_DIR = BASE_DIR / "tmp/videos"

# Crear directorios si no existen
for directory in [UPLOAD_DIR, PROCESSED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Definir modelo de solicitud para corte de vídeo
class CutVideoRequest(BaseModel):
    file_id: str
    start_time: float
    end_time: float
    original_name: Optional[str] = None

# Ruta original para compatibilidad con el frontend existente
@router.post("/api/upload-video-for-cut")
async def upload_video_for_cut(file: UploadFile = File(...)):
    """Sube un archivo de vídeo para su procesamiento (ruta compatible con frontend)."""
    return await _upload_video_impl(file)

# Ruta nueva siguiendo el estándar de la API
@router.post("/api/video/upload")
async def upload_video(file: UploadFile = File(...)):
    """Sube un archivo de vídeo para su procesamiento (ruta nueva estandarizada)."""
    return await _upload_video_impl(file)

# Implementación compartida para ambas rutas
async def _upload_video_impl(file: UploadFile):
    """Implementación compartida para subir vídeos."""
    try:
        # Validar extensión
        filename = file.filename
        file_extension = Path(filename).suffix.lower()
        
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        if file_extension not in valid_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato no válido. Formatos permitidos: {', '.join(valid_extensions)}"
            )
        
        # Generar ID único y guardar archivo
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}{file_extension}"
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Obtener información del vídeo
        video_info = get_video_info(file_path)
        
        return {
            "file_id": file_id,
            "filename": filename,
            "path": str(file_path),
            "duration": video_info.get("duration", 0),
            "size": video_info.get("size", file_path.stat().st_size),
            "format": video_info.get("format", file_extension[1:]),
            "width": video_info.get("width", 0),
            "height": video_info.get("height", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el vídeo: {str(e)}")

# Ruta original para compatibilidad con el frontend existente (usando JSON)
@router.post("/api/cut-video")
async def cut_video_original_endpoint(request: CutVideoRequest):
    """Corta un segmento de un vídeo (ruta compatible con frontend)."""
    return await _cut_video_impl(
        file_id=request.file_id,
        start_time=request.start_time,
        end_time=request.end_time,
        original_name=request.original_name
    )

# Rutas alternativas (ambas aceptan datos de formulario para compatibilidad)
@router.post("/api/video/cut-form")
async def cut_video_form_endpoint(
    file_id: str = Form(...),
    start_time: float = Form(...),
    end_time: float = Form(...),
    original_name: Optional[str] = Form(None)
):
    """Corta un segmento de un vídeo (para formularios)."""
    return await _cut_video_impl(file_id, start_time, end_time, original_name)

# Ruta nueva siguiendo el estándar de la API (JSON)
@router.post("/api/video/cut")
async def cut_video_endpoint(request: CutVideoRequest):
    """Corta un segmento de un vídeo (ruta nueva estandarizada)."""
    return await _cut_video_impl(
        file_id=request.file_id,
        start_time=request.start_time,
        end_time=request.end_time,
        original_name=request.original_name
    )

# Implementación compartida para ambas rutas
async def _cut_video_impl(file_id: str, start_time: float, end_time: float, original_name: Optional[str] = None):
    """Implementación compartida para cortar vídeos."""
    try:
        # Buscar archivo original
        input_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        if not input_files:
            raise HTTPException(status_code=404, detail="Vídeo no encontrado")
        
        input_file = input_files[0]
        file_extension = input_file.suffix
        
        # Definir archivo de salida
        output_filename = f"{original_name or file_id}_cortado{file_extension}"
        output_path = PROCESSED_DIR / output_filename
        
        # Cortar vídeo
        result = cut_video(
            video_path=input_file,
            output_path=output_path,
            start_time=start_time,
            end_time=end_time
        )
        
        # Preparar URL de descarga
        download_url = f"/api/download/{output_filename}"
        
        return {
            "status": "success",
            "file_id": file_id,
            "original_name": original_name,
            "output_filename": output_filename,
            "download_url": download_url,
            "video_info": {
                "duration": result.get("duration", end_time - start_time),
                "size": result.get("size", 0),
                "format": result.get("format", file_extension[1:])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cortar el vídeo: {str(e)}")

# Rutas para descargar vídeos
@router.get("/api/video/download/{filename}")
@router.get("/api/download-video/{filename}")
async def download_video(filename: str):
    """Descarga un vídeo procesado."""
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4"  # Podría ajustarse según la extensión
    ) 