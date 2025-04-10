#!/usr/bin/env python3
"""
Script para crear montajes de vídeo a partir de imágenes y audio usando FFmpeg.
Este script genera un slideshow con transiciones basadas en tiempos especificados.
"""

import os
import sys
import json
import uuid
import logging
import subprocess
import tempfile
import shutil
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('video_montage')

def create_montage(
    audio_path: str,
    image_paths_with_times: List[Dict[str, Any]],
    output_path: str,
    fps: int = 25,
    transition_duration: float = 0.8,  # Aumentada para transiciones más suaves
    resolution: Tuple[int, int] = (1920, 1080)
) -> str:
    """
    Crea un montaje de vídeo combinando un archivo de audio con imágenes en tiempos específicos.
    
    Args:
        audio_path: Ruta al archivo de audio
        image_paths_with_times: Lista de diccionarios con 'path' y 'start_time' para cada imagen
        output_path: Ruta donde guardar el vídeo generado
        fps: Fotogramas por segundo (por defecto 25)
        transition_duration: Duración de la transición entre imágenes en segundos (por defecto 0.8)
        resolution: Resolución del vídeo en píxeles (ancho, alto) (por defecto 1920x1080)
    
    Returns:
        Ruta al archivo de vídeo generado
    """
    try:
        # Verificar que el audio existe
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"El archivo de audio no existe: {audio_path}")
        
        # Verificar que todas las imágenes existen
        for img_info in image_paths_with_times:
            img_path = Path(img_info['path'])
            if not img_path.exists():
                raise FileNotFoundError(f"La imagen no existe: {img_path}")
        
        # Crear directorio de output si no existe
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear directorio temporal para archivos intermedios
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Ordenar imágenes por tiempo de inicio
            sorted_images = sorted(image_paths_with_times, key=lambda x: x['start_time'])
            
            # Obtener duración del audio para calcular la duración del último segmento
            audio_duration = get_audio_duration(audio_path)
            logger.info(f"Duración del audio: {audio_duration} segundos")
            
            # Lista para almacenar los segmentos de vídeo
            video_segments = []
            xfade_files = temp_dir_path / "xfade_list.txt"
            
            # Crear un fichero con la lista de clips y transiciones para xfade
            with open(xfade_files, 'w') as xfade_file:
                # Procesar cada imagen
                for i, img_info in enumerate(sorted_images):
                    img_path = Path(img_info['path'])
                    start_time = img_info['start_time']
                    
                    # Determinar la duración de este segmento
                    if i < len(sorted_images) - 1:
                        next_start = sorted_images[i + 1]['start_time']
                        duration = next_start - start_time
                    else:
                        duration = audio_duration - start_time
                    
                    # Ajustar duración si es negativa o muy pequeña
                    if duration <= 0:
                        logger.warning(f"Duración incorrecta para imagen {i+1}, ajustando a 1 segundo")
                        duration = 1.0
                    
                    logger.info(f"Imagen {i+1}: {img_path} - Inicia en {start_time}s - Duración {duration}s")
                    
                    # Crear un segmento de vídeo para esta imagen
                    segment_path = temp_dir_path / f"segment_{i:03d}.mp4"
                    
                    # Extender ligeramente la duración para permitir el crossfade
                    actual_duration = duration
                    if i < len(sorted_images) - 1 and duration > transition_duration:
                        actual_duration += transition_duration
                    
                    # Crear el segmento de vídeo a partir de la imagen
                    create_video_segment(
                        img_path, 
                        segment_path, 
                        actual_duration, 
                        fps, 
                        resolution
                    )
                    
                    # Añadir a la lista de entradas para filtro xfade
                    xfade_file.write(f"file '{segment_path}'\n")
                    
                    # Añadir transición de crossfade excepto para el último clip
                    if i < len(sorted_images) - 1:
                        transition_time = actual_duration - transition_duration
                        if transition_time > 0:
                            xfade_file.write(f"duration {transition_time}\n")
                            xfade_file.write(f"transition xfade duration {transition_duration}\n")
                        else:
                            # Si no hay suficiente tiempo para una transición, simplemente cortar
                            xfade_file.write(f"duration {actual_duration}\n")
                    else:
                        # Para el último clip, añadir su duración completa
                        xfade_file.write(f"duration {actual_duration}\n")
            
            # Usar el filtro de xfade para crear las transiciones entre clips
            logger.info("Creando vídeo con transiciones xfade")
            video_with_transitions = temp_dir_path / "video_with_transitions.mp4"
            
            xfade_cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(xfade_files),
                "-filter_complex", "xfade=transition=fade:duration=1:offset=0:color=white",
                "-c:v", "libx264",
                "-preset", "medium",
                "-pix_fmt", "yuv420p",
                str(video_with_transitions),
                "-y"
            ]
            
            logger.info(f"Comando xfade: {' '.join(xfade_cmd)}")
            
            try:
                process = subprocess.run(
                    xfade_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=180  # 3 minutos timeout
                )
                
                if process.returncode != 0:
                    logger.error(f"Error en xfade: {process.stderr}")
                    logger.info("Intentando método alternativo de concatenación...")
                    
                    # Método alternativo si xfade falla - usar concatenación simple
                    # Crear los segmentos sin extensión adicional
                    for i, img_info in enumerate(sorted_images):
                        segment_path = temp_dir_path / f"segment_simple_{i:03d}.mp4"
                        img_path = Path(img_info['path'])
                        
                        # Determinar duración correcta
                        start_time = img_info['start_time']
                        if i < len(sorted_images) - 1:
                            duration = sorted_images[i + 1]['start_time'] - start_time
                        else:
                            duration = audio_duration - start_time
                        
                        if duration <= 0:
                            duration = 1.0
                        
                        # Crear cada segmento con fade in y fade out
                        fade_in = min(transition_duration / 2, duration / 4)
                        fade_out = min(transition_duration / 2, duration / 4)
                        
                        create_video_segment_with_fades(
                            img_path,
                            segment_path,
                            duration,
                            fps,
                            resolution,
                            fade_in,
                            fade_out
                        )
                        
                        video_segments.append(segment_path)
                    
                    # Archivo de concatenación simple
                    concat_file = temp_dir_path / "concat_simple.txt"
                    with open(concat_file, 'w') as f:
                        for segment in video_segments:
                            f.write(f"file '{segment}'\n")
                    
                    # Concatenar todos los segmentos
                    concat_output = temp_dir_path / "concatenated.mp4"
                    concat_cmd = [
                        "ffmpeg",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", str(concat_file),
                        "-c", "copy",
                        str(concat_output),
                        "-y"
                    ]
                    
                    logger.info(f"Ejecutando concatenación simple: {' '.join(concat_cmd)}")
                    process = subprocess.run(
                        concat_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=120  # 2 minutos timeout
                    )
                    
                    if process.returncode != 0:
                        logger.error(f"Error en concatenación simple: {process.stderr}")
                        raise RuntimeError(f"Error al concatenar segmentos: {process.stderr}")
                    
                    video_with_transitions = concat_output
                
            except subprocess.TimeoutExpired:
                logger.error("Timeout en la creación de transiciones")
                raise RuntimeError("Timeout en la creación de transiciones")
            
            # Añadir el audio al vídeo
            logger.info(f"Añadiendo audio al vídeo")
            final_cmd = [
                "ffmpeg",
                "-i", str(video_with_transitions),
                "-i", str(audio_path),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(output_path),
                "-y"
            ]
            
            process = subprocess.run(
                final_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120  # 2 minutos timeout
            )
            
            if process.returncode != 0:
                logger.error(f"Error al añadir audio: {process.stderr}")
                raise RuntimeError(f"Error al añadir audio al vídeo: {process.stderr}")
        
        if not output_path.exists():
            raise RuntimeError(f"El archivo de salida no se generó correctamente: {output_path}")
        
        logger.info(f"Montaje creado exitosamente: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Error al crear montaje: {str(e)}", exc_info=True)
        raise

def create_video_segment(
    image_path: Path,
    output_path: Path,
    duration: float,
    fps: int,
    resolution: Tuple[int, int],
    fade_duration: float = 0
) -> Path:
    """
    Crea un segmento de vídeo a partir de una imagen estática.
    
    Args:
        image_path: Ruta a la imagen
        output_path: Ruta de salida para el segmento de vídeo
        duration: Duración del segmento en segundos
        fps: Fotogramas por segundo
        resolution: Resolución del vídeo (ancho, alto)
        fade_duration: Duración del fade in/out en segundos (0 para desactivar)
    
    Returns:
        Ruta al segmento de vídeo creado
    """
    # Construir el comando FFmpeg base
    width, height = resolution
    
    # Filtros para fade in/out si se especifica
    if fade_duration > 0:
        # Asegurarse de que la duración del fade no sea mayor que la mitad de la duración total
        fade_duration = min(fade_duration, duration / 3)
        fade_filter = f",fade=in:0:{int(fade_duration * fps)}:color=white"
    else:
        fade_filter = ""
    
    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", str(image_path),
        "-t", str(duration),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=white{fade_filter}",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        str(output_path),
        "-y"
    ]
    
    logger.info(f"Creando segmento para {image_path}")
    logger.info(f"Comando FFmpeg: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60  # Añadir timeout de 60 segundos
        )
        
        if process.returncode != 0:
            logger.error(f"Error al crear segmento: {process.stderr}")
            # Probar con un comando simplificado como alternativa
            logger.info("Intentando con comando FFmpeg simplificado...")
            
            # Comando simplificado con menos opciones
            simple_cmd = [
                "ffmpeg",
                "-loop", "1",
                "-i", str(image_path),
                "-t", str(duration),
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=white",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",  # Usar preset más rápido
                "-r", str(fps),
                str(output_path),
                "-y"
            ]
            
            logger.info(f"Comando simplificado: {' '.join(simple_cmd)}")
            process = subprocess.run(
                simple_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
            
            if process.returncode != 0:
                logger.error(f"Error con comando simplificado: {process.stderr}")
                raise RuntimeError(f"Error al crear segmento de vídeo: {process.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout al ejecutar FFmpeg para {image_path}")
        raise RuntimeError(f"FFmpeg se ejecutó por más de 60 segundos y fue cancelado")
    except Exception as e:
        logger.error(f"Excepción al crear segmento: {str(e)}", exc_info=True)
        raise
    
    if not output_path.exists():
        raise RuntimeError(f"El segmento no se generó correctamente: {output_path}")
    
    logger.info(f"Segmento creado exitosamente: {output_path}")
    return output_path

def create_video_segment_with_fades(
    image_path: Path,
    output_path: Path,
    duration: float,
    fps: int,
    resolution: Tuple[int, int],
    fade_in_duration: float = 0.5,
    fade_out_duration: float = 0.5
) -> Path:
    """
    Crea un segmento de vídeo a partir de una imagen estática con fade in y fade out.
    
    Args:
        image_path: Ruta a la imagen
        output_path: Ruta de salida para el segmento de vídeo
        duration: Duración del segmento en segundos
        fps: Fotogramas por segundo
        resolution: Resolución del vídeo (ancho, alto)
        fade_in_duration: Duración del fade in en segundos
        fade_out_duration: Duración del fade out en segundos
    
    Returns:
        Ruta al segmento de vídeo creado
    """
    width, height = resolution
    
    # Construir el filtro de fade in/out
    fade_filter = ""
    if fade_in_duration > 0:
        fade_in_frames = int(fade_in_duration * fps)
        fade_filter += f",fade=in:0:{fade_in_frames}:color=white"
    
    if fade_out_duration > 0:
        fade_out_frames = int(fade_out_duration * fps)
        fade_out_start = int((duration - fade_out_duration) * fps)
        if fade_out_start > 0:  # Asegurar que el fade out no empieza antes que el fade in
            fade_filter += f",fade=out:{fade_out_start}:{fade_out_frames}:color=white"
    
    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", str(image_path),
        "-t", str(duration),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=white{fade_filter}",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        str(output_path),
        "-y"
    ]
    
    logger.info(f"Creando segmento con fades para {image_path}")
    
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        
        if process.returncode != 0:
            logger.error(f"Error al crear segmento con fades: {process.stderr}")
            raise RuntimeError(f"Error al crear segmento de vídeo: {process.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout al ejecutar FFmpeg para {image_path}")
        raise RuntimeError(f"FFmpeg se ejecutó por más de 60 segundos y fue cancelado")
    
    if not output_path.exists():
        raise RuntimeError(f"El segmento no se generó correctamente: {output_path}")
    
    logger.info(f"Segmento con fades creado exitosamente: {output_path}")
    return output_path

def get_audio_duration(audio_path: str) -> float:
    """
    Obtiene la duración de un archivo de audio usando FFprobe.
    
    Args:
        audio_path: Ruta al archivo de audio
    
    Returns:
        Duración en segundos
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(audio_path)
    ]
    
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if process.returncode != 0:
        logger.warning(f"Error al obtener duración del audio: {process.stderr}")
        return 0
    
    try:
        result = json.loads(process.stdout)
        duration = float(result["format"]["duration"])
        return duration
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning("No se pudo obtener la duración del audio")
        return 0

def get_video_info(video_path: str) -> dict:
    """
    Obtiene información sobre un archivo de vídeo usando FFprobe.
    
    Args:
        video_path: Ruta al archivo de vídeo
        
    Returns:
        Dict con información del vídeo
    """
    try:
        video_path = Path(video_path)
        
        # Comando FFprobe para obtener información en formato JSON
        ffprobe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]
        
        process = subprocess.run(
            ffprobe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            logger.warning(f"Error al obtener información del vídeo: {process.stderr}")
            return {}
        
        # Analizar resultado JSON
        info = json.loads(process.stdout)
        
        # Extraer información relevante
        format_info = info.get("format", {})
        
        result = {
            "duration": float(format_info.get("duration", 0)),
            "size": int(format_info.get("size", 0)),
            "format": format_info.get("format_name", "")
        }
        
        # Encontrar stream de vídeo
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                result["width"] = stream.get("width", 0)
                result["height"] = stream.get("height", 0)
                result["codec"] = stream.get("codec_name", "")
                break
        
        return result
        
    except Exception as e:
        logger.error(f"Error en get_video_info: {str(e)}")
        return {}

def generate_video_montage(
    audio_path: str,
    image_paths: List[Dict[str, Any]],
    output_dir: str,
    output_filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera un vídeo montaje a partir de un audio y varias imágenes.
    
    Args:
        audio_path: Ruta al archivo de audio
        image_paths: Lista de diccionarios con 'path' y 'start_time' para cada imagen
        output_dir: Directorio donde guardar el output
        output_filename: Nombre del archivo de salida (opcional)
    
    Returns:
        Diccionario con información del archivo generado
    """
    try:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")
        
        # Verificar que todas las imágenes existen
        for img_info in image_paths:
            if not os.path.exists(img_info['path']):
                raise FileNotFoundError(f"Imagen no encontrada: {img_info['path']}")
        
        # Crear directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Generar nombre de archivo si no se proporciona
        if not output_filename:
            output_filename = f"montage_{uuid.uuid4().hex[:8]}.mp4"
        
        # Asegurar que tiene extensión .mp4
        if not output_filename.lower().endswith('.mp4'):
            output_filename += '.mp4'
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Crear el montaje
        created_path = create_montage(
            audio_path=audio_path,
            image_paths_with_times=image_paths,
            output_path=output_path
        )
        
        # Obtener información del archivo
        file_size = os.path.getsize(created_path)
        video_info = get_video_info(created_path)
        
        return {
            'status': 'success',
            'output_path': created_path,
            'output_filename': output_filename,
            'file_size': file_size,
            'duration': video_info.get('duration', 0)
        }
        
    except Exception as e:
        logger.error(f"Error en generate_video_montage: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }

if __name__ == "__main__":
    # Ejemplo de uso desde línea de comandos
    if len(sys.argv) < 4:
        print("Uso: python video_montage.py <audio_file> <images_json> <output_path>")
        print("Donde images_json es un archivo JSON con lista de {'path': 'ruta/imagen.jpg', 'start_time': 0.0}")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    images_json_file = sys.argv[2]
    output_path = sys.argv[3]
    
    with open(images_json_file, 'r') as f:
        images_data = json.load(f)
    
    result = generate_video_montage(
        audio_path=audio_file,
        image_paths=images_data,
        output_dir=os.path.dirname(output_path),
        output_filename=os.path.basename(output_path)
    )
    
    print(json.dumps(result, indent=2))
