from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pydantic.config import ConfigDict
import os
import json
import uuid
import logging
from pathlib import Path
import tempfile

# Importar servicio
from services.video_translate_service import translate_text, translate_file

# Crear router
router = APIRouter(tags=["video-translate"])

# Configurar logging
logger = logging.getLogger("video-translate-router")

# Obtener directorio base
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "tmp/uploads"
TRANSLATIONS_DIR = BASE_DIR / "storage/translations"

# Asegurar que existan los directorios
for directory in [UPLOAD_DIR, TRANSLATIONS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Modelo para solicitud de traducción directa
class TranslationRequest(BaseModel):
    text: str
    target_language: str = "English"
    original_language: Optional[str] = None
    
    # Configurar para evitar advertencias con namespaces protegidos
    model_config = ConfigDict(protected_namespaces=())

# Idiomas disponibles
AVAILABLE_LANGUAGES = [
    "English", "Spanish", "French", "German", "Italian", 
    "Portuguese", "Russian", "Chinese", "Japanese", "Korean", 
    "Arabic", "Dutch", "Swedish", "Norwegian", "Danish", 
    "Finnish", "Polish", "Turkish", "Greek", "Czech",
    "Hungarian", "Romanian", "Thai", "Vietnamese", "Indonesian"
]

@router.get("/api/video-translate/languages")
async def get_languages():
    """Retorna la lista de idiomas disponibles para traducción."""
    return {
        "languages": AVAILABLE_LANGUAGES
    }

@router.post("/api/upload-text-for-translation")
async def upload_text_for_translation(file: UploadFile = File(...)):
    """Sube un archivo de texto para traducción."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No se proporcionó un archivo")
        
        ext = Path(file.filename).suffix.lower()
        if ext != '.txt':
            raise HTTPException(
                status_code=400, 
                detail="Solo se permiten archivos de texto (.txt)"
            )
        
        # Generar ID único
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        file_path = UPLOAD_DIR / f"{file_id}.txt"
        
        # Guardar archivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Error al guardar el archivo")
        
        # Leer contenido para preview
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()
            
        # Limitar preview a 500 caracteres
        text_preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
        
        logger.info(f"Archivo de texto subido exitosamente: {file_path}")
        
        return {
            "file_id": file_id,
            "original_name": original_name,
            "filename": file.filename,
            "file_path": str(file_path),
            "text_preview": text_preview,
            "text_length": len(text_content),
            "status": "uploaded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir archivo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.post("/api/translate-text")
async def translate_text_endpoint(request: TranslationRequest):
    """Traduce un texto directamente."""
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="El texto a traducir está vacío")
        
        if request.target_language not in AVAILABLE_LANGUAGES:
            raise HTTPException(
                status_code=400, 
                detail=f"Idioma no soportado. Opciones válidas: {', '.join(AVAILABLE_LANGUAGES)}"
            )
        
        # Traducir el texto
        result = translate_text(
            text=request.text,
            target_language=request.target_language,
            original_language=request.original_language
        )
        
        # Verificar resultado
        if "status" in result and result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Error desconocido"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en la traducción: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al traducir: {str(e)}")

@router.post("/api/translate-file")
async def translate_file_endpoint(
    file_id: str = Form(...),
    target_language: str = Form("English"),
    original_language: Optional[str] = Form(None)
):
    """Traduce un archivo de texto previamente subido."""
    try:
        # Verificar idioma
        if target_language not in AVAILABLE_LANGUAGES:
            raise HTTPException(
                status_code=400, 
                detail=f"Idioma no soportado. Opciones válidas: {', '.join(AVAILABLE_LANGUAGES)}"
            )
        
        # Buscar archivo
        file_path = UPLOAD_DIR / f"{file_id}.txt"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Archivo con ID {file_id} no encontrado")
        
        # Generar ID único para la traducción
        translation_id = str(uuid.uuid4())
        output_path = TRANSLATIONS_DIR / f"{translation_id}.txt"
        
        # Traducir el archivo
        result = translate_file(
            file_path=str(file_path),
            target_language=target_language,
            output_path=str(output_path),
            original_language=original_language
        )
        
        # Verificar resultado
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Error desconocido"))
        
        # Leer el contenido del archivo traducido
        with open(output_path, "r", encoding="utf-8") as f:
            translated_text = f.read()
        
        # Añadir información adicional
        result["translation_id"] = translation_id
        result["download_url"] = f"/api/download-translation/{translation_id}"
        result["translated_text"] = translated_text
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al traducir archivo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al traducir archivo: {str(e)}")

@router.get("/api/download-translation/{translation_id}")
async def download_translation(translation_id: str):
    """Descarga un archivo de traducción."""
    try:
        file_path = TRANSLATIONS_DIR / f"{translation_id}.txt"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo de traducción no encontrado")
        
        return FileResponse(
            path=file_path,
            media_type="text/plain",
            filename=f"traduccion_{translation_id}.txt"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al descargar traducción: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al descargar la traducción: {str(e)}")

@router.post("/api/save-edited-translation")
async def save_edited_translation(
    translation_id: Optional[str] = Form(None),
    translated_text: str = Form(...),
    original_name: Optional[str] = Form(None),
    target_language: str = Form("English")
):
    """Guarda una traducción editada manualmente."""
    try:
        # Generar ID si no se proporciona
        if not translation_id:
            translation_id = str(uuid.uuid4())
        
        # Configurar nombre de archivo
        filename = f"{translation_id}.txt"
        file_path = TRANSLATIONS_DIR / filename
        
        # Guardar la traducción
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(translated_text)
        
        # Generar nombre para mostrar
        display_name = original_name or f"traduccion_{target_language.lower()}"
        
        return {
            "status": "success",
            "translation_id": translation_id,
            "message": "Traducción guardada correctamente",
            "download_url": f"/api/download-translation/{translation_id}",
            "display_name": display_name
        }
        
    except Exception as e:
        logger.error(f"Error al guardar traducción editada: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar traducción: {str(e)}") 