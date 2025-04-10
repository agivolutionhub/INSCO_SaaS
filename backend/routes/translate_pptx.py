from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import tempfile
import os
import shutil
import uuid
from pathlib import Path
import logging
import json
import sys
import zipfile
import time

# Añadir directorio base al path para importar el script de traducción
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.translation_service import Translator, PPTXEditor

router = APIRouter(prefix="/api/translate", tags=["translate"])

# Directorio para almacenar archivos procesados
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "./storage"))
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

# Configurar logging
logger = logging.getLogger("translate_pptx")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
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

def process_translation_task(input_path: str, output_dir: str, source_lang: str, target_lang: str, job_id: str):
    """Tarea en segundo plano para traducir la presentación"""
    process_file = None
    result_file = STORAGE_DIR / f"{job_id}_result.json"
    
    try:
        logger.info(f"Iniciando traducción: {input_path}, de {source_lang} a {target_lang}")
        
        # Identificar file_id
        file_id = None
        process_matches = list(STORAGE_DIR.glob(f"*_processing_{job_id}.json"))
        if process_matches:
            process_file = process_matches[0]
            file_id = process_file.name.split("_processing_")[0]
            logger.info(f"ID identificado: {file_id} para job: {job_id}")
        
        # Comprobar archivo
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        logger.info(f"Tamaño del archivo: {file_size_mb:.2f} MB")
        
        # Definir salida
        output_path = Path(output_dir) / f"{Path(input_path).stem}_translated_{target_lang}.pptx"
        
        # Iniciar traductor
        translator = Translator(target_language=target_lang, use_cache=True)
        editor = PPTXEditor(translator)
        
        # Procesar presentación
        logger.info(f"Traduciendo presentación de {source_lang} a {target_lang}")
        start_time = time.time()
        
        result_path = editor.process_pptx(input_path, output_path)
        
        if not result_path or not Path(result_path).exists():
            raise Exception("No se generó el archivo de salida")
        
        logger.info(f"Traducción completada: {result_path}")
        
        # Recopilar estadísticas
        stats = _collect_translation_stats(editor, translator, start_time)
        
        # Almacenar resultado
        file_id_result = file_id or str(uuid.uuid4())
        result_file_id = save_to_storage(str(result_path))
        filename = Path(result_path).name
        
        # Actualizar estado
        result_data = {
            "status": "completed",
            "file_id": result_file_id,
            "filename": filename,
            "download_url": f"/api/translate/files/{result_file_id}/{filename}",
            "completion_time": time.time(),
            "stats": stats
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False)
            
        logger.info(f"Proceso completado para job {job_id}")
        
    except Exception as e:
        logger.error(f"Error procesando traducción: {str(e)}", exc_info=True)
        
        # Guardar error
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({
                "status": "error", 
                "message": str(e),
                "completion_time": time.time()
            }, f, ensure_ascii=False)
    finally:
        _cleanup_temp_files(process_file, input_path, output_dir)

def _collect_translation_stats(editor, translator, start_time):
    """Recopila estadísticas del proceso de traducción"""
    stats = {
        "slides_processed": getattr(editor, "slides_processed", 0),
        "texts_translated": getattr(editor, "total_texts", 0),
        "total_time": time.time() - start_time,
        "api_calls": max(1, getattr(translator, "api_calls", 0)),
        "rate_limit_retries": getattr(translator, "rate_limit_retries", 0),
        "successful_retries": getattr(translator, "successful_retries", 0),
        "errors": getattr(translator, "errors", 0),
        "duplicates_avoided": getattr(translator, "duplicates_avoided", 0),
        "cache_hits": getattr(translator, "cache_hits", 0),
        "cache_misses": getattr(translator, "cache_misses", 0),
        "input_tokens": getattr(translator, "total_input_tokens", 0),
        "output_tokens": getattr(translator, "total_output_tokens", 0),
        "cached_tokens": getattr(translator, "cached_tokens", 0),
    }
    
    # Asegurar tokens mínimos si hay textos
    if stats["texts_translated"] > 0 and stats["input_tokens"] == 0 and stats["cached_tokens"] == 0:
        tokens_per_text = 25
        if stats["cache_hits"] > 0:
            stats["cached_tokens"] = stats["texts_translated"] * tokens_per_text
        else:
            stats["input_tokens"] = stats["texts_translated"] * tokens_per_text
            stats["output_tokens"] = stats["texts_translated"] * tokens_per_text * 1.2
    
    # Calcular totales
    stats["total_tokens"] = stats["input_tokens"] + stats["output_tokens"] + stats["cached_tokens"]
    
    # Calcular costos
    input_cost = (stats["input_tokens"] / 1_000_000) * 3.75
    cached_cost = (stats["cached_tokens"] / 1_000_000) * 1.875
    output_cost = (stats["output_tokens"] / 1_000_000) * 15.0
    total_cost = input_cost + cached_cost + output_cost
    
    stats["input_cost"] = input_cost
    stats["cached_cost"] = cached_cost
    stats["output_cost"] = output_cost
    stats["total_cost"] = total_cost
    
    # Métricas adicionales
    if stats["total_tokens"] > 0:
        stats["cost_per_1k_tokens"] = (total_cost * 1000) / stats["total_tokens"]
    else:
        stats["cost_per_1k_tokens"] = 0
    
    stats["tokens_per_second"] = stats["total_tokens"] / max(0.1, stats["total_time"])
    stats["slides_per_second"] = stats["slides_processed"] / max(0.1, stats["total_time"])
    
    # Métricas de caché
    cache_total = stats["cache_hits"] + stats["cache_misses"]
    stats["cache_hit_rate"] = (stats["cache_hits"] / cache_total) * 100 if cache_total > 0 else 0
    
    # Resumen global
    stats["efficiency_summary"] = {
        "processing_speed": f"{stats['slides_per_second']:.2f} diapositivas/seg",
        "token_rate": f"{stats['tokens_per_second']:.2f} tokens/seg",
        "cache_efficiency": f"{stats['cache_hit_rate']:.1f}%",
        "cost_efficiency": f"${stats['cost_per_1k_tokens']:.6f}/1K tokens"
    }
    
    return stats

def _cleanup_temp_files(process_file, input_path, output_dir):
    """Limpia archivos temporales del proceso de traducción"""
    # Limpiar archivo de proceso
    if process_file and process_file.exists():
        try:
            process_file.unlink()
        except Exception as e:
            logger.error(f"Error al eliminar archivo de proceso: {str(e)}")
    
    # Eliminar entrada temporal
    if os.path.exists(input_path):
        try:
            os.unlink(input_path)
        except Exception as e:
            logger.error(f"Error al eliminar temporal: {str(e)}")
            
    # Eliminar directorio temporal
    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
        except Exception as e:
            logger.error(f"Error al eliminar directorio temporal: {str(e)}")

def _validate_translation_request(file, source_language, target_language):
    """Valida los parámetros de una solicitud de traducción"""
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser PPTX")
    
    supported_languages = ["es", "en", "fr", "de", "it", "pt"]
    if source_language not in supported_languages or target_language not in supported_languages:
        raise HTTPException(status_code=400, detail="Idioma no soportado")
    
    if source_language == target_language:
        raise HTTPException(status_code=400, detail="Los idiomas deben ser diferentes")

@router.post("/upload-pptx-for-translation")
async def upload_pptx_for_translation(
    file: UploadFile = File(...),
    source_language: str = Form("es"),
    target_language: str = Form("en")
):
    """Endpoint para subir un archivo PPTX para traducción"""
    try:
        logger.info(f"Solicitud para traducir: {file.filename}, de {source_language} a {target_language}")
        
        # Validaciones
        _validate_translation_request(file, source_language, target_language)
        
        # Crear directorio y guardar archivo
        temp_dir = tempfile.mkdtemp()
        safe_filename = file.filename.replace(" ", "_").replace("(", "").replace(")", "")
        input_path = os.path.join(temp_dir, safe_filename)
        
        with open(input_path, "wb") as buffer:
            # Leer por chunks
            chunk_size = 1024 * 1024  # 1MB
            total_size = 0
            
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                buffer.write(chunk)
                total_size += len(chunk)
            
            logger.info(f"Archivo guardado. Tamaño: {total_size/1024/1024:.2f}MB")
        
        # Generar ID
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        
        # Almacenar metadata
        file_meta = STORAGE_DIR / f"{file_id}_meta.json"
        with open(file_meta, "w", encoding="utf-8") as f:
            json.dump({
                "file_id": file_id,
                "original_name": original_name,
                "input_path": input_path,
                "source_language": source_language,
                "target_language": target_language,
                "timestamp": str(int(time.time()))
            }, f, ensure_ascii=False)
        
        logger.info(f"Archivo registrado con ID: {file_id}")
        
        # Respuesta
        return JSONResponse({
            "file_id": file_id,
            "filename": file.filename,
            "original_name": original_name,
            "status": "uploaded",
            "message": "Archivo subido correctamente, listo para procesar"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

@router.post("/process-translation")
async def process_translation(
    background_tasks: BackgroundTasks,
    request: dict
):
    """Inicia el proceso de traducción para un archivo previamente subido"""
    try:
        file_id = request.get("file_id")
        original_name = request.get("original_name")
        source_language = request.get("source_language", "es")
        target_language = request.get("target_language", "en")
        
        if not file_id:
            raise HTTPException(status_code=400, detail="Se requiere file_id")
            
        logger.info(f"Procesando traducción para {file_id}, de {source_language} a {target_language}")
        
        # Verificar si ya existe un trabajo
        result_check = list(STORAGE_DIR.glob(f"{file_id}_processing_*.json"))
        if result_check:
            # Trabajo en proceso
            with open(result_check[0], "r", encoding="utf-8") as f:
                existing_job = json.load(f)
                
            logger.info(f"Ya existe un trabajo para {file_id}: {existing_job.get('job_id')}")
            return JSONResponse({
                "job_id": existing_job.get("job_id"),
                "file_id": file_id,
                "output_filename": existing_job.get("output_filename", f"{original_name}_translated_{target_language}.pptx"),
                "status": "processing",
                "message": "Ya existe un proceso de traducción en curso",
                "download_url": f"/api/translate/jobs/{existing_job.get('job_id')}"
            })
        
        # Cargar metadata
        file_meta_path = STORAGE_DIR / f"{file_id}_meta.json"
        if not file_meta_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        with open(file_meta_path, "r", encoding="utf-8") as f:
            file_meta = json.load(f)
        
        input_path = file_meta.get("input_path")
        if not input_path or not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail="Archivo original no encontrado")
        
        # Verificar archivo
        file_size = os.path.getsize(input_path)
        if file_size == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío")
        
        # Crear directorio de salida
        output_dir = tempfile.mkdtemp()
        
        # Generar nombre de salida
        output_filename = f"{original_name or file_meta.get('original_name')}_translated_{target_language}.pptx"
        
        # Iniciar tarea
        job_id = str(uuid.uuid4())
        
        # Registrar trabajo
        processing_file = STORAGE_DIR / f"{file_id}_processing_{job_id}.json"
        with open(processing_file, "w", encoding="utf-8") as f:
            json.dump({
                "job_id": job_id,
                "file_id": file_id,
                "input_path": input_path,
                "output_dir": output_dir,
                "output_filename": output_filename,
                "source_language": source_language,
                "target_language": target_language,
                "start_time": time.time()
            }, f, ensure_ascii=False)
        
        # Iniciar tarea
        background_tasks.add_task(
            process_translation_task,
            input_path,
            output_dir,
            source_language,
            target_language,
            job_id
        )
        
        logger.info(f"Tarea iniciada con ID: {job_id}")
        
        # Respuesta
        return JSONResponse({
            "job_id": job_id,
            "file_id": file_id,
            "output_filename": output_filename,
            "status": "processing",
            "message": "Procesando traducción en segundo plano",
            "download_url": f"/api/translate/jobs/{job_id}"
        })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar traducción: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_translation_status(job_id: str):
    """Obtiene el estado de un trabajo de traducción"""
    result_file = STORAGE_DIR / f"{job_id}_result.json"
    
    # Buscar archivo de resultado
    if result_file.exists():
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            
            if "job_id" not in result:
                result["job_id"] = job_id
                
            return JSONResponse(result)
        except Exception as e:
            logger.error(f"Error al leer resultado: {str(e)}")
            return JSONResponse({
                "job_id": job_id,
                "status": "error",
                "message": f"Error al recuperar estado: {str(e)}"
            })
    
    # Buscar archivo de proceso
    processing_files = list(STORAGE_DIR.glob(f"*_processing_{job_id}.json"))
    if processing_files:
        try:
            with open(processing_files[0], "r", encoding="utf-8") as f:
                process_info = json.load(f)
            
            # Calcular progreso
            start_time = process_info.get("start_time", 0)
            elapsed = time.time() - float(start_time) if start_time else 0
            
            # Estimar porcentaje (máximo 30 min)
            max_time = 30 * 60
            progress = min(95, (elapsed / max_time) * 100) if elapsed > 0 else 5
            
            return JSONResponse({
                "job_id": job_id,
                "file_id": process_info.get("file_id"),
                "status": "processing",
                "message": "La traducción está en proceso",
                "elapsed_seconds": int(elapsed),
                "estimated_progress": round(progress, 1),
                "start_time": start_time
            })
        except Exception as e:
            logger.error(f"Error al leer info: {str(e)}")
            return JSONResponse({
                "job_id": job_id,
                "status": "processing",
                "message": "La traducción sigue en proceso"
            })
    
    # No encontrado
    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "message": "Trabajo en cola o no encontrado"
    })

@router.get("/files/{file_id}/{filename}")
async def download_translated_file(file_id: str, filename: str):
    """Descarga un archivo traducido"""
    file_path = STORAGE_DIR / file_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

def _create_zip_from_files(files_to_zip, zip_path):
    """Crea un archivo ZIP con los archivos especificados"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path, filename in files_to_zip:
            zipf.write(file_path, filename)
            logger.info(f"Añadido {filename} al ZIP")
    
    # Verificar ZIP
    if not zip_path.exists() or os.path.getsize(zip_path) == 0:
        raise Exception("Error al crear ZIP")
    
    return zip_path

def _get_files_for_zip(file_infos):
    """Obtiene la lista de archivos para comprimir en ZIP"""
    files_to_zip = []
    for file_info in file_infos:
        file_id = file_info.get("file_id")
        filename = file_info.get("filename")
        
        if not file_id or not filename:
            continue
        
        file_path = STORAGE_DIR / file_id / filename
        
        if file_path.exists():
            files_to_zip.append((file_path, filename))
            logger.info(f"Archivo encontrado: {file_path}")
        else:
            logger.warning(f"Archivo no encontrado: {file_path}")
    
    if not files_to_zip:
        raise HTTPException(status_code=404, detail="Ningún archivo encontrado")
    
    return files_to_zip

def _prepare_zip_response(zip_path):
    """Prepara la respuesta con el archivo ZIP y programación de limpieza"""
    temp_dir = zip_path.parent
    
    def cleanup_temp():
        try:
            if zip_path.exists():
                os.unlink(zip_path)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Error en limpieza: {str(e)}")
    
    response = FileResponse(
        path=zip_path,
        filename="traducciones.zip",
        media_type="application/zip"
    )
    
    response.headers["Content-Disposition"] = "attachment; filename=traducciones.zip"
    
    # Programar limpieza
    response.background = BackgroundTasks()
    response.background.add_task(cleanup_temp)
    
    return response

@router.post("/download-all")
async def download_all_files(request: dict):
    """Crea un archivo ZIP con todos los archivos traducidos solicitados"""
    try:
        logger.info(f"Request recibido: {request}")
        
        # Obtener archivos
        files = request.get("files", [])
        
        # Compatibilidad con diferentes formatos
        if not files and "data" in request and isinstance(request["data"], dict):
            files = request["data"].get("files", [])
        
        if not files and "body" in request and isinstance(request["body"], dict):
            files = request["body"].get("files", [])
        
        if not files:
            raise HTTPException(status_code=400, detail="No se especificaron archivos")
        
        logger.info(f"Solicitada descarga de {len(files)} archivos")
        
        # Verificar archivos
        files_to_zip = _get_files_for_zip(files)
        
        # Crear ZIP
        temp_dir = Path(tempfile.mkdtemp())
        zip_file_path = temp_dir / "traducciones.zip"
        
        _create_zip_from_files(files_to_zip, zip_file_path)
        
        return _prepare_zip_response(zip_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ZIP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/download-all-files")
async def download_all_files_get(file_ids: str, filenames: str):
    """Endpoint alternativo para descargar múltiples archivos en ZIP"""
    try:
        # Parsear parámetros
        file_ids_list = file_ids.split(',') if file_ids else []
        filenames_list = filenames.split(',') if filenames else []
        
        if len(file_ids_list) != len(filenames_list):
            raise HTTPException(status_code=400, detail="La cantidad de IDs y nombres debe coincidir")
            
        if not file_ids_list:
            raise HTTPException(status_code=400, detail="No se especificaron archivos")
            
        logger.info(f"Solicitada descarga de {len(file_ids_list)} archivos via GET")
        
        # Preparar archivos
        files_to_zip = []
        for i in range(len(file_ids_list)):
            file_id = file_ids_list[i]
            filename = filenames_list[i]
            
            file_path = STORAGE_DIR / file_id / filename
            
            if file_path.exists():
                files_to_zip.append((file_path, filename))
                logger.info(f"Archivo encontrado: {file_path}")
            else:
                logger.warning(f"Archivo no encontrado: {file_path}")
        
        if not files_to_zip:
            raise HTTPException(status_code=404, detail="Ningún archivo encontrado")
        
        # Crear ZIP
        temp_dir = Path(tempfile.mkdtemp())
        zip_file_path = temp_dir / "traducciones.zip"
        
        _create_zip_from_files(files_to_zip, zip_file_path)
        
        return _prepare_zip_response(zip_file_path)
                
    except HTTPException:
        raise            
    except Exception as e:
        logger.error(f"Error ZIP: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}") 