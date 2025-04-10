# Informe Optimizado de Refactorización: Carpeta `/scripts`

## 1. Estructura Actual

El análisis de la carpeta `/scripts` muestra los siguientes archivos y sus características:

### 📊 Visión General de Scripts

<div align="center">

| 📄 Script | 📏 Líneas | 🔧 Funciones | 🎯 Propósito |
|:------------|:---------:|:------------:|:-------------|
| **video_montage.py** | **635** | **7** | Generación de montajes de video con imágenes y audio |
| **video_cut.py** | **194** | **5** | Corte de segmentos de vídeo usando FFmpeg |
| **setup_server.sh** | **156** | **4** | Configuración del servidor para la API en Ubuntu |
| **setup_libreoffice_macos.sh** | **121** | **0** | Configuración de LibreOffice en macOS |
| **text_to_speech.py** | **92** | **1** | Interfaz CLI para generación de voz a partir de texto |
| **translate_presentation.py** | **79** | **1** | Traducción de presentaciones PowerPoint |
| **autofit.py** | **71** | **2** | Ajuste automático de texto en presentaciones PowerPoint |
| **transcript.py** | **63** | **1** | Interfaz CLI para transcripción de audio a texto |
| **snapshot.py** | **54** | **2** | Generación de imágenes a partir de diapositivas PPTX |

</div>

## 2. Inconsistencias Detectadas

- **Estructura CLI variable**: Diferentes patrones y estilos para scripts de línea de comandos.
- **Configuración inconsistente de logging**: Algunos usan logging, otros print directo.
- **Manejo inconsistente de argumentos**: Diferentes enfoques para definir y procesar parámetros.
- **Manejo de errores heterogéneo**: Variación en captura y reporte de errores.
- **Importación inconsistente de servicios**: Diferentes técnicas para importar módulos principales.
- **Diferentes niveles de interactividad**: Mezcla de scripts automatizados e interactivos.

## 3. Propuesta Optimizada de Refactorización

### 3.1. Enfoque Principal: Scripts Autocontenidos

Establecer un patrón para scripts independientes que sean autocontenidos pero con estructura estandarizada:

```
scripts/
├── autofit.py
├── snapshot.py
├── split_pptx.py         # Nuevo script
├── text_to_speech.py
├── transcript.py
└── translate_presentation.py
```

Cada script seguirá una estructura interna común, pero sin crear dependencias entre ellos ni módulos compartidos adicionales.

### 3.2. Estandarización de Estructura Interna

Establecer pautas para la estructura interna de cada script:

1. **Cabecera con docstring informativo**
2. **Configuración de logging consistente**
3. **Manejo de argumentos estandarizado**
4. **Funciones de utilidad internas con prefijo _**
5. **Manejo de errores centralizado**

### 3.3. Plantilla para Scripts CLI de Python

```python
#!/usr/bin/env python3
"""
Descripción del script.

Detalles sobre la funcionalidad y uso.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Ajustar path para importar servicios
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar servicios
from services import nombre_servicio

# Configurar logger
logger = logging.getLogger("nombre-script")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Descripción del script...")
    parser.add_argument("input", help="Descripción del input")
    parser.add_argument("-o", "--output", help="Descripción del output")
    
    # Añadir argumentos específicos
    parser.add_argument("--argumento", "-a", help="Descripción del argumento")
    
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        logger.info(f"Procesando archivo: {args.input}")
        
        # Lógica principal
        resultado = nombre_servicio.funcion_principal(args.input, args.output, args.argumento)
        
        logger.info(f"Proceso completado. Resultado: {resultado}")
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### 3.4. Plantilla para Scripts Shell

```bash
#!/bin/bash
# Título: Nombre del script
# Descripción: Breve descripción del propósito

# Colores para la salida
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

# Funciones de utilidad
log_info() {
    echo -e "[INFO] $1"
}

log_success() {
    echo -e "${GREEN}[ÉXITO]${RESET} $1"
}

log_warning() {
    echo -e "${YELLOW}[AVISO]${RESET} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $1"
    exit 1
}

# Verificar dependencias
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        log_warning "$1 no está instalado"
        return 1
    else
        log_info "$1 está instalado: $(command -v "$1")"
        return 0
    fi
}

# Función principal
main() {
    log_info "Iniciando script..."
    
    # Verificar dependencias
    check_dependency "comando1" || log_error "Falta comando1, por favor instálalo"
    
    # Lógica principal
    # ...
    
    log_success "Script completado"
}

# Ejecutar función principal
main "$@"
```

## 4. Ejemplo de Aplicación: Refactorización de `split_pptx.py`

### Implementación
```python
#!/usr/bin/env python3
"""
Script para dividir presentaciones PowerPoint en archivos más pequeños.

Permite fragmentar presentaciones PPTX grandes en múltiples archivos con un número
específico de diapositivas por archivo.
"""
import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

# Ajustar path para importar servicios
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar servicio
from services.pptx_service import split_presentation

# Configurar logger
logger = logging.getLogger("split-pptx-cli")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def parse_args():
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Divide presentaciones PPTX en archivos más pequeños")
    parser.add_argument("input", type=Path, help="Archivo PPTX a dividir")
    parser.add_argument("-o", "--output-dir", type=Path, help="Directorio para guardar los archivos resultantes")
    parser.add_argument("-s", "--slides", type=int, default=20, 
                      help="Número de diapositivas por archivo (default: 20)")
    return parser.parse_args()

def main():
    """Función principal del script."""
    try:
        args = parse_args()
        
        input_file = args.input
        
        # Validar archivo de entrada
        if not input_file.exists():
            logger.error(f"Error: No se encuentra el archivo {input_file}")
            return 1
        
        if input_file.suffix.lower() != '.pptx':
            logger.error(f"Error: El archivo debe ser PPTX: {input_file}")
            return 1
        
        output_dir = args.output_dir or input_file.parent / f"{input_file.stem}_partes"
        slides_per_chunk = args.slides
        
        logger.info(f"Dividiendo presentación: {input_file}")
        logger.info(f"Diapositivas por archivo: {slides_per_chunk}")
        logger.info(f"Directorio de salida: {output_dir}")
        
        # Dividir la presentación
        output_files = split_presentation(
            input_file=str(input_file),
            output_dir=str(output_dir),
            slides_per_chunk=slides_per_chunk
        )
        
        # Mostrar resultados
        logger.info("\nArchivos generados:")
        for i, file_path in enumerate(output_files, 1):
            file = Path(file_path)
            file_size = file.stat().st_size / (1024 * 1024)  # Tamaño en MB
            logger.info(f"  {i}. {file.name} ({file_size:.1f} MB)")
        
        logger.info(f"\nProceso completado. Se generaron {len(output_files)} archivos en {output_dir}")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### 4.1 Consideraciones de compatibilidad en scripts CLI

Cuando un script pueda ser invocado desde otros módulos o el frontend:

1. **Mantener firmas de función**:
   ```python
   # Versión original - mantener para compatibilidad
   def procesar_pptx(file_path, output_path=None):
       # Mantener la misma firma y valor de retorno
       # Puede llamar internamente a una versión mejorada
       return _procesar_pptx_impl(file_path, output_path)
   
   # Nueva implementación interna
   def _procesar_pptx_impl(file_path, output_path=None, **opciones_nuevas):
       # Implementación mejorada
   ```

2. **Funciones de utilidad como funciones privadas**:
   - Utilizar prefijo `_` para funciones internas no expuestas
   - Evitar cambiar interfaces públicas utilizadas por otros módulos

## 5. Implementación Pragmática por Fases

### Fase 1: Definir Estándares (1/2 día)
- Documentar la estructura estándar para scripts Python
- Documentar la estructura estándar para scripts Shell
- Crear plantillas de referencia

### Fase 2: Refactorizar Scripts Python (1 día por script)
- Comenzar con scripts más pequeños y usados con frecuencia
- Aplicar plantilla estándar
- Mejorar manejo de argumentos y documentación

### Fase 3: Refactorizar Scripts Shell (1 día por script)
- Estandarizar formato y funciones de utilidad
- Mejorar mensajes y manejo de errores

## 6. Comparación con Enfoque Original

| Área | Enfoque Original | Enfoque Optimizado |
|------|------------------|-------------------|
| **Complejidad** | Alta (clase base, jerarquías) | Mínima (scripts independientes) |
| **Compatibilidad** | Cambios profundos en interfaz | Mantiene interfaz CLI original |
| **Tiempo** | 5-7 días | 2-3 días |
| **Riesgo** | Alto (reescritura significativa) | Muy bajo (mejoras incrementales) |
| **Mantenimiento** | Más complejo inicialmente | Máxima simplicidad |

## 7. Conclusión

Este enfoque optimizado permite mejorar la calidad y consistencia de los scripts CLI sin introducir complejidad ni dependencias innecesarias. Al establecer un patrón consistente pero manteniendo cada script como una unidad autocontenida, se logra una mejor mantenibilidad y se evitan problemas de acoplamiento.

La propuesta prioriza la simplicidad y funcionalidad directa, permitiendo que cada script sea comprensible y mantenible de forma individual, facilitando también que nuevos desarrolladores puedan entender y modificar los scripts sin necesidad de comprender un sistema de utilidades compartidas. 