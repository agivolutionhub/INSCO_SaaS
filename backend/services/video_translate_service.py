import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
import openai

# Importar OpenAI
from dotenv import load_dotenv
from datetime import datetime

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("video_translate_service")
console = Console()

# Cargar variables de entorno desde diferentes ubicaciones
env_file_paths = [
    Path(__file__).resolve().parent.parent / "config" / ".env",
    Path("/app/config/.env"),
]

for env_path in env_file_paths:
    if env_path.exists():
        console.print(f"[video_translate_service] Cargando variables desde: {env_path}")
        with open(env_path, "r") as env_file:
            for line in env_file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value

# Cargar credenciales
def load_openai_credentials():
    credentials_paths = [
        Path(__file__).resolve().parent.parent / "config" / "auth_credentials.json",
        Path("/app/config/auth_credentials.json"),
    ]
    
    for path in credentials_paths:
        if path.exists():
            logger.info(f"Cargando credenciales desde: {path}")
            try:
                with open(path, "r") as f:
                    credentials = json.load(f)
                
                if "openai" in credentials:
                    if "api_key" in credentials["openai"]:
                        os.environ["OPENAI_API_KEY"] = credentials["openai"]["api_key"]
                    if "assistant_id" in credentials["openai"]:
                        os.environ["OPENAI_ASSISTANT_ID"] = credentials["openai"]["assistant_id"]
                
                logger.info("Credenciales de OpenAI cargadas correctamente")
                return True
            except Exception as e:
                logger.error(f"Error al cargar credenciales desde {path}: {e}")
    
    logger.warning("No se encontró archivo de credenciales en ninguna ubicación conocida")
    return False

# Intentar inicializar cliente de OpenAI
openai_client = None

try:
    load_openai_credentials()
    # Eliminar el parámetro 'proxies' que está causando el error
    openai_client = openai.OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )
except Exception as e:
    logger.error(f"❌ Error de conexión a OpenAI: {e}")
    openai_client = None

# Configuración de OpenAI
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "asst_mBShBt93TIVI0PKE7zsNO0eZ")
OPENAI_BETA_HEADER = {"OpenAI-Beta": "assistants=v2"}

# Verificar configuración de OpenAI
def test_openai_connection():
    """Verifica la conexión con OpenAI y la configuración del asistente."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ API key de OpenAI no encontrada")
            return False
            
        # Inicializar cliente sin el parámetro proxies
        client = openai.OpenAI(api_key=api_key)
        
        # Probar una llamada simple
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Responde con 'OK' si puedes leer este mensaje."},
                {"role": "user", "content": "¿Funcionas correctamente?"}
            ],
            max_tokens=5
        )
        
        if response and response.choices:
            logger.info(f"✓ Conexión a OpenAI verificada: '{response.choices[0].message.content}'")
            return True
        logger.warning("⚠️ Respuesta vacía de OpenAI")
    except Exception as e:
        logger.error(f"❌ Error de conexión a OpenAI: {str(e)}")
    return False

# Intentar verificar la conexión al cargar el módulo
try:
    test_openai_connection()
except Exception as e:
    logger.warning(f"No se pudo verificar la conexión inicialmente: {str(e)}")

def translate_text(
    text: str,
    target_language: str = "English",
    original_language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Traduce un texto usando la API de OpenAI Assistant.
    Nota: El asistente parece estar optimizado principalmente para traducir al inglés.
    
    Args:
        text: Texto a traducir
        target_language: Idioma al que traducir (por defecto inglés)
        original_language: Idioma original del texto (opcional, se autodetecta)
        
    Returns:
        Dict con la traducción y metadatos
    """
    try:
        if not text:
            raise ValueError("El texto a traducir está vacío")
        
        logger.info(f"Iniciando traducción al {target_language}")
        
        # Iniciar cronómetro
        start_time = time.time()
        
        # Configurar el prompt según el idioma
        if not original_language:
            system_prompt = f"Eres un traductor profesional. Traduce el siguiente texto al {target_language}."
        else:
            system_prompt = f"Eres un traductor profesional. Traduce el siguiente texto de {original_language} a {target_language}."
        
        user_prompt = text
        
        # Crear un thread
        thread = openai_client.beta.threads.create()
        logger.info(f"Thread creado: {thread.id}")
        
        # Añadir mensaje al thread
        openai_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"{system_prompt}\n\n{user_prompt}"
        )
        
        # Ejecutar el asistente
        run = openai_client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        logger.info(f"Ejecución iniciada: {run.id}")
        
        # Esperar a que termine la ejecución
        while run.status in ["queued", "in_progress"]:
            logger.info(f"Estado: {run.status}")
            time.sleep(1)
            run = openai_client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        # Verificar si se completó correctamente
        if run.status != "completed":
            error_msg = f"Error en la traducción. Estado final: {run.status}"
            if hasattr(run, "last_error"):
                error_msg += f" - Detalle: {run.last_error}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Obtener mensajes
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread.id
        )
        
        # Encontrar la respuesta del asistente
        translation = ""
        for msg in messages.data:
            if msg.role == "assistant":
                for content in msg.content:
                    if content.type == "text":
                        translation += content.text.value
        
        if not translation:
            raise RuntimeError("No se recibió traducción del asistente")
        
        # Calcular duración
        duration = time.time() - start_time
        logger.info(f"Traducción completada en {duration:.2f} segundos")
        
        # Guardar la última respuesta
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"translation_log_{timestamp}.json"
        log_path = Path(__file__).resolve().parent.parent / "storage/translations" / log_filename
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "original_text": text,
                "translated_text": translation,
                "target_language": target_language,
                "original_language": original_language,
                "timestamp": timestamp
            }, f, ensure_ascii=False, indent=2)
        
        # Devolver resultado
        return {
            "original_text": text,
            "translated_text": translation,
            "target_language": target_language,
            "original_language": original_language,
            "processing_time": duration
        }
    
    except Exception as e:
        logger.error(f"Error en la traducción: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "original_text": text,
            "target_language": target_language
        }

def translate_file(
    file_path: str,
    target_language: str = "English",
    output_path: Optional[str] = None,
    original_language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Traduce un archivo de texto usando la API de OpenAI Assistant.
    
    Args:
        file_path: Ruta al archivo a traducir
        target_language: Idioma al que traducir (por defecto inglés)
        output_path: Ruta para guardar la traducción (opcional)
        original_language: Idioma original del texto (opcional)
        
    Returns:
        Dict con información sobre la traducción
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        # Leer el archivo
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Traducir el texto
        result = translate_text(text, target_language, original_language)
        
        # Si hay error, propagarlo
        if "status" in result and result["status"] == "error":
            return result
        
        # Si no se especifica ruta de salida, generar una
        if not output_path:
            stem = file_path.stem
            output_path = file_path.parent / f"{stem}_{target_language.lower()}.txt"
        else:
            output_path = Path(output_path)
        
        # Guardar la traducción
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result["translated_text"])
        
        # Añadir información sobre el archivo
        result["input_file"] = str(file_path)
        result["output_file"] = str(output_path)
        result["status"] = "success"
        
        return result
    
    except Exception as e:
        logger.error(f"Error al traducir archivo: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "input_file": file_path if isinstance(file_path, str) else str(file_path)
        }

def summarize_transcript(transcript, max_words=150):
    """
    Genera un resumen del texto de la transcripción usando OpenAI.
    
    Args:
        transcript: Texto completo de la transcripción
        max_words: Número máximo de palabras para el resumen
        
    Returns:
        Resumen del texto
    """
    try:
        # Crear el prompt para el resumen
        system_prompt = f"Eres un asistente especializado en crear resúmenes concisos. Resume el siguiente texto en un máximo de {max_words} palabras, manteniendo las ideas principales y el contexto esencial."
        user_prompt = transcript
        
        # Medir tiempo de respuesta
        start_time = time.time()
        
        # Solicitar resumen
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        # Obtener resumen
        summary = response.choices[0].message.content
        duration = time.time() - start_time
        
        logger.info(f"Resumen completado en {duration:.2f} segundos")
        
        return {
            "summary": summary,
            "original_text": transcript,
            "duration_seconds": duration
        }
        
    except Exception as e:
        logger.error(f"❌ Error al generar resumen: {str(e)}")
        return {"error": f"Error al generar resumen: {str(e)}"} 