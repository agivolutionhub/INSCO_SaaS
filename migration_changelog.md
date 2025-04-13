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
  - Solucionado problema de conflicto entre frontend y backend
  - Eliminado montaje del frontend en la aplicación backend
  - Corregidas rutas de API para funcionar correctamente con proxy
  - Actualizada configuración CORS para permitir solicitudes desde el dominio de producción
- **Archivos añadidos**:
  - scripts/diapos_autofit.py
- **Archivos modificados**:
  - main.py
- **Mejoras**:
  - Separación clara de responsabilidades entre frontend (puerto 3001) y backend (puerto 8088)
  - Resolución de problemas de enrutamiento en producción
  - Implementación modular de funcionalidades como scripts independientes
- **Resultado**: Primera herramienta (AutoFit) funcional en producción
- **Próximos pasos**: Continuar con la migración de funcionalidades adicionales siguiendo el patrón establecido 