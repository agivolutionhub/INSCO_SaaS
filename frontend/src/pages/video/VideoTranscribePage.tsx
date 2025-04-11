import VideoTranscribeTool from "../../components/video/VideoTranscribeTool";
import { Helmet } from "react-helmet";

const VideoTranscribePage = () => {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Helmet>
        <title>Transcribir Vídeo | INSCO</title>
        <meta name="description" content="Herramienta para transcribir audio de vídeos a texto" />
      </Helmet>
      
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta Transcribir</h1>
        <p className="text-primary-700">
          Esta herramienta convierte el audio de vídeos y archivos de audio en texto escrito.
        </p>
      </div>
      
      <VideoTranscribeTool />
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué transcribir vídeos?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Hacer que el contenido sea accesible para personas con discapacidad auditiva</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Facilitar la búsqueda de contenido específico en vídeos largos</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Crear subtítulos y closed captions para vídeos</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Convertir entrevistas y presentaciones a formato de texto</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Generar subtítulos para vídeos educativos y corporativos</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Crear transcripciones de entrevistas para análisis</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Documentar reuniones y conferencias grabadas</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Mejorar la SEO y accesibilidad de contenido multimedia</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoTranscribePage; 