# Migración de Credenciales: De .env a auth_credentials.json

## Cambios Realizados

Hemos migrado las credenciales de OpenAI desde el archivo `.env` a un nuevo archivo JSON llamado `auth_credentials.json`. Este cambio resuelve problemas de despliegue en Docker y proporciona una manera más estructurada de gestionar las credenciales.

### Estructura del nuevo archivo

El nuevo archivo `backend/config/auth_credentials.json` tiene la siguiente estructura:

```json
{
    "openai": {
        "api_key": "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",
        "assistant_id": "asst_mBShBt93TIVI0PKE7zsNO0eZ"
    }
}
```

### Archivos modificados

1. **`setup_env.py`** - Actualizado para cargar credenciales desde `auth_credentials.json`.
2. **`main.py`** - Reemplazada la carga de dotenv por una función que lee del archivo JSON.
3. **`video_translate_service.py`** - Añadida función para cargar credenciales desde JSON.
4. **`translation_service.py`** - Eliminada la dependencia de dotenv.
5. **`Dockerfile`** - Eliminada la referencia al archivo `.env`.
6. **`docker-compose.yml`** - Actualizado para montar `auth_credentials.json` en lugar de `.env`.

## Ventajas de esta Solución

1. **Mejor compatibilidad con Docker** - Evita errores cuando el archivo `.env` no está presente.
2. **Estructura más clara** - El formato JSON es más estructurado y fácil de procesar.
3. **Consistencia con otros archivos de configuración** - Ahora todas las configuraciones están en formato JSON.
4. **Mayor flexibilidad** - Facilita la expansión para incluir más configuraciones en el futuro.

## Cómo Actualizar un Entorno Existente

1. **Crear el archivo JSON**:
   ```bash
   cp backend/config/.env backend/config/auth_credentials.json.template
   ```

2. **Editar el archivo** para convertirlo al formato JSON mostrado arriba.

3. **Actualizar el código**:
   ```bash
   git pull origin main
   ```

4. **Reiniciar los contenedores**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

## Nota Importante

El archivo `auth_credentials.json` contiene claves de API sensibles. Asegúrate de que:

1. No se incluya en los commits de Git (añádelo a `.gitignore`).
2. Se mantenga con permisos restringidos (`chmod 600 backend/config/auth_credentials.json`).
3. Se haga una copia de seguridad en un lugar seguro. 