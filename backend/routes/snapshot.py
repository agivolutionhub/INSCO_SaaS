from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import tempfile, os, shutil, uuid, time, zipfile, logging, json, psutil
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.snapshot_service import extract_pptx_slides

router = APIRouter(prefix="/api/snapshot", tags=["snapshot"])

# Configuración
STORAGE_DIR = Path(os.environ.get("SNAPSHOT_STORAGE_DIR", "./storage/snapshots"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = int(os.environ.get("SNAPSHOT_MAX_FILE_SIZE", 100 * 1024 * 1024))
MAX_CONCURRENT_JOBS = int(os.environ.get("SNAPSHOT_MAX_CONCURRENT_JOBS", 3))
JOB_TIMEOUT = int(os.environ.get("SNAPSHOT_JOB_TIMEOUT", 600))

# Logger
logger = logging.getLogger("snapshot-routes")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# Control de trabajos
active_jobs = {}

def success_response(data: Any = None, message: Optional[str] = None, preserve_structure: bool = True) -> Dict[str, Any]:
    """
    Genera una respuesta de éxito estandarizada.
    
    Args:
        data: Datos a devolver
        message: Mensaje opcional
        preserve_structure: Si True, devuelve data directamente para mantener compatibilidad
    
    Returns:
        Respuesta formateada según corresponda
    """
    # Para endpoints consumidos por el frontend, mantener estructura original
    if preserve_structure and data is not None:
        return data
        
    # Nuevo formato estandarizado para endpoints nuevos
    response = {"status": "success"}
    
    if message:
        response["message"] = message
        
    if data is not None:
        response["data"] = data
        
    return response

def error_response(message: str, status_code: int = 400, details: Optional[Any] = None) -> Dict[str, Any]:
    """Genera una respuesta de error estandarizada."""
    response = {"status": "error", "message": message}
    
    if details:
        response["details"] = details
    
    return response

def save_to_storage(dir_path: str) -> str:
    """Guarda archivos en el almacenamiento persistente."""
    file_id = str(uuid.uuid4())
    
    # Obtener el nombre del directorio original (posiblemente contiene un ID)
    original_dir_name = Path(dir_path).name
    
    # Si el nombre del directorio contiene un patrón UUID, usarlo como file_id
    import re
    uuid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    if uuid_pattern.search(original_dir_name):
        file_id = original_dir_name
    
    dest_dir = STORAGE_DIR / file_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Guardando archivos de {dir_path} en {dest_dir}")
    
    for file in Path(dir_path).glob("*"):
        if file.is_file():
            shutil.copy2(file, dest_dir / file.name)
    
    return file_id

def process_pptx_to_images(pptx_path: str, job_id: str, dpi: int, format: str):
    """Procesa un archivo PPTX para generar imágenes."""
    result_file = STORAGE_DIR / f"{job_id}_result.json"
    temp_dir = None
    start_time = time.time()
    
    try:
        logger.info(f"Convirtiendo {pptx_path} a imágenes ({dpi} DPI, {format})")
        
        # Recursos y entorno
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        if job_id in active_jobs:
            active_jobs[job_id] = {"start_time": start_time}
        
        # Directorio temporal
        temp_dir = tempfile.mkdtemp(prefix=f"insco_snapshot_{job_id}_")
        os.environ["INSCO_MEMORY_LIMIT"] = "1"
        
        # Procesamiento
        result = extract_pptx_slides(
            pptx_path=pptx_path,
            output_dir=temp_dir,
            format=format,
            dpi=dpi
        )
        
        # Métricas
        elapsed = time.time() - start_time
        memory_used = (process.memory_info().rss / 1024 / 1024) - initial_memory
        logger.info(f"Generadas {result['slides']} imágenes en {elapsed:.1f}s ({memory_used:.1f}MB)")
        
        # Resultados
        slides_dir_id = save_to_storage(temp_dir)
        with open(result_file, "w") as f:
            json.dump({
                "status": "completed",
                "dir_id": slides_dir_id,
                "slides_count": result["slides"],
                "format": result["format"],
                "dpi": result["dpi"],
                "completion_time": time.time(),
                "elapsed_seconds": elapsed,
                "files": [Path(f).name for f in result["generated_files"]],
                "metrics": {"memory_mb": memory_used, "time_seconds": elapsed}
            }, f)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        with open(result_file, "w") as f:
            json.dump({
                "status": "error", 
                "message": str(e),
                "error_type": type(e).__name__,
                "completion_time": time.time(),
                "elapsed_seconds": time.time() - start_time
            }, f)
    finally:
        # Limpieza
        if job_id in active_jobs:
            active_jobs.pop(job_id, None)
        try:
            if pptx_path and os.path.exists(pptx_path):
                os.unlink(pptx_path)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Error limpiando: {e}")

def validate_upload_parameters(file: UploadFile, dpi: int, format: str) -> None:
    """Valida los parámetros de carga de archivos."""
    if len(active_jobs) >= MAX_CONCURRENT_JOBS:
        # Limpiar trabajos viejos
        now = time.time()
        for jid, info in list(active_jobs.items()):
            if now - info["start_time"] > JOB_TIMEOUT:
                active_jobs.pop(jid, None)
        
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            raise HTTPException(
                status_code=429, 
                detail=error_response(f"Máximo {MAX_CONCURRENT_JOBS} trabajos simultáneos")
            )
    
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(
            status_code=400, 
            detail=error_response("El archivo debe ser PPTX")
        )
    
    if format not in ["png", "jpg"]:
        raise HTTPException(
            status_code=400, 
            detail=error_response("Formato debe ser png o jpg")
        )
    
    if dpi < 72 or dpi > 600:
        raise HTTPException(
            status_code=400, 
            detail=error_response("DPI debe estar entre 72 y 600")
        )
    
    size = file.size if hasattr(file, "size") else 0
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=error_response(f"Archivo demasiado grande. Máximo {MAX_FILE_SIZE//1024//1024}MB")
        )

@router.post("/upload-pptx")
async def upload_pptx_for_snapshot(
    file: UploadFile = File(...),
    dpi: int = Form(300),
    format: str = Form("png")
):
    try:
        # Validaciones
        validate_upload_parameters(file, dpi, format)
        
        # Guardar archivo
        temp_dir = tempfile.mkdtemp()
        safe_name = ''.join(c for c in file.filename.replace(" ", "_").replace("(", "").replace(")", "") 
                          if c.isalnum() or c in "_-.").strip()
        safe_name = safe_name or f"presentacion_{int(time.time())}.pptx"
        input_path = os.path.join(temp_dir, safe_name)
        
        with open(input_path, "wb") as f:
            total_size = 0
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk: break
                f.write(chunk)
                total_size += len(chunk)
        
        if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
            raise HTTPException(
                status_code=500, 
                detail=error_response("Error al guardar el archivo")
            )
            
        # Crear trabajo
        job_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        
        with open(STORAGE_DIR / f"{job_id}_job.json", "w") as f:
            json.dump({
                "job_id": job_id,
                "original_name": original_name,
                "input_path": input_path,
                "dpi": dpi,
                "format": format,
                "timestamp": str(int(time.time())),
                "file_size": total_size
            }, f)
        
        active_jobs[job_id] = {"start_time": time.time()}
        
        # Ejecutar proceso
        bg_task = BackgroundTasks()
        if os.environ.get("FASTAPI_ENV") == "development":
            process_pptx_to_images(input_path, job_id, dpi, format)
        else:
            bg_task.add_task(process_pptx_to_images, input_path, job_id, dpi, format)
        
        return JSONResponse(success_response({
            "job_id": job_id,
            "filename": file.filename,
            "original_name": original_name,
            "status": "processing",
            "check_status_url": f"/api/snapshot/jobs/{job_id}"
        }))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=error_response(str(e))
        )

@router.get("/jobs/{job_id}")
async def get_snapshot_status(job_id: str):
    # Verificar resultado
    result_file = STORAGE_DIR / f"{job_id}_result.json"
    if result_file.exists():
        try:
            with open(result_file) as f:
                result = json.load(f)
            
            # Añadir metadatos
            result["job_id"] = result.get("job_id", job_id)
            if result.get("status") == "completed" and "dir_id" in result:
                result["files_url"] = f"/api/snapshot/files/{result['dir_id']}"
                result["download_zip_url"] = f"/api/snapshot/download-zip/{result['dir_id']}"
                
            return JSONResponse(success_response(result))
        except Exception as e:
            logger.error(f"Error leyendo resultado: {e}")
            return JSONResponse(
                success_response({
                    "job_id": job_id, 
                    "status": "error", 
                    "message": f"Error al recuperar estado: {e}"
                })
            )
    
    # Verificar trabajo en proceso
    job_file = STORAGE_DIR / f"{job_id}_job.json"
    if job_file.exists():
        try:
            with open(job_file) as f:
                job_info = json.load(f)
            
            start_time = int(job_info.get("timestamp", 0))
            elapsed = time.time() - start_time if start_time else 0
            
            return JSONResponse(success_response({
                "job_id": job_id,
                "status": "processing",
                "elapsed_seconds": int(elapsed)
            }))
        except Exception:
            return JSONResponse(success_response({
                "job_id": job_id, 
                "status": "processing"
            }))
    
    # No encontrado
    return JSONResponse(
        success_response({"job_id": job_id, "status": "not_found"}), 
        status_code=404
    )

@router.get("/files/{dir_id}")
async def list_snapshot_files(dir_id: str):
    dir_path = STORAGE_DIR / dir_id
    if not dir_path.exists() or not dir_path.is_dir():
        raise HTTPException(
            status_code=404, 
            detail=error_response("Directorio no encontrado")
        )
    
    files = [{
        "name": f.name,
        "size": f.stat().st_size,
        "url": f"/api/snapshot/files/{dir_id}/{f.name}"
    } for f in sorted(dir_path.glob("*")) if f.is_file()]
    
    return JSONResponse(success_response({
        "dir_id": dir_id,
        "files_count": len(files),
        "files": files,
        "download_zip_url": f"/api/snapshot/download-zip/{dir_id}"
    }))

@router.get("/files/{dir_id}/{filename}")
async def download_snapshot_file(dir_id: str, filename: str):
    """Descarga un archivo de imagen específico."""
    # Primero buscar en el directorio de almacenamiento estándar
    file_path = STORAGE_DIR / dir_id / filename
    
    # Si no existe, buscar en el directorio temporal de capturas
    if not file_path.exists() or not file_path.is_file():
        captures_dir = Path(os.environ.get("CAPTURES_DIR", "./tmp/captures"))
        tmp_file_path = captures_dir / dir_id / filename
        
        if tmp_file_path.exists() and tmp_file_path.is_file():
            file_path = tmp_file_path
            logger.debug(f"Sirviendo archivo desde directorio temporal: {file_path}")
        else:
            logger.error(f"Archivo no encontrado: {file_path} ni {tmp_file_path}")
            raise HTTPException(
                status_code=404, 
                detail=error_response("Archivo no encontrado")
            )
    
    media_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
    return FileResponse(path=file_path, filename=filename, media_type=media_type)

@router.get("/download-zip/{dir_id}")
async def download_snapshot_zip(dir_id: str, background_tasks: BackgroundTasks):
    dir_path = STORAGE_DIR / dir_id
    if not dir_path.exists() or not dir_path.is_dir():
        raise HTTPException(
            status_code=404, 
            detail=error_response("Directorio no encontrado")
        )
    
    temp_dir = tempfile.mkdtemp()
    zip_path = Path(temp_dir) / f"snapshot_{dir_id}.zip"
    
    try:
        files_to_zip = [f for f in sorted(dir_path.glob("*")) if f.is_file()]
        if not files_to_zip:
            raise HTTPException(
                status_code=404, 
                detail=error_response("No hay archivos para descargar")
            )
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files_to_zip:
                zipf.write(file, file.name)
        
        def cleanup_temp():
            try:
                if zip_path.exists(): os.unlink(zip_path)
                if temp_dir and os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            except: pass
        
        response = FileResponse(
            path=zip_path,
            filename=f"snapshot_{dir_id}.zip",
            media_type="application/zip"
        )
        
        background_tasks.add_task(cleanup_temp)
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        try:
            if zip_path.exists(): os.unlink(zip_path)
            if temp_dir and os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        except: pass
        
        logger.error(f"Error ZIP: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=error_response(str(e))
        ) 