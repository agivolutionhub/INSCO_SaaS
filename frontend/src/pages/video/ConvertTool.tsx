import { useState } from 'react';

const ConvertTool = () => {
  const [selectedFormat, setSelectedFormat] = useState('mp4');
  
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Convertir Vídeo</h1>
      <p className="text-gray-600 mb-6">
        Convierte archivos de vídeo entre diferentes formatos.
      </p>
      
      <div className="bg-white p-6 rounded-lg shadow-md max-w-2xl">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Archivo de vídeo
          </label>
          <input
            type="file"
            accept="video/*"
            className="w-full p-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Formato de salida
          </label>
          <select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md bg-white"
          >
            <option value="mp4">MP4</option>
            <option value="avi">AVI</option>
            <option value="mov">MOV</option>
            <option value="webm">WebM</option>
            <option value="mkv">MKV</option>
          </select>
        </div>
        
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Opciones adicionales</h3>
          
          <div className="space-y-3">
            <label className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Comprimir vídeo</span>
            </label>
            
            <label className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Extraer audio</span>
            </label>
            
            <label className="flex items-center">
              <input
                type="checkbox"
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Reducir resolución</span>
            </label>
          </div>
        </div>
        
        <button
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md"
        >
          Convertir vídeo
        </button>
      </div>
    </div>
  );
};

export default ConvertTool; 