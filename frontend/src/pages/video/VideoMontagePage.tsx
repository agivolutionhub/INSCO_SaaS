import VideoMontageTool from "../../components/video/VideoMontageTool";
import { Helmet } from "react-helmet";

const VideoMontagePage = () => {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Helmet>
        <title>Montaje de Vídeos | INSCO</title>
        <meta name="description" content="Herramienta para crear montajes combinando múltiples vídeos" />
      </Helmet>
      
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta Montaje</h1>
        <p className="text-primary-700">
          Esta herramienta permite combinar varios vídeos para crear un montaje unificado.
        </p>
      </div>
      
      <VideoMontageTool />
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué crear montajes de vídeo?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Combinar múltiples clips en una sola presentación coherente</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Crear secuencias lógicas a partir de grabaciones separadas</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Organizar material audiovisual de forma narrativa</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Reducir la necesidad de grabar todo el contenido en una sola toma</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Crear recopilaciones de momentos destacados de eventos</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Combinar diferentes entrevistas en un solo vídeo</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Generar contenido para redes sociales a partir de múltiples clips</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Crear presentaciones multimedia con vídeos de diferentes fuentes</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoMontagePage;