import React, { useState } from 'react';
import { FaUpload, FaCog, FaDownload, FaCheckCircle, FaExclamationTriangle, FaLanguage } from 'react-icons/fa';
import { MdGTranslate } from 'react-icons/md';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

const VideoTranslateTool = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetLanguage, setTargetLanguage] = useState<string>('es');
  const [processedFiles, setProcessedFiles] = useState<Array<{url: string, name: string}>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'processed' | 'error'>('idle');
  const [progress, setProgress] = useState<number>(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setError(null);
      setStatus('idle');
      setProcessedFiles([]);
      setProgress(0);
    }
  };

  // Función para simular la barra de progreso mientras se procesa el archivo
  const startFakeProgressBar = () => {
    setProgress(0);
    const maxProgress = 90; // Solo llega al 90% máximo, el 100% se alcanza cuando termina realmente
    const intervalStep = 300; // Intervalo entre incrementos
    const smallStep = 1; // Incremento pequeño regular
    const initialBoost = 10; // Impulso inicial para que se vea movimiento inmediato
    const largeStepChance = 0.15; // Probabilidad de incrementos grandes
    const largeStepSize = 5; // Tamaño del incremento grande
    
    // Dar un impulso inicial para que el usuario vea movimiento inmediato
    setProgress(initialBoost);
    
    const interval = setInterval(() => {
      setProgress(current => {
        // Si estamos procesando y no hemos llegado al máximo
        if (current < maxProgress) {
          // Decidir si aplicar un incremento pequeño o grande
          const increment = Math.random() < largeStepChance ? largeStepSize : smallStep;
          const newProgress = Math.min(current + increment, maxProgress);
          return newProgress;
        }
        // Mantener el progreso actual si ya alcanzó el máximo
        return current;
      });
    }, intervalStep);
    
    // Devolver el ID del intervalo para limpiarlo después
    return interval;
  };

  const handleProcess = async () => {
    if (!selectedFile) {
      setError('Por favor seleccione un archivo de vídeo para traducir');
      return;
    }

    setIsLoading(true);
    setStatus('processing');
    setError(null);
    setProgress(0);
    
    // Iniciar la simulación de progreso inmediatamente
    const progressInterval = startFakeProgressBar();

    try {
      console.log(`Iniciando traducción al idioma: ${targetLanguage}...`);
      
      // TODO: Implementar la conexión con el backend aquí
      // Por ahora solo simulamos un proceso exitoso
      
      setTimeout(() => {
        // Simulación de proceso exitoso
        setProcessedFiles([{
          url: "/api/download/video_traducido.mp4",
          name: "video_traducido.mp4"
        }, {
          url: "/api/download/subtitulos_traducidos.srt",
          name: "subtitulos_traducidos.srt"
        }]);
        setStatus('processed');
        
        // Completar la barra de progreso
        setProgress(100);
        
        // Esperar un momento antes de ocultar la barra de progreso
        setTimeout(() => {
          setIsLoading(false);
        }, 500);
      }, 3000); // Simular 3 segundos de procesamiento
      
    } catch (err) {
      console.error('Error en handleProcess:', err);
      
      // Limpiar el intervalo de progreso en caso de error
      clearInterval(progressInterval);
      
      setError('Error al traducir el vídeo');
      setStatus('error');
      setIsLoading(false);
    }
  };

  const handleDownload = (url: string) => {
    if (url) {
      const fullUrl = `${API_BASE_URL}${url}`;
      console.log(`Descargando archivo desde: ${fullUrl}`);
      window.open(fullUrl, '_blank');
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
        <h2 className="text-white font-medium text-center">Seleccionar archivo de vídeo</h2>
      </div>
      
      <div className="p-6 bg-primary-50">
        <div className="mb-6">
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-primary-200 border-dashed rounded-xl cursor-pointer bg-white hover:bg-gray-50">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <FaUpload className="w-8 h-8 mb-3 text-primary-500" />
                <p className="mb-2 text-sm text-gray-700 text-center">
                  <span className="font-semibold">Haga clic para cargar</span> o arrastre y suelte
                </p>
                <p className="text-xs text-gray-500 text-center">Archivos de vídeo (MP4, AVI, MOV)</p>
              </div>
              <input
                type="file"
                className="hidden"
                accept="video/*"
                onChange={handleFileChange}
                disabled={isLoading}
              />
            </label>
          </div>
          {selectedFile && (
            <div className="mt-3 text-sm text-gray-600 text-center">
              Archivo seleccionado: {selectedFile.name}
            </div>
          )}
        </div>
        
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Idioma de destino:</label>
          <select
            value={targetLanguage}
            onChange={(e) => setTargetLanguage(e.target.value)}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 bg-white shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            disabled={isLoading}
          >
            <option value="es">Español</option>
            <option value="en">Inglés</option>
            <option value="fr">Francés</option>
            <option value="de">Alemán</option>
            <option value="it">Italiano</option>
            <option value="pt">Portugués</option>
          </select>
        </div>
        
        {/* Barra de progreso mejorada */}
        {isLoading && (
          <div className="mb-6 mt-2">
            <div className="flex justify-between text-sm text-primary-700 mb-2">
              <span className="font-medium flex items-center">
                <FaCog className="animate-spin mr-2" />
                Procesando traducción...
              </span>
              <span className="font-medium">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 shadow-inner">
              <div 
                className="bg-primary-600 h-4 rounded-full transition-all duration-300 flex items-center justify-end"
                style={{ width: `${progress}%` }}
              >
                <div className="bg-primary-400 h-2 w-10 rounded-full animate-pulse mx-2" 
                     style={{ display: progress < 10 ? 'none' : 'block' }}></div>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              {progress < 30 && "Analizando audio..."}
              {progress >= 30 && progress < 60 && "Traduciendo contenido..."}
              {progress >= 60 && progress < 90 && "Generando nuevo audio..."}
              {progress >= 90 && "Finalizando proceso..."}
            </p>
          </div>
        )}
        
        <div className="space-y-4">
          <button
            onClick={handleProcess}
            disabled={!selectedFile || isLoading}
            className={`w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
              !selectedFile || isLoading 
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
            }`}
          >
            {isLoading ? (
              <>
                <FaCog className="animate-spin mr-2" />
                Procesando...
              </>
            ) : (
              <>
                <MdGTranslate className="mr-2" /> Traducir vídeo
              </>
            )}
          </button>
          
          {processedFiles.length > 0 && (
            <div className="mt-4 bg-primary-100 p-5 rounded-xl border border-primary-200">
              <div className="mb-4 border-b border-primary-200 pb-3">
                <h3 className="text-lg font-medium text-primary-800 text-center">Archivos generados:</h3>
              </div>
              
              <div className="space-y-2">
                {processedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between bg-white p-3 rounded-lg border border-primary-200">
                    <span className="text-primary-700 font-medium truncate pr-4" style={{ flex: '1 1 auto', minWidth: 0 }}>{file.name}</span>
                    <button
                      onClick={() => handleDownload(file.url)}
                      className={`bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white px-3 py-2 rounded-lg text-sm flex items-center flex-shrink-0 shadow-md`}
                    >
                      <FaDownload className="mr-2" /> Descargar
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg flex items-center justify-center border border-red-200">
            <FaExclamationTriangle className="mr-2" /> {error}
          </div>
        )}
        
        {status === 'processed' && processedFiles.length === 0 && (
          <div className="mt-4 p-3 bg-green-50 text-green-600 rounded-lg flex items-center justify-center border border-green-200">
            <FaCheckCircle className="mr-2" /> Vídeo traducido correctamente. Listo para descargar.
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoTranslateTool; 