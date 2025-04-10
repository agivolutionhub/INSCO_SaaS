import React, { useState } from 'react';
import axios from 'axios';
import { FaUpload, FaCog, FaDownload, FaCamera, FaExclamationTriangle, FaArrowLeft, FaArrowRight } from 'react-icons/fa';
import "react-responsive-carousel/lib/styles/carousel.min.css";
import { Carousel } from 'react-responsive-carousel';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

const CapturesTools = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [slideImages, setSlideImages] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'processed' | 'error'>('idle');
  const [progress, setProgress] = useState<number>(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setError(null);
      setStatus('idle');
      setSlideImages([]);
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
      setError('Por favor seleccione un archivo PPTX');
      return;
    }

    setIsLoading(true);
    setStatus('processing');
    setError(null);
    setProgress(0);
    
    // Iniciar la simulación de progreso inmediatamente
    const progressInterval = startFakeProgressBar();

    try {
      console.log("Iniciando procesamiento del archivo para capturas...");
      
      // Crear formData para el archivo
      const formData = new FormData();
      formData.append('file', selectedFile);

      // Enviar el archivo al servidor
      const uploadResponse = await axios.post(`${API_BASE_URL}/api/upload-pptx-for-captures`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log("Respuesta de carga:", uploadResponse.data);
      
      const fileId = uploadResponse.data.file_id;
      const originalName = uploadResponse.data.original_name;

      // Usando URLSearchParams para enviar datos de formulario
      const params = new URLSearchParams();
      params.append('file_id', fileId);
      if (originalName) {
        params.append('original_name', originalName);
      }

      // Procesar el archivo para generar capturas
      const processResponse = await axios.post(
        `${API_BASE_URL}/api/process-captures`,
        params,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );
      
      console.log("Respuesta de procesamiento:", processResponse.data);
      
      // Actualizar el estado con las URLs de las imágenes
      setSlideImages(processResponse.data.image_urls);
      setStatus('processed');
      
      // Completar la barra de progreso
      setProgress(100);
      
      // Esperar un momento antes de ocultar la barra de progreso
      setTimeout(() => {
        setIsLoading(false);
      }, 500);
      
    } catch (err) {
      console.error('Error en handleProcess:', err);
      
      // Limpiar el intervalo de progreso en caso de error
      clearInterval(progressInterval);
      
      if (axios.isAxiosError(err)) {
        // Error de red o respuesta del servidor
        const errorMsg = err.response?.data?.detail || err.message || 'Error al procesar el archivo';
        setError(`Error: ${errorMsg}`);
      } else {
        setError('Error al procesar el archivo');
      }
      setStatus('error');
      setIsLoading(false);
    }
  };

  const handleDownloadAll = async () => {
    if (slideImages.length === 0) return;
    
    try {
      setIsLoading(true);
      
      // Solicitar compresión y descarga de todas las imágenes
      const response = await axios.post(`${API_BASE_URL}/api/download-captures-zip`, {
        image_urls: slideImages,
        original_name: selectedFile?.name || 'capturas'
      }, {
        responseType: 'blob'
      });
      
      // Crear un enlace de descarga para el archivo ZIP
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${selectedFile?.name.replace('.pptx', '')}_capturas.zip`);
      document.body.appendChild(link);
      link.click();
      
      // Limpiar
      window.URL.revokeObjectURL(url);
      link.remove();
    } catch (err) {
      console.error('Error al descargar las imágenes:', err);
      setError('Error al descargar las imágenes. Inténtelo de nuevo.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta Capturas</h1>
        <p className="text-primary-700">
          Esta herramienta genera imágenes PNG de alta calidad a partir de las diapositivas PPTX.
        </p>
      </div>
      
      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
          <h2 className="text-white font-medium text-center">Seleccionar archivo PPTX</h2>
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
                  <p className="text-xs text-gray-500 text-center">Archivos PPTX</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".pptx"
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
          
          {/* Barra de progreso mejorada */}
          {isLoading && (
            <div className="mb-6 mt-2">
              <div className="flex justify-between text-sm text-primary-700 mb-2">
                <span className="font-medium flex items-center">
                  <FaCog className="animate-spin mr-2" />
                  Procesando presentación...
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
                {progress < 30 && "Analizando presentación..."}
                {progress >= 30 && progress < 60 && "Generando capturas..."}
                {progress >= 60 && progress < 90 && "Procesando imágenes..."}
                {progress >= 90 && "Finalizando proceso..."}
              </p>
            </div>
          )}
          
          <div className="space-y-4">
            <button
              onClick={handleProcess}
              disabled={!selectedFile || isLoading}
              className={`w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
                !selectedFile || isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
              }`}
            >
              {isLoading ? (
                <>
                  <FaCog className="animate-spin mr-2" />
                  Procesando...
                </>
              ) : (
                <>
                  <FaCamera className="mr-2" />
                  Generar capturas
                </>
              )}
            </button>
            
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl flex items-center">
                <FaExclamationTriangle className="mr-2" />
                {error}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Carrusel de imágenes */}
      {status === 'processed' && slideImages.length > 0 && (
        <div className="mt-8 bg-white rounded-xl shadow-md overflow-hidden">
          <div className="bg-primary-600 p-4">
            <h2 className="text-white font-medium text-center">Capturas generadas</h2>
          </div>
          
          <div className="p-6 bg-primary-50">
            <div className="mb-6">
              <Carousel
                showArrows={true}
                showThumbs={true}
                infiniteLoop={true}
                showStatus={true}
                renderArrowPrev={(onClickHandler, hasPrev) => 
                  hasPrev && (
                    <button 
                      type="button" 
                      onClick={onClickHandler} 
                      className="absolute left-0 top-1/2 z-10 -translate-y-1/2 bg-black bg-opacity-50 p-2 rounded-r-lg"
                    >
                      <FaArrowLeft className="w-5 h-5 text-white" />
                    </button>
                  )
                }
                renderArrowNext={(onClickHandler, hasNext) => 
                  hasNext && (
                    <button 
                      type="button" 
                      onClick={onClickHandler} 
                      className="absolute right-0 top-1/2 z-10 -translate-y-1/2 bg-black bg-opacity-50 p-2 rounded-l-lg"
                    >
                      <FaArrowRight className="w-5 h-5 text-white" />
                    </button>
                  )
                }
              >
                {slideImages.map((imageUrl, index) => (
                  <div key={index} className="w-full">
                    <img 
                      src={`${API_BASE_URL}${imageUrl}`} 
                      alt={`Diapositiva ${index + 1}`}
                      className="max-h-[500px] object-contain mx-auto"
                    />
                    <p className="legend">Diapositiva {index + 1}</p>
                  </div>
                ))}
              </Carousel>
            </div>
            
            <button
              onClick={handleDownloadAll}
              disabled={isLoading}
              className={`w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
                isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
              }`}
            >
              {isLoading ? (
                <>
                  <FaCog className="animate-spin mr-2" />
                  Preparando archivos...
                </>
              ) : (
                <>
                  <FaDownload className="mr-2" />
                  Descargar todas las capturas
                </>
              )}
            </button>
          </div>
        </div>
      )}
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué generar capturas de diapositivas?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Facilita la inclusión de contenido en documentos y sitios web</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Permite compartir diapositivas sin enviar el archivo completo</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Genera versiones visuales que no requieren PowerPoint</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Preserva exactamente lo que se ve en cada diapositiva</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Crear miniaturas para catálogos de presentaciones</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Incorporar diapositivas en documentos Word y PDF</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Publicar contenido en redes sociales o plataformas de e-learning</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Generar recursos visuales para informes y artículos</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CapturesTools; 