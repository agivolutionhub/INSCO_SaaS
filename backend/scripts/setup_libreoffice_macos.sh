#!/bin/bash
# Script para configurar LibreOffice en macOS

echo "Configurando LibreOffice para trabajar con Python en macOS..."

# Comprobar si LibreOffice está instalado
if [ ! -d "/Applications/LibreOffice.app" ]; then
  echo "LibreOffice no está instalado en la ubicación estándar."
  echo "Descárgalo desde https://www.libreoffice.org/download/download/"
  exit 1
fi

echo "✅ LibreOffice encontrado en: /Applications/LibreOffice.app"

# Intentar encontrar pyuno
pyuno_paths=(
  "/Applications/LibreOffice.app/Contents/Resources/python/lib"
  "/Applications/LibreOffice.app/Contents/MacOS/python"
  "/Applications/LibreOffice.app/Contents/Resources/python"
)

PYUNO_FOUND=false

for path in "${pyuno_paths[@]}"; do
  if [ -d "$path" ]; then
    if [ -f "$path/pyuno.so" ] || [ -f "$path/pyuno.dylib" ]; then
      echo "✅ Encontrado pyuno en: $path"
      PYUNO_FOUND=true
      
      # Comprobar PYTHONPATH actual
      if [[ ":$PYTHONPATH:" != *":$path:"* ]]; then
        # Añadir a .zshrc o .bash_profile
        if [ -f "$HOME/.zshrc" ]; then
          echo "Añadiendo $path a PYTHONPATH en .zshrc"
          echo "export PYTHONPATH=\"$path:\$PYTHONPATH\"" >> "$HOME/.zshrc"
        elif [ -f "$HOME/.bash_profile" ]; then
          echo "Añadiendo $path a PYTHONPATH en .bash_profile"
          echo "export PYTHONPATH=\"$path:\$PYTHONPATH\"" >> "$HOME/.bash_profile"
        fi
      fi
    fi
  fi
done

if [ "$PYUNO_FOUND" = false ]; then
  echo "⚠️ No se encontró pyuno en las ubicaciones estándar."
  
  # Buscar recursivamente
  echo "Buscando pyuno.so recursivamente..."
  PYUNO_PATH=$(find /Applications/LibreOffice.app -name "pyuno.so" | head -n 1)
  
  if [ -n "$PYUNO_PATH" ]; then
    PYUNO_DIR=$(dirname "$PYUNO_PATH")
    echo "✅ Encontrado pyuno.so en: $PYUNO_DIR"
    
    # Añadir a .zshrc o .bash_profile
    if [ -f "$HOME/.zshrc" ]; then
      echo "Añadiendo $PYUNO_DIR a PYTHONPATH en .zshrc"
      echo "export PYTHONPATH=\"$PYUNO_DIR:\$PYTHONPATH\"" >> "$HOME/.zshrc"
    elif [ -f "$HOME/.bash_profile" ]; then
      echo "Añadiendo $PYUNO_DIR a PYTHONPATH en .bash_profile"
      echo "export PYTHONPATH=\"$PYUNO_DIR:\$PYTHONPATH\"" >> "$HOME/.bash_profile"
    fi
  else
    echo "❌ No se encontró pyuno.so en ninguna ubicación."
  fi
fi

# Añadir DYLD_LIBRARY_PATH para macOS
LIBREOFFICE_MACOS="/Applications/LibreOffice.app/Contents/MacOS"
if [ -d "$LIBREOFFICE_MACOS" ]; then
  if [ -f "$HOME/.zshrc" ]; then
    echo "Añadiendo DYLD_LIBRARY_PATH a .zshrc"
    echo "export DYLD_LIBRARY_PATH=\"$LIBREOFFICE_MACOS:\$DYLD_LIBRARY_PATH\"" >> "$HOME/.zshrc"
  elif [ -f "$HOME/.bash_profile" ]; then
    echo "Añadiendo DYLD_LIBRARY_PATH a .bash_profile"
    echo "export DYLD_LIBRARY_PATH=\"$LIBREOFFICE_MACOS:\$DYLD_LIBRARY_PATH\"" >> "$HOME/.bash_profile"
  fi
fi

# Crear symlink de Python de LibreOffice en el entorno virtual si existe
VENV_DIR="$(dirname "$(dirname "$0")")/venv"
if [ -d "$VENV_DIR" ]; then
  LIBREOFFICE_PYTHON="/Applications/LibreOffice.app/Contents/MacOS/python"
  if [ -f "$LIBREOFFICE_PYTHON" ]; then
    echo "Creando enlaces simbólicos en el entorno virtual..."
    
    # Buscar directorio site-packages
    SITE_PACKAGES=$(find "$VENV_DIR" -name "site-packages" | head -n 1)
    if [ -n "$SITE_PACKAGES" ]; then
      # Buscar pyuno.so y crear symlink
      PYUNO_PATH=$(find /Applications/LibreOffice.app -name "pyuno.so" | head -n 1)
      if [ -n "$PYUNO_PATH" ]; then
        echo "Creando symlink de pyuno.so en $SITE_PACKAGES"
        ln -sf "$PYUNO_PATH" "$SITE_PACKAGES/pyuno.so"
      fi
      
      # Buscar directorio de paquetes UNO
      UNO_PACKAGE_DIR=$(find /Applications/LibreOffice.app -name "com" -type d | grep -v "Components" | head -n 1)
      if [ -n "$UNO_PACKAGE_DIR" ]; then
        PARENT_DIR=$(dirname "$UNO_PACKAGE_DIR")
        echo "Creando symlink para paquetes UNO desde $PARENT_DIR"
        ln -sf "$PARENT_DIR/com" "$SITE_PACKAGES/com"
        if [ -d "$PARENT_DIR/uno" ]; then
          ln -sf "$PARENT_DIR/uno" "$SITE_PACKAGES/uno"
        fi
      fi
    fi
  fi
fi

echo ""
echo "✅ Configuración completada."
echo "Es necesario reiniciar la terminal o ejecutar 'source ~/.zshrc' (o 'source ~/.bash_profile')"
echo "para que los cambios surtan efecto."
echo ""
echo "Para probar si funciona correctamente, ejecuta:"
echo "python -c 'import uno; print(\"UNO importado correctamente\")'"
echo ""
echo "Si sigue fallando, prueba a ejecutar los scripts con el Python de LibreOffice:"
echo "$LIBREOFFICE_PYTHON backend/scripts/split_presentation.py <ruta_archivo.pptx> -s 10" 