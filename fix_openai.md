# Solución al Problema de Conexión OpenAI

## Descripción del Problema

Los logs muestran este error:
```
❌ Error de conexión a OpenAI: The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable
```

El problema es que las variables de entorno de OpenAI no están siendo correctamente cargadas durante el despliegue.

## Solución Implementada

He modificado la configuración de Docker para cargar las variables de entorno directamente desde `backend/config/.env`:

1. **docker-compose.yml**:
   - Actualizado para cargar el archivo de variables de entorno desde la ubicación correcta:
     ```yaml
     env_file:
       - ./backend/config/.env
     ```

2. **deploy.sh**:
   - Añadida verificación de la existencia del archivo `.env`
   - Añadido mensaje de error si no existe
   - Añadida verificación de la configuración de OpenAI al final del despliegue

## Cómo Verificar que Funciona

Para verificar que la configuración está correcta:

1. **Revisa el archivo de configuración**:
   ```bash
   cat backend/config/.env
   ```

   Debe contener:
   ```
   OPENAI_API_KEY=tu_api_key_aquí
   OPENAI_ASSISTANT_ID=tu_assistant_id_aquí
   ```

2. **Verifica que los contenedores puedan acceder a estas variables**:
   ```bash
   docker exec insco-app bash -c "echo \$OPENAI_API_KEY"
   ```

3. **Revisa los logs de la aplicación después del despliegue**:
   ```bash
   docker logs insco-app | grep "OpenAI API Key configurada"
   ```
   
   Deberías ver: `OpenAI API Key configurada: True`

## Si el Problema Persiste

Si el problema persiste, prueba estas alternativas:

1. **Solución 1: Copiar el archivo .env a la raíz**
   ```bash
   cp backend/config/.env ./.env
   ```
   Y luego modifica docker-compose.yml para usar:
   ```yaml
   env_file:
     - ./.env
   ```

2. **Solución 2: Definir las variables directamente en docker-compose.yml**
   Edita el archivo docker-compose.yml y añade las variables directamente:
   ```yaml
   environment:
     - OPENAI_API_KEY=tu_api_key_aquí
     - OPENAI_ASSISTANT_ID=tu_assistant_id_aquí
   ```

3. **Solución 3: Usar la API desde la interfaz web de OpenAI**
   Si ninguna de las soluciones anteriores funciona, puedes regenerar la API key desde:
   https://platform.openai.com/api-keys

## Información Adicional

- El código carga las variables de entorno usando `dotenv` en múltiples archivos
- El archivo principal `backend/main.py` intenta cargar desde `backend/config/.env`
- Los servicios individuales también cargan de esa ubicación

Para probar cualquier solución, reinicia los contenedores con:
```bash
docker-compose down
docker-compose up -d
``` 