import React from 'react';

const Dictionary = () => {
  const pdfUrl = '/docs/DiccionarioAFCO.pdf';

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Diccionario AFCO</h1>
        <p className="text-primary-700">
          Consulta todos los términos técnicos relacionados con la industria del cartón ondulado.
        </p>
      </div>
      
      <div className="bg-primary-50 rounded-xl shadow-md overflow-hidden flex flex-col mb-6">
        {/* Contenedor del PDF con altura fija */}
        <div style={{ height: "calc(100vh - 240px)" }} className="relative">
          <iframe
            id="pdf-viewer"
            src={pdfUrl}
            className="w-full h-full"
            title="Diccionario AFCO"
          ></iframe>
          <div className="absolute top-0 right-40 p-2 bg-gradient-to-b from-[#c29e74] to-[#a78559] rounded-b-lg text-white text-xs shadow-md">
            <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="hover:underline">
              Abrir en nueva pestaña
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dictionary; 