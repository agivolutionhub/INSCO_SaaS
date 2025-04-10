import React, { useEffect } from 'react';

// Componente para un único tutorial con vídeo
const TutorialVideo = ({ title, videoUrl, videoTitle }: { title: string; videoUrl: string; videoTitle: string }) => (
  <div className="mb-10">
    <h3 className="text-lg font-medium text-primary-700 mb-4 text-center">{title}</h3>
    <div className="rounded-xl overflow-hidden shadow-lg max-w-4xl mx-auto bg-black">
      <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0 }}>
        <iframe
          src={videoUrl}
          frameBorder="0"
          allow="autoplay; fullscreen; picture-in-picture"
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
          title={videoTitle}
        ></iframe>
      </div>
    </div>
  </div>
);

const Tutorials = () => {
  useEffect(() => {
    // Cargar el script de Vimeo
    const script = document.createElement('script');
    script.src = 'https://player.vimeo.com/api/player.js';
    script.async = true;
    document.body.appendChild(script);

    return () => {
      try {
        document.body.removeChild(script);
      } catch (error) {
        console.log('Error al eliminar el script:', error);
      }
    };
  }, []);

  // Datos de tutoriales
  const tutorialVideos = [
    {
      id: 1,
      title: "Movidas Adicionales",
      videoUrl: "https://player.vimeo.com/video/1072451543?badge=0&autopause=0&player_id=0&app_id=58479&title=1&byline=0&portrait=0",
      videoTitle: "Movidas Adicionales"
    },
    {
      id: 2,
      title: "Ambigüedad Términos",
      videoUrl: "https://player.vimeo.com/video/1072617788?badge=0&autopause=0&player_id=0&app_id=58479&title=1&byline=0&portrait=0",
      videoTitle: "ambigüedad términos"
    }
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Tutoriales</h1>
        <p className="text-primary-700">
          Vídeos explicativos sobre cómo utilizar las diferentes herramientas de la plataforma.
        </p>
      </div>
      
      <div className="bg-primary-50 rounded-xl shadow-md overflow-hidden mb-8">
        <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
          <h1 className="text-xl font-bold text-white text-center">Cómo usar la interfaz</h1>
        </div>
        
        <div className="p-6">
          <p className="text-gray-600 mb-6 text-center">
            Estos tutoriales te ayudarán a entender cómo funciona cada herramienta de la plataforma INSCO.
          </p>
          
          {/* Una columna para los tutoriales */}
          <div className="space-y-8 mb-8">
            {tutorialVideos.map(tutorial => (
              <TutorialVideo 
                key={tutorial.id}
                title={tutorial.title}
                videoUrl={tutorial.videoUrl}
                videoTitle={tutorial.videoTitle}
              />
            ))}
          </div>
          
          {/* Espacio para añadir más tutoriales en el futuro */}
          <div className="border-t border-gray-200 pt-6 mt-8">
            <h3 className="text-md font-medium text-primary-700 mb-2 text-center">Próximamente más tutoriales</h3>
            <p className="text-gray-600 text-center">
              Estamos preparando más tutoriales para ayudarte a sacar el máximo provecho de las herramientas.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Tutorials; 