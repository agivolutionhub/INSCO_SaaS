from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sys, os
import uuid
import shutil
import json
import io
import zipfile
import time
from typing import List, Dict, Optional, Any
from rich.console import Console
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
env_path = Path(__file__).resolve().parent / "config" / ".env"
load_dotenv(dotenv_path=env_path)

# Consola para logs
console = Console()

# Obtener el directorio base
BASE_DIR = Path(__file__).resolve().parent

# Añadir directorio de scripts al path
sys.path.insert(0, str(BASE_DIR))

# Importar los scripts necesarios
from services.autofit_service import procesar_pptx, procesar_lote
from scripts.snapshot import extract_pptx_slides
from services.transcript_service import transcribe_video
from services.video_service import cut_video
from services.video_montage_service import generate_video_montage
from scripts.text_to_speech import generate_speech_from_file

# Importar routers
from routes.translate_pptx import router as translate_pptx_router
from routes.split_pptx import router as split_pptx_router
from routes.snapshot import router as snapshot_router
from routes.autofit import router as autofit_router
from routes.transcript import router as transcript_router
from routes.text_to_speech import router as text_to_speech_router
from routes.video_cut import router as video_cut_router
from routes.video_montage import router as video_montage_router
from routes.video_translate import router as video_translate_router

# Crear una instancia de FastAPI
app = FastAPI(title="INSCO API", description="API para el proyecto INSCO")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Obtener directorio base
BASE_DIR = Path(__file__).resolve().parent

# Directorios de almacenamiento
UPLOAD_DIR = BASE_DIR / "tmp/uploads"
PROCESSED_DIR = BASE_DIR / "tmp/processed"
CAPTURES_DIR = BASE_DIR / "tmp/captures"
AUDIO_DIR = BASE_DIR / "tmp/audio"
TRANSCRIPTS_DIR = BASE_DIR / "storage/transcripts"
VIDEO_DIR = BASE_DIR / "tmp/videos"
AUDIO_OUTPUT_DIR = BASE_DIR / "storage/audio"
AUTOFIT_DIR = BASE_DIR / "storage/autofit"
TRANSLATIONS_DIR = BASE_DIR / "storage/translations"

# Crear directorios
for directory in [UPLOAD_DIR, PROCESSED_DIR, CAPTURES_DIR, AUDIO_DIR, 
                 TRANSCRIPTS_DIR, VIDEO_DIR, AUDIO_OUTPUT_DIR, AUTOFIT_DIR,
                 TRANSLATIONS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    console.print(f"Directorio creado: {directory}")

# Verificar configuración de OpenAI
console.print(f"OpenAI API Key configurada: {bool(os.getenv('OPENAI_API_KEY'))}")
console.print(f"OpenAI Assistant ID configurado: {bool(os.getenv('OPENAI_ASSISTANT_ID'))}")

# Montar directorios estáticos
app.mount("/tmp", StaticFiles(directory=BASE_DIR / "tmp"), name="temp")
app.mount("/storage", StaticFiles(directory=BASE_DIR / "storage"), name="storage")

# Incluir routers
app.include_router(translate_pptx_router)
app.include_router(split_pptx_router)
app.include_router(snapshot_router)
app.include_router(autofit_router)
app.include_router(transcript_router)
app.include_router(text_to_speech_router)
app.include_router(video_cut_router)
app.include_router(video_montage_router)
app.include_router(video_translate_router)

@app.get("/")
async def root():
    return {"message": "Bienvenido a la API de INSCO"}

@app.get("/health")
async def health_check():
    """Endpoint para verificar la salud del servicio (usado por Docker healthcheck)"""
    # Verificar los servicios críticos
    health_status = {
        "status": "healthy",
        "time": time.time(),
        "version": "1.0.0",
        "services": {
            "storage": True,
            "tmp": True
        }
    }
    
    # Verificar que los directorios críticos sean accesibles
    try:
        # Comprobar directorio de almacenamiento
        storage_test = BASE_DIR / "storage" / "test.txt"
        with open(storage_test, "w") as f:
            f.write("test")
        os.unlink(storage_test)
        
        # Comprobar directorio temporal
        tmp_test = BASE_DIR / "tmp" / "test.txt"
        with open(tmp_test, "w") as f:
            f.write("test")
        os.unlink(tmp_test)
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        return JSONResponse(status_code=500, content=health_status)
    
    # Intenta verificar LibreOffice si está siendo utilizado
    try:
        import subprocess
        result = subprocess.run(["libreoffice", "--version", "--headless"], 
                              capture_output=True, text=True, timeout=5)
        health_status["services"]["libreoffice"] = result.returncode == 0
        if result.returncode != 0:
            health_status["status"] = "degraded"
            health_status["libreoffice_error"] = result.stderr
    except Exception as e:
        health_status["services"]["libreoffice"] = False
        health_status["status"] = "degraded"
        health_status["libreoffice_error"] = str(e)
    
    return health_status

# Endpoints específicos para transcripción de video
@app.post("/api/upload-video-for-transcription")
async def upload_video_for_transcription(file: UploadFile = File(...)):
    """Endpoint para subir archivos de video para transcripción."""
    try:
        # Validar archivo
        if not file.filename or not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".webm", ".mkv")):
            raise HTTPException(status_code=400, detail="El archivo debe ser un vídeo compatible")
        
        # Generar ID único y guardar archivo
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        file_extension = Path(file.filename).suffix.lower()
        file_path = VIDEO_DIR / f"{file_id}{file_extension}"
        
        console.print(f"[green]Guardando archivo '{file.filename}' como '{file_path}'")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Error al guardar el archivo")
        
        console.print(f"[green]Archivo guardado exitosamente como {file_path}")
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "original_name": original_name,
            "status": "uploaded",
            "file_path": str(file_path)
        }
    except Exception as e:
        console.print(f"[red]Error en upload_video_for_transcription: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/transcribe-video")
async def transcribe_video_endpoint(
    file_id: str = Form(...),
    original_name: str = Form(None),
    model_name: str = Form("gpt-4o-transcribe"),
    formats: str = Form("txt,json")
):
    """Endpoint para transcribir videos."""
    try:
        console.print(f"[green]Iniciando transcripción para archivo_id: {file_id}")
        
        # Buscar el archivo
        file_path = None
        for directory in [VIDEO_DIR, UPLOAD_DIR]:
            files = list(directory.glob(f"{file_id}.*"))
            if files:
                file_path = files[0]
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail=f"Archivo con ID {file_id} no encontrado")
        
        console.print(f"[green]Archivo encontrado: {file_path}")
        
        # Configurar formatos y directorio de salida
        formats_list = formats.split(",") if formats else ["txt", "json"]
        output_dir = TRANSCRIPTS_DIR / file_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Llamar al servicio de transcripción
        console.print(f"[green]Iniciando transcripción real...")
        result = transcribe_video(
            video_path=file_path,
            output_dir=output_dir,
            model_name=model_name,
            formats=formats_list,
            original_name=original_name,
            silent=False
        )
        
        console.print(f"[green]Transcripción completada con éxito")
        
        # Preparar respuesta
        response = {
            "job_id": file_id,
            "text": result.get("text", ""),
            "segments": result.get("segments", []),
            "stats": result.get("stats", {}),
            "status": "completed",
            "files": []
        }
        
        # Añadir URLs para descargar archivos con nombre
        display_name = original_name or Path(file_path).stem
        
        for fmt, path_str in result.get("files", {}).items():
            path = Path(path_str)
            filename = path.name
            
            # Generar un nombre descriptivo para el archivo
            file_description = f"Transcripción {fmt.upper()}"
            file_name = f"{display_name}.{fmt}"
            
            response["files"].append({
                "format": fmt,
                "url": f"/api/download-transcript/{file_id}/{filename}",
                "description": file_description,
                "name": file_name  # Añadir el nombre del archivo para el frontend
            })
        
        return response
    except Exception as e:
        console.print(f"[red]Error en transcripción: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al transcribir video: {str(e)}")

@app.get("/api/transcription-status/{job_id}")
async def transcription_status(job_id: str):
    """Endpoint para verificar el estado de una transcripción."""
    try:
        # Verificar resultado en archivo
        result_file = TRANSCRIPTS_DIR / f"{job_id}_result.json"
        
        if result_file.exists():
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            
            # Formatear URLs de archivos si es necesario
            if 'files' in result and isinstance(result['files'], dict):
                files_list = []
                for fmt, path in result['files'].items():
                    if isinstance(path, str):
                        path_obj = Path(path)
                        url = f"/api/download-transcript/{job_id}/{path_obj.name}"
                        files_list.append({
                            "format": fmt,
                            "url": url,
                            "description": f"Archivo {fmt.upper()}"
                        })
                
                if files_list:
                    result['files'] = files_list
            
            return result
        
        # Si no hay resultado, verificar directorio
        job_dir = TRANSCRIPTS_DIR / job_id
        if job_dir.exists():
            # La transcripción existe pero no hay archivo de resultado
            return {
                "job_id": job_id, 
                "status": "processing"
            }
        
        # No se encontró la transcripción
        return {
            "job_id": job_id, 
            "status": "not_found",
            "message": "La transcripción no existe"
        }
    except Exception as e:
        console.print(f"[red]Error al verificar estado: {str(e)}")
        return {
            "job_id": job_id,
            "status": "error",
            "message": f"Error al verificar estado: {str(e)}"
        }

@app.get("/api/download-transcript/{job_id}/{filename}")
async def download_transcript(job_id: str, filename: str):
    """Endpoint para descargar archivos de transcripción."""
    try:
        # Buscar en múltiples ubicaciones posibles
        possible_paths = [
            TRANSCRIPTS_DIR / job_id / filename,  # Estructura job_id/filename
            TRANSCRIPTS_DIR / filename,           # Directamente en storage/transcripts
        ]
        
        # Buscar en todas las ubicaciones posibles
        for file_path in possible_paths:
            if file_path.exists():
                # Determinar el tipo de contenido basado en la extensión
                if filename.endswith('.json'):
                    media_type = "application/json"
                elif filename.endswith('.txt'):
                    media_type = "text/plain"
                elif filename.endswith('.md'):
                    media_type = "text/markdown"
                else:
                    media_type = "application/octet-stream"
                
                return FileResponse(
                    path=file_path,
                    filename=filename,
                    media_type=media_type
                )
        
        # Archivo no encontrado
        return JSONResponse(
            {"status": "error", "message": "Archivo no encontrado"}, 
            status_code=404
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Error al descargar: {str(e)}"}, 
            status_code=500
        )

@app.post("/api/update-transcription")
async def update_transcription(request: Request):
    """Endpoint para actualizar una transcripción existente con correcciones manuales."""
    try:
        data = await request.json()
        file_id = data.get("file_id")
        original_name = data.get("original_name")
        text = data.get("text")
        segments = data.get("segments", [])
        
        if not file_id or not text:
            raise HTTPException(status_code=400, detail="Se requiere file_id y texto corregido")
        
        # Crear un directorio para la transcripción actualizada
        update_id = str(uuid.uuid4())
        update_dir = TRANSCRIPTS_DIR / update_id
        update_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar el texto corregido
        display_name = original_name or f"transcripcion_corregida"
        txt_path = update_dir / f"{display_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        # Guardar la versión JSON con segmentos
        json_path = update_dir / f"{display_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "text": text,
                "segments": segments,
                "file_id": file_id,
                "original_name": original_name,
                "update_time": time.time()
            }, f, ensure_ascii=False, indent=2)
        
        # Generar respuesta con URLs para descargar los archivos
        return {
            "status": "success",
            "message": "Transcripción actualizada correctamente",
            "files": [
                {
                    "format": "txt",
                    "url": f"/api/download-transcript/{update_id}/{txt_path.name}",
                    "description": "Texto plano",
                    "name": f"{display_name}.txt"
                },
                {
                    "format": "json",
                    "url": f"/api/download-transcript/{update_id}/{json_path.name}",
                    "description": "JSON con segmentos",
                    "name": f"{display_name}.json"
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar transcripción: {str(e)}")

# Endpoints para mejora de texto (simulados para mantener compatibilidad)
@app.post("/api/improve-text")
async def improve_text(request: Request):
    """Endpoint simulado para mejorar fragmentos de texto usando IA."""
    try:
        data = await request.json()
        text = data.get("text")
        context = data.get("context", "")
        segment_id = data.get("segment_id", -1)
        
        if not text:
            raise HTTPException(status_code=400, detail="Se requiere texto para mejorar")
        
        # Simular costo para propósitos de compatibilidad
        input_tokens = len(text.split()) + len(context.split())
        output_tokens = len(text.split())
        
        return {
            "original_text": text,
            "improved_text": text,  # Sin cambios en esta simulación
            "is_improved": False,
            "segment_id": segment_id,
            "tokens": {
                "prompt": input_tokens,
                "completion": output_tokens,
                "total": input_tokens + output_tokens
            },
            "cost": {
                "input_cost": input_tokens * 0.00001,
                "output_cost": output_tokens * 0.00003,
                "total_cost": (input_tokens * 0.00001) + (output_tokens * 0.00003)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al mejorar texto: {str(e)}")

@app.post("/api/improve-multiple-sentences")
async def improve_multiple_sentences(request: Request):
    """Endpoint simulado para mejorar múltiples oraciones usando IA."""
    try:
        data = await request.json()
        sentences = data.get("sentences", [])
        context = data.get("context", "")
        
        if not sentences:
            raise HTTPException(status_code=400, detail="Se requieren oraciones para mejorar")
        
        # Simular respuesta
        results = []
        for sentence in sentences:
            results.append({
                "id": sentence.get("id", 0),
                "original_text": sentence.get("text", ""),
                "improved_text": sentence.get("text", ""),  # Sin cambios
                "is_improved": False
            })
        
        # Simular costo total
        input_tokens = len(context.split()) + sum(len(s.get("text", "").split()) for s in sentences)
        output_tokens = sum(len(s.get("text", "").split()) for s in sentences)
        
        return {
            "results": results,
            "tokens": {
                "prompt": input_tokens,
                "completion": output_tokens,
                "total": input_tokens + output_tokens
            },
            "cost": {
                "input_cost": input_tokens * 0.00001,
                "output_cost": output_tokens * 0.00003,
                "total_cost": (input_tokens * 0.00001) + (output_tokens * 0.00003)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al mejorar oraciones: {str(e)}")

# Endpoints para capturas de PPTX
@app.post("/api/upload-pptx-for-captures")
async def upload_pptx_for_captures(file: UploadFile = File(...)):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/process-captures")
async def process_captures(file_id: str = Form(...), original_name: str = Form(None)):
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
            
            # Crear URLs correctas para acceder a las imágenes
            image_urls = []
            for img_path in sorted(capture_dir.glob("*.png")):
                slide_name = img_path.name
                image_urls.append(f"/api/snapshot/files/{file_id}/{slide_name}")
            
            return {
                "status": "success",
                "file_id": file_id,
                "original_name": original_name or Path(file_path).stem,
                "slides_count": stats["slides"],
                "image_urls": image_urls
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al generar capturas: {str(e)}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Endpoint para descargar archivos procesados."""
    file_path = PROCESSED_DIR / filename
    
    # Si no está en PROCESSED_DIR, buscar en VIDEO_DIR
    if not file_path.exists():
        file_path = VIDEO_DIR / filename
        
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Determinar el tipo MIME basado en la extensión
    extension = file_path.suffix.lower()
    media_type = "application/octet-stream"  # Por defecto
    
    if extension == ".pptx":
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif extension in [".mp4", ".avi", ".mov"]:
        media_type = "video/mp4"
    elif extension in [".mp3", ".wav"]:
        media_type = "audio/mpeg"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )

# Modelo para solicitudes de descarga de ZIP
class ZipRequest(BaseModel):
    image_urls: List[str]
    original_name: Optional[str] = "capturas"

@app.post("/api/download-captures-zip")
async def download_captures_zip(request: ZipRequest):
    try:
        image_urls = request.image_urls
        original_name = request.original_name
        
        if not image_urls:
            raise HTTPException(status_code=400, detail="No se proporcionaron URLs de imágenes")
        
        # Crear un archivo ZIP en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, url in enumerate(image_urls, 1):
                # Extraer el ID del directorio y el nombre del archivo de la URL
                # Las URLs tienen formato /api/snapshot/files/{dir_id}/{filename}
                parts = url.strip('/').split('/')
                if len(parts) >= 5:
                    dir_id = parts[-2]
                    filename = parts[-1]
                    
                    # Buscar primero en storage/snapshots
                    snapshot_path = BASE_DIR / "storage/snapshots" / dir_id / filename
                    capture_path = CAPTURES_DIR / dir_id / filename
                    
                    if snapshot_path.exists():
                        image_path = snapshot_path
                    elif capture_path.exists():
                        image_path = capture_path
                    else:
                        continue
                    
                    zip_file.write(image_path, arcname=f"diapositiva_{i:03d}.png")
        
        # Preparar el buffer para lectura
        zip_buffer.seek(0)
        
        # Limpiar el nombre original para evitar problemas con caracteres especiales
        safe_name = ''.join(c for c in original_name if c.isalnum() or c in ('_', '-', '.'))
        
        # Crear respuesta con el archivo ZIP
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}_capturas.zip"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear archivo ZIP: {str(e)}")

# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8088))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 