import React, { useState } from 'react';

const BatchProcessTool = () => {
  const [selectedDirectory, setSelectedDirectory] = useState<string>('');
  const [availableFolders, setAvailableFolders] = useState([
    'WEBINARS',
    'CURSOS',
    'EJEMPLOS'
  ]);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Procesamiento por Lotes</h1>
      <p className="text-gray-600 mb-6">
        Procesa múltiples presentaciones PowerPoint en un único paso.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-lg font-semibold text-blue-700 mb-4">Directorios disponibles</h2>
          
          <div className="space-y-2 mb-4">
            {availableFolders.map((folder) => (
              <div 
                key={folder}
                className={`p-3 rounded-md cursor-pointer border transition-colors duration-150 ${
                  selectedDirectory === folder 
                    ? 'bg-blue-100 border-blue-500' 
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
                onClick={() => setSelectedDirectory(folder)}
              >
                <div className="flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-yellow-500 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M2 6a2 2 0 012-2h4l2 2h4a2 2 0 012 2v7a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" clipRule="evenodd" />
                  </svg>
                  <span className="font-medium">{folder}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-lg font-semibold text-blue-700 mb-4">Configuración</h2>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Directorio seleccionado
            </label>
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
              {selectedDirectory || 'Ninguno seleccionado'}
            </div>
          </div>
          
          <div className="mb-6">
            <label className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Aplicar autofit a los textos</span>
            </label>
          </div>
          
          <button
            className={`w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-md ${
              !selectedDirectory ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'
            }`}
            disabled={!selectedDirectory}
          >
            Procesar directorio
          </button>
        </div>
      </div>
    </div>
  );
};

export default BatchProcessTool; 