"""
Servicio para procesar y manipular archivos de vídeo.
"""
import subprocess
import json
import logging
import os
import platform
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Configurar logger
logger = logging.getLogger("video-service")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Detectar sistema operativo para compatibilidad
IS_MACOS = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

# Ruta de FFmpeg, ajustar según el sistema
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

def cut_video(
    video_path: Union[str, Path], 
    output_path: Union[str, Path], 
    start_time: float, 
    end_time: float,
    output_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    Corta un segmento de un archivo de vídeo usando FFmpeg.
    
    Args:
        video_path: Ruta al archivo de vídeo original
        output_path: Ruta donde guardar el archivo de salida
        start_time: Tiempo de inicio del segmento en segundos
        end_time: Tiempo final del segmento en segundos
        output_format: Formato de salida (opcional, por defecto mantiene el mismo formato)
        
    Returns:
        Dict con información del proceso y archivo resultante
    """
    try:
        video_path = Path(video_path)
        output_path = Path(output_path)
        
        # Verificar que el archivo de entrada existe
        if not video_path.exists():
            raise FileNotFoundError(f"El archivo de entrada no existe: {video_path}")
        
        # Crear directorio de salida si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convertir tiempos a formato hh:mm:ss.xxx que espera FFmpeg
        start_time_str = _format_time_for_ffmpeg(start_time)
        duration_seconds = end_time - start_time
        
        # Comando FFmpeg para cortar el vídeo
        ffmpeg_cmd = [
            FFMPEG_BIN,
            "-i", str(video_path),
            "-ss", start_time_str,
            "-t", str(duration_seconds),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-strict", "experimental",
            "-b:a", "128k",
            str(output_path),
            "-y"  # Sobrescribir si existe
        ]
        
        logger.info(f"Ejecutando comando FFmpeg: {' '.join(ffmpeg_cmd)}")
        
        # Ejecutar FFmpeg
        process = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Verificar errores
        if process.returncode != 0:
            logger.error(f"Error de FFmpeg: {process.stderr}")
            raise RuntimeError(f"Error al cortar el vídeo: {process.stderr}")
        
        # Verificar que el archivo de salida existe
        if not output_path.exists():
            raise RuntimeError(f"El archivo de salida no se generó correctamente: {output_path}")
        
        # Obtener información del vídeo resultante
        video_info = get_video_info(output_path)
        
        return {
            "status": "success",
            "output_file": str(output_path),
            "duration": video_info.get("duration", duration_seconds),
            "size": video_info.get("size", output_path.stat().st_size),
            "format": video_info.get("format", output_path.suffix[1:]),
            "start_time": start_time,
            "end_time": end_time
        }
        
    except Exception as e:
        logger.error(f"Error en cut_video: {str(e)}")
        raise

def get_video_info(video_path: Union[str, Path]) -> Dict[str, Any]:
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
            FFPROBE_BIN,
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

def _format_time_for_ffmpeg(seconds: float) -> str:
    """
    Convierte segundos a formato HH:MM:SS.mmm para FFmpeg
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}" 