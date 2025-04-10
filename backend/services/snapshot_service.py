#!/usr/bin/env python3
import logging
from pathlib import Path
import subprocess, tempfile, platform, os, shutil
from pdf2image import convert_from_path
from typing import Dict, List, Optional, Union

DEFAULT_DPI, DEFAULT_FORMAT = 300, "png"
DEFAULT_OUTPUT_DIR = Path("output")
LIBREOFFICE_TIMEOUT = 60

# Configuración de logger
logger = logging.getLogger("snapshot-service")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def get_libreoffice_python() -> str:
    """Obtiene la ruta al binario de Python usado por LibreOffice."""
    system = platform.system().lower()
    
    if "UNO_PATH" in os.environ and os.path.exists(os.environ["UNO_PATH"]):
        return os.environ.get("LIBREOFFICE_PYTHON", "python3")
    
    if system == "darwin":
        return "/Applications/LibreOffice.app/Contents/MacOS/python"
    elif system == "linux":
        linux_paths = ["/usr/bin/python3", "/usr/lib/libreoffice/program/python", 
                      "/usr/lib/libreoffice/program/python3", "/opt/libreoffice/program/python"]
        for path in linux_paths:
            if Path(path).exists(): return path
    elif system == "windows":
        for prog_dir in ["C:\\Program Files", "C:\\Program Files (x86)"]:
            for ver in ["", " 5", " 6", " 7", " 8"]:
                path = f"{prog_dir}\\LibreOffice{ver}\\program\\python.exe"
                if Path(path).exists(): return path
    
    return "python3"

def pptx_to_pdf(input_file: Union[str, Path], output_file: Union[str, Path]) -> str:
    """Convierte un archivo PPTX a PDF usando LibreOffice."""
    input_file, output_file = str(input_file), str(output_file)
    env = os.environ.copy()
    
    logger.info(f"Convirtiendo PPTX a PDF: {input_file} -> {output_file}")
    
    if platform.system().lower() == "linux":
        env["LC_ALL"], env["SAL_USE_VCLPLUGIN"] = "C.UTF-8", "gen"
    
    try:
        try:
            logger.debug("Intentando conversión con unoconv...")
            subprocess.run(["unoconv", "-f", "pdf", "-o", output_file, input_file], 
                          check=True, capture_output=True, text=True,
                          env=env, timeout=LIBREOFFICE_TIMEOUT)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.debug("Fallback a Python de LibreOffice con unoconv...")
            subprocess.run([get_libreoffice_python(), "-m", "unoconv", "-f", "pdf", "-o", 
                           output_file, input_file], check=True, capture_output=True, 
                           text=True, env=env, timeout=LIBREOFFICE_TIMEOUT)
        
        if not Path(output_file).exists():
            raise RuntimeError(f"La conversión a PDF falló: {output_file} no fue creado")
        
        logger.info(f"Conversión PPTX a PDF completada: {output_file}")
        return output_file
    except subprocess.TimeoutExpired:
        logger.error(f"Tiempo agotado al convertir PPTX a PDF (límite: {LIBREOFFICE_TIMEOUT}s)")
        raise RuntimeError(f"Tiempo agotado al convertir PPTX a PDF (límite: {LIBREOFFICE_TIMEOUT}s)")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Error en unoconv, intentando con LibreOffice directo: {str(e)}")
        try:
            out_dir = os.path.dirname(output_file)
            subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", 
                           "--outdir", out_dir, input_file], check=True, 
                           capture_output=True, text=True, env=env, timeout=LIBREOFFICE_TIMEOUT)
            
            gen_pdf = os.path.join(out_dir, os.path.basename(input_file).replace(".pptx", ".pdf"))
            if os.path.exists(gen_pdf) and gen_pdf != output_file:
                shutil.move(gen_pdf, output_file)
            
            if Path(output_file).exists(): 
                logger.info(f"Conversión con LibreOffice exitosa: {output_file}")
                return output_file
        except Exception as e:
            logger.error(f"Error en fallback a LibreOffice: {str(e)}")
        
        raise RuntimeError("Error al convertir PPTX a PDF")

def extract_pptx_slides(
    pptx_path: Union[str, Path], 
    output_dir: Optional[Union[str, Path]] = None, 
    format: str = DEFAULT_FORMAT, 
    dpi: int = DEFAULT_DPI
) -> Dict:
    """
    Extrae diapositivas de un archivo PPTX como imágenes.
    
    Args:
        pptx_path: Ruta al archivo PPTX
        output_dir: Directorio de salida (opcional)
        format: Formato de imagen ('png' o 'jpg')
        dpi: Resolución en DPI
        
    Returns:
        Dict con estadísticas y rutas de archivos generados
    """
    pptx_path = Path(pptx_path)
    if not pptx_path.exists():
        logger.error(f"No se encuentra el archivo PPTX: {pptx_path}")
        raise FileNotFoundError(f"No se encuentra el archivo PPTX: {pptx_path}")

    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR / pptx_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extrayendo diapositivas de {pptx_path} a {output_dir} ({format.upper()}, {dpi}dpi)")
    
    stats = {"slides": 0, "generated_files": []}
    temp_dir = tempfile.mkdtemp(prefix="insco_snapshot_")
    pdf_file = os.path.join(temp_dir, f"{pptx_path.stem}.pdf")
    
    try:
        pdf_file = pptx_to_pdf(pptx_path, pdf_file)
        
        conversion_args = {}
        if os.environ.get("INSCO_MEMORY_LIMIT") and platform.system().lower() == "linux":
            conversion_args["thread_count"] = 1
            logger.debug("Limitando threads para conversión de PDF a imágenes")
        
        logger.info(f"Convirtiendo PDF a imágenes {format.upper()} ({dpi}dpi)")
        images = convert_from_path(pdf_file, dpi=dpi, **conversion_args)
        
        for i, image in enumerate(images, 1):
            output_file = output_dir / f"slide_{i:03d}.{format}"
            image.save(output_file, format.upper())
            stats["generated_files"].append(str(output_file))
            stats["slides"] += 1
            
        logger.info(f"Generadas {stats['slides']} imágenes en {output_dir}")
    except Exception as e:
        logger.error(f"Error al extraer diapositivas: {str(e)}")
        raise
    finally:
        try: 
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"Directorio temporal eliminado: {temp_dir}")
        except Exception as e: 
            logger.warning(f"No se pudo eliminar directorio temporal: {str(e)}")
    
    return {
        "slides": stats["slides"],
        "output_dir": str(output_dir),
        "format": format.upper(),
        "dpi": dpi,
        "generated_files": stats["generated_files"]
    } 