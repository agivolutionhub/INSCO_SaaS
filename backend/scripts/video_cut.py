import subprocess
from pathlib import Path
import os
import json
import uuid
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("video_cut")

def cut_video(
    video_path: str, 
    output_path: str, 
    start_time: float, 
    end_time: float,
    output_format: str = None
) -> dict:
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
        start_time_str = format_time_for_ffmpeg(start_time)
        duration_seconds = end_time - start_time
        
        # Comando FFmpeg para cortar el vídeo
        ffmpeg_cmd = [
            "ffmpeg",
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

def format_time_for_ffmpeg(seconds: float) -> str:
    """
    Convierte segundos a formato HH:MM:SS.mmm para FFmpeg
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

if __name__ == "__main__":
    """
    Función principal para ejecutar desde línea de comandos
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Cortar segmentos de vídeo usando FFmpeg")
    parser.add_argument("input", help="Archivo de vídeo de entrada")
    parser.add_argument("output", help="Archivo de vídeo de salida")
    parser.add_argument("--start", type=float, default=0, help="Tiempo de inicio en segundos")
    parser.add_argument("--end", type=float, required=True, help="Tiempo final en segundos")
    
    args = parser.parse_args()
    
    try:
        result = cut_video(
            video_path=args.input,
            output_path=args.output,
            start_time=args.start,
            end_time=args.end
        )
        
        print(f"Vídeo cortado exitosamente: {result['output_file']}")
        print(f"Duración: {result['duration']:.2f} segundos")
        print(f"Tamaño: {result['size']/1024/1024:.2f} MB")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1) 