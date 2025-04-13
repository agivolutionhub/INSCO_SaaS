#!/usr/bin/env python3
import os, re, zipfile, tempfile, shutil, uuid, time
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from openai import OpenAI
from xml.etree import ElementTree as ET

# Credenciales embebidas
API_KEY = "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"
ASSISTANT_ID = "asst_mBShBt93TIVI0PKE7zsNO0eZ"
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "./storage"))
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

router = APIRouter(prefix="/api/translate", tags=["translate"])

def traducir_textos(textos: List[str], idioma_destino: str = "inglés") -> List[str]:
    """Traducir textos usando OpenAI Chat API directamente (sin asistente)"""
    if not textos:
        return []
    
    cliente = OpenAI(api_key=API_KEY)
    batch_texto = "\n\n".join(f"[{i+1}] {texto}" for i, texto in enumerate(textos))
    
    # Prompt específico para traducción
    system_prompt = f"Eres un traductor profesional especializado en traducir de español a {idioma_destino}. Traduce únicamente el texto proporcionado, manteniendo el formato y la numeración exacta."
    user_prompt = f"Traduce los siguientes textos de español a {idioma_destino}. Devuelve SOLO las traducciones con su numeración original [1], [2], etc. No agregues explicaciones ni texto adicional:\n\n{batch_texto}"
    
    try:
        # Usar directamente el modelo de chat en lugar del asistente
        print(f"Enviando {len(textos)} textos para traducción al modelo")
        
        # Llamada directa al API de chat completions
        respuesta = cliente.chat.completions.create(
            model="gpt-4o",  # Usar un modelo potente para traducciones precisas
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Baja temperatura para traducciones consistentes
        )
        
        # Extraer el contenido de la respuesta
        respuesta_texto = respuesta.choices[0].message.content
        print(f"Respuesta recibida, longitud: {len(respuesta_texto)}")
        
        # Procesar la respuesta
        pattern = r"\[(\d+)\](.*?)(?=\[\d+\]|$)"
        matches = re.findall(pattern, respuesta_texto, re.DOTALL)
        
        if not matches or len(matches) < len(textos):
            print("No se encontró el formato esperado, procesando línea por línea")
            lines = respuesta_texto.strip().split("\n")
            return [line.strip() for line in lines if line.strip()]
        
        # Ordenar las traducciones por número
        traducciones = [match[1].strip() for match in sorted(matches, key=lambda x: int(x[0]))]
        
        # Asegurarse de que tenemos el mismo número de traducciones que textos originales
        if len(traducciones) != len(textos):
            print(f"Advertencia: número desigual de traducciones ({len(traducciones)}) y textos originales ({len(textos)})")
            if len(traducciones) < len(textos):
                traducciones.extend(["" for _ in range(len(textos) - len(traducciones))])
            else:
                traducciones = traducciones[:len(textos)]
                
        return traducciones
        
    except Exception as e:
        print(f"Error durante la traducción: {e}")
        # Devolver una lista con el mismo número de elementos que el original
        return ["Error: " + str(e) for _ in textos]

def procesar_pptx(input_file, output_file, idioma_destino="inglés"):
    """Procesa un PPTX extrayendo, traduciendo y reempaquetando"""
    # Asegurarnos de que estamos trabajando con objetos Path
    input_path = Path(input_file) if not isinstance(input_file, Path) else input_file
    output_path = Path(output_file) if not isinstance(output_file, Path) else output_file
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(temp_path)
        
        slides_dir = temp_path / 'ppt' / 'slides'
        if not slides_dir.exists():
            return None
            
        slide_files = sorted(slides_dir.glob('slide*.xml'))
        if not slide_files:
            return None
        
        namespaces = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        for prefix, uri in namespaces.items():
            ET.register_namespace(prefix, uri)
        
        # Extraer textos
        todos_textos = []
        for slide_file in slide_files:
            tree = ET.parse(slide_file)
            root = tree.getroot()
            for t_elem in root.findall('.//a:t', namespaces):
                if t_elem.text and t_elem.text.strip():
                    texto = t_elem.text.strip()
                    if texto not in todos_textos:
                        todos_textos.append(texto)
        
        # Traducir textos
        traducciones = traducir_textos(todos_textos, idioma_destino)
        traduccion_dict = {orig: trad for orig, trad in zip(todos_textos, traducciones)}
        
        # Reemplazar textos
        for slide_file in slide_files:
            tree = ET.parse(slide_file)
            root = tree.getroot()
            for t_elem in root.findall('.//a:t', namespaces):
                if t_elem.text and t_elem.text.strip() in traduccion_dict:
                    t_elem.text = t_elem.text.replace(t_elem.text.strip(), traduccion_dict[t_elem.text.strip()])
            
            with open(slide_file, 'wb') as f:
                f.write(ET.tostring(root, encoding='UTF-8'))
        
        # Reempaquetar PPTX
        temp_output = output_path.with_suffix('.tmp')
        with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(temp_path))
        
        if output_path.exists():
            output_path.unlink()
        shutil.move(temp_output, output_path)
        return output_path

def process_translation_task(input_path, target_lang, job_id):
    """Tarea en segundo plano para realizar la traducción"""
    try:
        output_filename = f"{Path(input_path).stem}_translated_{target_lang}.pptx"
        output_dir = STORAGE_DIR / job_id
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / output_filename
        
        result = procesar_pptx(input_path, output_path, target_lang)
        
        # Guardar resultado
        with open(STORAGE_DIR / f"{job_id}_result.json", "w") as f:
            if result:
                import json
                json.dump({
                    "status": "completed",
                    "file_id": job_id,
                    "filename": output_filename,
                    "download_url": f"/api/translate/files/{job_id}/{output_filename}"
                }, f)
            else:
                json.dump({"status": "error", "message": "Error en la traducción"}, f)
    except Exception as e:
        import json
        with open(STORAGE_DIR / f"{job_id}_result.json", "w") as f:
            json.dump({"status": "error", "message": str(e)}, f)

@router.post("/upload-pptx-for-translation")
async def upload_pptx_for_translation(
    file: UploadFile = File(...),
    source_language: str = Form("es"),
    target_language: str = Form("en")
):
    """Endpoint para subir presentación para traducción"""
    try:
        # Validar que el archivo sea PPTX
        if not file.filename.lower().endswith(".pptx"):
            raise HTTPException(status_code=400, detail="El archivo debe ser una presentación PPTX")
        
        # Guardar archivo
        temp_dir = tempfile.mkdtemp()
        safe_filename = file.filename.replace(" ", "_")
        input_path = os.path.join(temp_dir, safe_filename)
        
        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Registrar metadatos
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        
        # Guardar metadatos para poder recuperar el archivo después
        meta_file = STORAGE_DIR / f"{file_id}_meta.json"
        import json
        with open(meta_file, "w") as f:
            json.dump({
                "file_id": file_id,
                "original_name": original_name,
                "input_path": input_path,
                "source_language": source_language,
                "target_language": target_language,
                "timestamp": str(int(time.time()))
            }, f)
        
        return JSONResponse({
            "file_id": file_id,
            "filename": file.filename,
            "original_name": original_name,
            "status": "uploaded",
            "message": "Archivo subido correctamente, listo para procesar"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-translation")
async def process_translation(background_tasks: BackgroundTasks, request: dict):
    """Inicia proceso de traducción en segundo plano"""
    try:
        file_id = request.get("file_id")
        target_language = request.get("target_language", "en")
        
        if not file_id:
            raise HTTPException(status_code=400, detail="Se requiere file_id")
            
        # Recuperar metadatos del archivo
        meta_file = STORAGE_DIR / f"{file_id}_meta.json"
        if not meta_file.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
            
        import json
        with open(meta_file, "r") as f:
            file_meta = json.load(f)
            
        input_path = file_meta.get("input_path")
        if not input_path or not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail="Archivo original no encontrado")
            
        # Usar el idioma de destino del request o del metadato
        target_language = request.get("target_language") or file_meta.get("target_language", "en")
        
        job_id = str(uuid.uuid4())
        original_name = file_meta.get("original_name")
        
        # Guardar información del trabajo
        job_file = STORAGE_DIR / f"{file_id}_job_{job_id}.json"
        with open(job_file, "w") as f:
            json.dump({
                "job_id": job_id,
                "file_id": file_id,
                "input_path": input_path,
                "original_name": original_name,
                "target_language": target_language,
                "start_time": time.time()
            }, f)
        
        # Iniciar tarea en segundo plano
        background_tasks.add_task(
            process_translation_task,
            input_path,
            target_language,
            job_id
        )
        
        output_filename = f"{original_name}_translated_{target_language}.pptx"
        
        return JSONResponse({
            "job_id": job_id,
            "file_id": file_id,
            "output_filename": output_filename,
            "status": "processing",
            "message": "Procesando traducción en segundo plano",
            "download_url": f"/api/translate/jobs/{job_id}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_translation_status(job_id: str):
    """Obtiene estado de un trabajo de traducción"""
    result_file = STORAGE_DIR / f"{job_id}_result.json"
    
    if result_file.exists():
        import json
        with open(result_file, "r") as f:
            return JSONResponse(json.load(f))
    
    return JSONResponse({"job_id": job_id, "status": "processing", "message": "En proceso"})

@router.get("/files/{file_id}/{filename}")
async def download_translated_file(file_id: str, filename: str):
    """Descarga archivo traducido"""
    file_path = STORAGE_DIR / file_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(path=file_path, filename=filename)
