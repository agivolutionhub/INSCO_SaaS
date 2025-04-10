import React from 'react';

const Dashboard = () => {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Panel Principal</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-lg font-semibold text-blue-700 mb-2">Herramientas para Diapositivas</h2>
          <p className="text-gray-600 mb-4">
            Procesa y optimiza presentaciones PowerPoint con nuestras herramientas especializadas.
          </p>
          <div className="mt-2 flex justify-end">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              Ver herramientas →
            </button>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-lg font-semibold text-blue-700 mb-2">Herramientas para Vídeo</h2>
          <p className="text-gray-600 mb-4">
            Convierte, recorta y ajusta archivos de vídeo para optimizar tu contenido multimedia.
          </p>
          <div className="mt-2 flex justify-end">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              Ver herramientas →
            </button>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-lg font-semibold text-blue-700 mb-2">Actividad Reciente</h2>
          <div className="space-y-3 mt-3">
            <div className="text-sm text-gray-600">
              <span className="text-gray-400">Hoy, 14:32</span> - Procesado autofit completado
            </div>
            <div className="text-sm text-gray-600">
              <span className="text-gray-400">Hoy, 10:15</span> - Conversión de vídeo completada
            </div>
            <div className="text-sm text-gray-600">
              <span className="text-gray-400">Ayer, 17:45</span> - Procesamiento por lotes completado
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 