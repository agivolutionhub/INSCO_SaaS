from pathlib import Path
from typing import Dict, List, Union, Optional, Any
from enum import Enum
import json
import time
import subprocess
import tempfile
import re
import os
import warnings
import logging
from openai import OpenAI

# Configurar logging
logger = logging.getLogger("transcript")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Optimizaciones para rendimiento y prevención de advertencias
os.environ["KMP_WARNINGS"] = "off"
os.environ["OMP_NUM_THREADS"] = "4"
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.conv")
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

class OutputFormat(Enum):
    JSON = "json"
    TXT = "txt"
    MD = "md"
    ALL = "all"

class Stats:
    def __init__(self):
        self.start_time = time.time()
        self.audio_duration = 0
        self.segments = 0
        self.tokens = 0
        self.chars = 0
        self.words = 0
        self.api_cost = 0
        self.model_name = ""
        self.cost_per_minute = 0

    def get_summary(self) -> dict:
        elapsed = time.time() - self.start_time
        minutes_transcribed = self.audio_duration / 60
        return {
            "tiempo_proceso": f"{elapsed:.2f}s",
            "duración_audio": f"{self.audio_duration:.2f}s",
            "minutos_transcritos": f"{minutes_transcribed:.2f}",
            "segmentos": self.segments,
            "tokens": self.tokens,
            "caracteres": self.chars,
            "palabras": self.words,
            "modelo_utilizado": self.model_name,
            "coste_por_minuto": f"{self.cost_per_minute:.4f}€",
            "coste_total": f"{self.api_cost:.4f}€",
            "velocidad_procesamiento": f"{(self.audio_duration/elapsed):.1f}x" if elapsed > 0 else "0x",
            "palabras_por_minuto": f"{(self.words / (self.audio_duration/60)):.1f}" if self.audio_duration else 0
        }

def load_api_config() -> Dict:
    script_dir = Path(__file__).resolve().parent.parent
    config_paths = [
        script_dir / "config" / "sttapi.json",
        Path("config/sttapi.json"),
    ]
    for config_path in config_paths:
        if config_path.exists():
            logger.info(f"Usando archivo de configuración: {config_path}")
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("No se encuentra el archivo de configuración en ninguna ruta probada")

def verify_ffmpeg() -> bool:
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def extract_audio(video_path: Path, temp_dir: Path) -> Optional[Path]:
    try:
        audio_path = temp_dir / f"{video_path.stem}_audio.mp3"
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "0",
            "-ac", "1",
            "-ar", "16000",
            str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error extrayendo audio: {result.stderr}")
            return None
        return audio_path
    except Exception as e:
        logger.error(f"Error extrayendo audio: {str(e)}")
        return None

def find_video_files(directory: Path) -> List[Path]:
    video_extensions = [".mp4", ".avi", ".mkv", ".mov", ".webm"]
    return sorted([f for f in directory.glob("*") if f.suffix.lower() in video_extensions])

def reconstruct_sentences(segments: List[Dict]) -> List[Dict]:
    if not segments:
        return []
    
    end_patterns = [r'[\.\?\!]\s*$', r'[\:\;]\s*$']
    pause_patterns = [r',\s*$', r'-\s*$']
    
    processed_segments = []
    current_seg = {
        'id': 0,
        'start': segments[0]['start'],
        'end': segments[0]['end'],
        'text': segments[0]['text'].strip()
    }
    
    for i in range(1, len(segments)):
        segment = segments[i]
        current_text = current_seg['text']
        next_text = segment['text'].strip()
        
        is_sentence_end = any(re.search(pattern, current_text) for pattern in end_patterns)
        has_pause = any(re.search(pattern, current_text) for pattern in pause_patterns)
        starts_with_capital = bool(re.match(r'^[A-ZÁÉÍÓÚÑ]', next_text))
        long_pause = float(segment['start']) - float(segments[i-1]['end']) > 0.7
        
        if (is_sentence_end or has_pause or long_pause or 
            (starts_with_capital and len(current_text) > 15)):
            processed_segments.append(current_seg)
            current_seg = {
                'id': len(processed_segments),
                'start': segment['start'],
                'end': segment['end'],
                'text': next_text
            }
        else:
            current_seg['end'] = segment['end']
            current_seg['text'] += ' ' + next_text
    
    if current_seg['text']:
        processed_segments.append(current_seg)
    
    logger.info(f"Segmentos reconstruidos: {len(segments)} → {len(processed_segments)}")
    return processed_segments

def format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"

def calculate_api_cost(audio_duration: float, model: str = "gpt-4o-transcribe") -> Dict:
    config = load_api_config()
    models_info = config.get("documentation", {}).get("models", {})
    
    result = {
        "cost": 0,
        "cost_per_minute": 0,
        "model_name": model,
        "minutes": audio_duration / 60
    }
    
    if model in models_info:
        model_info = models_info[model]
        cost_per_minute = model_info.get("pricing", {}).get("transcription", {}).get("cost_per_minute", 0)
        result["cost_per_minute"] = cost_per_minute
        result["model_description"] = model_info.get("description", "")
        result["cost"] = result["minutes"] * cost_per_minute
    
    return result

def estimate_audio_duration(audio_path: Path) -> float:
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Advertencia al estimar duración: {str(e)}")
    return 0.0

def format_text_by_sentences(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'([.!?])\s+(?=[A-ZÁÉÍÓÚÑ])', r'\1\n', text)
    if re.search(r'[.!?]$', text) and not text.endswith('\n'):
        text += '\n'
    return text

def export_results(segments: List[Dict], output_dir: Path, filename: str, formats: List[str]) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_files = {}
    
    if OutputFormat.JSON.value in formats or OutputFormat.ALL.value in formats:
        json_path = output_dir / f"{filename}_transcript.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"segments": segments}, f, ensure_ascii=False, indent=2)
        result_files["json"] = json_path
    
    if OutputFormat.TXT.value in formats or OutputFormat.ALL.value in formats:
        txt_path = output_dir / f"{filename}_transcript.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                start = format_timestamp(float(segment['start']))
                end = format_timestamp(float(segment['end']))
                f.write(f"[{start} --> {end}] {segment['text']}\n")
        result_files["txt"] = txt_path
    
    if OutputFormat.MD.value in formats or OutputFormat.ALL.value in formats:
        md_path = output_dir / f"{filename}_transcript.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Transcripción: {filename}\n\n")
            for segment in segments:
                minutes = int(float(segment['start'])) // 60
                seconds = int(float(segment['start'])) % 60
                timestamp = f"{minutes}:{seconds:02d}"
                f.write(f"[{timestamp}] {segment['text']}\n\n")
        result_files["md"] = md_path
        
    return result_files

def transcribe_with_openai(
    audio_path: Path, 
    model: str = "gpt-4o-transcribe",
    language: str = "es",
    prompt: str = None,
    response_format: str = "text"
) -> Any:
    config = load_api_config()
    api_key = config.get("stt", {}).get("api_key")
    
    if not api_key:
        raise ValueError("API key no encontrada en la configuración")
    
    client = OpenAI(api_key=api_key)
    industry_prompt = "Transcribe como experto en cartón ondulado usando terminología AFCO. Optimiza el texto para síntesis de voz (TTS) con claridad, naturalidad y precisión técnica. Redacta para ser locutado sin edición posterior."
    
    with open(audio_path, "rb") as audio_file:
        params = {
            "model": model,
            "file": audio_file,
            "response_format": response_format
        }
        
        if language:
            params["language"] = language
        
        final_prompt = prompt if prompt else industry_prompt
        params["prompt"] = final_prompt
            
        return client.audio.transcriptions.create(**params)

def transcribe_video(
    video_path: Union[str, Path],
    output_dir: Optional[Path] = None,
    model_name: str = "gpt-4o-transcribe",
    formats: List[str] = ["txt"],
    original_name: Optional[str] = None,
    silent: bool = False
) -> Dict:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"No se encuentra el vídeo: {video_path}")

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        
        if output_dir is None:
            output_dir = Path("data/output/07_transcript")
            output_dir.mkdir(parents=True, exist_ok=True)
        
        output_name = original_name if original_name else video_path.stem
        logger.info(f"Usando nombre de salida: {output_name}")
        
        stats = Stats()
        stats.model_name = model_name
        results = {"filename": video_path.name, "segments": [], "stats": {}}

        if not verify_ffmpeg():
            raise RuntimeError("FFmpeg no está instalado. Instálalo para continuar.")

        logger.info("Extrayendo audio...")
        audio_path = extract_audio(video_path, temp_dir)
        if not audio_path:
            raise RuntimeError("Fallo en extracción de audio")
        
        audio_duration = estimate_audio_duration(audio_path)
        stats.audio_duration = audio_duration
        
        cost_info = calculate_api_cost(audio_duration, model_name)
        estimated_cost = cost_info["cost"]
        stats.cost_per_minute = cost_info["cost_per_minute"]
        
        logger.info(f"Duración estimada: {audio_duration:.2f}s ({audio_duration/60:.2f} min)")
        logger.info(f"Modelo: {model_name}")
        logger.info(f"Coste por minuto: {stats.cost_per_minute:.4f}€")
        logger.info(f"Coste estimado total: {estimated_cost:.4f}€")
        
        logger.info(f"Transcribiendo con {model_name}...")
        response = transcribe_with_openai(
            audio_path=audio_path,
            model=model_name,
            language="es",
            prompt="Eres un redactor técnico especializado en la industria del cartón ondulado, con dominio del vocabulario AFCO. Optimiza el texto para síntesis de voz con claridad, naturalidad y precisión técnica.",
            response_format="text"
        )

        text = str(response)
        formatted_text = format_text_by_sentences(text)
        lines = formatted_text.strip().split('\n')
        segments = []
        
        total_duration = stats.audio_duration
        segment_duration = total_duration / len(lines) if lines else total_duration
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration if i < len(lines) - 1 else total_duration
            
            segments.append({
                'id': i,
                'start': start_time,
                'end': end_time,
                'text': line.strip()
            })
        
        stats.segments = len(segments)
        stats.words = len(text.split())
        stats.chars = len(text)
        
        cost_info = calculate_api_cost(stats.audio_duration, model_name)
        stats.api_cost = cost_info["cost"]
        
        txt_path = output_dir / f"{output_name}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
        
        logger.info(f"Transcripción guardada en: {txt_path}")
        output_files = {"txt": txt_path}
        
        if "json" in formats or "all" in formats:
            json_path = output_dir / f"{output_name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "text": formatted_text,
                    "segments": segments,
                    "stats": stats.get_summary()
                }, f, ensure_ascii=False, indent=2)
            output_files["json"] = json_path
                
        if "md" in formats or "all" in formats:
            md_path = output_dir / f"{output_name}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# Transcripción: {video_path.stem}\n\n")
                for segment in segments:
                    f.write(f"{segment['text']}\n\n")
                f.write("\n\n## Estadísticas de la transcripción\n\n")
                for key, value in stats.get_summary().items():
                    f.write(f"- **{key}**: {value}\n")
            output_files["md"] = md_path
        
        if not silent:
            for key, value in stats.get_summary().items():
                logger.info(f"✓ {key}: {value}")
            
        results["text"] = formatted_text
        results["segments"] = segments
        results["stats"] = stats.get_summary()
        results["files"] = output_files
        return results 