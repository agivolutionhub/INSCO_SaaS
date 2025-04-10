from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import tempfile, os, shutil, uuid, json
from pathlib import Path
from typing import List, Dict, Optional, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.transcript_service import transcribe_video, verify_ffmpeg

router = APIRouter(prefix="/api/transcript", tags=["transcript"])

# Configuración
UPLOAD_DIR = Path(os.environ.get("TRANSCRIPT_UPLOAD_DIR", "./tmp/videos"))
OUTPUT_DIR = Path(os.environ.get("TRANSCRIPT_OUTPUT_DIR", "./storage/transcripts"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = int(os.environ.get("TRANSCRIPT_MAX_FILE_SIZE", 500 * 1024 * 1024))  # 500MB
MAX_CONCURRENT_JOBS = int(os.environ.get("TRANSCRIPT_MAX_CONCURRENT_JOBS", 2))
JOB_TIMEOUT = int(os.environ.get("TRANSCRIPT_JOB_TIMEOUT", 1800))  # 30 minutos

# Control de trabajos
active_jobs = {}

@router.get("/verify-ffmpeg")
async def verify_ffmpeg_endpoint():
    is_available = verify_ffmpeg()
    return {"ffmpeg_available": is_available}

def process_video_transcription(video_path: str, job_id: str, model_name: str, formats: List[str]):
    result_file = OUTPUT_DIR / f"{job_id}_result.json"
    
    try:
        job_dir = OUTPUT_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        result = transcribe_video(
            video_path=video_path,
            output_dir=job_dir,
            model_name=model_name,
            formats=formats,
            silent=True
        )
        
        with open(result_file, "w", encoding="utf-8") as f:
            result_data = {
                "status": "completed",
                "job_id": job_id,
                "text": result["text"],
                "segments": result["segments"],
                "stats": result["stats"],
                "files": {fmt: str(path) for fmt, path in result.get("files", {}).items()},
                "completion_time": result["stats"].get("tiempo_proceso", ""),
            }
            json.dump(result_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({
                "status": "error", 
                "message": str(e),
                "error_type": type(e).__name__,
            }, f, ensure_ascii=False, indent=2)
    finally:
        # Limpiar archivos temporales
        if job_id in active_jobs:
            active_jobs.pop(job_id, None)
        try:
            # No borramos el video original para permitir reintentos
            pass
        except Exception:
            pass

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        # Validaciones
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            raise HTTPException(status_code=429, 
                               detail=f"Máximo {MAX_CONCURRENT_JOBS} trabajos simultáneos")
        
        if not file.filename or not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".webm", ".mkv")):
            raise HTTPException(status_code=400, detail="El archivo debe ser un vídeo compatible")
        
        content_length = 0
        try:
            content_length = int(file.size if hasattr(file, "size") else 0)
        except:
            pass
            
        if content_length > MAX_FILE_SIZE:
            raise HTTPException(status_code=413,
                              detail=f"Archivo demasiado grande. Máximo {MAX_FILE_SIZE//1024//1024}MB")
        
        # Guardar archivo
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        file_extension = Path(file.filename).suffix.lower()
        
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        file_path = UPLOAD_DIR / f"{file_id}{file_extension}"
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Error al guardar el archivo")
        
        return JSONResponse({
            "file_id": file_id,
            "filename": file.filename,
            "original_name": original_name,
            "status": "uploaded",
            "file_path": str(file_path)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process")
async def process_video(
    file_id: str = Form(...),
    original_name: str = Form(None),
    model_name: str = Form("gpt-4o-transcribe"),
    formats: str = Form("txt,json"),
    background_tasks: BackgroundTasks = None
):
    try:
        # Buscar archivo por ID
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        file_path = files[0]
        output_name = original_name if original_name else Path(file_path).stem
        
        # Procesar formatos
        formats_list = [fmt.strip() for fmt in formats.split(",") if fmt.strip()] 
        if not formats_list:
            formats_list = ["txt"]
        
        # Validar modelo
        valid_models = ["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"]
        if model_name not in valid_models:
            raise HTTPException(status_code=400, detail=f"Modelo no válido. Opciones: {', '.join(valid_models)}")
        
        # Registrar trabajo
        job_id = str(uuid.uuid4())
        active_jobs[job_id] = {"start_time": 0, "file_id": file_id}
        
        # Ejecutar proceso
        if background_tasks:
            background_tasks.add_task(
                process_video_transcription,
                str(file_path), 
                job_id, 
                model_name, 
                formats_list
            )
        else:
            # Para desarrollo/pruebas, ejecución síncrona
            process_video_transcription(str(file_path), job_id, model_name, formats_list)
        
        return JSONResponse({
            "job_id": job_id,
            "file_id": file_id,
            "original_name": output_name,
            "status": "processing",
            "check_status_url": f"/api/transcript/status/{job_id}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_transcription_status(job_id: str):
    # Verificar resultado
    result_file = OUTPUT_DIR / f"{job_id}_result.json"
    if result_file.exists():
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse({
                "job_id": job_id, 
                "status": "error", 
                "message": f"Error al leer resultado: {str(e)}"
            })
    
    # No encontrado
    if job_id in active_jobs:
        return JSONResponse({"job_id": job_id, "status": "processing"})
    else:
        return JSONResponse({"job_id": job_id, "status": "not_found"}, status_code=404)

@router.get("/download/{job_id}/{filename}")
async def download_transcript_file(job_id: str, filename: str):
    # Buscar en el directorio específico del trabajo
    job_dir = OUTPUT_DIR / job_id
    if job_dir.exists():
        file_path = job_dir / filename
        if file_path.exists():
            media_type = "application/json" if filename.endswith(".json") else "text/plain"
            return FileResponse(path=file_path, filename=filename, media_type=media_type)
    
    # Buscar en el directorio raíz
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        media_type = "application/json" if filename.endswith(".json") else "text/plain"
        return FileResponse(path=file_path, filename=filename, media_type=media_type)
    
    raise HTTPException(status_code=404, detail="Archivo no encontrado") 