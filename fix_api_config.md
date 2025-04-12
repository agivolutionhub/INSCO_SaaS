# Solución para el Problema de Configuración de APIs

## Problema Identificado

El sistema muestra un error de conexión con OpenAI porque no está encontrando las claves API:

```
❌ Error de conexión a OpenAI: The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable
```

Después de una revisión del código, hemos identificado que hay múltiples fuentes de claves API en el proyecto:

1. **archivo `.env`** en `backend/config/`
2. **archivos JSON de configuración**:
   - `openapi.json`: Contiene la clave principal de OpenAI
   - `sttapi.json`: Clave para servicios de transcripción
   - `ttsapi.json`: Clave para servicios de text-to-speech
   - `translator.json`: Configuración para el traductor

## Solución Implementada

Hemos realizado las siguientes mejoras:

1. **Mejora del script `setup_env.py`** - Ahora busca las claves API en:
   - Archivo `.env`
   - Archivos JSON de configuración
   - Ubicaciones alternativas del contenedor

2. **Actualización de `docker-compose.yml`** - Montaje explícito de todos los archivos de configuración:
   ```yaml
   volumes:
     - ./backend/config/.env:/app/.env
     - ./backend/config/openapi.json:/app/config/openapi.json
     - ./backend/config/sttapi.json:/app/config/sttapi.json
     - ./backend/config/ttsapi.json:/app/config/ttsapi.json
     - ./backend/config/translator.json:/app/config/translator.json
   ```

3. **Script de diagnóstico `fix_api_keys.sh`** - Herramienta para verificar y resolver problemas:
   - Comprueba la existencia y validez de los archivos de configuración
   - Verifica la correcta configuración de volúmenes en docker-compose.yml
   - Ofrece reparación automática de problemas comunes

## Pasos para Aplicar la Solución

1. **Actualizar archivos en el servidor**:
   ```bash
   git pull
   ```

2. **Ejecutar el script de diagnóstico**:
   ```bash
   ./fix_api_keys.sh
   ```
   - Sigue las instrucciones del script para reparar automáticamente los problemas

3. **Verificar la configuración de las APIs**:
   - Asegúrate de que el archivo `backend/config/.env` contiene:
     ```
     OPENAI_API_KEY=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
     OPENAI_ASSISTANT_ID=asst_mBShBt93TIVI0PKE7zsNO0eZ
     ```

4. **Reconstruir y levantar los contenedores**:
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

5. **Verificar los logs**:
   ```bash
   docker logs insco-app
   ```

## Solución Alternativa (si el problema persiste)

Si el problema persiste, una solución directa es modificar el código para que utilice explícitamente las claves de los archivos JSON de configuración:

1. Modificar el archivo `backend/services/video_translate_service.py`:
   ```python
   # Al principio del archivo, después de importar las librerías
   def load_api_key_from_json():
       json_path = Path(__file__).parent.parent / "config" / "openapi.json"
       if json_path.exists():
           with open(json_path, "r") as f:
               config = json.load(f)
               if "openai" in config and "api_key" in config["openai"]:
                   return config["openai"]["api_key"]
       return None
   
   # Sustituir esta línea:
   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   
   # Por esta:
   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or load_api_key_from_json())
   ```

## Información Adicional

La estructura actual del proyecto utiliza múltiples fuentes para las claves API, lo que puede causar confusión. Para proyectos futuros, recomendamos:

1. Centralizar todas las claves API en un solo lugar, preferiblemente variables de entorno
2. Documentar claramente la jerarquía de prioridad para la obtención de claves
3. Incluir validación y mensajes de error claros cuando falten claves API esenciales 