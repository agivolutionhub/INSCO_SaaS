from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import tempfile, os, shutil, uuid, json
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.autofit_service import procesar_pptx, procesar_lote

router = APIRouter(prefix="/api/autofit", tags=["autofit"])

# Directorios de almacenamiento
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = Path(os.environ.get("AUTOFIT_STORAGE_DIR", BASE_DIR / "../storage/autofit")).resolve()
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

# Log de la ruta para depuración
print(f"Directorio de almacenamiento Autofit: {STORAGE_DIR}")

# Funciones de utilidad para respuestas estandarizadas
def success_response(data: Any = None, message: Optional[str] = None) -> Dict[str, Any]:
    """Genera una respuesta de éxito estandarizada."""
    response = {"status": "success"}
    if message:
        response["message"] = message
    if data is not None:
        response["data"] = data
    return response

def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Genera una respuesta de error estandarizada."""
    return {"status": "error", "message": message}

@router.post("/upload-pptx")
async def upload_pptx_for_autofit(file: UploadFile = File(...)):
    """Sube un archivo PPTX para aplicar autofit."""
    try:
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem
        file_extension = Path(filename).suffix
        
        if file_extension.lower() != '.pptx':
            raise HTTPException(status_code=400, detail=error_response("Solo se permiten archivos PPTX"))
        
        file_location = STORAGE_DIR / f"{file_id}{file_extension}"
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=error_response("No se pudo guardar el archivo"))
        
        return success_response({
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location)
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=error_response(f"Error al procesar la carga del archivo: {str(e)}")
        )

@router.post("/process")
async def process_autofit(file_id: str = Form(...), original_name: str = Form(None)):
    """Procesa un archivo PPTX previamente subido para aplicar autofit."""
    try:
        # Buscar archivo por ID
        files = list(STORAGE_DIR.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail=error_response("Archivo no encontrado"))
        
        file_path = files[0]
        
        # Usar el nombre original o un UUID si no está disponible
        output_filename = f"{original_name or file_id}_autofit.pptx"
        output_path = STORAGE_DIR / output_filename
        
        # Procesar archivo
        result_path = procesar_pptx(file_path, output_path, silent=False)
        
        # Verificar que el archivo procesado existe
        if not Path(result_path).exists():
            raise HTTPException(
                status_code=500, 
                detail=error_response("El procesamiento falló: No se generó el archivo")
            )
        
        # Construir respuesta
        response_data = {
            "file_id": file_id,
            "original_name": original_name,
            "processed_file": result_path,
            "output_filename": output_filename,
            "download_url": f"/api/autofit/download/{output_filename}"
        }
        
        return success_response(response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=error_response(f"Error al procesar el archivo: {str(e)}")
        )

@router.post("/process-multiple")
async def process_multiple_autofit(file_infos: str = Form(...)):
    """Procesa múltiples archivos PPTX para aplicar autofit."""
    try:
        # Convertir JSON string a lista de objetos
        file_data = json.loads(file_infos)
        
        if len(file_data) > 10:
            raise HTTPException(
                status_code=400, 
                detail=error_response("Máximo 10 archivos permitidos")
            )
            
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
                files = list(STORAGE_DIR.glob(f"{file_id}.*"))
                
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
                output_path = STORAGE_DIR / output_filename
                
                # Procesar archivo
                result_path = procesar_pptx(file_path, output_path, silent=True)
                
                results.append({
                    "file_id": file_id,
                    "original_name": original_name,
                    "status": "success",
                    "processed_file": result_path,
                    "output_filename": output_filename,
                    "download_url": f"/api/autofit/download/{output_filename}"
                })
                
            except Exception as e:
                results.append({
                    "file_id": file_id if 'file_id' in locals() else "desconocido",
                    "status": "error",
                    "message": str(e)
                })
        
        return success_response({"results": results})
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=error_response(f"Error al procesar los archivos: {str(e)}")
        )

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Descarga un archivo procesado por autofit."""
    file_path = STORAGE_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=error_response("Archivo no encontrado")
        )
    
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename
    )

@router.post("/process-batch")
async def process_batch(
    input_dir: str = Form(None), 
    output_dir: str = Form(None), 
    background_tasks: BackgroundTasks = None
):
    """Procesa un lote de archivos PPTX por directorio."""
    try:
        job_id = str(uuid.uuid4())
        
        # Función para procesar en segundo plano
        def process_batch_background(in_dir, out_dir, job_id):
            try:
                results = procesar_lote(in_dir, out_dir, silent=True)
                
                # Guardar resultados
                result_file = STORAGE_DIR / f"{job_id}_results.json"
                with open(result_file, "w") as f:
                    json.dump({
                        "status": "completed",
                        "job_id": job_id,
                        "results": results
                    }, f)
            except Exception as e:
                # Guardar error
                result_file = STORAGE_DIR / f"{job_id}_results.json"
                with open(result_file, "w") as f:
                    json.dump({
                        "status": "error",
                        "job_id": job_id,
                        "message": str(e)
                    }, f)
        
        # Registrar tarea
        if background_tasks:
            background_tasks.add_task(process_batch_background, input_dir, output_dir, job_id)
            return success_response({
                "status": "processing",
                "job_id": job_id,
                "message": "Procesamiento iniciado en segundo plano"
            })
        else:
            # Procesar sincrónicamente
            results = procesar_lote(input_dir, output_dir, silent=True)
            return success_response({
                "status": "completed",
                "job_id": job_id,
                "results": results
            })
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=error_response(f"Error al procesar el lote: {str(e)}")
        )

@router.get("/batch-status/{job_id}")
async def get_batch_status(job_id: str):
    """Consulta el estado de un trabajo de procesamiento por lotes."""
    result_file = STORAGE_DIR / f"{job_id}_results.json"
    
    if not result_file.exists():
        return success_response({
            "status": "processing",
            "job_id": job_id,
            "message": "El trabajo sigue en proceso"
        })
    
    try:
        with open(result_file, "r") as f:
            results = json.load(f)
        return success_response(results)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=error_response(f"Error al leer los resultados: {str(e)}")
        ) 