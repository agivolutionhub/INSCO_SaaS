from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import tempfile, os, shutil, uuid, logging, json
from pathlib import Path
from typing import Dict, Any

# Importar el servicio de PPTX
from services.pptx_service import split_presentation

router = APIRouter(prefix="/api/pptx", tags=["pptx"])

# Directorio para almacenar archivos procesados
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "./storage"))
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

# Configurar logging
logger = logging.getLogger("split_pptx")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def save_to_storage(file_path: str) -> str:
    """Guarda un archivo en almacenamiento permanente y devuelve su ID"""
    file_id = str(uuid.uuid4())
    dest_dir = STORAGE_DIR / file_id
    dest_dir.mkdir(exist_ok=True)
    
    dest_path = dest_dir / Path(file_path).name
    shutil.copy2(file_path, dest_path)
    
    return file_id

def process_pptx_task(input_path: str, output_dir: str, slides_per_chunk: int, job_id: str) -> None:
    """Tarea en segundo plano para procesar la presentación"""
    result_file = STORAGE_DIR / f"{job_id}_result.json"
    
    try:
        # Comprobar tamaño y procesar archivo
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        logger.info(f"Procesando: {input_path} ({file_size_mb:.2f} MB), diapositivas/chunk: {slides_per_chunk}")
        
        # Dividir la presentación
        output_files = split_presentation(input_path, output_dir, slides_per_chunk)
        
        if not output_files:
            raise Exception("No se generaron archivos de salida")
        
        # Guardar resultados
        results = []
        for output_file in output_files:
            file_id = save_to_storage(str(output_file))
            filename = Path(output_file).name
            results.append({
                "file_id": file_id,
                "filename": filename,
                "url": f"/api/pptx/files/{file_id}/{filename}"
            })
        
        # Guardar resultado exitoso
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({"status": "completed", "files": results}, f, ensure_ascii=False)
            
        logger.info(f"Proceso completado: job_id={job_id}, archivos={len(output_files)}")
            
    except Exception as e:
        # Guardar resultado con error
        logger.error(f"Error procesando PPTX: {str(e)}", exc_info=True)
        try:
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump({"status": "error", "message": str(e)}, f, ensure_ascii=False)
        except Exception as write_error:
            logger.error(f"Error al escribir resultado: {str(write_error)}")
    finally:
        # Limpiar archivos temporales
        try:
            os.path.exists(input_path) and os.unlink(input_path)
            os.path.exists(output_dir) and shutil.rmtree(output_dir)
        except Exception as e:
            logger.error(f"Error limpiando temporales: {str(e)}")

@router.post("/split")
async def split_pptx_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    slides_per_chunk: int = Form(20)
) -> JSONResponse:
    """Divide una presentación PPTX en múltiples archivos más pequeños"""
    try:
        logger.info(f"Solicitud recibida: archivo={file.filename}, slides_per_chunk={slides_per_chunk}")
        
        # Validar parámetros
        if not file.filename or not file.filename.lower().endswith(".pptx"):
            raise HTTPException(status_code=400, detail="El archivo debe ser PPTX")
        
        if not 1 <= slides_per_chunk <= 100:
            raise HTTPException(status_code=400, detail="El número de diapositivas debe estar entre 1 y 100")
        
        # Crear directorios temporales
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Guardar archivo
        total_size = 0
        with open(input_path, "wb") as buffer:
            chunk_size = 1024 * 1024  # 1MB chunks
            while chunk := await file.read(chunk_size):
                buffer.write(chunk)
                total_size += len(chunk)
        
        logger.info(f"Archivo guardado: {input_path} ({total_size/1024/1024:.2f} MB)")
        
        # Generar ID de trabajo e iniciar tarea
        job_id = str(uuid.uuid4())
        background_tasks.add_task(process_pptx_task, input_path, output_dir, slides_per_chunk, job_id)
        logger.info(f"Tarea iniciada: job_id={job_id}")
        
        # Devolver respuesta inmediata
        return JSONResponse({
            "job_id": job_id,
            "status": "processing",
            "message": "Procesando presentación en segundo plano"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JSONResponse:
    """Obtiene el estado de un trabajo de división de PPTX"""
    result_file = STORAGE_DIR / f"{job_id}_result.json"
    
    if not result_file.exists():
        return JSONResponse({
            "job_id": job_id,
            "status": "processing",
            "message": "El trabajo sigue en proceso"
        })
    
    try:
        with open(result_file, "r", encoding="utf-8") as f:
            return JSONResponse(json.load(f))
    except Exception as e:
        logger.error(f"Error leyendo resultado {result_file}: {str(e)}")
        return JSONResponse({
            "job_id": job_id,
            "status": "error",
            "message": f"Error al recuperar el estado: {str(e)}"
        })

@router.get("/files/{file_id}/{filename}")
async def get_file(file_id: str, filename: str) -> FileResponse:
    """Descarga un archivo procesado"""
    file_path = STORAGE_DIR / file_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ) 