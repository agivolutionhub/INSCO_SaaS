import VideoTranslateTool from "../../components/video/VideoTranslateTool";
import ToolLayout from "../../components/layouts/ToolLayout";

const VideoTranslatePage = () => {
  const infoContent = (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="bg-primary-50 p-4 rounded-lg">
        <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">✓</span>
            <span>Hacer el contenido accesible para audiencias internacionales</span>
          </li>
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">✓</span>
            <span>Ampliar el alcance de materiales educativos y formativos</span>
          </li>
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">✓</span>
            <span>Facilitar la comunicación en equipos multinacionales</span>
          </li>
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">✓</span>
            <span>Conservar las voces originales con el nuevo idioma superpuesto</span>
          </li>
        </ul>
      </div>
      <div className="bg-primary-50 p-4 rounded-lg">
        <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">•</span>
            <span>Traducir materiales de formación para equipos internacionales</span>
          </li>
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">•</span>
            <span>Adaptar contenido promocional para mercados extranjeros</span>
          </li>
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">•</span>
            <span>Crear versiones de vídeos educativos en múltiples idiomas</span>
          </li>
          <li className="flex items-start">
            <span className="text-primary-500 mr-2">•</span>
            <span>Localizar presentaciones corporativas para filiales internacionales</span>
          </li>
        </ul>
      </div>
    </div>
  );

  return (
    <ToolLayout
      title="Traducir Vídeos"
      description="Herramienta para traducir el audio de vídeos a diferentes idiomas"
      toolName="Traducir"
      toolDescription="Esta herramienta traduce el audio de los vídeos a diferentes idiomas automáticamente."
      infoTitle="¿Por qué traducir vídeos?"
      infoContent={infoContent}
    >
      <VideoTranslateTool />
    </ToolLayout>
  );
};

export default VideoTranslatePage; 