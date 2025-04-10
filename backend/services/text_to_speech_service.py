from pathlib import Path
import json, re, subprocess, os, time, shutil
import logging
from typing import Dict, List, Any, Tuple, Optional, Union
from openai import OpenAI

# Configurar logging
logger = logging.getLogger("tts-service")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Configuración por defecto
DEFAULT_CONFIG = {
    "audio": {
        "sample_rate": 44100, 
        "channels": 2, 
        "bitrate": "128k", 
        "target_lufs": -23
    },
    "tts": {
        "model": "gpt-4o-mini-tts", 
        "voice": "echo",
        "speed": 1.0,
        "instructions": "Eres un locutor técnico experto en la industria del cartón ondulado. Lee el texto de manera didáctica, clara y profesional. Enfatiza ligeramente términos técnicos como 'ECT', 'fluting', 'liner' y 'onduladora'."
    },
    "pausa": {
        "duracion_ms": 1300
    },
    "compressor": {
        "threshold": "-32dB",
        "ratio": "8",
        "attack": "20",
        "release": "250",
        "makeup": "8"
    }
}

def load_api_config() -> Dict[str, Any]:
    script_dir = Path(__file__).resolve().parent.parent
    config_file = script_dir / "config" / "ttsapi.json"
    
    if not config_file.exists():
        raise FileNotFoundError(f"No se encuentra archivo de configuración: {config_file}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)

def check_ffmpeg() -> bool:
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def create_silence(duration: float, output_file: Path, config: Dict) -> None:
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi',
        '-i', f'anullsrc=r={config["audio"]["sample_rate"]}:cl=stereo',
        '-t', str(duration), '-ar', str(config["audio"]["sample_rate"]),
        '-ac', str(config["audio"]["channels"]), '-ab', config["audio"]["bitrate"],
        '-acodec', 'libmp3lame', str(output_file)
    ], check=True, capture_output=True)

def get_audio_duration(file_path: Path) -> float:
    result = subprocess.run([
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
        '-of', 'json', str(file_path)
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.warning(f"No se pudo obtener la duración de {file_path}")
        return 0
    
    try:
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except (json.JSONDecodeError, KeyError):
        logger.warning(f"Error al parsear la duración de {file_path}")
        return 0

def analyze_audio_levels(file_path: Path) -> Dict[str, Any]:
    try:
        result = subprocess.run([
            'ffmpeg', '-i', str(file_path),
            '-af', f'loudnorm=I={DEFAULT_CONFIG["audio"]["target_lufs"]}:LRA=7:TP=-2.0:print_format=json',
            '-f', 'null', '-'
        ], capture_output=True, text=True)
        
        stderr = result.stderr
        json_start = stderr.find('{')
        json_end = stderr.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = stderr[json_start:json_end]
            measured_data = json.loads(json_str)
            
            return {
                'input_i': measured_data["input_i"],
                'input_tp': measured_data["input_tp"],
                'input_lra': measured_data["input_lra"],
                'input_thresh': measured_data["input_thresh"],
                'target_offset': measured_data["target_offset"]
            }
    
    except Exception as e:
        logger.error(f"Error al analizar niveles de audio: {e}")
    
    return {
        'input_i': "Error",
        'input_tp': "Error",
        'input_lra': "Error",
        'input_thresh': "Error",
        'target_offset': "Error"
    }

def normalize_audio(input_file: Path, output_file: Path, target_lufs: float = -23) -> Dict[str, Any]:
    try:
        measured_data = analyze_audio_levels(input_file)
        
        if "Error" in measured_data["input_i"]:
            raise ValueError("Error en medición de niveles de audio")
        
        subprocess.run([
            'ffmpeg', '-y', '-i', str(input_file),
            '-af', f'loudnorm=print_format=summary:linear=true:I={target_lufs}:LRA=7:TP=-2.0:'
                 f'measured_I={measured_data["input_i"]}:measured_LRA={measured_data["input_lra"]}:'
                 f'measured_TP={measured_data["input_tp"]}:measured_thresh={measured_data["input_thresh"]}:'
                 f'offset={measured_data["target_offset"]}',
            '-ar', '48k', '-c:a', 'libmp3lame', '-q:a', '0', str(output_file)
        ], check=True, capture_output=True)
        
        return {
            'input_lufs': measured_data["input_i"],
            'target_lufs': target_lufs,
            'true_peak': measured_data["input_tp"],
            'lra': measured_data["input_lra"]
        }
        
    except Exception as e:
        logger.error(f"Error al normalizar: {str(e)}")
        shutil.copy(str(input_file), str(output_file))
        return {'input_lufs': "Error", 'target_lufs': target_lufs, 'true_peak': "Error", 'lra': "Error"}

def compress_audio(input_file: Path, output_file: Path, config: Dict) -> bool:
    comp = config["compressor"]
    # Añadir fade-out de 30ms al final del audio para evitar clics en la transición
    fade_duration = 0.03  # 30 milisegundos
    
    compressor_filter = (
        f"acompressor=threshold={comp['threshold']}:ratio={comp['ratio']}:"
        f"attack={comp['attack']}:release={comp['release']}:makeup={comp['makeup']},"
        f"afade=t=out:st=-{fade_duration}:d={fade_duration}:curve=exp"  # Añadir fade out exponencial al final
    )
    
    try:
        logger.info(f"Comprimiendo y aplicando fade-out: {input_file.name}")
        
        subprocess.run([
            'ffmpeg', '-y', '-i', str(input_file),
            '-af', compressor_filter,
            '-c:a', 'libmp3lame', '-q:a', '0',
            str(output_file)
        ], check=True, capture_output=True)
        
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al comprimir {input_file.name}: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            logger.warning(f"Salida de error: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
        return False

def split_text_into_sentences(text: str) -> List[Dict[str, Any]]:
    sentence_pattern = r'([^.!?]+[.!?]+)'
    sentences = re.findall(sentence_pattern, text)
    
    segments = []
    for i, sentence in enumerate(sentences):
        if sentence.strip():
            segments.append({
                "id": i,
                "text": sentence.strip()
            })
    
    if not segments and text.strip():
        segments.append({
            "id": 0,
            "text": text.strip()
        })
    
    return segments

def generate_segment_speech(
    client: OpenAI, 
    segment: Dict[str, Any], 
    output_file: Path, 
    config: Dict, 
    cost_min: float
) -> Tuple[float, float]:
    start_time = time.time()
    
    text = segment["text"]
    
    try:
        response = client.audio.speech.create(
            model=config["tts"]["model"], 
            voice=config["tts"]["voice"],
            input=text, 
            response_format="mp3",
            speed=config["tts"]["speed"]
        )
        
        response.stream_to_file(str(output_file))
        
        elapsed = time.time() - start_time
        
        palabras_estimadas = len(text) / 5
        minutos_estimados = palabras_estimadas / 150
        costo_estimado = minutos_estimados * cost_min
        
        return costo_estimado, elapsed
    
    except Exception as e:
        logger.error(f"Error generando audio para segmento: {str(e)}")
        create_silence(2, output_file, config)
        return 0, time.time() - start_time

def generate_ffmpeg_script(
    segments: List[Path], 
    temp_dir: Path, 
    config: Dict
) -> Path:
    concat_content = []
    concat_file = temp_dir / "concat.txt"
    
    pause_duration_sec = config["pausa"]["duracion_ms"] / 1000.0
    silence_file = temp_dir / "silence_pause.mp3"
    create_silence(pause_duration_sec, silence_file, config)
    
    for i, segment_file in enumerate(segments):
        concat_content.append(f"file '{segment_file.absolute()}'")
        
        if i < len(segments) - 1:
            concat_content.append(f"file '{silence_file.absolute()}'")
    
    concat_file.write_text("\n".join(concat_content), encoding="utf-8")
    
    return concat_file

def concatenate_audio_files(concat_file: Path, output_file: Path) -> None:
    try:
        logger.info("Concatenando archivos de audio con pausas explícitas...")
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_file), '-c:a', 'libmp3lame', '-q:a', '2', str(output_file)
        ], check=True, capture_output=True)
        logger.info(f"✓ Audio concatenado guardado en: {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al concatenar audio: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            logger.warning(f"Salida de error: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
        raise

def generate_speech(
    text: str, 
    output_file: Path, 
    temp_dir: Path,
    voice: str = "echo",
    model: str = "gpt-4o-mini-tts",
    instructions: Optional[str] = None,
    speed: float = 1.0,
    pause_duration_ms: int = 1300,
    silent: bool = False
) -> Dict[str, Any]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg no está instalado. Es necesario para procesar audio.")
        
    try:
        api_config = load_api_config()
        api_key = api_config.get("tts", {}).get("api_key")
        
        if not api_key:
            raise ValueError("API key no encontrada en la configuración")
            
        client = OpenAI(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"Error al cargar configuración de API: {str(e)}")
    
    config = {
        "audio": DEFAULT_CONFIG["audio"].copy(),
        "tts": {
            "model": model,
            "voice": voice,
            "speed": speed,
            "instructions": instructions or DEFAULT_CONFIG["tts"]["instructions"]
        },
        "pausa": {
            "duracion_ms": pause_duration_ms
        },
        "compressor": DEFAULT_CONFIG["compressor"].copy()
    }
    
    stats = {
        "start_time": time.time(),
        "characters": len(text),
        "api_time": 0,
        "cost": 0,
        "voice": voice,
        "model": model,
        "segments_generated": 0,
    }
    
    logger.info(f"Procesando texto de {len(text)} caracteres...")
    segments = split_text_into_sentences(text)
    logger.info(f"Texto dividido en {len(segments)} oraciones")
    
    temp_files = []
    compressed_files = []
    cost_per_minute = api_config.get("documentation", {}).get("models", {}).get(model, {}).get("cost", {}).get("per_minute", 0.015)
    
    logger.info(f"Generando audio con voz '{voice}' usando modelo '{model}'...")
    
    for i, segment in enumerate(segments):
        if not silent:
            logger.info(f"Generando segmento {i+1}/{len(segments)}...")
        
        segment_file = temp_dir / f"segment_{i:03d}.mp3"
        segment_cost, segment_time = generate_segment_speech(client, segment, segment_file, config, cost_per_minute)
        
        stats["cost"] += segment_cost
        stats["api_time"] += segment_time
        stats["segments_generated"] += 1
        
        segment_comp_file = temp_dir / f"segment_{i:03d}_comp.mp3"
        if compress_audio(segment_file, segment_comp_file, config):
            compressed_files.append(segment_comp_file)
            temp_files.append(segment_file)
            
            if not silent:
                duracion = get_audio_duration(segment_comp_file)
                logger.info(f"✓ Segmento {i+1}/{len(segments)}: {duracion:.2f}s | {len(segment['text'])} caracteres | ${segment_cost:.6f}")
        else:
            logger.warning(f"Advertencia: Error al comprimir segmento {i+1}, usando original")
            compressed_files.append(segment_file)
            temp_files.append(segment_file)
    
    logger.info(f"Preparando concatenación con pausas de {config['pausa']['duracion_ms']}ms...")
    concat_file = generate_ffmpeg_script(compressed_files, temp_dir, config)
    
    temp_output = temp_dir / "temp_output.mp3"
    concatenate_audio_files(concat_file, temp_output)
    
    logger.info("Normalizando audio final...")
    audio_metrics = normalize_audio(temp_output, output_file, config["audio"]["target_lufs"])
    
    final_duration = get_audio_duration(output_file)
    total_time = time.time() - stats["start_time"]
    pause_duration_sec = config["pausa"]["duracion_ms"] / 1000.0
    total_pause_duration = pause_duration_sec * (len(segments) - 1)
    
    stats.update({
        "duration": final_duration,
        "duration_without_pauses": final_duration - total_pause_duration,
        "total_pause_duration": total_pause_duration,
        "number_of_pauses": len(segments) - 1,
        "pause_duration_ms": config["pausa"]["duracion_ms"],
        "file_size": output_file.stat().st_size,
        "total_time": total_time,
        "words_estimate": len(text) // 5,
        "audio_metrics": audio_metrics,
        "segments_count": len(segments)
    })
    
    if not silent:
        logger.info(f"✓ Audio generado exitosamente en {total_time:.2f}s")
        logger.info(f"  - Caracteres: {stats['characters']:,}")
        logger.info(f"  - Oraciones: {len(segments)}")
        logger.info(f"  - Duración: {final_duration:.2f}s ({final_duration/60:.2f}m)")
        logger.info(f"  - Pausas: {len(segments)-1} pausas de {pause_duration_sec:.2f}s ({total_pause_duration:.2f}s total)")
        logger.info(f"  - Costo estimado: ${stats['cost']:.6f} USD")
    
    return stats

def generate_speech_from_file(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    voice: str = "echo",
    model: str = "gpt-4o-mini-tts",
    instructions: Optional[str] = None,
    speed: float = 1.0,
    pause_duration_ms: int = 1300,
    silent: bool = False
) -> Dict[str, Any]:
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo de entrada: {input_path}")
    
    try:
        if input_path.suffix.lower() == '.json':
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                text = data.get('text', '')
                if not text and 'segments' in data:
                    text = ' '.join([seg.get('text', '') for seg in data.get('segments', [])])
        else:
            text = input_path.read_text(encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Error al leer el archivo de entrada: {str(e)}")
    
    if not text:
        raise ValueError("No se pudo extraer texto del archivo de entrada")
    
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        output_path.parent.mkdir(exist_ok=True, parents=True)
        stats = generate_speech(
            text=text, 
            output_file=output_path, 
            temp_dir=temp_dir,
            voice=voice, 
            model=model, 
            instructions=instructions,
            speed=speed,
            pause_duration_ms=pause_duration_ms,
            silent=silent
        )
        return stats
    finally:
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Advertencia: No se pudieron eliminar archivos temporales: {str(e)}")

def list_available_voices() -> Dict[str, Any]:
    try:
        api_config = load_api_config()
        voices_info = api_config.get("documentation", {}).get("voices", {})
        models_info = api_config.get("documentation", {}).get("models", {})
        
        return {
            "voices": voices_info,
            "models": models_info
        }
    except Exception as e:
        logger.error(f"Error al obtener voces disponibles: {e}")
        return {"voices": {}, "models": {}, "error": str(e)} 