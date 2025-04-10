import React, { useState } from 'react';
import axios from 'axios';
import { FaUpload, FaCog, FaDownload, FaCheckCircle, FaExclamationTriangle, FaFileArchive } from 'react-icons/fa';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

const AutofitTool = () => {
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [processedFiles, setProcessedFiles] = useState<Array<{url: string, name: string}>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'processed' | 'error'>('idle');
  const [progress, setProgress] = useState<number>(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      // Verificar si hay más de 10 archivos
      if (e.target.files.length > 10) {
        setError('Máximo 10 archivos permitidos');
        return;
      }
      
      setSelectedFiles(e.target.files);
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
    if (!selectedFiles || selectedFiles.length === 0) {
      setError('Por favor seleccione al menos un archivo');
      return;
    }

    setIsLoading(true);
    setStatus('processing');
    setError(null);
    setProgress(0);
    
    // Iniciar la simulación de progreso inmediatamente
    const progressInterval = startFakeProgressBar();

    try {
      console.log("Iniciando procesamiento de archivos...");
      
      if (selectedFiles.length === 1) {
        await processSingleFile(selectedFiles[0]);
      } else {
        await processMultipleFiles(selectedFiles);
      }
      
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
        const serverErrorMsg = err.response?.data?.detail?.message || 
                            err.response?.data?.message || 
                            err.response?.data?.detail || 
                            err.message;
        setError(`Error: ${serverErrorMsg || 'Error de comunicación con el servidor'}`);
      } else if (err instanceof Error) {
        setError(`Error: ${err.message}`);
      } else {
        setError('Error desconocido al procesar archivo(s)');
      }
      setStatus('error');
      setIsLoading(false);
    }
  };

  const processSingleFile = async (file: File) => {
    console.log(`Procesando archivo único: ${file.name}`);
    
    // Crear formData para el archivo
    const formData = new FormData();
    formData.append('file', file);

    try {
      // Paso 1: Subir el archivo
      console.log("Subiendo archivo al servidor...");
      const uploadResponse = await axios.post(`${API_BASE_URL}/api/autofit/upload-pptx`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log("Respuesta de carga:", uploadResponse.data);
      
      // Verificar que la respuesta tiene el formato correcto
      if (!uploadResponse.data.data || !uploadResponse.data.data.file_id) {
        throw new Error("Formato de respuesta inválido en la carga del archivo");
      }
      
      const fileId = uploadResponse.data.data.file_id;
      const originalName = uploadResponse.data.data.original_name;

      // Paso 2: Procesar el archivo
      console.log("Procesando archivo en el servidor...");
      const processFormData = new FormData();
      processFormData.append('file_id', fileId);
      processFormData.append('original_name', originalName);

      const processResponse = await axios.post(`${API_BASE_URL}/api/autofit/process`, processFormData);
      console.log("Respuesta de procesamiento:", processResponse.data);
      
      // Verificar que la respuesta de procesamiento es correcta
      if (!processResponse.data.data) {
        throw new Error("Formato de respuesta inválido en el procesamiento");
      }
      
      setProcessedFiles([{
        url: processResponse.data.data.download_url,
        name: processResponse.data.data.output_filename
      }]);
      setStatus('processed');
    } catch (err) {
      console.error('Error en processSingleFile:', err);
      throw err;
    }
  };

  const processMultipleFiles = async (files: FileList) => {
    console.log(`Procesando ${files.length} archivos`);
    
    // Crear formData para múltiples archivos
    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });

    try {
      // Paso 1: Subir los archivos
      console.log("Subiendo archivos al servidor...");
      const uploadResponse = await axios.post(`${API_BASE_URL}/api/autofit/upload-multiple-pptx`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log("Respuesta de carga múltiple:", uploadResponse.data);
      
      // Verificar que la respuesta tiene el formato correcto
      if (!uploadResponse.data.data || !uploadResponse.data.data.results) {
        throw new Error("Formato de respuesta inválido en la carga de archivos");
      }
      
      const fileInfos = uploadResponse.data.data.results.filter(
        (result: any) => result.status === 'success'
      );

      if (fileInfos.length === 0) {
        throw new Error('No se pudieron subir los archivos');
      }

      // Paso 2: Procesar los archivos
      console.log("Procesando archivos en el servidor...");
      const processFormData = new FormData();
      processFormData.append('file_infos', JSON.stringify(fileInfos));

      const processResponse = await axios.post(`${API_BASE_URL}/api/autofit/process-multiple`, processFormData);
      console.log("Respuesta de procesamiento múltiple:", processResponse.data);
      
      // Verificar que la respuesta tiene el formato correcto
      if (!processResponse.data.data || !processResponse.data.data.results) {
        throw new Error("Formato de respuesta inválido en el procesamiento");
      }
      
      // Extraer los URLs de descarga
      const processedFilesData = processResponse.data.data.results
        .filter((result: any) => result.status === 'success')
        .map((result: any) => ({
          url: result.download_url,
          name: result.output_filename
        }));
      
      setProcessedFiles(processedFilesData);
      setStatus('processed');
    } catch (err) {
      console.error('Error en processMultipleFiles:', err);
      throw err;
    }
  };

  const handleDownload = (url: string) => {
    if (url) {
      const fullUrl = `${API_BASE_URL}${url}`;
      console.log(`Descargando archivo desde: ${fullUrl}`);
      window.open(fullUrl, '_blank');
    }
  };

  const handleDownloadAll = async () => {
    if (processedFiles.length > 0) {
      try {
        setIsLoading(true);
        
        // Crear una solicitud para descargar un ZIP con todos los archivos
        const fileUrls = processedFiles.map(file => file.url);
        
        // Llamada al endpoint que comprime los archivos en un ZIP
        const response = await axios.post(
          `${API_BASE_URL}/api/autofit/download-zip`, 
          { file_urls: fileUrls },
          { responseType: 'blob' } // Importante para recibir datos binarios
        );
        
        // Crear un objeto URL para el blob
        const blob = new Blob([response.data], { type: 'application/zip' });
        const url = window.URL.createObjectURL(blob);
        
        // Crear un enlace temporal y forzar la descarga
        const link = document.createElement('a');
        link.href = url;
        link.download = 'archivos_procesados.zip';
        document.body.appendChild(link);
        link.click();
        
        // Limpiar
        setTimeout(() => {
          window.URL.revokeObjectURL(url);
          document.body.removeChild(link);
        }, 100);
      } catch (error) {
        console.error('Error al descargar ZIP:', error);
        setError('Error al descargar el archivo ZIP. Intente descargar los archivos individualmente.');
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta Autofit</h1>
        <p className="text-primary-700">
          Esta herramienta ajusta automáticamente el texto en las presentaciones PowerPoint.
        </p>
      </div>
      
      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
          <h2 className="text-white font-medium text-center">Seleccionar archivos PPTX</h2>
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
                  <p className="text-xs text-gray-500 text-center">Archivos PPTX (máximo 10)</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".pptx"
                  onChange={handleFileChange}
                  multiple
                  disabled={isLoading}
                />
              </label>
            </div>
            {selectedFiles && selectedFiles.length > 0 && (
              <div className="mt-3 text-sm text-gray-600 text-center">
                {selectedFiles.length === 1 
                  ? `Archivo seleccionado: ${selectedFiles[0].name}` 
                  : `${selectedFiles.length} archivos seleccionados`}
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
                {progress >= 30 && progress < 60 && "Ajustando textos..."}
                {progress >= 60 && progress < 90 && "Generando archivo final..."}
                {progress >= 90 && "Finalizando proceso..."}
              </p>
            </div>
          )}
          
          <div className="space-y-4">
            <button
              onClick={handleProcess}
              disabled={!selectedFiles || isLoading}
              className={`w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
                !selectedFiles || isLoading 
                  ? 'bg-gray-300 cursor-not-allowed'
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
                  <FaCog className="mr-2" /> Procesar {selectedFiles && selectedFiles.length > 1 ? 'archivos' : 'archivo'}
                </>
              )}
            </button>
            
            {processedFiles.length > 0 && (
              <div className="mt-4 bg-primary-100 p-5 rounded-xl border border-primary-200">
                <div className="mb-4 border-b border-primary-200 pb-3">
                  <h3 className="text-lg font-medium text-primary-800 text-center">Archivos procesados:</h3>
                </div>
                
                <div className="space-y-2">
                  {processedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-white p-3 rounded-lg border border-primary-200">
                      <span className="text-primary-700 font-medium truncate pr-4" style={{ flex: '1 1 auto', minWidth: 0 }}>{file.name}</span>
                      <button
                        onClick={() => handleDownload(file.url)}
                        className="bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white px-3 py-2 rounded-lg text-sm flex items-center flex-shrink-0 shadow-md"
                      >
                        <FaDownload className="mr-2" /> Descargar
                      </button>
                    </div>
                  ))}
                </div>
                
                {processedFiles.length > 1 && (
                  <div className="mt-6 flex justify-center">
                    <button
                      onClick={handleDownloadAll}
                      className="bg-primary-700 hover:bg-primary-800 text-white px-5 py-2.5 rounded-lg flex items-center"
                    >
                      <FaFileArchive className="mr-2" /> Descargar todos
                    </button>
                  </div>
                )}
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
              <FaCheckCircle className="mr-2" /> Archivos procesados correctamente. Listos para descargar.
            </div>
          )}
        </div>
      </div>

      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué ajustar el texto automáticamente?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Evita problemas con cuadros de texto desbordados</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Mantiene la consistencia en la visualización de textos</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Ahorra tiempo en ajustes manuales de cada diapositiva</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Mejora la legibilidad del contenido en presentaciones</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Procesar presentaciones creadas por diferentes autores</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Adaptar contenido traducido al espacio disponible</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Preparar materiales para impresión o publicación online</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Estandarizar presentaciones corporativas o académicas</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AutofitTool; 