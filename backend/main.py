from scripts.autofit import procesar_pptx, procesar_lote
from scripts.snapshot import extract_pptx_slides
from scripts.transcript import transcribe_video
from scripts.video_cut import cut_video, format_time_for_ffmpeg
from scripts.video_montage import generate_video_montage
from scripts.text_to_speech import generate_speech_from_file
from routes.translate_pptx import router as translate_pptx_router
from routes.split_pptx import router as split_pptx_router
from routes.snapshot import router as snapshot_router
from routes.autofit import router as autofit_router

# Incluir routers
app.include_router(translate_pptx_router)
app.include_router(split_pptx_router)
app.include_router(snapshot_router)
app.include_router(autofit_router)

@app.post("/api/upload-pptx-for-captures")
async def upload_pptx_for_captures(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        filename = file.filename
        original_name = Path(filename).stem
        file_extension = Path(filename).suffix
        
        if file_extension.lower() != '.pptx':
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PPTX")
        
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        file_location = UPLOAD_DIR / f"{file_id}{file_extension}"
        
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        if not file_location.exists():
            raise HTTPException(status_code=500, detail=f"Error: No se pudo guardar el archivo en {file_location}")
        
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": original_name,
            "file_path": str(file_location)
        }
    except Exception as e:
        print(f"Error en upload_pptx_for_captures: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la carga del archivo: {str(e)}")

@app.post("/api/process-captures")
async def process_captures(file_id: str = Form(...), original_name: str = Form(None)):
    try:
        files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
        
        if not files:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        file_path = files[0]
        
        capture_dir = CAPTURES_DIR / file_id
        capture_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            stats = extract_pptx_slides(
                pptx_path=file_path,
                output_dir=capture_dir,
                format="png",
                dpi=300
            )
            
            image_urls = []
            for img_path in sorted(capture_dir.glob("*.png")):
                rel_path = img_path.relative_to(BASE_DIR)
                image_urls.append(f"/{str(rel_path)}")
            
            return {
                "status": "success",
                "file_id": file_id,
                "original_name": original_name or Path(file_path).stem,
                "slides_count": stats["slides"],
                "image_urls": image_urls
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error al generar capturas: {str(e)}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}") 