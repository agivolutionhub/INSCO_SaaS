#!/usr/bin/env python3
import argparse, sys, time, os, json, re, zipfile, tempfile, shutil, uuid, logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from openai import OpenAI
import tiktoken
from xml.etree import ElementTree as ET

# CREDENCIALES EMBEBIDAS PARA VERSIÓN DE PRUEBA
OPENAI_API_KEY = "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"
OPENAI_ASSISTANT_ID = "asst_mBShBt93TIVI0PKE7zsNO0eZ"

router = APIRouter(prefix="/api/translate", tags=["translate"])

# Configuración global
CONFIG = {
    "storage_dir": Path(os.environ.get("STORAGE_DIR", "./storage")),
    "cache_dir": Path(os.environ.get("CACHE_DIR", "/app/config/cache")),
    "supported_languages": ["es", "en", "fr", "de", "it", "pt"],
    "retries": 3,
    "wait_times": {"base": 2.0, "max": 30.0, "backoff": 2.0},
    "headers": {"OpenAI-Beta": "assistants=v2"},
    "use_cache": True,
    "batch_size": 10
}

# Rutas posibles para credenciales (en orden de prioridad)
CREDENTIALS_PATHS = [
    # Ruta desde variable de entorno
    os.environ.get("CREDENTIALS_FILE"),
    # Rutas para entorno de producción
    "/app/config/auth_credentials.json",
    "/app/backend/config/auth_credentials.json",
    # Rutas para entorno de desarrollo
    Path(__file__).parent.parent / "config" / "auth_credentials.json",
    Path.cwd() / "backend" / "config" / "auth_credentials.json"
]

# Crear directorios necesarios
CONFIG["storage_dir"].mkdir(exist_ok=True, parents=True)
CONFIG["cache_dir"].mkdir(exist_ok=True, parents=True)
CACHE_FILE = CONFIG["cache_dir"] / "translations.json"

# Configurar logger
logger = logging.getLogger("translate-pptx")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

def load_credentials():
    """Carga configuración y credenciales desde el archivo JSON o usa las embebidas"""
    # Primero intentar cargar desde archivo
    for path in CREDENTIALS_PATHS:
        if not path:
            continue
            
        try:
            path = Path(path) if not isinstance(path, Path) else path
            if path.exists():
                logger.info(f"Cargando credenciales desde: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error accediendo a {path}: {e}")
    
    # Si no se encontró archivo, crear un diccionario con las credenciales embebidas
    logger.info("Usando credenciales embebidas en el código")
    return {
        "openai": {
            "api_key": OPENAI_API_KEY,
            "assistant_id": OPENAI_ASSISTANT_ID
        }
    }

class TranslationCache:
    def __init__(self):
        self.cache, self.modified = {}, False
        self.hits = self.misses = 0
        try:
            if CACHE_FILE.exists():
                self.cache = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
                logger.info(f"Caché cargada: {len(self.cache)} traducciones")
            else:
                logger.info("Creando nueva caché")
        except Exception as e:
            logger.error(f"Error de caché: {e}")
    
    def get(self, text):
        if not text or not text.strip(): return None
        if text in self.cache:
            self.hits += 1
            return self.cache[text]
        self.misses += 1
        return None
    
    def set(self, text, translation):
        if text and text.strip() and translation:
            self.cache[text] = translation
            self.modified = True
    
    def save(self):
        if not self.modified: return
        try:
            CACHE_FILE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding='utf-8')
            logger.info(f"Caché guardada: {len(self.cache)} traducciones")
            self.modified = False
        except Exception as e:
            logger.error(f"Error al guardar caché: {e}")

class Translator:
    """Clase para gestionar traducciones con diferentes métodos"""
    
    def __init__(self, target_language="inglés", use_cache=True):
        """Inicializa el traductor con configuración para OpenAI."""
        self.target_language = target_language
        self.use_cache = use_cache
        
        # Inicializar estadísticas
        self.translations = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
        self.errors = 0
        self.rate_limit_retries = 0
        self.successful_retries = 0
        self.duplicates_avoided = 0
        self.tokens_used = 0
        
        # Cargar credenciales
        self.credentials = load_credentials()
        
        # Inicializar cliente de OpenAI y asistente ID
        try:
            # Validar credenciales esenciales - usar las embebidas como fallback
            api_key = self.credentials.get("openai", {}).get("api_key", OPENAI_API_KEY)
            if not api_key:
                api_key = OPENAI_API_KEY
                logger.warning("API key no encontrada en las credenciales, usando la embebida")
            
            self.assistant_id = self.credentials.get("openai", {}).get("assistant_id", OPENAI_ASSISTANT_ID)
            if not self.assistant_id:
                self.assistant_id = OPENAI_ASSISTANT_ID
                logger.warning("Assistant ID no encontrado en las credenciales, usando el embebido")
                
            logger.info(f"API key encontrada: {api_key[:8]}...{api_key[-4:]}")
            logger.info(f"Asistente ID: {self.assistant_id}")
            
            # Inicializar cliente con solo el API key
            self.client = OpenAI(api_key=api_key)
            
        except Exception as e:
            logger.error(f"Error al inicializar OpenAI: {e}")
            self.client = None
            self.assistant_id = None
        
        # Inicializar caché
        if self.use_cache:
            self._init_cache()
    
    def _init_cache(self):
        self.cache = TranslationCache()
    
    def translate(self, texts: Union[str, List[str]], source_language: str = "español") -> Union[str, List[str]]:
        """
        Traduce textos al idioma objetivo.
        
        Args:
            texts: Texto o lista de textos a traducir
            source_language: Idioma de origen (por defecto 'español')
            
        Returns:
            Texto traducido o lista de textos traducidos
        """
        if not texts:
            return [] if isinstance(texts, list) else ""
            
        # Convertir texto único a lista para procesamiento uniforme
        single_text = not isinstance(texts, list)
        texts_to_translate = [texts] if single_text else texts
        
        # Filtrar textos vacíos
        non_empty_texts = []
        empty_indices = []
        
        for i, text in enumerate(texts_to_translate):
            if text and text.strip():
                non_empty_texts.append(text)
            else:
                empty_indices.append(i)
        
        if not non_empty_texts:
            return "" if single_text else ["" for _ in texts_to_translate]
        
        # Traducir usando el asistente de OpenAI
        translated_texts = self._translate_with_assistant(non_empty_texts, source_language)
        
        # Reinsertamos los textos vacíos en sus posiciones originales
        final_translations = []
        non_empty_idx = 0
        
        for i in range(len(texts_to_translate)):
            if i in empty_indices:
                final_translations.append("")
            else:
                if non_empty_idx < len(translated_texts):
                    final_translations.append(translated_texts[non_empty_idx])
                    non_empty_idx += 1
                else:
                    final_translations.append("")  # Por si acaso hay algún problema
        
        # Devolver el resultado en el mismo formato que se recibió
        return final_translations[0] if single_text else final_translations
    
    def _translate_batch(self, texts):
        """Divide y traduce textos en lotes óptimos"""
        if not texts: 
            return {}
        
        translations = {}
        chunks = [texts[i:i+30] for i in range(0, len(texts), 30)]
        
        for chunk in chunks:
            translations.update(self._translate_with_assistant(chunk))
        
        if self.cache:
            self.cache.save()
        
        return translations
    
    def _translate_with_assistant(self, texts: List[str], source_language: str) -> List[str]:
        """Traduce un lote de textos usando el asistente de OpenAI"""
        if not texts:
            return []
            
        if not self.client or not self.assistant_id:
            raise ValueError("No se han configurado correctamente las credenciales de OpenAI")
            
        # Preparar textos con formato
        batch_texts = "\n\n".join(f"[{i+1}] {text}" for i, text in enumerate(texts))
        content = f"""
Traduce los siguientes textos de {source_language} a {self.target_language}. 
Devuelve SOLO los textos traducidos, conservando el formato original de enumeración [1], [2], etc.

{batch_texts}
"""
        max_retries = CONFIG["retries"]
        attempt = 0
        wait_time = CONFIG["wait_times"]["base"]
        
        while attempt <= max_retries:
            try:
                # Actualizar estadísticas
                self.api_calls += 1
                logger.info(f"Iniciando traducción de {len(texts)} textos")
                
                # 1. Crear un thread (nueva conversación)
                thread = self.client.beta.threads.create()
                logger.info(f"Thread creado: {thread.id}")
                
                # 2. Añadir mensaje al thread
                message = self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=content
                )
                
                # 3. Ejecutar el asistente en el thread
                run = self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id
                )
                logger.info(f"Run iniciado: {run.id}")
                
                # 4. Esperar a que se complete la ejecución
                while run.status != "completed":
                    time.sleep(1)
                    run = self.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                    
                    if run.status in ["failed", "cancelled", "expired"]:
                        raise Exception(f"Error en la ejecución del asistente: {run.status}")
                
                # 5. Obtener la respuesta del asistente
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                
                # El primer mensaje del asistente contiene la traducción
                assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
                if not assistant_messages:
                    raise Exception("No se recibió respuesta del asistente")
                
                # Extraer el texto de la respuesta
                try:
                    translation_text = assistant_messages[0].content[0].text.value
                except (IndexError, AttributeError, KeyError) as e:
                    logger.error(f"Error al extraer respuesta: {e}")
                    logger.error(f"Contenido del mensaje: {assistant_messages[0].content}")
                    raise Exception(f"Error al extraer respuesta: {e}")
                
                # Procesar las traducciones
                translations = []
                
                # Buscar todos los bloques numerados [1], [2], etc. en la respuesta
                pattern = r"\[(\d+)\](.*?)(?=\[\d+\]|$)"
                matches = re.findall(pattern, translation_text, re.DOTALL)
                
                # Si no hay coincidencias o faltan algunas, intentar extraer línea por línea
                if not matches or len(matches) < len(texts):
                    lines = translation_text.strip().split("\n")
                    translations = [line.strip() for line in lines if line.strip()]
                else:
                    # Ordenar las coincidencias por número y extraer solo el texto
                    sorted_matches = sorted(matches, key=lambda x: int(x[0]))
                    translations = [match[1].strip() for match in sorted_matches]
                
                # Verificar que tenemos el mismo número de traducciones que de textos originales
                if len(translations) != len(texts):
                    logger.warning(f"Desajuste entre originales ({len(texts)}) y traducciones ({len(translations)})")
                    if len(translations) < len(texts):
                        translations.extend(["" for _ in range(len(texts) - len(translations))])
                    else:
                        translations = translations[:len(texts)]
                
                logger.info(f"Traducción completada exitosamente para {len(translations)} textos")
                return translations
                
            except Exception as e:
                attempt += 1
                error_msg = str(e).lower()
                
                # Manejar específicamente los rate limits
                if "rate limit" in error_msg or "rate_limit" in error_msg:
                    self.rate_limit_retries += 1
                    logger.warning(f"Rate limit alcanzado, intento {attempt}/{max_retries}, esperando {wait_time}s")
                    time.sleep(wait_time)
                    wait_time = min(wait_time * CONFIG["wait_times"]["backoff"], CONFIG["wait_times"]["max"])
                    if attempt <= max_retries:
                        self.successful_retries += 1
                        continue
                
                # Para otros errores, también reintentamos pero con menos espera
                logger.error(f"Error en la traducción (intento {attempt}/{max_retries}): {e}")
                if attempt <= max_retries:
                    time.sleep(CONFIG["wait_times"]["base"])
                    self.successful_retries += 1
                    continue
                else:
                    self.errors += 1
                    raise Exception(f"Error en la traducción después de {max_retries} intentos: {e}")
        
        # No debería llegar aquí, pero por si acaso
        raise Exception(f"Error inesperado en la traducción después de {max_retries} intentos")
    
    def _estimate_tokens(self, text):
        """Estima tokens en un texto para el modelo cl100k_base"""
        if not text: return 0
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            return len(text) // 4

class PPTXEditor:
    def __init__(self, translator):
        self.translator = translator
        self.slides_processed = self.total_texts = 0
        self.namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
        }
        
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)
    
    def process_pptx(self, input_path, output_path):
        """Procesa un archivo PPTX para traducir su contenido textual"""
        input_path, output_path = Path(input_path), Path(output_path)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        try:
            logger.info(f"Procesando: {input_path.name}")
            temp_output = output_path.with_suffix('.tmp')
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                self._extract_and_translate_pptx(input_path, temp_dir, temp_output, output_path)
            
            if hasattr(self.translator, 'cache') and self.translator.cache:
                self.translator.cache.save()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error al procesar presentación: {str(e)}")
            return None
    
    def _extract_and_translate_pptx(self, input_path, temp_dir, temp_output, output_path):
        """Extrae, traduce y recomprime el PPTX"""
        # Extraer PPTX
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Procesar diapositivas
        slides_dir = temp_dir / 'ppt' / 'slides'
        if not slides_dir.exists():
            raise Exception(f"Estructura PPTX inválida: no existe {slides_dir}")
        
        slide_files = sorted(slides_dir.glob('slide*.xml'), 
            key=lambda f: int(re.search(r'slide(\d+)\.xml', f.name).group(1))
        )
        
        if not slide_files:
            raise Exception(f"No hay diapositivas en {slides_dir}")
        
        # Extraer textos
        all_texts, slide_data = self._extract_texts(slide_files)
        
        # Traducir textos únicos
        logger.info(f"Traduciendo {len(all_texts)} textos únicos...")
        translations = self.translator.translate(all_texts)
        
        # Actualizar diapositivas
        self._update_slides(slide_files, slide_data, translations)
        
        # Reempaquetar
        self._repack_pptx(temp_dir, temp_output, output_path)
    
    def _extract_texts(self, slide_files):
        """Extrae todos los textos de las diapositivas"""
        all_texts = []
        slide_data = {}
        
        for i, slide_file in enumerate(slide_files, 1):
            logger.info(f"Analizando diapositiva {i}/{len(slide_files)}...")
            
            parser = ET.XMLParser(encoding="utf-8")
            tree = ET.parse(slide_file, parser=parser)
            root = tree.getroot()
            
            texts = []
            for paragraph in root.findall('.//a:p', self.namespaces):
                paragraph_runs = []
                full_text = ""
                
                for run in paragraph.findall('.//a:t', self.namespaces):
                    if run.text and run.text.strip():
                        text = run.text.strip()
                        has_space = run.text.endswith(" ")
                        
                        paragraph_runs.append({
                            "element": run,
                            "text": text,
                            "length": len(text),
                            "has_space": has_space
                        })
                        
                        full_text += text + (" " if has_space else "")
                
                full_text = full_text.strip()
                if full_text:
                    texts.append({
                        "full_text": full_text,
                        "runs": paragraph_runs,
                        "total_length": sum(r["length"] for r in paragraph_runs)
                    })
                    if full_text not in all_texts:
                        all_texts.append(full_text)
            
            slide_data[slide_file] = {
                "tree": tree,
                "root": root,
                "texts": texts
            }
            self.slides_processed += 1
        
        return all_texts, slide_data
    
    def _update_slides(self, slide_files, slide_data, translations):
        """Actualiza diapositivas con texto traducido"""
        for i, slide_file in enumerate(slide_files, 1):
            if slide_file not in slide_data:
                continue
            
            info = slide_data[slide_file]
            texts_translated = 0
            
            for paragraph in info["texts"]:
                original = paragraph["full_text"]
                translated = translations.get(original)
                
                if not translated or translated == original:
                    continue
                
                if len(paragraph["runs"]) == 1:
                    paragraph["runs"][0]["element"].text = translated
                    texts_translated += 1
                else:
                    self._distribute_translation(paragraph, translated)
                    texts_translated += 1
            
            self.total_texts += texts_translated
            
            # Guardar XML actualizado
            xml_string = ET.tostring(info["root"], encoding='UTF-8', method='xml')
            if not xml_string.startswith(b'<?xml'):
                xml_string = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_string
            
            with open(slide_file, 'wb') as f:
                f.write(xml_string)
    
    def _distribute_translation(self, paragraph, translated):
        """Distribuye el texto traducido entre múltiples runs"""
        words = translated.split()
        runs = paragraph["runs"]
        total_length = paragraph["total_length"]
        assigned_words = 0
        
        for i, run in enumerate(runs):
            elem = run["element"]
            proportion = run["length"] / total_length if total_length > 0 else 0
            words_for_run = max(1, round(proportion * len(words)))
            words_for_run = min(words_for_run, len(words) - assigned_words)
            
            if words_for_run <= 0:
                continue
            
            segment = words[assigned_words:assigned_words + words_for_run]
            partial_text = " ".join(segment)
            
            if i == len(runs) - 1 and assigned_words + words_for_run < len(words):
                remaining = words[assigned_words + words_for_run:]
                partial_text += " " + " ".join(remaining)
            
            if run.get("has_space", False) or i < len(runs) - 1:
                partial_text += " "
            
            elem.text = partial_text
            assigned_words += words_for_run
    
    def _repack_pptx(self, temp_dir, temp_output, output_path):
        """Reempaqueta el PPTX con los cambios"""
        with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
        
        if output_path.exists():
            output_path.unlink()
        shutil.move(temp_output, output_path)
        logger.info(f"Archivo generado: {output_path}")

# Funciones de utilidad
def save_to_storage(file_path):
    """Guarda un archivo en almacenamiento permanente y devuelve su ID"""
    file_id = str(uuid.uuid4())
    dest_dir = CONFIG["storage_dir"] / file_id
    dest_dir.mkdir(exist_ok=True)
    
    dest_path = dest_dir / Path(file_path).name
    shutil.copy2(file_path, dest_path)
    
    return file_id

def process_translation_task(input_path, output_dir, source_lang, target_lang, job_id):
    """Tarea en segundo plano para realizar la traducción"""
    process_file = None
    result_file = CONFIG["storage_dir"] / f"{job_id}_result.json"
    
    try:
        logger.info(f"Iniciando traducción: {input_path}, de {source_lang} a {target_lang}")
        
        # Identificar file_id
        file_id = None
        process_matches = list(CONFIG["storage_dir"].glob(f"*_processing_{job_id}.json"))
        if process_matches:
            process_file = process_matches[0]
            file_id = process_file.name.split("_processing_")[0]
        
        output_path = Path(output_dir) / f"{Path(input_path).stem}_translated_{target_lang}.pptx"
        
        # Iniciar proceso de traducción
        translator = Translator()
        
        # Verificar que el traductor se inicializó correctamente
        if not translator.assistant_id:
            raise Exception("No se pudo inicializar el traductor: ID de asistente no disponible")
            
        editor = PPTXEditor(translator)
        
        start_time = time.time()
        result_path = editor.process_pptx(input_path, output_path)
        
        if not result_path or not Path(result_path).exists():
            raise Exception("No se generó el archivo de salida")
        
        # Recopilar estadísticas
        stats = {
            "slides_processed": editor.slides_processed,
            "texts_translated": editor.total_texts,
            "total_time": time.time() - start_time,
            "api_calls": translator.api_calls,
            "rate_limit_retries": translator.rate_limit_retries,
            "successful_retries": translator.successful_retries,
            "errors": translator.errors,
            "duplicates_avoided": translator.duplicates_avoided,
            "cache_hits": translator.cache_hits,
            "cache_misses": translator.cache_misses,
            "input_tokens": translator.total_input_tokens,
            "output_tokens": translator.total_output_tokens,
            "cached_tokens": translator.cached_tokens
        }
        
        # Almacenar resultado
        file_id_result = file_id or str(uuid.uuid4())
        result_file_id = save_to_storage(str(result_path))
        filename = Path(result_path).name
        
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
            
    except Exception as e:
        logger.error(f"Error procesando traducción: {str(e)}")
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({
                "status": "error", 
                "message": str(e),
                "completion_time": time.time()
            }, f, ensure_ascii=False)
    finally:
        # Limpieza de archivos temporales
        if process_file and process_file.exists():
            try:
                process_file.unlink()
            except:
                pass
        
        if os.path.exists(input_path):
            try:
                os.unlink(input_path)
            except:
                pass
            
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
            except:
                pass

# API Endpoints
@router.post("/upload-pptx-for-translation")
async def upload_pptx_for_translation(
    file: UploadFile = File(...),
    source_language: str = Form("es"),
    target_language: str = Form("en")
):
    """Endpoint para subir presentación para traducción"""
    try:
        logger.info(f"Solicitud para traducir: {file.filename}, de {source_language} a {target_language}")
        
        # Validaciones
        if source_language not in CONFIG["supported_languages"] or target_language not in CONFIG["supported_languages"]:
            raise HTTPException(status_code=400, detail="Idioma no soportado")
        
        if source_language == target_language:
            raise HTTPException(status_code=400, detail="Los idiomas deben ser diferentes")
        
        if not file.filename or not file.filename.lower().endswith(".pptx"):
            raise HTTPException(status_code=400, detail="El archivo debe ser PPTX")
        
        # Verificar que podemos acceder al asistente
        credentials = load_credentials()
        assistant_id = credentials.get("openai", {}).get("assistant_id")
        if not assistant_id:
            raise HTTPException(status_code=500, detail="Configuración de traducción no disponible: ID de asistente no encontrado")
        
        # Guardar archivo
        temp_dir = tempfile.mkdtemp()
        safe_filename = file.filename.replace(" ", "_").replace("(", "").replace(")", "")
        input_path = os.path.join(temp_dir, safe_filename)
        
        with open(input_path, "wb") as buffer:
            chunk_size = 1024 * 1024
            total_size = 0
            
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                buffer.write(chunk)
                total_size += len(chunk)
        
        # Registrar metadatos
        file_id = str(uuid.uuid4())
        original_name = Path(file.filename).stem
        
        file_meta = CONFIG["storage_dir"] / f"{file_id}_meta.json"
        with open(file_meta, "w", encoding="utf-8") as f:
            json.dump({
                "file_id": file_id,
                "original_name": original_name,
                "input_path": input_path,
                "source_language": source_language,
                "target_language": target_language,
                "timestamp": str(int(time.time()))
            }, f, ensure_ascii=False)
        
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
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

@router.post("/process-translation")
async def process_translation(
    background_tasks: BackgroundTasks,
    request: dict
):
    """Inicia proceso de traducción en segundo plano"""
    try:
        file_id = request.get("file_id")
        original_name = request.get("original_name")
        source_language = request.get("source_language", "es")
        target_language = request.get("target_language", "en")
        
        if not file_id:
            raise HTTPException(status_code=400, detail="Se requiere file_id")
        
        # Verificar si ya está en proceso
        result_check = list(CONFIG["storage_dir"].glob(f"{file_id}_processing_*.json"))
        if result_check:
            with open(result_check[0], "r", encoding="utf-8") as f:
                existing_job = json.load(f)
                
            return JSONResponse({
                "job_id": existing_job.get("job_id"),
                "file_id": file_id,
                "output_filename": existing_job.get("output_filename", f"{original_name}_translated_{target_language}.pptx"),
                "status": "processing",
                "message": "Ya existe un proceso de traducción en curso",
                "download_url": f"/api/translate/jobs/{existing_job.get('job_id')}"
            })
        
        # Cargar metadatos
        file_meta_path = CONFIG["storage_dir"] / f"{file_id}_meta.json"
        if not file_meta_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        with open(file_meta_path, "r", encoding="utf-8") as f:
            file_meta = json.load(f)
        
        input_path = file_meta.get("input_path")
        if not input_path or not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail="Archivo original no encontrado")
        
        file_size = os.path.getsize(input_path)
        if file_size == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío")
        
        # Verificar que podemos acceder al asistente
        credentials = load_credentials()
        assistant_id = credentials.get("openai", {}).get("assistant_id")
        if not assistant_id:
            raise HTTPException(status_code=500, detail="Configuración de traducción no disponible: ID de asistente no encontrado")
        
        # Preparar tarea
        output_dir = tempfile.mkdtemp()
        output_filename = f"{original_name or file_meta.get('original_name')}_translated_{target_language}.pptx"
        
        job_id = str(uuid.uuid4())
        
        # Registrar trabajo
        processing_file = CONFIG["storage_dir"] / f"{file_id}_processing_{job_id}.json"
        with open(processing_file, "w", encoding="utf-8") as f:
            json.dump({
                "job_id": job_id,
                "file_id": file_id,
                "input_path": input_path,
                "output_dir": output_dir,
                "output_filename": output_filename,
                "source_language": source_language,
                "target_language": target_language,
                "start_time": time.time(),
                "assistant_id": assistant_id
            }, f, ensure_ascii=False)
        
        # Iniciar tarea en segundo plano
        background_tasks.add_task(
            process_translation_task,
            input_path,
            output_dir,
            source_language,
            target_language,
            job_id
        )
        
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
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar traducción: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_translation_status(job_id: str):
    """Obtiene estado de un trabajo de traducción"""
    result_file = CONFIG["storage_dir"] / f"{job_id}_result.json"
    
    # Comprobar si completado
    if result_file.exists():
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            
            if "job_id" not in result:
                result["job_id"] = job_id
                
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse({
                "job_id": job_id,
                "status": "error",
                "message": f"Error al recuperar estado: {str(e)}"
            })
    
    # Comprobar si en proceso
    processing_files = list(CONFIG["storage_dir"].glob(f"*_processing_{job_id}.json"))
    if processing_files:
        try:
            with open(processing_files[0], "r", encoding="utf-8") as f:
                process_info = json.load(f)
            
            start_time = process_info.get("start_time", 0)
            elapsed = time.time() - float(start_time) if start_time else 0
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
    """Descarga archivo traducido"""
    file_path = CONFIG["storage_dir"] / file_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

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
            
            file_path = CONFIG["storage_dir"] / file_id / filename
            
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
        
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, filename in files_to_zip:
                zipf.write(file_path, filename)
                logger.info(f"Añadido {filename} al ZIP")
        
        # Verificar ZIP
        if not zip_file_path.exists() or os.path.getsize(zip_file_path) == 0:
            raise Exception("Error al crear ZIP")
        
        # Programar limpieza de archivos temporales
        background_tasks = BackgroundTasks()
        
        async def cleanup_temp():
            try:
                if zip_file_path.exists():
                    os.unlink(zip_file_path)
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Error en limpieza: {e}")
        
        background_tasks.add_task(cleanup_temp)
        
        # Devolver ZIP
        response = FileResponse(
            path=zip_file_path,
            filename="traducciones.zip",
            media_type="application/zip",
            background=background_tasks
        )
        
        return response
                
    except HTTPException:
        raise            
    except Exception as e:
        logger.error(f"Error ZIP: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {e}")

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
        files_to_zip = []
        for file_info in files:
            file_id = file_info.get("file_id")
            filename = file_info.get("filename")
            
            if not file_id or not filename:
                continue
            
            file_path = CONFIG["storage_dir"] / file_id / filename
            
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
        
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, filename in files_to_zip:
                zipf.write(file_path, filename)
                logger.info(f"Añadido {filename} al ZIP")
        
        # Programar limpieza de archivos temporales
        background_tasks = BackgroundTasks()
        
        async def cleanup_temp():
            try:
                if zip_file_path.exists():
                    os.unlink(zip_file_path)
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Error en limpieza: {e}")
        
        background_tasks.add_task(cleanup_temp)
        
        # Devolver ZIP
        response = FileResponse(
            path=zip_file_path,
            filename="traducciones.zip",
            media_type="application/zip",
            background=background_tasks
        )
        
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ZIP: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {e}")

# Interfaz CLI
def parse_args():
    parser = argparse.ArgumentParser(description="Traductor de presentaciones PPTX")
    parser.add_argument("input_file", type=str, help="Archivo PPTX de entrada")
    parser.add_argument("-o", "--output", type=str, help="Ruta del archivo de salida")
    parser.add_argument("-l", "--language", type=str, default="en", 
                      choices=CONFIG["supported_languages"],
                      help="Idioma destino (por defecto: en)")
    parser.add_argument("--no-cache", action="store_true", help="Desactivar caché de traducciones")
    
    return parser.parse_args()

def main():
    """Función principal para ejecución como script"""
    try:
        args = parse_args()
        
        input_path = Path(args.input_file)
        if not input_path.exists():
            logger.error(f"Error: No se encuentra el archivo {input_path}")
            return 1
        
        if not input_path.is_file() or input_path.suffix.lower() != '.pptx':
            logger.error(f"Error: El archivo debe ser PPTX: {input_path}")
            return 1
        
        # Verificar que tenemos acceso al asistente
        credentials = load_credentials()
        assistant_id = credentials.get("openai", {}).get("assistant_id")
        if not assistant_id:
            logger.error("Error: No se encontró el ID de asistente en las credenciales")
            return 1
            
        logger.info(f"Usando Asistente ID: {assistant_id}")
        
        output_path = args.output
        if not output_path:
            output_path = input_path.with_name(f"{input_path.stem}_translated_{args.language}{input_path.suffix}")
        else:
            output_path = Path(output_path)
        
        logger.info(f"Iniciando traducción de {input_path.name} a {args.language}")
        
        translator = Translator()
        
        # Verificar que el traductor se inicializó correctamente
        if not translator.assistant_id:
            logger.error("Error: No se pudo inicializar el traductor (ID de asistente no disponible)")
            return 1
            
        editor = PPTXEditor(translator)
        
        start_time = time.time()
        result_path = editor.process_pptx(input_path, output_path)
        elapsed = time.time() - start_time
        
        if not result_path or not os.path.exists(result_path):
            logger.error("Error: No se generó el archivo de salida")
            return 1
            
        logger.info(f"\n✅ Traducción completada en {elapsed:.2f} segundos")
        logger.info(f"Archivo generado: {result_path}")
        logger.info(f"\nEstadísticas:")
        logger.info(f"- Diapositivas procesadas: {editor.slides_processed}")
        logger.info(f"- Textos traducidos: {editor.total_texts}")
        
        if hasattr(translator, 'cache') and translator.cache:
            cache_hits = translator.cache_hits
            cache_misses = translator.cache_misses
            total = cache_hits + cache_misses
            hit_rate = cache_hits / total * 100 if total > 0 else 0
            logger.info(f"- Caché: {cache_hits} hits, {cache_misses} misses ({hit_rate:.1f}% aciertos)")
        
        return 0
            
    except Exception as e:
        logger.error(f"\n❌ Error durante la traducción: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
