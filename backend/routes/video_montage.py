from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import os
import json
import uuid
import logging
from pathlib import Path

# Importar servicio
from services.video_montage_service import generate_video_montage

# Crear router sin prefijo, ya que las rutas incluyen el prefijo completo
router = APIRouter(tags=["video-montage"])

# Configurar logging
logger = logging.getLogger("video-montage-router")

# Obtener directorio base
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "tmp/uploads"
VIDEO_DIR = BASE_DIR / "tmp/videos"
AUDIO_DIR = BASE_DIR / "tmp/audio"
PROCESSED_DIR = BASE_DIR / "tmp/processed"

# Asegurar que existan los directorios
for directory in [UPLOAD_DIR, VIDEO_DIR, AUDIO_DIR, PROCESSED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Modelo para las imágenes con tiempos (formato interno)
class ImageTimeInfo(BaseModel):
    path: str
    start_time: float

# Modelo para la solicitud de montaje (formato interno)
class MontageRequest(BaseModel):
    audio_path: str
    images: List[ImageTimeInfo]
    output_filename: Optional[str] = None

# Modelos para compatibilidad con el frontend
class FrontendImageInfo(BaseModel):
    id: str
    startTime: float

class FrontendMontageRequest(BaseModel):
    audio_id: str
    images: List[FrontendImageInfo]
    original_name: Optional[str] = None
    output_format: Optional[str] = "mp4"

@router.post("/api/upload-audio-for-montage")
async def upload_audio_for_montage(file: UploadFile = File(...)):
    """Sube un archivo de audio para usarlo en un montaje."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No se proporcionó un archivo")
        
        ext = Path(file.filename).suffix.lower()
        if ext not in ['.mp3', '.wav', '.aac', '.m4a']:
            raise HTTPException(
                status_code=400, 
                detail="Formato de audio no soportado. Use MP3, WAV, AAC o M4A"
            )
        
        # Generar ID único
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        file_path = AUDIO_DIR / f"{file_id}{ext}"
        
        # Guardar archivo
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Error al guardar el archivo de audio")
        
        logger.info(f"Audio guardado exitosamente: {file_path}")
        
        return {
            "file_id": file_id,
            "original_name": original_name,
            "filename": file.filename,
            "file_path": str(file_path),
            "status": "uploaded"
        }
        
    except HTTPException as he:
        logger.error(f"Error HTTP en upload_audio_for_montage: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"Error al subir audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.post("/api/upload-image-for-montage")
async def upload_image_for_montage(file: UploadFile = File(...)):
    """Sube una imagen para usarla en un montaje."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No se proporcionó un archivo")
        
        ext = Path(file.filename).suffix.lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            raise HTTPException(
                status_code=400, 
                detail="Formato de imagen no soportado. Use JPG o PNG"
            )
        
        # Generar ID único
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        file_path = UPLOAD_DIR / f"{file_id}{ext}"
        
        # Guardar archivo
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Error al guardar la imagen")
        
        return {
            "file_id": file_id,
            "original_name": original_name,
            "filename": file.filename,
            "file_path": str(file_path),
            "status": "uploaded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir imagen: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.post("/api/generate-montage")
async def generate_montage_endpoint(request: FrontendMontageRequest):
    """Crea un montaje de vídeo a partir de audio e imágenes.
    Acepta el formato de datos enviado por el frontend."""
    try:
        logger.info(f"Recibida solicitud de montaje: {request.dict()}")
        
        # Buscar el archivo de audio por ID
        audio_id = request.audio_id
        audio_files = list(AUDIO_DIR.glob(f"{audio_id}.*"))
        
        if not audio_files:
            raise HTTPException(status_code=404, detail=f"Archivo de audio con ID {audio_id} no encontrado")
        
        audio_path = str(audio_files[0])
        
        # Construir datos de imágenes
        image_data = []
        for img in request.images:
            # Buscar la imagen por ID
            image_id = img.id
            image_files = list(UPLOAD_DIR.glob(f"{image_id}.*"))
            
            if not image_files:
                raise HTTPException(status_code=404, detail=f"Imagen con ID {image_id} no encontrada")
            
            image_path = str(image_files[0])
            
            image_data.append({
                "path": image_path,
                "start_time": img.startTime
            })
        
        # Ordenar por tiempo
        image_data.sort(key=lambda x: x["start_time"])
        
        # Configurar salida
        output_filename = f"{request.original_name or 'montage'}_{uuid.uuid4().hex[:8]}.{request.output_format or 'mp4'}"
        
        logger.info(f"Iniciando generación de montaje con {len(image_data)} imágenes y audio {audio_path}")
        
        # Crear montaje
        result = generate_video_montage(
            audio_path=audio_path,
            image_paths=image_data,
            output_dir=str(VIDEO_DIR),
            output_filename=output_filename
        )
        
        if result['status'] != 'success':
            logger.error(f"Error en generación de montaje: {result.get('error', 'Error desconocido')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Error desconocido'))
        
        # Añadir URL para descargar
        output_filename = Path(result['output_path']).name
        result['download_url'] = f"/api/download-montage/{output_filename}"
        
        logger.info(f"Montaje generado exitosamente: {result['output_path']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear montaje: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al crear el montaje: {str(e)}")

@router.post("/api/process-montage")
async def process_montage(
    audio_path: str = Form(...),
    image_paths_json: str = Form(...),
    output_filename: Optional[str] = Form(None)
):
    """Procesa un montaje usando rutas de archivos existentes."""
    try:
        # Validar audio
        if not os.path.exists(audio_path):
            raise HTTPException(status_code=400, detail=f"Archivo de audio no encontrado: {audio_path}")
        
        # Validar y parsear JSON de imágenes
        try:
            image_paths = json.loads(image_paths_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="El JSON de imágenes no es válido")
        
        if not isinstance(image_paths, list):
            raise HTTPException(status_code=400, detail="El JSON debe contener una lista de imágenes")
        
        # Verificar estructura y existencia de imágenes
        for item in image_paths:
            if not isinstance(item, dict) or 'path' not in item or 'start_time' not in item:
                raise HTTPException(status_code=400, detail="Cada elemento debe tener 'path' y 'start_time'")
            
            if not os.path.exists(item['path']):
                raise HTTPException(status_code=400, detail=f"Imagen no encontrada: {item['path']}")
        
        # Crear montaje
        result = generate_video_montage(
            audio_path=audio_path,
            image_paths=image_paths,
            output_dir=str(VIDEO_DIR),
            output_filename=output_filename
        )
        
        if result['status'] != 'success':
            raise HTTPException(status_code=500, detail=result.get('error', 'Error desconocido'))
        
        # Añadir URL para descargar
        output_filename = Path(result['output_path']).name
        result['download_url'] = f"/api/download-montage/{output_filename}"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al procesar montaje: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al crear el montaje: {str(e)}")

@router.get("/api/download-montage/{filename}")
async def download_montage(filename: str):
    """Descarga un archivo de montaje de vídeo."""
    try:
        # Buscar el archivo en varias ubicaciones posibles
        possible_paths = [
            VIDEO_DIR / filename,
            PROCESSED_DIR / filename
        ]
        
        file_path = None
        for path in possible_paths:
            if path.exists():
                file_path = path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al descargar montaje: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al descargar el archivo: {str(e)}")

# Otros endpoints según sea necesario para el frontend 