#!/usr/bin/env python3
from pathlib import Path
import subprocess, tempfile, platform, os, shutil
from pdf2image import convert_from_path
from typing import Dict

DEFAULT_DPI, DEFAULT_FORMAT = 300, "png"
DEFAULT_OUTPUT_DIR = Path("output")
LIBREOFFICE_TIMEOUT = 60

def get_libreoffice_python():
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

def pptx_to_pdf(input_file, output_file):
    input_file, output_file = str(input_file), str(output_file)
    env = os.environ.copy()
    
    if platform.system().lower() == "linux":
        env["LC_ALL"], env["SAL_USE_VCLPLUGIN"] = "C.UTF-8", "gen"
    
    try:
        try:
            subprocess.run(["unoconv", "-f", "pdf", "-o", output_file, input_file], 
                          check=True, capture_output=True, text=True,
                          env=env, timeout=LIBREOFFICE_TIMEOUT)
        except (subprocess.SubprocessError, FileNotFoundError):
            subprocess.run([get_libreoffice_python(), "-m", "unoconv", "-f", "pdf", "-o", 
                           output_file, input_file], check=True, capture_output=True, 
                           text=True, env=env, timeout=LIBREOFFICE_TIMEOUT)
        
        if not Path(output_file).exists():
            raise RuntimeError(f"La conversión a PDF falló: {output_file} no fue creado")
        
        return output_file
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Tiempo agotado al convertir PPTX a PDF (límite: {LIBREOFFICE_TIMEOUT}s)")
    except subprocess.CalledProcessError:
        try:
            out_dir = os.path.dirname(output_file)
            subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", 
                           "--outdir", out_dir, input_file], check=True, 
                           capture_output=True, text=True, env=env, timeout=LIBREOFFICE_TIMEOUT)
            
            gen_pdf = os.path.join(out_dir, os.path.basename(input_file).replace(".pptx", ".pdf"))
            if os.path.exists(gen_pdf) and gen_pdf != output_file:
                shutil.move(gen_pdf, output_file)
            
            if Path(output_file).exists(): return output_file
        except: pass
        
        raise RuntimeError("Error al convertir PPTX a PDF")

def extract_pptx_slides(pptx_path, output_dir=None, format=DEFAULT_FORMAT, dpi=DEFAULT_DPI):
    pptx_path = Path(pptx_path)
    if not pptx_path.exists():
        raise FileNotFoundError(f"No se encuentra el archivo PPTX: {pptx_path}")

    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR / pptx_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {"slides": 0, "generated_files": []}
    temp_dir = tempfile.mkdtemp(prefix="insco_snapshot_")
    pdf_file = os.path.join(temp_dir, f"{pptx_path.stem}.pdf")
    
    try:
        pdf_file = pptx_to_pdf(pptx_path, pdf_file)
        
        conversion_args = {}
        if os.environ.get("INSCO_MEMORY_LIMIT") and platform.system().lower() == "linux":
            conversion_args["thread_count"] = 1
        
        images = convert_from_path(pdf_file, dpi=dpi, **conversion_args)
        
        for i, image in enumerate(images, 1):
            output_file = output_dir / f"slide_{i:03d}.{format}"
            image.save(output_file, format.upper())
            stats["generated_files"].append(str(output_file))
            stats["slides"] += 1
    finally:
        try: shutil.rmtree(temp_dir, ignore_errors=True)
        except: pass
    
    return {
        "slides": stats["slides"],
        "output_dir": str(output_dir),
        "format": format.upper(),
        "dpi": dpi,
        "generated_files": stats["generated_files"]
    } 