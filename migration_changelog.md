# Registro de Migración de INSCO Backend

Este documento registra el proceso de migración desde el backend original hacia la nueva versión, implementando componentes de forma progresiva.

## Estado Inicial

- **Backend mínimo** con solo `main.py` y `requirements.txt`
- Endpoints básicos: `/api/root` y `/health`
- Sin dependencias de OpenAI ni otras API externas

## Plan de Migración

Seguiremos este orden para añadir componentes:

1. Estructura básica de directorios
2. Scripts de utilidades y configuración
3. Modelos de datos
4. Servicios principales
5. Routers y endpoints

Cada fase será documentada con su fecha, cambios realizados y resultado.

## Fases de Migración

### Fase 0: Backend Mínimo (Actual)

- **Fecha**: 12-04-2025
- **Estado**: Completo
- **Cambios**:
  - Backend mínimo funcional con FastAPI
  - Endpoints básicos implementados
  - Scripts de despliegue adaptados
- **Resultado**: Backend funcionando correctamente en local y en producción

### Fase 1: Estructura básica y configuración de entorno

- **Fecha**: 12-04-2025
- **Estado**: Completo
- **Cambios**:
  - Creada estructura base de directorios (routes, services, scripts)
  - Migrado setup_env.py para cargar credenciales de OpenAI
  - Creado script verify_dependencies.sh básico
  - Actualizado main.py para integrar setup_env.py
- **Archivos migrados**:
  - scripts/setup_env.py
  - scripts/verify_dependencies.sh
- **Simplificaciones**:
  - Eliminadas configuraciones de APIs adicionales (STT, TTS)
  - Reducido a solo gestión de credenciales básicas de OpenAI
- **Resultado**: Backend con estructura básica y capacidad de cargar configuración

### Fase 2: Consolidación de configuración y actualización de dependencias

- **Fecha**: 12-04-2025
- **Estado**: Completo
- **Cambios**:
  - Consolidados todos los archivos JSON de configuración en un solo archivo auth_credentials.json
  - Unificados parámetros para diferentes modelos (chat, transcripción, TTS, traducción)
  - Actualizado requirements.txt con todas las dependencias del proyecto original
  - Configurado servicio systemd para ejecución persistente
- **Archivos actualizados**:
  - config/auth_credentials.json
  - requirements.txt
- **Archivos añadidos**:
  - insco.service
  - start_background.sh
  - setup_service.sh
- **Mejoras**:
  - Simplificación de la gestión de credenciales
  - Preparación para migración de funcionalidades avanzadas
  - Soporte para ejecución como servicio del sistema
- **Próximos pasos**: Migrar servicios básicos y utilidades 

### Fase 3: Integración y corrección de AutoFit

- **Fecha**: 13-04-2025
- **Estado**: Completo
- **Cambios**:
  - Implementada herramienta AutoFit como script independiente consolidado
  - **Corregido problema crítico de conflicto entre frontend y backend**
  - Eliminado montaje del frontend en la aplicación backend
  - Corregidas rutas de API para funcionar correctamente con proxy
  - Actualizada configuración CORS para permitir solicitudes desde el dominio de producción
- **Archivos añadidos**:
  - scripts/diapos_autofit.py
- **Archivos modificados**:
  - main.py
- **Problema crítico resuelto**:
  - Se identificó que el backend estaba intentando servir el frontend desde la misma ruta raíz (`/`), lo que provocaba conflictos con las rutas API
  - Las solicitudes OPTIONS para CORS fallaban con errores 400 Bad Request
  - La estructura de rutas duplicada (`/api/api/...`) impedía el funcionamiento correcto
  - La separación incompleta entre frontend y backend bloqueaba toda la implementación de herramientas
- **Solución implementada**:
  - Eliminación del montaje del frontend en el backend
  - Corrección de las rutas para adaptarse al patrón de proxy (`/root` en lugar de `/api/root`)
  - Configuración correcta de CORS con el dominio de producción
  - Definición clara de responsabilidades: frontend en puerto 3001, backend en puerto 8088
- **Resultado verificado en logs**:
  - Solicitudes OPTIONS ahora reciben respuesta 200 OK
  - Solicitudes POST funcionan correctamente
  - Procesamiento completo de diapositivas exitoso
  - Descarga de archivos procesados funcionando sin errores
- **Mejoras**:
  - Separación clara de responsabilidades entre frontend (puerto 3001) y backend (puerto 8088)
  - Resolución de problemas de enrutamiento en producción
  - Implementación modular de funcionalidades como scripts independientes
  - Establecimiento de un patrón para todas las futuras implementaciones
- **Resultado**: Primera herramienta (AutoFit) completamente funcional en producción
- **Conclusión**: Este cambio es fundamental y establece las bases para todo el desarrollo futuro del proyecto
- **Próximos pasos**: Continuar con la migración de funcionalidades adicionales siguiendo el patrón establecido 

### Fase 4: Integración de herramienta de división de presentaciones (PPTX Split)

- **Fecha**: 13-04-2025
- **Estado**: Completo
- **Cambios**:
  - Unificación de código de división de PPTX en un solo script independiente
  - Consolidación de funcionalidades CLI y API en una sola herramienta
  - Integración con el sistema principal a través del router existente
  - Mantenimiento del patrón establecido en la fase anterior
- **Archivos añadidos**:
  - scripts/diapos_split.py
- **Archivos modificados**:
  - main.py
- **Código migrado desde**:
  - backend_OLD/services/pptx_service.py
  - backend_OLD/scripts/split_pptx.py
  - backend_OLD/routes/split_pptx.py
- **Mejoras**:
  - Simplificación mediante unificación de código relacionado en un solo archivo
  - Implementación de interfaz dual (CLI/API) para facilitar pruebas y uso
  - Mantenimiento del patrón de integración limpio con la API principal
  - Sistema de almacenamiento de archivos consistente
- **Resultado**: Segunda herramienta (PPTX Split) completamente funcional e integrada
- **Próximos pasos**: Continuar con la migración de funcionalidades adicionales (herramientas de video y audio) 

### Fase 5: Solución de problemas de enrutamiento frontend-backend (Iteración 1)

- **Fecha**: 14-04-2025
- **Estado**: Implementado (con ajustes pendientes)
- **Cambios**:
  - Implementación de endpoints de respaldo para rutas de frontend
  - Mejora de la compatibilidad entre frontend SPA y backend API
  - Solución sin necesidad de modificar la configuración del servidor web
- **Archivos modificados**:
  - backend/main.py
- **Problema resuelto**:
  - Se identificó que las rutas frontend como `/slides/split` estaban siendo interceptadas por el backend
  - El error 404 (Not Found) aparecía al intentar cargar la página de herramientas
  - El enrutamiento de React Router fallaba porque el backend no sabía manejar estas rutas
  - Las peticiones GET a rutas de frontend no llegaban a cargar el HTML principal
- **Solución implementada**:
  - Creación de un endpoint catch-all para rutas de frontend (`/slides/{rest_of_path:path}`)
  - Respuesta JSON indicando que estas rutas deben ser manejadas por el frontend
  - Patrón que puede extenderse a otras secciones de herramientas (`/video/*`, `/docs/*`, etc.)
- **Ventajas**:
  - Solución inmediata sin necesidad de modificar la configuración de nginx
  - Compatibilidad entre aplicación SPA de React y backend FastAPI
  - Estructura fácilmente ampliable para futuras secciones
- **Alternativa ideal para el futuro**:
  - Configuración de nginx para servir frontend en rutas no-API
  - Proxy inverso solo para rutas `/api/*` hacia el backend
- **Resultado**: Implementación inicial, pero con problemas persistentes en producción
- **Próximos pasos**: Refinar la solución para el entorno de producción

### Fase 5: Solución mejorada de problemas de enrutamiento frontend-backend (Iteración 2)

- **Fecha**: 14-04-2025
- **Estado**: Completo
- **Cambios**:
  - Rediseño de la solución anterior para utilizar redirecciones HTTP en lugar de respuestas JSON
  - Implementación de RedirectResponse para enviar al usuario a la raíz de la aplicación
- **Archivos modificados**:
  - backend/main.py
- **Problema persistente resuelto**:
  - La primera implementación devolvía un objeto JSON, pero no redirigía al usuario
  - El navegador seguía mostrando errores 404 al intentar acceder a rutas del frontend
  - Las respuestas JSON no eran procesadas por el navegador para cargar el frontend
- **Nueva solución implementada**:
  - Uso de `RedirectResponse` de FastAPI para redirigir al usuario a la URL principal
  - Redirección a `https://tools.inscoia.es/` donde ya está cargado el frontend
  - Una vez cargado el frontend, React Router puede manejar correctamente la navegación
- **Ventajas de la redirección**:
  - Funciona independientemente de la estructura de archivos del frontend
  - No requiere conocer la ubicación exacta del archivo index.html
  - Es una solución estándar web que todos los navegadores manejan correctamente
  - No depende de permisos de archivos o rutas específicas
- **Resultado esperado**: Navegación transparente para el usuario final
- **Próximos pasos**: Monitorizar el comportamiento en producción y extender el patrón a otras secciones si es necesario 