# Informe Optimizado de Refactorización: Carpeta `/routes`

## 1. Estructura Actual

El análisis de la carpeta `/routes` muestra los siguientes archivos y sus características:

### 📊 Visión General de Rutas

<div align="center">

| 📄 Ruta | 📏 Líneas | 🔧 Endpoints | 🎯 Propósito |
|:------------|:---------:|:------------:|:-------------|
| **translate_pptx.py** | **631** | **6** | Traducción de presentaciones PowerPoint |
| **snapshot.py** | **311** | **4** | Generación de informes y capturas |
| **text_to_speech.py** | **301** | **3** | Conversión de texto a voz |
| **autofit.py** | **227** | **3** | Ajuste automático de contenido |
| **transcript.py** | **217** | **3** | Transcripción de audio a texto |
| **split_pptx.py** | **167** | **2** | División de presentaciones PowerPoint |

</div>

## 2. Inconsistencias Detectadas

- **Estructura de rutas variable**: Diferentes patrones para definir y registrar rutas.
- **Validación inconsistente**: Diversos enfoques para validar parámetros de entrada.
- **Respuestas heterogéneas**: Variación en estructura y códigos de estado en respuestas.
- **Manejo de archivos repetitivo**: Código duplicado para procesar archivos subidos.
- **Manejo de errores inconsistente**: Variación en captura y reporte de excepciones.
- **Importación dispersa de servicios**: Diferentes patrones para usar servicios.

## 3. Propuesta Optimizada de Refactorización

### 3.1. Enfoque Principal: Módulo `routes/utils`

```
routes/
├── __init__.py
├── utils/
│   ├── __init__.py
│   ├── request_utils.py    # Procesamiento de solicitudes
│   ├── response_utils.py   # Formatos de respuesta estándar
│   ├── file_utils.py       # Manejo de archivos subidos
│   └── validation.py       # Validación de parámetros
```

### 3.2. Estandarización de Respuestas

```python
# routes/utils/response_utils.py
from typing import Dict, Any, Optional, List, Union

def success_response(data: Any = None, message: Optional[str] = None, preserve_structure: bool = False) -> Dict[str, Any]:
    """
    Genera una respuesta de éxito estandarizada.
    
    Args:
        data: Datos a devolver
        message: Mensaje opcional
        preserve_structure: Si True, devuelve data directamente para mantener compatibilidad con frontend
    
    Returns:
        Respuesta formateada según corresponda
    """
    # Para endpoints consumidos por el frontend existente, mantener estructura original
    if preserve_structure:
        return data
        
    # Nuevo formato estandarizado para endpoints nuevos
    response = {"status": "success"}
    
    if message:
        response["message"] = message
        
    if data is not None:
        response["data"] = data
        
    return response

def error_response(message: str, status_code: int = 400, details: Optional[Any] = None) -> Dict[str, Any]:
    """Genera una respuesta de error estandarizada."""
    response = {"status": "error", "message": message}
    
    if details:
        response["details"] = details
    
    # La respuesta será devuelta con HTTPException(status_code=status_code, detail=response)
    return response
```

### 3.3. Simplificación de Validación

```python
# routes/utils/validation.py
from fastapi import HTTPException, UploadFile, Form, Query
from typing import List, Dict, Any, Optional
from pathlib import Path

def validate_file_upload(file: UploadFile, allowed_extensions: List[str]) -> None:
    """Valida un archivo subido."""
    if not file:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "No se proporcionó archivo"})
    
    ext = Path(file.filename).suffix.lower()[1:] if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail={"status": "error", "message": f"Formato no válido. Permitidos: {', '.join(allowed_extensions)}"}
        )
```

### 3.4. Plantilla para Nuevas Rutas

```python
# Plantilla para rutas
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional

from routes.utils.response_utils import success_response, error_response
from routes.utils.validation import validate_file_upload
from services import nombre_servicio

router = APIRouter(prefix="/api/nombre-recurso", tags=["nombre-tag"])

@router.post("/endpoint")
async def nombre_endpoint(
    param1: str = Form(...),
    param2: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Descripción del endpoint."""
    try:
        # Validación si es necesario
        if file:
            validate_file_upload(file, allowed_extensions=["ext1", "ext2"])
        
        # Lógica principal
        result = nombre_servicio.funcion_principal(param1, param2, file)
        
        # Respuesta estandarizada
        return success_response(
            data=result,
            message="Operación completada con éxito"
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger().error(f"Error en nombre_endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(f"Error interno del servidor: {str(e)}")
        )
```

### 3.5. Refactorización de Rutas Existentes

Ejemplo de refactorización para `autofit.py`:

```python
# routes/autofit.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import json, uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from routes.utils.response_utils import success_response, error_response
from routes.utils.validation import validate_file_upload
from routes.utils.file_utils import save_uploaded_file, get_storage_path

from services import autofit_service

router = APIRouter(prefix="/api/autofit", tags=["autofit"])

# Directorio de almacenamiento
STORAGE_DIR = get_storage_path("autofit")

@router.post("/upload-pptx")
async def upload_pptx_for_autofit(file: UploadFile = File(...)):
    """Sube un archivo PPTX para aplicar autofit."""
    try:
        validate_file_upload(file, allowed_extensions=["pptx"])
        
        file_id, file_path, original_name = save_uploaded_file(
            file, STORAGE_DIR
        )
        
        return success_response({
            "file_id": file_id,
            "filename": file.filename,
            "original_name": original_name
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=error_response(f"Error al procesar el archivo: {str(e)}")
        )

# Otros endpoints...
```

### 3.6. Estrategia de Compatibilidad con Frontend Existente

Para garantizar que la refactorización no rompa la integración actual:

1. **Rutas existentes**:
   - Usar `preserve_structure=True` en llamadas a `success_response()`
   - Ejemplo:
   ```python
   @router.post("/process")
   async def process_autofit(file_id: str = Form(...)):
       # Código existente...
       result = {
           "file_id": file_id,
           "download_url": download_url,
           "output_filename": output_filename
       }
       # Preservar estructura para compatibilidad con frontend
       return success_response(result, preserve_structure=True)
   ```

2. **Documentación de compatibilidad**:
   - Identificar y documentar todos los endpoints consumidos por el frontend
   - Comentar claramente en el código cuándo se usa modo de compatibilidad
   - Ejemplo:
   ```python
   # IMPORTANTE: Endpoint consumido por el frontend - mantener estructura de respuesta
   @router.post("/upload-pptx")
   ```

3. **Validación de integridad**:
   - Probar cada endpoint refactorizado contra el frontend existente
   - Verificar estructura de respuesta con herramientas como Postman antes de integrar

## 4. Implementación Pragmática por Fases

### Fase 1: Crear Módulo de Utilidades (1-2 días)
- Implementar `response_utils.py`
- Implementar `validation.py`
- Implementar `file_utils.py`

### Fase 2: Refactorizar Rutas Existentes (1-2 días por ruta)
- Empezar con rutas más simples (autofit.py, split_pptx.py)
- Estandarizar respuestas y validación
- Extraer lógica duplicada

### Fase 3: Mover Endpoints de `main.py` (1 día)
- Crear rutas específicas para endpoints directos en main.py
- Asegurar compatibilidad con clientes existentes

## 5. Comparación con Enfoque Original

| Área | Enfoque Original | Enfoque Optimizado |
|------|------------------|-------------------|
| **Complejidad** | Alta (múltiples capas, decoradores) | Media (utilidades simples) |
| **Compatibilidad** | Mantiene URLs pero cambia estructura | Mantiene URLs y estructura similar |
| **Tiempo** | 5-8 días | 3-5 días |
| **Riesgo** | Medio (cambios en manejo de respuestas) | Bajo (cambios progresivos) |
| **Mantenimiento** | Más estructura pero más complejo | Balance simplicidad/estructura |

## 6. Conclusión

Este enfoque optimizado proporciona una refactorización pragmática que mejora la consistencia y reduce la duplicación de código, manteniendo la compatibilidad con la API existente. Al crear un conjunto sencillo de utilidades comunes, se logra estandarizar aspectos clave como respuestas, validación y manejo de archivos sin introducir excesiva complejidad arquitectónica. 