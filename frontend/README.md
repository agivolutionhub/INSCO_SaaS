# INSCO Frontend

Interfaz de usuario para el proyecto INSCO de procesamiento de presentaciones PowerPoint.

## Tecnologías

- React 18
- TypeScript
- Tailwind CSS
- Vite
- React Router
- Axios

## Estructura

```
frontend/
├── public/          # Archivos estáticos
├── src/             # Código fuente
│   ├── components/  # Componentes reutilizables
│   ├── pages/       # Páginas/vistas
│   ├── services/    # Servicios de API
│   ├── hooks/       # Hooks personalizados
│   └── context/     # Contextos de React
├── tailwind.config.js # Configuración de Tailwind
└── vite.config.ts   # Configuración de Vite
```

## Instalación

```bash
# Instalar dependencias
npm install
```

## Ejecución

```bash
# Iniciar servidor de desarrollo
npm run dev
```

La aplicación estará disponible en http://localhost:5173

## Construcción para producción

```bash
# Generar build optimizado
npm run build
```

Los archivos se generarán en el directorio `dist/`.

## Comunicación con Backend

La aplicación se comunica con el backend a través de la API REST en http://localhost:8000. 
Vite está configurado para hacer proxy de las solicitudes a `/api` durante el desarrollo. 