# Solución para la Advertencia de Pydantic

## Problema Identificado

En los logs de despliegue aparece esta advertencia:

```
/usr/local/lib/python3.10/site-packages/pydantic/_internal/_fields.py:127: UserWarning: Field "model_name" has conflict with protected namespace "model_".

You may be able to resolve this warning by setting `model_config['protected_namespaces'] = ()`.
  warnings.warn(
```

Esta advertencia se produce porque hay un conflicto entre el nombre del campo `model_name` utilizado en varios endpoints del API y el espacio de nombres protegido `model_` de Pydantic.

## Solución Implementada

He aplicado la solución recomendada en la advertencia, que es configurar `model_config['protected_namespaces'] = ()` para desactivar la protección de espacios de nombres en Pydantic.

He realizado las siguientes modificaciones:

1. **En `backend/main.py`**:
   ```python
   from pydantic.config import ConfigDict
   
   # Configuración global para Pydantic
   model_config = ConfigDict(protected_namespaces=())
   ```

2. **En `backend/routes/transcript.py`**:
   ```python
   from pydantic.config import ConfigDict
   
   # Configuración global para Pydantic para evitar advertencias con model_name
   model_config = ConfigDict(protected_namespaces=())
   ```

3. **En `backend/routes/video_translate.py`**:
   ```python
   # Dentro de la clase TranslationRequest
   class TranslationRequest(BaseModel):
       text: str
       target_language: str = "English"
       original_language: Optional[str] = None
       
       # Configurar para evitar advertencias con namespaces protegidos
       model_config = ConfigDict(protected_namespaces=())
   ```

## Explicación Técnica

Pydantic, la biblioteca utilizada por FastAPI para validación de datos, tiene espacios de nombres protegidos que están reservados para uso interno. Por defecto, `model_` es uno de estos espacios de nombres protegidos.

Cuando creamos un campo llamado `model_name` en un modelo o lo usamos como parámetro en un endpoint de FastAPI, se genera una advertencia porque Pydantic detecta un posible conflicto con su espacio de nombres interno `model_`.

La solución consiste en configurar `model_config['protected_namespaces'] = ()` para desactivar esta protección, lo que permite usar nombres de campos que empiecen con `model_` sin generar advertencias.

## Alternativas Consideradas

Otras posibles soluciones incluían:

1. **Renombrar el parámetro**: Cambiar `model_name` por otro nombre como `ai_model` o `transcription_model`, pero esto habría requerido cambios en más lugares, incluyendo el frontend.

2. **Usar alias en Pydantic**: Definir un alias para el campo, pero esto es más complejo y requiere cambios en la serialización/deserialización.

La solución implementada es la más simple y directa, y está recomendada por Pydantic en la propia advertencia.

## Actualización del Sistema

Para aplicar estos cambios:

1. Actualiza el código con `git pull`
2. Reconstruye los contenedores Docker:
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

Después de aplicar estos cambios, la advertencia no debería aparecer más en los logs. 