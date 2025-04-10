from pathlib import Path
import time
from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE

DEFAULT_INPUT_DIR = Path("data/input/diapos")
DEFAULT_OUTPUT_DIR = Path("data/output/01_autofit2")

def procesar_pptx(pptx_entrada, pptx_salida=None, silent=False):
    pptx_entrada = Path(pptx_entrada)
    if not pptx_entrada.exists() or pptx_entrada.suffix.lower() != '.pptx':
        raise FileNotFoundError(f"Archivo inválido o no encontrado: {pptx_entrada}")
    
    pptx_salida = pptx_salida or DEFAULT_OUTPUT_DIR / f"{pptx_entrada.stem}_autofit{pptx_entrada.suffix}"
    pptx_salida = Path(pptx_salida)
    pptx_salida.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if not silent:
            print(f"Procesando archivo: {pptx_entrada} -> {pptx_salida}")
        presentacion = Presentation(pptx_entrada)
        num_slides = len(presentacion.slides)
        if not silent:
            print(f"Presentación cargada, {num_slides} diapositivas")
        
        for i, slide in enumerate(presentacion.slides):
            if not silent:
                print(f"Procesando diapositiva {i+1}/{num_slides}")
            for shape in slide.shapes:
                try:
                    if hasattr(shape, "text_frame"):
                        shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
                    
                    if hasattr(shape, "has_table") and shape.has_table:
                        for cell in (cell for row in shape.table.rows for cell in row.cells if hasattr(cell, "text_frame")):
                            cell.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
                except Exception as e:
                    if not silent:
                        print(f"Error al ajustar shape: {e}")
        
        presentacion.save(pptx_salida)
        if not silent:
            print(f"✅ Archivo generado: {pptx_salida} ({num_slides} diapositivas)")
        return str(pptx_salida)
    except Exception as e:
        import traceback
        if not silent:
            traceback.print_exc()
        raise Exception(f"Error al procesar archivo: {str(e)}")

def procesar_lote(directorio=None, salida=None, silent=False):
    inicio = time.time()
    directorio, salida = Path(directorio or DEFAULT_INPUT_DIR), Path(salida or DEFAULT_OUTPUT_DIR)
    directorio.mkdir(parents=True, exist_ok=True)
    salida.mkdir(parents=True, exist_ok=True)
    
    es_archivo = directorio.is_file() and directorio.suffix.lower() == '.pptx'
    archivos = [directorio] if es_archivo else [f for f in directorio.glob("**/*.pptx") if not f.stem.endswith('_autofit')]
    
    if not archivos:
        if not silent:
            print(f"No se encontraron archivos PPTX en {directorio}")
        return {"encontrados": 0, "procesados": 0, "errores": 0, "archivos": []}
    
    if not silent:
        print(f"Encontrados {len(archivos)} archivos PPTX para procesar")
    resultados = {"encontrados": len(archivos), "procesados": 0, "errores": 0, "archivos": []}
    
    for archivo in archivos:
        try:
            if directorio.is_dir():
                ruta_relativa = archivo.relative_to(directorio)
                destino = salida / ruta_relativa.parent if len(ruta_relativa.parts) > 1 else salida
                destino.mkdir(parents=True, exist_ok=True)
                salida_archivo = destino / f"{archivo.stem}_autofit{archivo.suffix}"
            else:
                salida_archivo = salida / f"{archivo.stem}_autofit{archivo.suffix}"
            
            resultado = procesar_pptx(archivo, salida_archivo, silent=True)
            resultados["procesados"] += 1
            resultados["archivos"].append({
                "entrada": str(archivo),
                "salida": resultado,
                "nombre": archivo.name,
                "estado": "completado"
            })
            if not silent:
                print(f"✓ {archivo.name} → {salida_archivo.name}")
        except Exception as e:
            resultados["errores"] += 1
            resultados["archivos"].append({
                "entrada": str(archivo),
                "nombre": archivo.name,
                "estado": "error",
                "mensaje": str(e)
            })
            if not silent:
                print(f"✗ Error al procesar {archivo.name}: {str(e)}")
    
    tiempo = time.time() - inicio
    resultados["tiempo"] = tiempo
    
    if not silent:
        print(f"\n📊 Resumen: {resultados['procesados']}/{len(archivos)} archivos procesados ({resultados['errores']} errores) en {tiempo:.2f}s")
        print(f"📁 Archivos generados en: {salida}")
    
    return resultados 