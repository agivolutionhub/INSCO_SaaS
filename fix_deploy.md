# Solución de Problemas de Despliegue - INSCO

## Cambios realizados

1. **docker-compose.yml**:
   - Corregida la duplicación de la sección nginx al final del archivo

2. **nginx/conf.d/default.conf**:
   - Añadidos endpoints de health check para verificar el estado del backend
   - Corregida la ruta de los archivos estáticos para apuntar a `/var/www/html/` en lugar de `/app/static/`

3. **deploy.sh**:
   - Añadidos pasos para copiar los archivos del frontend a la carpeta de nginx
   - Añadido reinicio de nginx después de la copia

4. **backend/scripts/verify_dependencies.sh**:
   - Eliminadas las comprobaciones de LibreOffice y unoconv, ya que no se utilizan más

5. **test_deploy.sh**:
   - Creado nuevo script para diagnosticar problemas en el despliegue

## Pasos para solucionar el problema

1. **Actualizar los archivos locales**:
   - Asegúrate de que todos los cambios estén guardados y commiteados en tu repositorio local

2. **Actualizar el servidor**:
   - Sube los cambios al servidor: `git push`
   - Conéctate al servidor vía SSH
   - Navega al directorio del proyecto: `cd /ruta/al/proyecto`
   - Actualiza el código: `git pull`

3. **Eliminar contenedores antiguos**:
   ```bash
   docker-compose down
   ```

4. **Reconstruir y levantar los contenedores**:
   ```bash
   ./deploy.sh
   ```

5. **Diagnosticar problemas (si persisten)**:
   ```bash
   ./test_deploy.sh
   ```

## Errores comunes y soluciones

1. **Frontend no carga**:
   - Verifica que los archivos estáticos estén correctamente copiados:
     ```bash
     docker exec insco-nginx ls -la /var/www/html/
     ```
   - Si no hay archivos, cópialos manualmente:
     ```bash
     docker cp insco-app:/app/static/. nginx/www/
     docker-compose restart nginx
     ```

2. **Backend no responde**:
   - Verifica los logs:
     ```bash
     docker logs insco-app
     ```
   - Revisa que el contenedor esté funcionando:
     ```bash
     docker ps | grep insco-app
     ```

3. **Problemas de red**:
   - Verifica que nginx pueda conectarse al backend:
     ```bash
     docker exec insco-nginx curl -v http://insco-app:8088/health
     ```
   - Verifica que los puertos estén abiertos:
     ```bash
     netstat -tulpn | grep -E '80|443|8088'
     ```

4. **Problemas de certificados SSL**:
   - Verifica que los certificados existan:
     ```bash
     ls -la nginx/ssl/
     ```
   - Regenera los certificados si es necesario (usando el script deploy.sh)

## Configuración del entorno de producción

Para un entorno de producción más robusto, considera:

1. **Certificados SSL válidos**:
   - Usar Let's Encrypt para obtener certificados válidos
   - Seguir las instrucciones al final del script deploy.sh

2. **Seguridad**:
   - Configurar un firewall (UFW) para limitar el acceso
   - Habilitar solo los puertos necesarios (80, 443, 22)

3. **Monitoreo**:
   - Configurar alertas para caídas del servicio
   - Implementar logs centralizados para facilitar el diagnóstico

Si el problema persiste después de aplicar estos cambios, por favor proporciona los nuevos logs para un análisis más detallado. 