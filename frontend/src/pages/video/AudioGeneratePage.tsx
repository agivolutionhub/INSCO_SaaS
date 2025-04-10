import React from 'react';
import AudioGenerateTool from "../../components/video/AudioGenerateTool";
import { Helmet } from "react-helmet";

const AudioGeneratePage = () => {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Helmet>
        <title>Generar Audio | INSCO</title>
        <meta name="description" content="Herramienta para generar audio a partir de texto" />
      </Helmet>
      
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta Generar</h1>
        <p className="text-primary-700">
          Esta herramienta convierte archivos de texto (transcripción) en audio con voces naturales.
        </p>
      </div>
      
      <AudioGenerateTool />
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué generar audio a partir de texto?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Crear narraciones profesionales para vídeos y presentaciones</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Convertir documentos y artículos en formato de audio</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Generar locuciones para contenido educativo y corporativo</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Producir audio accesible para personas con discapacidad visual</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Creación de audiolibros y podcasts</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Locuciones para vídeos explicativos y tutoriales</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Audio para aplicaciones móviles y asistentes virtuales</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Contenido sonoro para presentaciones y materiales formativos</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AudioGeneratePage; 