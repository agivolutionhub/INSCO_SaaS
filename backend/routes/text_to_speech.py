from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import tempfile, os, shutil, uuid, json
from pathlib import Path
from typing import List, Dict, Optional, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.text_to_speech_service import generate_speech_from_file, generate_speech, list_available_voices, check_ffmpeg

router = APIRouter(prefix="/api/tts", tags=["tts"])

# Configuración
UPLOAD_DIR = Path(os.environ.get("TTS_UPLOAD_DIR", "./tmp/transcripts"))
OUTPUT_DIR = Path(os.environ.get("TTS_OUTPUT_DIR", "./storage/audio"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = int(os.environ.get("TTS_MAX_FILE_SIZE", 5 * 1024 * 1024))  # 5MB
MAX_CONCURRENT_JOBS = int(os.environ.get("TTS_MAX_CONCURRENT_JOBS", 3))
JOB_TIMEOUT = int(os.environ.get("TTS_JOB_TIMEOUT", 900))  # 15 minutos

# Control de trabajos
active_jobs = {}

@router.get("/verify-ffmpeg")
async def verify_ffmpeg_endpoint():
    is_available = check_ffmpeg()
    return {"ffmpeg_available": is_available}

@router.get("/voices")
async def get_voices():
    """Devuelve la lista de voces y modelos disponibles"""
    try:
        voices_info = list_available_voices()
        return voices_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def process_tts(
    input_path: str, 
    job_id: str, 
    voice: str, 
    model: str, 
    speed: float, 
    pause_duration_ms: int
):
    result_file = OUTPUT_DIR / f"{job_id}_result.json"
    
    try:
        job_dir = OUTPUT_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = job_dir / f"{job_id}.mp3"
        
        stats = generate_speech_from_file(
            input_file=input_path,
            output_file=output_path,
            voice=voice,
            model=model,
            speed=speed,
            pause_duration_ms=pause_duration_ms,
            silent=True
        )
        
        with open(result_file, "w", encoding="utf-8") as f:
            result_data = {
                "status": "completed",
                "job_id": job_id,
                "file_path": str(output_path),
                "stats": stats,
                "download_url": f"/api/tts/download/{job_id}/audio.mp3",
                "completion_time": stats.get("total_time", 0),
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
        # Limpiar recursos
        if job_id in active_jobs:
            active_jobs.pop(job_id, None)

@router.post("/upload-text")
async def upload_text_for_tts(file: UploadFile = File(...)):
    """Sube un archivo de texto para procesamiento TTS"""
    try:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            raise HTTPException(status_code=429, 
                              detail=f"Máximo {MAX_CONCURRENT_JOBS} trabajos simultáneos")
        
        content_length = int(file.size if hasattr(file, "size") else 0)
        if content_length > MAX_FILE_SIZE:
            raise HTTPException(status_code=413,
                              detail=f"Archivo demasiado grande. Máximo {MAX_FILE_SIZE//1024}KB")
        
        # Guardar archivo
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in ['.txt', '.json']:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos TXT o JSON")
        
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
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_tts(
    file_id: str = Form(...),
    original_name: str = Form(None),
    voice: str = Form("echo"),
    model: str = Form("gpt-4o-mini-tts"),
    speed: float = Form(1.0),
    pause_duration_ms: int = Form(1300),
    background_tasks: BackgroundTasks = None
):
    """Genera audio a partir de un archivo de texto previamente subido"""
    try:
        # Buscar archivo por ID
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        file_path = files[0]
        output_name = original_name if original_name else Path(file_path).stem
        
        # Validar voz y modelo
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice not in valid_voices:
            raise HTTPException(status_code=400, detail=f"Voz no válida. Opciones: {', '.join(valid_voices)}")
        
        # Validar parámetros
        if speed < 0.25 or speed > 4.0:
            raise HTTPException(status_code=400, detail="Velocidad debe estar entre 0.25 y 4.0")
        
        if pause_duration_ms < 0 or pause_duration_ms > 5000:
            raise HTTPException(status_code=400, detail="Duración de pausa debe estar entre 0 y 5000 ms")
            
        # Registrar trabajo
        job_id = str(uuid.uuid4())
        active_jobs[job_id] = {"start_time": 0, "file_id": file_id}
        
        # Ejecutar proceso
        if background_tasks:
            background_tasks.add_task(
                process_tts,
                str(file_path), 
                job_id, 
                voice, 
                model, 
                speed, 
                pause_duration_ms
            )
        else:
            # Para desarrollo, ejecución síncrona
            process_tts(str(file_path), job_id, voice, model, speed, pause_duration_ms)
        
        return JSONResponse({
            "job_id": job_id,
            "file_id": file_id,
            "original_name": output_name,
            "status": "processing",
            "voice": voice,
            "model": model,
            "speed": speed,
            "pause_duration_ms": pause_duration_ms,
            "check_status_url": f"/api/tts/status/{job_id}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-from-text")
async def generate_from_text(
    text: str = Form(...),
    voice: str = Form("echo"),
    model: str = Form("gpt-4o-mini-tts"),
    speed: float = Form(1.0),
    pause_duration_ms: int = Form(1300),
    background_tasks: BackgroundTasks = None
):
    """Genera audio directamente a partir de texto proporcionado"""
    try:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            raise HTTPException(status_code=429, 
                              detail=f"Máximo {MAX_CONCURRENT_JOBS} trabajos simultáneos")
        
        if len(text) > MAX_FILE_SIZE // 2:  # Más estricto para texto directo
            raise HTTPException(status_code=413,
                              detail=f"Texto demasiado largo. Máximo {MAX_FILE_SIZE//2048}KB")
        
        # Guardar el texto en un archivo temporal
        file_id = str(uuid.uuid4())
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        file_path = UPLOAD_DIR / f"{file_id}.txt"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        # Validar voz y velocidad
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice not in valid_voices:
            raise HTTPException(status_code=400, detail=f"Voz no válida. Opciones: {', '.join(valid_voices)}")
        
        if speed < 0.25 or speed > 4.0:
            raise HTTPException(status_code=400, detail="Velocidad debe estar entre 0.25 y 4.0")
        
        if pause_duration_ms < 0 or pause_duration_ms > 5000:
            raise HTTPException(status_code=400, detail="Duración de pausa debe estar entre 0 y 5000 ms")
        
        # Registrar trabajo
        job_id = str(uuid.uuid4())
        active_jobs[job_id] = {"start_time": 0, "file_id": file_id}
        
        # Ejecutar proceso
        if background_tasks:
            background_tasks.add_task(
                process_tts,
                str(file_path), 
                job_id, 
                voice, 
                model, 
                speed, 
                pause_duration_ms
            )
        else:
            # Para desarrollo, ejecución síncrona
            process_tts(str(file_path), job_id, voice, model, speed, pause_duration_ms)
        
        return JSONResponse({
            "job_id": job_id,
            "file_id": file_id,
            "status": "processing",
            "voice": voice,
            "model": model,
            "text_length": len(text),
            "check_status_url": f"/api/tts/status/{job_id}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_tts_status(job_id: str):
    """Verifica el estado de un trabajo de TTS"""
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
async def download_audio_file(job_id: str, filename: str):
    """Descarga un archivo de audio generado"""
    # Buscar en el directorio específico del trabajo
    job_dir = OUTPUT_DIR / job_id
    if job_dir.exists():
        file_path = job_dir / f"{job_id}.mp3"
        if file_path.exists():
            return FileResponse(
                path=file_path, 
                filename=filename, 
                media_type="audio/mpeg"
            )
    
    raise HTTPException(status_code=404, detail="Archivo no encontrado") 