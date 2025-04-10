from pathlib import Path
import json, re, subprocess, os, time, shutil
from typing import Dict, List, Any, Tuple, Optional, Union
from openai import OpenAI
from rich.console import Console

console = Console()

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
        "duracion_ms": 1300  # Duración de la pausa en milisegundos (1.3 segundos)
    },
    "compressor": {
        "threshold": "-32dB",  # Umbral de activación del compresor
        "ratio": "8",          # Relación de compresión (8:1)
        "attack": "20",        # Tiempo de ataque en ms
        "release": "250",      # Tiempo de liberación en ms
        "makeup": "8"          # Ganancia de compensación
    }
}

def load_api_config() -> Dict[str, Any]:
    """Carga la configuración de la API desde el archivo JSON"""
    script_dir = Path(__file__).resolve().parent.parent
    config_file = script_dir / "config" / "ttsapi.json"
    
    if not config_file.exists():
        raise FileNotFoundError(f"No se encuentra archivo de configuración: {config_file}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)

def check_ffmpeg() -> bool:
    """Verifica si ffmpeg está instalado"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def create_silence(duration: float, output_file: Path, config: Dict) -> None:
    """Crea un archivo de silencio con la duración especificada"""
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi',
        '-i', f'anullsrc=r={config["audio"]["sample_rate"]}:cl=stereo',
        '-t', str(duration), '-ar', str(config["audio"]["sample_rate"]),
        '-ac', str(config["audio"]["channels"]), '-ab', config["audio"]["bitrate"],
        '-acodec', 'libmp3lame', str(output_file)
    ], check=True, capture_output=True)

def get_audio_duration(file_path: Path) -> float:
    """Obtiene la duración de un archivo de audio en segundos"""
    result = subprocess.run([
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
        '-of', 'json', str(file_path)
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        console.print(f"[yellow]Advertencia: No se pudo obtener la duración de {file_path}[/yellow]")
        return 0
    
    try:
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except (json.JSONDecodeError, KeyError):
        console.print(f"[yellow]Advertencia: Error al parsear la duración de {file_path}[/yellow]")
        return 0

def analyze_audio_levels(file_path: Path) -> Dict[str, Any]:
    """
    Analiza los niveles de audio usando ffmpeg loudnorm
    
    Args:
        file_path: Ruta del archivo de audio
        
    Returns:
        Diccionario con información de niveles de audio
    """
    try:
        # Medir niveles actuales
        result = subprocess.run([
            'ffmpeg', '-i', str(file_path),
            '-af', f'loudnorm=I={DEFAULT_CONFIG["audio"]["target_lufs"]}:LRA=7:TP=-2.0:print_format=json',
            '-f', 'null', '-'
        ], capture_output=True, text=True)
        
        # Extraer JSON de resultados de medición
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
        console.print(f"[red]Error al analizar niveles de audio: {e}[/red]")
    
    return {
        'input_i': "Error",
        'input_tp': "Error",
        'input_lra': "Error",
        'input_thresh': "Error",
        'target_offset': "Error"
    }

def normalize_audio(input_file: Path, output_file: Path, target_lufs: float = -23) -> Dict[str, Any]:
    """
    Normaliza el audio a un nivel LUFS específico usando los valores medidos
    
    Args:
        input_file: Ruta del archivo de entrada
        output_file: Ruta del archivo de salida
        target_lufs: Nivel objetivo en LUFS
        
    Returns:
        Diccionario con información de normalización
    """
    try:
        # Obtener análisis del audio
        measured_data = analyze_audio_levels(input_file)
        
        if "Error" in measured_data["input_i"]:
            raise ValueError("Error en medición de niveles de audio")
        
        # Normalizar con los valores medidos
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
        console.print(f"[red]Error al normalizar: {str(e)}[/red]")
        # Copiar el original si falla la normalización
        shutil.copy(str(input_file), str(output_file))
        return {'input_lufs': "Error", 'target_lufs': target_lufs, 'true_peak': "Error", 'lra': "Error"}

def compress_audio(input_file: Path, output_file: Path, config: Dict) -> bool:
    """
    Comprime un archivo de audio para eliminar el fade-in inicial usando acompressor
    
    Args:
        input_file: Ruta del archivo de entrada
        output_file: Ruta del archivo de salida
        config: Configuración del compresor
        
    Returns:
        True si el proceso fue exitoso, False en caso contrario
    """
    comp = config["compressor"]
    compressor_filter = (
        f"acompressor=threshold={comp['threshold']}:ratio={comp['ratio']}:"
        f"attack={comp['attack']}:release={comp['release']}:makeup={comp['makeup']}"
    )
    
    try:
        console.print(f"[cyan]Comprimiendo: {input_file.name}[/cyan]")
        
        # Ejecutar ffmpeg con el filtro acompressor
        subprocess.run([
            'ffmpeg', '-y', '-i', str(input_file),
            '-af', compressor_filter,
            '-c:a', 'libmp3lame', '-q:a', '0',
            str(output_file)
        ], check=True, capture_output=True)
        
        return True
    
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error al comprimir {input_file.name}: {e}[/red]")
        if hasattr(e, 'stderr') and e.stderr:
            console.print(f"[yellow]Salida de error: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}[/yellow]")
        return False

def split_text_into_sentences(text: str) -> List[Dict[str, Any]]:
    """Divide el texto en oraciones"""
    # Patrón para detectar finales de oración (punto, signo de interrogación, signo de exclamación)
    sentence_pattern = r'([^.!?]+[.!?]+)'
    sentences = re.findall(sentence_pattern, text)
    
    # Crear segmentos
    segments = []
    for i, sentence in enumerate(sentences):
        if sentence.strip():
            segments.append({
                "id": i,
                "text": sentence.strip()
            })
    
    # Si no se encontraron oraciones, tratar el texto completo como una sola oración
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
    """Genera el audio para un segmento usando la API de TTS de OpenAI"""
    start_time = time.time()
    
    text = segment["text"]
    
    try:
        response = client.audio.speech.create(
            model=config["tts"]["model"], 
            voice=config["tts"]["voice"],
            input=text, 
            instructions=config["tts"]["instructions"],
            response_format="mp3",
            speed=config["tts"]["speed"]
        )
        
        response.stream_to_file(str(output_file))
        
        elapsed = time.time() - start_time
        
        # Estimación de costo basada en caracteres y modelo
        palabras_estimadas = len(text) / 5  # ~5 caracteres por palabra en promedio
        minutos_estimados = palabras_estimadas / 150  # ~150 palabras por minuto
        costo_estimado = minutos_estimados * cost_min
        
        return costo_estimado, elapsed
    
    except Exception as e:
        console.print(f"[red]Error generando audio para segmento: {str(e)}[/red]")
        create_silence(2, output_file, config)  # Crear silencio en caso de error
        return 0, time.time() - start_time

def generate_ffmpeg_script(
    segments: List[Path], 
    temp_dir: Path, 
    config: Dict
) -> Path:
    """
    Genera un archivo de lista para concatenación con ffmpeg
    
    Args:
        segments: Lista de rutas a archivos de segmentos de audio
        temp_dir: Directorio temporal
        config: Configuración
        
    Returns:
        Ruta al archivo de concatenación generado
    """
    concat_content = []
    concat_file = temp_dir / "concat.txt"
    
    # Crear un archivo de silencio para las pausas
    pause_duration_sec = config["pausa"]["duracion_ms"] / 1000.0  # Convertir de ms a segundos
    silence_file = temp_dir / "silence_pause.mp3"
    create_silence(pause_duration_sec, silence_file, config)
    
    # Recorrer los segmentos y generar la lista de archivos para concatenación
    for i, segment_file in enumerate(segments):
        # Añadir el archivo de audio del segmento
        concat_content.append(f"file '{segment_file.absolute()}'")
        
        # Añadir pausa después de cada segmento (excepto el último)
        if i < len(segments) - 1:
            concat_content.append(f"file '{silence_file.absolute()}'")
    
    # Escribir el archivo de lista para ffmpeg
    concat_file.write_text("\n".join(concat_content), encoding="utf-8")
    
    return concat_file

def concatenate_audio_files(concat_file: Path, output_file: Path) -> None:
    """Concatena los archivos de audio según el archivo de lista"""
    try:
        console.print(f"[cyan]Concatenando archivos de audio con pausas explícitas...[/cyan]")
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_file), '-c:a', 'libmp3lame', '-q:a', '2', str(output_file)
        ], check=True, capture_output=True)
        console.print(f"[green]✓ Audio concatenado guardado en: {output_file}[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error al concatenar audio: {e}[/red]")
        if hasattr(e, 'stderr') and e.stderr:
            console.print(f"[yellow]Salida de error: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}[/yellow]")
        raise

def generate_speech(
    text: str, 
    output_file: Path, 
    temp_dir: Path,
    voice: str = "echo",
    model: str = "gpt-4o-mini-tts",
    instructions: Optional[str] = None,
    speed: float = 1.0,
    pause_duration_ms: int = 1300
) -> Dict[str, Any]:
    """
    Genera un archivo de audio a partir del texto proporcionado usando la API de OpenAI
    con pausas explícitas entre segmentos y compresión para eliminar fade-in
    
    Args:
        text: Texto a convertir en voz
        output_file: Ruta del archivo de salida
        temp_dir: Directorio para archivos temporales
        voice: ID de la voz a utilizar
        model: Modelo TTS a utilizar
        instructions: Instrucciones específicas para el tono y estilo
        speed: Velocidad de habla (1.0 es normal)
        pause_duration_ms: Duración de las pausas entre oraciones en milisegundos
        
    Returns:
        Dict con estadísticas del proceso
    """
    # Crear directorio temporal si no existe
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Verificar dependencias
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg no está instalado. Es necesario para procesar audio.")
        
    # Cargar configuración API
    try:
        api_config = load_api_config()
        api_key = api_config.get("tts", {}).get("api_key")
        
        if not api_key:
            raise ValueError("API key no encontrada en la configuración")
            
        client = OpenAI(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"Error al cargar configuración de API: {str(e)}")
    
    # Preparar configuración
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
    
    # Estadísticas
    stats = {
        "start_time": time.time(),
        "characters": len(text),
        "api_time": 0,
        "cost": 0,
        "voice": voice,
        "model": model,
        "segments_generated": 0,
    }
    
    # Dividir texto en oraciones
    console.print(f"[blue]Procesando texto de {len(text)} caracteres...[/blue]")
    segments = split_text_into_sentences(text)
    console.print(f"[blue]Texto dividido en {len(segments)} oraciones[/blue]")
    
    # Procesar cada segmento
    temp_files = []
    compressed_files = []
    cost_per_minute = api_config.get("documentation", {}).get("models", {}).get(model, {}).get("cost", {}).get("per_minute", 0.015)
    
    console.print(f"[blue]Generando audio con voz '{voice}' usando modelo '{model}'...[/blue]")
    
    for i, segment in enumerate(segments):
        console.print(f"[cyan]Generando segmento {i+1}/{len(segments)}...[/cyan]")
        
        # Generar audio para el segmento
        segment_file = temp_dir / f"segment_{i:03d}.mp3"
        segment_cost, segment_time = generate_segment_speech(client, segment, segment_file, config, cost_per_minute)
        
        # Actualizar estadísticas
        stats["cost"] += segment_cost
        stats["api_time"] += segment_time
        stats["segments_generated"] += 1
        
        # Comprimir el audio para eliminar fade-in
        segment_comp_file = temp_dir / f"segment_{i:03d}_comp.mp3"
        if compress_audio(segment_file, segment_comp_file, config):
            compressed_files.append(segment_comp_file)
            temp_files.append(segment_file)
            
            # Mensaje de progreso
            duracion = get_audio_duration(segment_comp_file)
            console.print(f"[green]✓ Segmento {i+1}/{len(segments)}: {duracion:.2f}s | {len(segment['text'])} caracteres | ${segment_cost:.6f}[/green]")
        else:
            console.print(f"[yellow]Advertencia: Error al comprimir segmento {i+1}, usando original[/yellow]")
            compressed_files.append(segment_file)
            temp_files.append(segment_file)
    
    # Generar script de concatenación con pausas
    console.print(f"\n[yellow]Preparando concatenación con pausas de {config['pausa']['duracion_ms']}ms...[/yellow]")
    concat_file = generate_ffmpeg_script(compressed_files, temp_dir, config)
    
    # Crear archivo intermedio con la concatenación
    temp_output = temp_dir / "temp_output.mp3"
    concatenate_audio_files(concat_file, temp_output)
    
    # Normalizar el audio final (UNA SOLA VEZ)
    console.print("[yellow]Normalizando audio final...[/yellow]")
    audio_metrics = normalize_audio(temp_output, output_file, config["audio"]["target_lufs"])
    
    # Calcular duración final
    final_duration = get_audio_duration(output_file)
    total_time = time.time() - stats["start_time"]
    pause_duration_sec = config["pausa"]["duracion_ms"] / 1000.0
    total_pause_duration = pause_duration_sec * (len(segments) - 1)
    
    # Completar estadísticas
    stats.update({
        "duration": final_duration,
        "duration_without_pauses": final_duration - total_pause_duration,
        "total_pause_duration": total_pause_duration,
        "number_of_pauses": len(segments) - 1,
        "pause_duration_ms": config["pausa"]["duracion_ms"],
        "file_size": output_file.stat().st_size,
        "total_time": total_time,
        "words_estimate": len(text) // 5,  # Estimación aproximada
        "audio_metrics": audio_metrics,
        "segments_count": len(segments)
    })
    
    # Resumen
    console.print(f"[green]✓ Audio generado exitosamente en {total_time:.2f}s[/green]")
    console.print(f"[green]  - Caracteres: {stats['characters']:,}[/green]")
    console.print(f"[green]  - Oraciones: {len(segments)}[/green]")
    console.print(f"[green]  - Duración: {final_duration:.2f}s ({final_duration/60:.2f}m)[/green]")
    console.print(f"[green]  - Pausas: {len(segments)-1} pausas de {pause_duration_sec:.2f}s ({total_pause_duration:.2f}s total)[/green]")
    console.print(f"[green]  - Costo estimado: ${stats['cost']:.6f} USD[/green]")
    
    return stats

def generate_speech_from_file(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    voice: str = "echo",
    model: str = "gpt-4o-mini-tts",
    instructions: Optional[str] = None,
    speed: float = 1.0,
    pause_duration_ms: int = 1300
) -> Dict[str, Any]:
    """
    Genera un archivo de audio a partir de un archivo de texto
    con pausas explícitas entre oraciones y compresión para eliminar fade-in.
    
    Args:
        input_file: Ruta del archivo de texto de entrada
        output_file: Ruta del archivo de audio de salida
        voice: ID de la voz a utilizar
        model: Modelo TTS a utilizar
        instructions: Instrucciones específicas para el tono y estilo
        speed: Velocidad de habla (1.0 es normal)
        pause_duration_ms: Duración de las pausas entre oraciones en milisegundos
        
    Returns:
        Dict con estadísticas del proceso
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo de entrada: {input_path}")
    
    # Leer el texto del archivo
    try:
        if input_path.suffix.lower() == '.json':
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                text = data.get('text', '')
                if not text and 'segments' in data:
                    # Intenta extraer el texto de los segmentos si está disponible
                    text = ' '.join([seg.get('text', '') for seg in data.get('segments', [])])
        else:
            # Asume que es un archivo de texto plano
            text = input_path.read_text(encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Error al leer el archivo de entrada: {str(e)}")
    
    if not text:
        raise ValueError("No se pudo extraer texto del archivo de entrada")
    
    # Crear directorio temporal
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Generar audio
        output_path.parent.mkdir(exist_ok=True, parents=True)
        stats = generate_speech(
            text=text, 
            output_file=output_path, 
            temp_dir=temp_dir,
            voice=voice, 
            model=model, 
            instructions=instructions,
            speed=speed,
            pause_duration_ms=pause_duration_ms
        )
        return stats
    finally:
        # Limpiar archivos temporales
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                console.print(f"[yellow]Advertencia: No se pudieron eliminar archivos temporales: {str(e)}[/yellow]")
    
if __name__ == "__main__":
    # Ejemplo de uso si se ejecuta directamente
    import argparse
    
    parser = argparse.ArgumentParser(description="Generar audio a partir de texto con pausas entre oraciones")
    parser.add_argument("input", help="Archivo de texto de entrada", type=str)
    parser.add_argument("--output", "-o", help="Archivo de audio de salida", type=str, default=None)
    parser.add_argument("--voice", "-v", help="Voz a utilizar", type=str, default="echo", 
                       choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
    parser.add_argument("--model", "-m", help="Modelo TTS", type=str, default="gpt-4o-mini-tts")
    parser.add_argument("--pause", "-p", help="Duración de pausas entre oraciones (ms)", type=int, default=1300)
    parser.add_argument("--speed", "-s", help="Velocidad de habla (1.0 es normal)", type=float, default=1.0)
    args = parser.parse_args()
    
    input_file = Path(args.input)
    
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = input_file.with_suffix('.mp3')
    
    try:
        stats = generate_speech_from_file(
            input_file=input_file, 
            output_file=output_file, 
            voice=args.voice, 
            model=args.model,
            pause_duration_ms=args.pause,
            speed=args.speed
        )
        console.print(f"[bold green]Archivo generado exitosamente: {output_file}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]") 