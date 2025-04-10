import React from 'react';
import VideoCutTool from "../../components/video/VideoCutTool";
import { Helmet } from "react-helmet";

const VideoCutPage = () => {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Helmet>
        <title>Cortar Vídeos | INSCO</title>
        <meta name="description" content="Herramienta para cortar y editar segmentos de vídeos" />
      </Helmet>
      
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta Cortar</h1>
        <p className="text-primary-700">
          Esta herramienta permite cortar y extraer segmentos específicos de archivos de vídeo.
        </p>
      </div>
      
      <VideoCutTool />
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué cortar vídeos?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Eliminar secciones innecesarias de los vídeos</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Extraer segmentos específicos para usar en otros proyectos</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Reducir la duración de los vídeos para compartirlos más fácilmente</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Crear clips cortos a partir de grabaciones extensas</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Extraer fragmentos relevantes de conferencias o presentaciones</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Eliminar momentos de silencio o pausas en grabaciones</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Crear clips cortos para redes sociales o plataformas de streaming</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Seleccionar las mejores partes de una grabación más larga</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoCutPage; 