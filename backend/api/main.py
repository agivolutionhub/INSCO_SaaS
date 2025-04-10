from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from pathlib import Path
import sys, os
import uuid
import shutil
import json
import io
import zipfile
from typing import List, Dict, Optional, Any
from openai import OpenAI, AsyncOpenAI
from rich.console import Console

# Consola para logs
console = Console()

# Configurar límites de carga de archivos - Aumentarlos significativamente
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Obtener el directorio base
BASE_DIR = Path(__file__).resolve().parent.parent

# Añadir directorio de scripts al path
sys.path.insert(0, str(BASE_DIR))
# Importar los scripts necesarios - Usar el nombre correcto del archivo
from scripts.autofit import procesar_pptx, procesar_lote
from scripts.snapshot import extract_pptx_slides
# Importar el script de transcripción
from scripts.transcript import transcribe_video
# Importar el script de corte de vídeo
from scripts.video_cut import cut_video, format_time_for_ffmpeg
# Importar el script de montaje de video
from scripts.video_montage import generate_video_montage
# Importar el script de text-to-speech
from scripts.text_to_speech import generate_speech_from_file
# Importar rutas
from routes.translate_pptx import router as translate_pptx_router
from routes.split_pptx import router as split_pptx_router
from routes.snapshot import router as snapshot_router
from routes.transcript import router as transcript_router

# Añadir el directorio del backend al path para importaciones
sys.path.append(str(Path(__file__).parent.parent))

# Crear una instancia de FastAPI con límites aumentados para uploads
app = FastAPI(title="INSCO API")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(translate_pptx_router)
app.include_router(split_pptx_router)
app.include_router(snapshot_router)
app.include_router(transcript_router)

# Crear directorios temporales para archivos subidos y procesados
UPLOAD_DIR = BASE_DIR / "tmp/uploads"
PROCESSED_DIR = BASE_DIR / "tmp/processed"
CAPTURES_DIR = BASE_DIR / "tmp/captures"
AUDIO_DIR = BASE_DIR / "tmp/audio"
TRANSCRIPTS_DIR = BASE_DIR / "storage/transcripts"
VIDEO_DIR = BASE_DIR / "tmp/videos"  # Directorio para archivos de vídeo
AUDIO_OUTPUT_DIR = BASE_DIR / "storage/audio"  # Directorio para almacenar audio generado
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # Crear directorio de audio generado

class ProcessFileRequest(BaseModel):
    input_file: str
    output_file: str = None

class ProcessBatchRequest(BaseModel):
    input_dir: str = None
    output_dir: str = None

# Modelo para las URLs de archivos
class FileUrlsRequest(BaseModel):
    file_urls: List[str]

# Modelo para actualizar transcripción
class UpdateTranscriptionRequest(BaseModel):
    file_id: str
    original_name: str
    text: str
    segments: List[dict]

# Modelo para mejorar texto con IA
class ImproveTextRequest(BaseModel):
    text: str
    context: str = Field("", description="Contexto opcional para mejorar comprensión")
    segment_id: int = Field(-1, description="ID del segmento a mejorar, -1 para texto completo")

# Modelo para mejorar múltiples oraciones
class ImproveMultipleSentencesRequest(BaseModel):
    sentences: List[Dict[str, Any]] = Field(..., description="Lista de oraciones a mejorar")
    context: str = Field("", description="Contexto completo del texto")

# Modelo para solicitud de corte de vídeo
class CutVideoRequest(BaseModel):
    file_id: str
    start_time: float
    end_time: float
    original_name: str = None

# Modelo para solicitud de montaje de vídeo
class MontageRequest(BaseModel):
    audio_id: str
    images: List[Dict[str, Any]]
    original_name: str = None
    output_format: str = "mp4"

# Modelo para solicitud de generación de voz
class GenerateAudioRequest(BaseModel):
    file_id: str
    original_name: str = None
    voice: str = "echo"
    model: str = "gpt-4o-mini-tts"
    instructions: str = None
    speed: float = 1.0
    pause_duration_ms: int = 1300

@app.get("/")
async def root():
    return {"message": "INSCO API está funcionando"}

@app.get("/api/directories")
async def get_directories():
    try:
        base_dir = BASE_DIR / "data/input/diapos"
        if not base_dir.exists():
            return {"directories": []}
        dirs = [d.name for d in base_dir.iterdir() if d.is_dir()]
        return {"directories": dirs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{directory}")
async def get_files(directory: str):
    try:
        dir_path = BASE_DIR / f"data/input/diapos/{directory}"
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Directorio {directory} no encontrado")
        
        files = [f.name for f in dir_path.glob("*.pptx")]
        return {"files": files}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-pptx")
async def upload_pptx(file: UploadFile = File(...)):
    try:
        # Generar ID único para este archivo
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem  # Guardar el nombre original sin extensión
        file_extension = Path(filename).suffix
        
        if file_extension.lower() != '.pptx':
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PPTX")
        
        # Asegurarse de que el directorio existe
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_location = UPLOAD_DIR / f"{file_id}{file_extension}"
        print(f"Guardando archivo en: {file_location}")
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Verificar que el archivo existe
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        print(f"Archivo guardado correctamente: {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location)
        }
    except Exception as e:
        print(f"Error en upload_pptx: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

# Nuevo endpoint para subir múltiples archivos
@app.post("/api/upload-multiple-pptx")
async def upload_multiple_pptx(files: list[UploadFile] = File(...)):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 archivos permitidos")
        
    results = []
    for file in files:
        try:
            # Generar ID único para este archivo
            file_id = str(uuid.uuid4())
            filename = file.filename
            original_name = Path(filename).stem  # Guardar el nombre original sin extensión
            file_extension = Path(filename).suffix
            
            if file_extension.lower() != '.pptx':
                results.append({
                    "filename": filename,
                    "status": "error",
                    "message": "Solo se permiten archivos PPTX"
                })
                continue
            
            # Asegurarse de que el directorio existe
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            
            # Guardar archivo
            file_location = UPLOAD_DIR / f"{file_id}{file_extension}"
            
            with open(file_location, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Verificar que el archivo existe
            if not file_location.exists():
                results.append({
                    "filename": filename,
                    "status": "error",
                    "message": f"Error: No se pudo guardar el archivo"
                })
                continue
            
            results.append({
                "file_id": file_id,
                "filename": filename,
                "original_name": original_name,
                "status": "success",
                "file_path": str(file_location)
            })
            
        except Exception as e:
            results.append({
                "filename": filename if 'filename' in locals() else "desconocido",
                "status": "error",
                "message": str(e)
            })
    
    return {"results": results}

@app.post("/api/process-autofit")
async def process_autofit(file_id: str = Form(...), original_name: str = Form(None)):
    try:
        # Buscar archivo por ID
        print(f"Buscando archivo con ID: {file_id} en {UPLOAD_DIR}")
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        print(f"Archivos encontrados: {files}")
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        file_path = files[0]  # Tomar el primer archivo que coincida
        print(f"Archivo encontrado: {file_path}")
        
        # Usar el nombre original o un UUID si no está disponible
        output_filename = f"{original_name or file_id}_autofit.pptx"
        output_path = PROCESSED_DIR / output_filename
        
        # Asegurarse de que el directorio existe
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"Procesando archivo {file_path} -> {output_path}")
        
        # Procesar archivo
        result_path = procesar_pptx(file_path, output_path)
        
        # Verificar que el archivo procesado existe
        if not Path(result_path).exists():
            raise HTTPException(status_code=500, detail=f"El procesamiento falló: No se generó el archivo {result_path}")
        
        print(f"Archivo procesado correctamente: {result_path}")
        
        return {
            "status": "success",
            "file_id": file_id,
            "original_name": original_name,
            "processed_file": str(result_path),
            "output_filename": output_filename,
            "download_url": f"/api/download/{output_filename}"
        }
    except Exception as e:
        print(f"Error en process_autofit: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

# Nuevo endpoint para procesar múltiples archivos
@app.post("/api/process-multiple-autofit")
async def process_multiple_autofit(file_infos: str = Form(...)):
    try:
        # Convertir JSON string a lista de objetos
        file_data = json.loads(file_infos)
        
        if len(file_data) > 10:
            raise HTTPException(status_code=400, detail="Máximo 10 archivos permitidos")
            
        results = []
        for item in file_data:
            try:
                file_id = item.get("file_id")
                original_name = item.get("original_name")
                
                if not file_id:
                    results.append({
                        "status": "error",
                        "message": "ID de archivo no especificado"
                    })
                    continue
                
                # Buscar archivo por ID
                files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
                
                if not files:
                    results.append({
                        "file_id": file_id,
                        "status": "error",
                        "message": "Archivo no encontrado"
                    })
                    continue
                
                file_path = files[0]
                
                # Usar el nombre original o un UUID si no está disponible
                output_filename = f"{original_name or file_id}_autofit.pptx"
                output_path = PROCESSED_DIR / output_filename
                
                # Asegurarse de que el directorio existe
                PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
                
                # Procesar archivo
                result_path = procesar_pptx(file_path, output_path, silent=True)
                
                results.append({
                    "file_id": file_id,
                    "original_name": original_name,
                    "status": "success",
                    "processed_file": str(result_path),
                    "output_filename": output_filename,
                    "download_url": f"/api/download/{output_filename}"
                })
                
            except Exception as e:
                results.append({
                    "file_id": file_id if 'file_id' in locals() else "desconocido",
                    "status": "error",
                    "message": str(e)
                })
        
        return {"results": results}
        
    except Exception as e:
        print(f"Error en process_multiple_autofit: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar los archivos: {str(e)}")

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename
    )

@app.post("/api/process-file")
async def process_file(request: ProcessFileRequest, background_tasks: BackgroundTasks):
    try:
        result = {"status": "processing", "file": request.input_file}
        background_tasks.add_task(
            procesar_pptx, 
            request.input_file,
            request.output_file
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-batch")
async def process_batch(request: ProcessBatchRequest, background_tasks: BackgroundTasks):
    try:
        result = {"status": "processing", "directory": request.input_dir or "default"}
        background_tasks.add_task(
            procesar_lote,
            request.input_dir,
            request.output_dir
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/download-zip")
async def download_zip(request: FileUrlsRequest):
    """
    Descarga múltiples archivos como un único archivo ZIP.
    Recibe una lista de URLs de archivos y devuelve un ZIP con todos ellos.
    """
    try:
        # Crear un buffer de memoria para el ZIP
        zip_buffer = io.BytesIO()
        
        # Crear el archivo ZIP
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_url in request.file_urls:
                # Extraer el nombre del archivo de la URL
                filename = file_url.split('/')[-1]
                
                # Construir la ruta completa del archivo
                file_path = PROCESSED_DIR / filename
                
                # Verificar que el archivo existe
                if not file_path.exists():
                    continue
                
                # Añadir el archivo al ZIP
                zip_file.write(file_path, arcname=filename)
        
        # Mover el cursor al inicio del buffer
        zip_buffer.seek(0)
        
        # Devolver el contenido del ZIP
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=archivos_procesados.zip"}
        )
    except Exception as e:
        print(f"Error al crear el ZIP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al crear el archivo ZIP: {str(e)}")

@app.post("/api/upload-pptx-for-captures")
async def upload_pptx_for_captures(file: UploadFile = File(...)):
    try:
        # Generar ID único para este archivo
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem  # Guardar el nombre original sin extensión
        file_extension = Path(filename).suffix
        
        if file_extension.lower() != '.pptx':
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PPTX")
        
        # Asegurarse de que el directorio existe
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_location = UPLOAD_DIR / f"{file_id}{file_extension}"
        print(f"Guardando archivo para capturas en: {file_location}")
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Verificar que el archivo existe
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        print(f"Archivo guardado correctamente: {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location)
        }
    except Exception as e:
        print(f"Error en upload_pptx_for_captures: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/process-captures")
async def process_captures(file_id: str = Form(...), original_name: str = Form(None)):
    try:
        # Buscar archivo por ID
        print(f"Buscando archivo con ID: {file_id} en {UPLOAD_DIR}")
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        print(f"Archivos encontrados: {files}")
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        file_path = files[0]  # Tomar el primer archivo que coincida
        print(f"Archivo encontrado: {file_path}")
        
        # Crear directorio específico para las capturas de este archivo
        capture_dir = CAPTURES_DIR / file_id
        capture_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Ejecutar la función de extracción de diapositivas
            print(f"Generando capturas para {file_path} en {capture_dir}")
            stats = extract_pptx_slides(
                pptx_path=file_path,
                output_dir=capture_dir,
                format="png",
                dpi=300
            )
            
            # Obtener las rutas relativas de las imágenes generadas
            image_urls = []
            for img_path in sorted(capture_dir.glob("*.png")):
                # Obtener ruta relativa para la URL
                rel_path = img_path.relative_to(BASE_DIR)
                image_urls.append(f"/{str(rel_path)}")
            
            print(f"Se generaron {len(image_urls)} capturas")
            
            return {
                "status": "success",
                "file_id": file_id,
                "original_name": original_name or Path(file_path).stem,
                "slides_count": stats["slides"],
                "image_urls": image_urls
            }
            
        except Exception as e:
            print(f"Error al generar capturas: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error al generar capturas: {str(e)}")
            
    except Exception as e:
        print(f"Error en process_captures: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@app.post("/api/download-captures-zip")
async def download_captures_zip(request: dict):
    try:
        image_urls = request.get("image_urls", [])
        original_name = request.get("original_name", "capturas")
        
        if not image_urls:
            raise HTTPException(status_code=400, detail="No se proporcionaron URLs de imágenes")
        
        # Crear un archivo ZIP en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, url in enumerate(image_urls, 1):
                # Convertir URL relativa a ruta absoluta del sistema
                image_path = BASE_DIR / url.lstrip('/')
                
                if not image_path.exists():
                    print(f"Advertencia: La imagen {image_path} no existe")
                    continue
                
                # Añadir archivo al ZIP con un nombre secuencial
                zip_file.write(
                    image_path, 
                    arcname=f"diapositiva_{i:03d}.png"
                )
        
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
        print(f"Error al crear archivo ZIP: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al crear archivo ZIP: {str(e)}")

# Endpoint para servir imágenes estáticas
@app.get("/tmp/captures/{file_id}/{filename}")
async def serve_capture(file_id: str, filename: str):
    image_path = CAPTURES_DIR / file_id / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    
    return FileResponse(
        path=image_path,
        media_type="image/png"
    )

@app.post("/api/upload-video-for-transcription")
async def upload_video_for_transcription(file: UploadFile = File(...)):
    try:
        # Generar ID único para este archivo
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem  # Guardar el nombre original sin extensión
        file_extension = Path(filename).suffix
        
        # Verificar que sea un archivo de video o audio
        valid_extensions = ['.mp4', '.avi', '.mov', '.mp3', '.wav', '.webm', '.ogg']
        if file_extension.lower() not in valid_extensions:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de video o audio (MP4, AVI, MOV, MP3, WAV, WEBM, OGG)")
        
        # Asegurarse de que el directorio existe
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_location = UPLOAD_DIR / f"{file_id}{file_extension}"
        print(f"Guardando archivo en: {file_location}")
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Verificar que el archivo existe
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        print(f"Archivo guardado correctamente: {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location),
            "media_type": "video" if file_extension.lower() in ['.mp4', '.avi', '.mov', '.webm'] else "audio"
        }
    except Exception as e:
        print(f"Error en upload_video_for_transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/transcribe-video")
async def transcribe_video_endpoint(
    file_id: str = Form(...), 
    original_name: str = Form(None),
    model_name: str = Form("gpt-4o-transcribe"),
    formats: str = Form("txt,json")
):
    try:
        # Buscar archivo por ID
        console.print(f"[blue]Buscando archivo con ID:[/blue] {file_id} en {UPLOAD_DIR}")
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        file_path = files[0]  # Tomar el primer archivo que coincida
        console.print(f"[green]Archivo encontrado:[/green] {file_path}")
        
        # Usar el nombre original o un UUID si no está disponible
        output_name = original_name or file_id
        console.print(f"[blue]Nombre para archivos de salida:[/blue] {output_name}")
        
        output_dir = TRANSCRIPTS_DIR / file_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convertir el string de formatos a una lista
        formats_list = formats.split(",")
        
        console.print(f"[blue]Transcribiendo archivo {file_path} a {output_dir}[/blue]")
        
        # Procesar archivo - pasar el nombre original para usarlo en los archivos de salida
        result = transcribe_video(
            video_path=file_path,
            output_dir=output_dir,
            model_name=model_name,
            formats=formats_list,
            original_name=output_name  # Pasando el nombre explícitamente aquí
        )
        
        # Lista de archivos generados
        output_files = []
        
        # Verificar que los archivos existen realmente antes de añadirlos a la respuesta
        for fmt in formats_list:
            if fmt == "json" or fmt == "all":
                file_path = output_dir / f"{output_name}.json"
                if file_path.exists():
                    output_files.append({
                        "url": f"/api/download-transcript/{file_id}/{output_name}.json",
                        "name": f"{output_name}.json"
                    })
                    console.print(f"[green]Archivo JSON generado:[/green] {file_path}")
                else:
                    console.print(f"[yellow]Advertencia: Archivo JSON no encontrado:[/yellow] {file_path}")
                    
            if fmt == "txt" or fmt == "all":
                file_path = output_dir / f"{output_name}.txt"
                if file_path.exists():
                    output_files.append({
                        "url": f"/api/download-transcript/{file_id}/{output_name}.txt",
                        "name": f"{output_name}.txt"
                    })
                    console.print(f"[green]Archivo TXT generado:[/green] {file_path}")
                else:
                    console.print(f"[yellow]Advertencia: Archivo TXT no encontrado:[/yellow] {file_path}")
                    
            if fmt == "md" or fmt == "all":
                file_path = output_dir / f"{output_name}.md"
                if file_path.exists():
                    output_files.append({
                        "url": f"/api/download-transcript/{file_id}/{output_name}.md",
                        "name": f"{output_name}.md"
                    })
                    console.print(f"[green]Archivo MD generado:[/green] {file_path}")
                else:
                    console.print(f"[yellow]Advertencia: Archivo MD no encontrado:[/yellow] {file_path}")
        
        # Preparar resultado
        response = {
            "status": "success",
            "file_id": file_id,
            "original_name": original_name,
            "text": result.get("text", ""),
            "stats": result.get("stats", {}),
            "files": output_files
        }
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en transcribe_video_endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al transcribir el archivo: {str(e)}")

@app.get("/api/download-transcript/{file_id}/{filename}")
async def download_transcript(file_id: str, filename: str):
    # Verificar primero en la ruta de transcripción
    file_path = TRANSCRIPTS_DIR / file_id / filename
    
    # Si el archivo no existe, intentar buscar en formato "output_name.[txt|json|md]"
    if not file_path.exists():
        # Verificar diferentes combinaciones de ruta
        # 1. Intentar buscar el archivo directamente en el directorio de transcripciones
        alternate_path = TRANSCRIPTS_DIR / file_id / filename.split('/')[-1]
        if alternate_path.exists():
            file_path = alternate_path
        else:
            # 2. Comprobar si hay un archivo con ese nombre sin la extensión "_transcript"
            base_name = filename.replace('_transcript', '')
            alternate_path = TRANSCRIPTS_DIR / file_id / base_name
            if alternate_path.exists():
                file_path = alternate_path
            else:
                # Si aún no lo encuentra, comprobar si existe con formato alternativo
                console.print(f"[yellow]Archivo no encontrado en {file_path}, buscando alternativas...[/yellow]")
                for format_extension in ['.txt', '.json', '.md']:
                    if filename.endswith(format_extension):
                        name_only = filename[:-len(format_extension)]
                        alt_file = f"{name_only}{format_extension}"
                        alternate_path = TRANSCRIPTS_DIR / file_id / alt_file
                        if alternate_path.exists():
                            file_path = alternate_path
                            break
    
    # Si después de todos los intentos no se encuentra el archivo
    if not file_path.exists():
        console.print(f"[red]Archivo no encontrado: {file_path}[/red]")
        raise HTTPException(status_code=404, detail="Archivo de transcripción no encontrado")
    
    # Determinar el tipo MIME basado en la extensión
    extension = Path(filename).suffix.lower()
    if extension == '.json':
        media_type = "application/json"
    elif extension == '.txt':
        media_type = "text/plain"
    elif extension == '.md':
        media_type = "text/markdown"
    else:
        media_type = "application/octet-stream"
    
    # Log para debugging
    console.print(f"[green]Enviando archivo: {file_path} con tipo MIME: {media_type}[/green]")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=Path(filename).name
    )

@app.post("/api/update-transcription")
async def update_transcription(request: UpdateTranscriptionRequest):
    try:
        # Directorio para almacenar las transcripciones
        transcript_dir = BASE_DIR / "storage/transcripts" / request.file_id
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        output_name = request.original_name or request.file_id
        
        # Guardar el texto actualizado en el archivo TXT
        txt_path = transcript_dir / f"{output_name}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(request.text)
        
        # Guardar el texto y segmentos actualizados en el archivo JSON
        json_path = transcript_dir / f"{output_name}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "text": request.text,
                "segments": request.segments
            }, f, ensure_ascii=False, indent=2)
        
        # Si existe un archivo MD, actualizarlo también
        md_path = transcript_dir / f"{output_name}.md"
        if md_path.exists():
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# Transcripción: {output_name}\n\n")
                for segment in request.segments:
                    f.write(f"{segment['text']}\n\n")
        
        # Preparar la respuesta con los archivos actualizados
        files = []
        if txt_path.exists():
            files.append({
                "url": f"/api/download-transcript/{request.file_id}/{output_name}.txt",
                "name": f"{output_name}.txt"
            })
        
        if json_path.exists():
            files.append({
                "url": f"/api/download-transcript/{request.file_id}/{output_name}.json",
                "name": f"{output_name}.json"
            })
        
        if md_path.exists():
            files.append({
                "url": f"/api/download-transcript/{request.file_id}/{output_name}.md",
                "name": f"{output_name}.md"
            })
        
        return {
            "status": "success",
            "message": "Transcripción actualizada correctamente",
            "files": files
        }
    except Exception as e:
        print(f"Error al actualizar la transcripción: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al actualizar la transcripción: {str(e)}")

# Cargar configuración de OpenAI
def load_openai_config():
    config_path = BASE_DIR / "config" / "openapi.json"
    if not config_path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo de configuración: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Función para calcular número aproximado de tokens
def estimate_tokens(text: str) -> int:
    # Aproximación: 1 token ≈ 4 caracteres en español
    return len(text) // 4

# Calcular costo basado en tokens
def calculate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o") -> dict:
    config = load_openai_config()
    models_info = config.get("documentation", {}).get("models", {})
    
    result = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": 0,
        "output_cost": 0,
        "total_cost": 0,
        "currency": "USD"
    }
    
    if model in models_info:
        model_costs = models_info[model].get("cost", {})
        input_cost_per_million = model_costs.get("input", 0)
        output_cost_per_million = model_costs.get("output", 0)
        
        result["input_cost"] = (input_tokens / 1000000) * input_cost_per_million
        result["output_cost"] = (output_tokens / 1000000) * output_cost_per_million
        result["total_cost"] = result["input_cost"] + result["output_cost"]
    
    return result

@app.post("/api/improve-text")
async def improve_text_with_ai(request: ImproveTextRequest):
    try:
        # Cargar configuración
        config = load_openai_config()
        api_key = config.get("openai", {}).get("api_key")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="API key de OpenAI no configurada")
        
        # Preparar mensaje para OpenAI con énfasis en mantener correspondencia exacta
        system_message = (
            "Eres un experto en formación técnica sobre la industria del cartón ondulado. "
            "Tu tarea es mejorar el texto proporcionado siguiendo estas reglas ESTRICTAS:\n\n"
            "1. Cada oración mejorada DEBE corresponder EXACTAMENTE con la oración original en temática y contenido.\n"
            "2. MANTÉN la misma idea principal y conceptos que la oración original.\n"
            "3. PROHIBIDO añadir información nueva que no esté presente o fuertemente implícita en el original.\n"
            "4. Puedes expandir o clarificar el texto original SOLO si mantienes su significado exacto.\n"
            "5. NO CAMBIES el tema de ninguna oración bajo ninguna circunstancia.\n"
            "6. Si hay múltiples oraciones, DEBES responder con el mismo número de oraciones, cada una correspondiendo a su original.\n"
            "7. Solo mejora la redacción, ortografía, gramática y claridad, SIN CAMBIAR el significado.\n\n"
            "EXTREMADAMENTE IMPORTANTE: Si no puedes mejorar el texto sin cambiar su significado, devuelve el texto original sin cambios.\n"
            "PROHIBIDO responder con información sobre un tema diferente al que se menciona en la oración original."
        )
        
        # Añadir contexto si está disponible
        content = request.text
        if request.context:
            content = f"Contexto (para comprender mejor, no modificar este texto): {request.context}\n\nTexto a mejorar (MANTÉN EXACTAMENTE EL MISMO TEMA Y SIGNIFICADO): {request.text}"
        
        # Calcular tokens aproximados y costo estimado
        estimated_input_tokens = estimate_tokens(system_message) + estimate_tokens(content)
        estimated_output_tokens = estimate_tokens(request.text) * 1.2  # Estimación conservadora
        cost_estimate = calculate_cost(estimated_input_tokens, estimated_output_tokens)
        
        # Usar la biblioteca oficial de OpenAI
        # Configurar variables de entorno para desactivar proxies
        os.environ["no_proxy"] = "*"
        if "HTTP_PROXY" in os.environ:
            del os.environ["HTTP_PROXY"]
        if "HTTPS_PROXY" in os.environ:
            del os.environ["HTTPS_PROXY"]
            
        client = OpenAI(api_key=api_key)
        
        # Realizar la llamada a la API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": content}
            ],
            temperature=0.2,  # Menor temperatura para resultados más predecibles
            max_tokens=2000
        )
        
        # Extraer el texto mejorado
        improved_text = response.choices[0].message.content
        
        # Calcular tokens reales y costo
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        actual_cost = calculate_cost(prompt_tokens, completion_tokens)
        
        return {
            "original_text": request.text,
            "improved_text": improved_text,
            "segment_id": request.segment_id,
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": prompt_tokens + completion_tokens
            },
            "cost": actual_cost
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error al mejorar texto con IA: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al mejorar texto con IA: {str(e)}")

@app.post("/api/improve-multiple-sentences")
async def improve_multiple_sentences(request: ImproveMultipleSentencesRequest):
    try:
        # Cargar configuración
        config = load_openai_config()
        api_key = config.get("openai", {}).get("api_key")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="API key de OpenAI no configurada")
        
        # Extraer todas las oraciones originales en un solo texto
        original_sentences = [item.get("text", "") for item in request.sentences]
        combined_text = "\n\n".join(original_sentences)
        
        # Preparar mensaje para OpenAI para mantener la correspondencia exacta
        system_message = (
            "Eres un experto en formación técnica sobre la industria del cartón ondulado. "
            "Te proporcionaré varias oraciones separadas por líneas en blanco. "
            "Tu tarea es mejorar CADA oración individualmente siguiendo estas reglas ESTRICTAS:\n\n"
            "1. Devuelve EXACTAMENTE el mismo número de oraciones, en el MISMO ORDEN.\n"
            "2. Cada oración mejorada DEBE corresponder EXACTAMENTE con la oración original en temática y contenido.\n"
            "3. MANTÉN la misma idea principal y conceptos que la oración original.\n"
            "4. PROHIBIDO añadir información nueva que no esté presente o fuertemente implícita en el original.\n"
            "5. Puedes expandir o clarificar el texto original SOLO si mantienes su significado exacto.\n"
            "6. NO CAMBIES el tema de ninguna oración bajo ninguna circunstancia.\n"
            "7. Separa cada oración con DOS SALTOS DE LÍNEA (línea en blanco entre oraciones).\n"
            "8. Si una oración está bien redactada y no necesita mejoras, devuélvela SIN CAMBIOS.\n\n"
            "EXTREMADAMENTE IMPORTANTE: Responde ÚNICAMENTE con las oraciones mejoradas, "
            "separadas por líneas en blanco. NO añadas numeración, explicaciones o texto adicional."
        )
        
        content = f"Contexto (para comprender mejor, no modificar este texto): {request.context}\n\n"
        content += "Oraciones a mejorar (separa tu respuesta con líneas en blanco, manteniendo el MISMO ORDEN y NÚMERO de oraciones):\n\n"
        content += combined_text
        
        # Calcular tokens aproximados y costo estimado
        estimated_input_tokens = estimate_tokens(system_message) + estimate_tokens(content)
        estimated_output_tokens = estimate_tokens(combined_text) * 1.2  # Estimación conservadora
        cost_estimate = calculate_cost(estimated_input_tokens, estimated_output_tokens)
        
        # Usar la biblioteca oficial de OpenAI
        # Configurar variables de entorno para desactivar proxies
        os.environ["no_proxy"] = "*"
        if "HTTP_PROXY" in os.environ:
            del os.environ["HTTP_PROXY"]
        if "HTTPS_PROXY" in os.environ:
            del os.environ["HTTPS_PROXY"]
            
        client = OpenAI(api_key=api_key)
        
        # Realizar la llamada a la API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": content}
            ],
            temperature=0.2,  # Menor temperatura para resultados más predecibles
            max_tokens=4000
        )
        
        # Extraer las oraciones mejoradas
        improved_text = response.choices[0].message.content
        improved_sentences = [sent.strip() for sent in improved_text.split("\n\n") if sent.strip()]
        
        # Verificar que tenemos el mismo número de oraciones
        if len(improved_sentences) != len(original_sentences):
            # Si no coinciden, devolver las originales con un mensaje de error
            print(f"Error: Número de oraciones no coincide. Original: {len(original_sentences)}, Mejorado: {len(improved_sentences)}")
            improved_sentences = original_sentences
        
        # Preparar resultado con oraciones originales y mejoradas
        results = []
        for i, (original, improved) in enumerate(zip(original_sentences, improved_sentences)):
            # Solo considerar como mejora si es diferente a la original
            is_improved = original.strip() != improved.strip()
            
            # Si hay más oraciones originales que mejoradas, usar la original
            if i >= len(improved_sentences):
                improved = original
                is_improved = False
                
            # Añadir a resultados
            results.append({
                "id": request.sentences[i].get("id", i),
                "original_text": original,
                "improved_text": improved,
                "is_improved": is_improved
            })
            
        # Calcular tokens reales y costo
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        actual_cost = calculate_cost(prompt_tokens, completion_tokens)
        
        return {
            "results": results,
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": prompt_tokens + completion_tokens
            },
            "cost": actual_cost
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error al mejorar oraciones con IA: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al mejorar oraciones con IA: {str(e)}")

@app.post("/api/upload-video-for-cut")
async def upload_video_for_cut(file: UploadFile = File(...)):
    """
    Endpoint para subir un archivo de vídeo para ser cortado.
    """
    try:
        # Generar ID único para este archivo
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem  # Guardar el nombre original sin extensión
        file_extension = Path(filename).suffix
        
        # Verificar que sea un archivo de video
        valid_extensions = ['.mp4', '.avi', '.mov', '.webm', '.mkv']
        if file_extension.lower() not in valid_extensions:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de video (MP4, AVI, MOV, WEBM, MKV)")
        
        # Asegurarse de que el directorio existe
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_location = VIDEO_DIR / f"{file_id}{file_extension}"
        print(f"Guardando archivo en: {file_location}")
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Verificar que el archivo existe
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        print(f"Archivo de vídeo guardado correctamente: {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location),
            "file_extension": file_extension
        }
    except Exception as e:
        print(f"Error en upload_video_for_cut: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/cut-video")
async def cut_video_endpoint(request: CutVideoRequest):
    """
    Endpoint para cortar un segmento de un archivo de vídeo usando FFmpeg.
    """
    try:
        # Buscar el archivo por ID
        files = list(VIDEO_DIR.glob(f"{request.file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo de vídeo no encontrado")
        
        input_file = files[0]
        file_extension = input_file.suffix
        
        # Crear nombre para el archivo de salida
        output_filename = f"{request.original_name or request.file_id}_cortado{file_extension}"
        output_file = PROCESSED_DIR / output_filename
        
        # Procesar el corte de vídeo usando la función del módulo
        result = cut_video(
            video_path=input_file,
            output_path=output_file,
            start_time=request.start_time,
            end_time=request.end_time
        )
        
        # Verificar que el archivo de salida existe
        if not output_file.exists():
            raise HTTPException(status_code=500, detail="El archivo de salida no se generó correctamente")
        
        # Devolver URL para descargar el archivo
        return {
            "status": "success",
            "file_id": request.file_id,
            "original_name": request.original_name,
            "output_filename": output_filename,
            "download_url": f"/api/download/{output_filename}",
            "video_info": {
                "duration": result.get("duration", 0),
                "size": result.get("size", 0),
                "format": result.get("format", file_extension[1:])
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en cut_video_endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar el vídeo: {str(e)}")

@app.post("/api/upload-audio-for-montage")
async def upload_audio_for_montage(file: UploadFile = File(...)):
    """
    Endpoint para subir un archivo de audio para montaje de vídeo.
    """
    try:
        # Generar ID único para este archivo
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem  # Guardar el nombre original sin extensión
        file_extension = Path(filename).suffix
        
        # Verificar que sea un archivo de audio
        valid_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg']
        if file_extension.lower() not in valid_extensions:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de audio (MP3, WAV, M4A, AAC, OGG)")
        
        # Asegurarse de que el directorio existe
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_location = AUDIO_DIR / f"{file_id}{file_extension}"
        print(f"Guardando audio en: {file_location}")
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Verificar que el archivo existe
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        print(f"Archivo de audio guardado correctamente: {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location),
            "file_extension": file_extension
        }
    except Exception as e:
        print(f"Error en upload_audio_for_montage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/upload-image-for-montage")
async def upload_image_for_montage(file: UploadFile = File(...)):
    """
    Endpoint para subir una imagen para montaje de vídeo.
    """
    try:
        # Generar ID único para este archivo
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem  # Guardar el nombre original sin extensión
        file_extension = Path(filename).suffix
        
        # Verificar que sea un archivo de imagen
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        if file_extension.lower() not in valid_extensions:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de imagen (JPG, PNG, WEBP, GIF)")
        
        # Asegurarse de que el directorio existe
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_location = CAPTURES_DIR / f"{file_id}{file_extension}"
        print(f"Guardando imagen en: {file_location}")
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Verificar que el archivo existe
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        print(f"Archivo de imagen guardado correctamente: {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location),
            "file_extension": file_extension
        }
    except Exception as e:
        print(f"Error en upload_image_for_montage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/generate-montage")
async def generate_montage_endpoint(request: MontageRequest):
    """
    Endpoint para generar un montaje de vídeo a partir de imágenes y audio.
    """
    try:
        # Buscar el archivo de audio por ID
        audio_files = list(AUDIO_DIR.glob(f"{request.audio_id}.*"))
        
        if not audio_files:
            raise HTTPException(status_code=404, detail="Archivo de audio no encontrado")
        
        audio_path = audio_files[0]
        print(f"Audio encontrado: {audio_path}")
        
        # Procesar cada imagen
        image_paths = []
        for img_info in request.images:
            img_id = img_info['id']
            img_files = list(CAPTURES_DIR.glob(f"{img_id}.*"))
            
            if not img_files:
                raise HTTPException(status_code=404, detail=f"Imagen con ID {img_id} no encontrada")
            
            image_path = img_files[0]
            
            # Añadir a la lista con el tiempo de inicio
            image_paths.append({
                'path': str(image_path),
                'start_time': img_info['startTime']  # Asegúrate de que coincide con el nombre en el frontend
            })
        
        # Verificar que hay al menos una imagen
        if not image_paths:
            raise HTTPException(status_code=400, detail="Se requiere al menos una imagen para crear el montaje")
        
        # Ordenar imágenes por tiempo de inicio
        image_paths.sort(key=lambda x: x['start_time'])
        
        # Crear nombre para el archivo de salida
        output_filename = f"{request.original_name or request.audio_id}_montaje.{request.output_format}"
        
        # Procesar el montaje de vídeo usando la función del módulo
        result = generate_video_montage(
            audio_path=str(audio_path),
            image_paths=image_paths,
            output_dir=str(PROCESSED_DIR),
            output_filename=output_filename
        )
        
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('error', 'Error desconocido'))
        
        output_path = result['output_path']
        
        # Verificar que el archivo de salida existe
        if not Path(output_path).exists():
            raise HTTPException(status_code=500, detail="El archivo de salida no se generó correctamente")
        
        # Devolver URL para descargar el archivo
        return {
            "status": "success",
            "audio_id": request.audio_id,
            "original_name": request.original_name,
            "output_filename": result['output_filename'],
            "download_url": f"/api/download/{result['output_filename']}",
            "video_info": {
                "duration": result.get('duration', 0),
                "size": result.get('file_size', 0),
                "format": request.output_format
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en generate_montage_endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al generar el montaje: {str(e)}")

@app.post("/api/generate-audio")
async def generate_audio_endpoint(request: GenerateAudioRequest):
    """Endpoint para generar un archivo de audio a partir de una transcripción"""
    try:
        # Buscar la transcripción por ID
        console.print(f"[blue]Generando audio para transcripción ID:[/blue] {request.file_id}")
        
        # Directorio donde se encuentran los archivos de transcripción
        transcript_dir = TRANSCRIPTS_DIR / request.file_id
        
        if not transcript_dir.exists():
            raise HTTPException(status_code=404, detail="Transcripción no encontrada")
        
        # Usar el nombre original o un UUID si no está disponible
        output_name = request.original_name or request.file_id
        
        # Verificar si existe el archivo de texto o JSON
        input_file = None
        txt_file = transcript_dir / f"{output_name}.txt"
        json_file = transcript_dir / f"{output_name}.json"
        
        if txt_file.exists():
            input_file = txt_file
            console.print(f"[green]Usando archivo TXT:[/green] {input_file}")
        elif json_file.exists():
            input_file = json_file
            console.print(f"[green]Usando archivo JSON:[/green] {input_file}")
        else:
            raise HTTPException(status_code=404, detail="No se encontró archivo de transcripción (txt o json)")
        
        # Directorio para archivos de audio generados
        audio_dir = AUDIO_OUTPUT_DIR / request.file_id
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar el archivo de audio
        output_file = audio_dir / f"{output_name}.mp3"
        
        # Ejecutar la generación de audio con los nuevos parámetros
        stats = generate_speech_from_file(
            input_file=input_file,
            output_file=output_file,
            voice=request.voice,
            model=request.model,
            instructions=request.instructions,
            speed=request.speed,
            pause_duration_ms=request.pause_duration_ms
        )
        
        # Verificar que el archivo se generó correctamente
        if not output_file.exists():
            raise HTTPException(status_code=500, detail="Error al generar el archivo de audio")
        
        # Preparar respuesta con más información
        return {
            "status": "success",
            "file_id": request.file_id,
            "original_name": output_name,
            "voice": request.voice,
            "model": request.model,
            "speed": request.speed,
            "pause_duration_ms": request.pause_duration_ms,
            "duration": stats.get("duration", 0),
            "duration_without_pauses": stats.get("duration_without_pauses", 0),
            "total_pause_duration": stats.get("total_pause_duration", 0),
            "segments_count": stats.get("segments_count", 0),
            "number_of_pauses": stats.get("number_of_pauses", 0),
            "file_size": stats.get("file_size", 0),
            "characters": stats.get("characters", 0),
            "cost": stats.get("cost", 0),
            "download_url": f"/api/download-audio/{request.file_id}/{output_name}.mp3"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[red]Error al generar audio:[/red] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al generar audio: {str(e)}")

@app.post("/api/upload-transcript-for-audio")
async def upload_transcript_for_audio(file: UploadFile = File(...)):
    """Endpoint para subir un archivo de transcripción para generar audio"""
    try:
        # Generar ID único para este archivo
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem  # Guardar el nombre original sin extensión
        file_extension = Path(filename).suffix.lower()
        
        # Verificar que sea un archivo de texto o JSON
        if file_extension not in ['.txt', '.json']:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de texto (.txt) o JSON (.json)")
        
        # Directorio para las transcripciones
        transcript_dir = TRANSCRIPTS_DIR / file_id
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_location = transcript_dir / f"{original_name}{file_extension}"
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Verificar que el archivo existe
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        console.print(f"[green]Archivo de transcripción guardado correctamente:[/green] {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location)
        }
    except HTTPException:
        raise
    except Exception as e:
        console.print(f"[red]Error al procesar la carga del archivo:[/red] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.get("/api/download-audio/{file_id}/{filename}")
async def download_audio(file_id: str, filename: str):
    """Endpoint para descargar un archivo de audio generado"""
    # Ruta del archivo de audio
    file_path = AUDIO_OUTPUT_DIR / file_id / filename
    
    # Si el archivo no existe, intentar otras rutas
    if not file_path.exists():
        # Intentar con solo el nombre del archivo
        alt_path = AUDIO_OUTPUT_DIR / file_id / Path(filename).name
        if alt_path.exists():
            file_path = alt_path
        else:
            console.print(f"[red]Archivo de audio no encontrado:[/red] {file_path}")
            raise HTTPException(status_code=404, detail="Archivo de audio no encontrado")
    
    console.print(f"[green]Enviando archivo de audio:[/green] {file_path}")
    
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=Path(filename).name
    )

@app.get("/api/voices")
async def get_available_voices():
    """Endpoint para obtener la lista de voces disponibles"""
    try:
        # Cargar configuración de TTS
        config_path = BASE_DIR / "config" / "ttsapi.json"
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="Archivo de configuración no encontrado")
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Extraer voces disponibles
        voices = config.get("documentation", {}).get("models", {}).get("gpt-4o-mini-tts", {}).get("voices", [])
        
        return {
            "status": "success",
            "voices": voices
        }
    except Exception as e:
        console.print(f"[red]Error al obtener voces:[/red] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener voces: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8088, reload=True) 