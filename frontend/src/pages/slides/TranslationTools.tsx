import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { FaUpload, FaCog, FaDownload, FaCheckCircle, FaExclamationTriangle, FaFileArchive } from 'react-icons/fa';
import { MdGTranslate } from 'react-icons/md';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

interface ProcessingFile {
  originalFile: File;
  jobId: string | null;
  progress: number;
  status: 'idle' | 'processing' | 'processed' | 'error';
  error: string | null;
  result: { url: string, name: string } | null;
  processingStage: string;
  stats?: {
    slides_processed: number;
    texts_translated: number;
    api_calls: number;
    rate_limit_retries: number;
    successful_retries: number;
    duplicates_avoided: number;
    cache_hits: number;
    cache_misses: number;
    errors: number;
    total_time: number;
    input_tokens: number;
    output_tokens: number;
    cached_tokens: number;
    total_tokens?: number;
    input_cost: number;
    cached_cost: number;
    output_cost: number;
    total_cost: number;
    processing_speed?: number;
    tokens_per_second?: number;
    slides_per_second?: number;
    cost_per_1k_tokens?: number;
    cache_hit_rate?: number;
    api_response_time?: number;
    efficiency_summary?: {
      processing_speed: string;
      token_rate: string;
      cache_efficiency: string;
      cost_efficiency: string;
    };
  };
}

const TranslationTools = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[] | null>(null);
  const [sourceLanguage, setSourceLanguage] = useState<string>('es');
  const [targetLanguage, setTargetLanguage] = useState<string>('en');
  const [processingFiles, setProcessingFiles] = useState<ProcessingFile[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentFileIndex, setCurrentFileIndex] = useState<number>(-1); 
  const [expandedStats, setExpandedStats] = useState<{[key: string]: boolean}>({});
  const pollingRefs = useRef<{[key: string]: number}>({});

  // Limpiar los intervalos de polling cuando se desmonte el componente
  useEffect(() => {
    return () => {
      Object.values(pollingRefs.current).forEach(interval => {
        clearInterval(interval);
      });
    };
  }, []);

  // Función para cancelar todo el proceso de traducción
  const handleCancelAll = () => {
    Object.values(pollingRefs.current).forEach(interval => {
      clearInterval(interval);
    });
    pollingRefs.current = {};
    setIsLoading(false);
    setProcessingFiles([]);
    setCurrentFileIndex(-1);
  };

  // Función para cancelar la traducción de un archivo específico
  const handleCancelFile = (index: number) => {
    const file = processingFiles[index];
    if (file.jobId && pollingRefs.current[file.jobId]) {
      clearInterval(pollingRefs.current[file.jobId]);
      delete pollingRefs.current[file.jobId];
    }

    const updatedFiles = [...processingFiles];
    updatedFiles[index] = {
      ...updatedFiles[index],
      status: 'idle',
      progress: 0,
      error: null,
      processingStage: 'Cancelado'
    };
    setProcessingFiles(updatedFiles);

    // Si era el archivo actual, pasar al siguiente
    if (currentFileIndex === index) {
      processNextFile(index + 1);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setSelectedFiles(files);
      setError(null);
      setProcessingFiles([]);
    }
  };

  const handleSourceLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSourceLanguage(e.target.value);
  };

  const handleTargetLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTargetLanguage(e.target.value);
  };

  // Función para verificar el estado del trabajo
  const checkJobStatus = async (jobId: string, fileIndex: number) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/translate/jobs/${jobId}`);
      const result = response.data;
      
      console.log(`Estado del trabajo ${jobId} (archivo ${fileIndex + 1}):`, result);
      
      // Actualizar los archivos de forma segura
      setProcessingFiles(prevFiles => {
        // Si el índice no es válido, no hacer nada
        if (prevFiles.length <= fileIndex) return prevFiles;
        
        const updatedFiles = [...prevFiles];
        
        if (result.status === "completed") {
          // El trabajo se ha completado
          updatedFiles[fileIndex] = {
            ...updatedFiles[fileIndex],
            status: 'processed',
            progress: 100,
            processingStage: '¡Traducción completada!',
            result: {
              url: result.download_url,
              name: result.filename
            },
            stats: result.stats // Guardar estadísticas del procesamiento
          };
          
          // Detener el polling
          if (pollingRefs.current[jobId]) {
            clearInterval(pollingRefs.current[jobId]);
            delete pollingRefs.current[jobId];
          }
          
          // Procesar el siguiente archivo si hay más
          // Usamos setTimeout para evitar la manipulación de estado durante el render
          setTimeout(() => {
            processNextFile(fileIndex + 1);
          }, 0);
          
        } else if (result.status === "error") {
          // Error en el proceso
          updatedFiles[fileIndex] = {
            ...updatedFiles[fileIndex],
            status: 'error',
            error: result.message || 'Error durante el procesamiento',
            processingStage: 'Error en la traducción'
          };
          
          // Detener el polling
          if (pollingRefs.current[jobId]) {
            clearInterval(pollingRefs.current[jobId]);
            delete pollingRefs.current[jobId];
          }
          
          // Procesar el siguiente archivo aunque este haya fallado
          // Usamos setTimeout para evitar la manipulación de estado durante el render
          setTimeout(() => {
            processNextFile(fileIndex + 1);
          }, 0);
          
        } else {
          // El trabajo sigue en proceso, actualizar progreso simulado de forma más rápida
          const progressIncrement = Math.random() * (5 - 2) + 2; // Incremento entre 2% y 5%
          
          if (updatedFiles[fileIndex].progress < 95) {
            const newProgress = Math.min(updatedFiles[fileIndex].progress + progressIncrement, 95);
            
            // Mensajes más detallados según el progreso
            let stageMessage = 'Procesando...';
            if (newProgress < 10) {
              stageMessage = 'Analizando estructura de la presentación...';
            } else if (newProgress < 20) {
              stageMessage = 'Examinando diapositivas y contenido...';
            } else if (newProgress < 30) {
              stageMessage = 'Extrayendo textos para traducción...';
            } else if (newProgress < 40) {
              stageMessage = 'Preparando lotes de textos para API...';
            } else if (newProgress < 50) {
              stageMessage = 'Enviando textos a OpenAI para traducción...';
            } else if (newProgress < 60) {
              stageMessage = 'Traduciendo contenido de diapositivas...';
            } else if (newProgress < 70) {
              stageMessage = 'Verificando calidad de la traducción...';
            } else if (newProgress < 80) {
              stageMessage = 'Reconstruyendo la presentación con textos traducidos...';
            } else if (newProgress < 90) {
              stageMessage = 'Aplicando formato a la presentación traducida...';
            } else {
              stageMessage = 'Finalizando y preparando archivo para descarga...';
            }
            
            updatedFiles[fileIndex] = {
              ...updatedFiles[fileIndex],
              progress: newProgress,
              processingStage: stageMessage
            };
          }
        }
        
        return updatedFiles;
      });
    } catch (err) {
      console.error(`Error al verificar estado del trabajo ${jobId}:`, err);
    }
  };

  // Procesa el siguiente archivo en la cola
  const processNextFile = (nextIndex: number) => {
    if (!selectedFiles || nextIndex >= selectedFiles.length) {
      // Todos los archivos han sido procesados
      setIsLoading(false);
      setCurrentFileIndex(-1);
      return;
    }

    // Usamos setTimeout para evitar posibles problemas de actualización de estado
    setTimeout(() => {
      setCurrentFileIndex(nextIndex);
      processFile(nextIndex);
    }, 0);
  };

  // Procesa un archivo específico
  const processFile = async (fileIndex: number) => {
    if (!selectedFiles || fileIndex >= selectedFiles.length) {
      console.error(`Índice inválido o no hay archivos seleccionados: ${fileIndex}`);
      setIsLoading(false);
      return;
    }

    const file = selectedFiles[fileIndex];
    
    try {
      console.log(`Iniciando procesamiento del archivo ${fileIndex + 1}/${selectedFiles.length}: ${file.name}`);
      
      // Actualizar estado para este archivo de forma segura
      setProcessingFiles(prevFiles => {
        const updatedFiles = [...prevFiles];
        // Asegurarse de que el índice existe
        while (updatedFiles.length <= fileIndex) {
          updatedFiles.push({
            originalFile: selectedFiles[updatedFiles.length],
            jobId: null,
            progress: 0,
            status: 'idle',
            error: null,
            result: null,
            processingStage: 'En espera...',
            stats: undefined
          });
        }
        
        updatedFiles[fileIndex] = {
          ...updatedFiles[fileIndex],
          originalFile: file,
          jobId: null,
          progress: 10,
          status: 'processing',
          error: null,
          result: null,
          processingStage: 'Subiendo archivo para traducción...',
          stats: undefined
        };
        
        return updatedFiles;
      });
      
      // Crear formData para el archivo
      const formData = new FormData();
      formData.append('file', file);
      formData.append('source_language', sourceLanguage);
      formData.append('target_language', targetLanguage);

      // Enviar el archivo al servidor
      const uploadResponse = await axios.post(`${API_BASE_URL}/api/translate/upload-pptx-for-translation`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log(`Respuesta de carga para ${file.name}:`, uploadResponse.data);
      
      const fileId = uploadResponse.data.file_id;
      const originalName = uploadResponse.data.original_name;

      // Procesar el archivo para traducción
      const processResponse = await axios.post(`${API_BASE_URL}/api/translate/process-translation`, {
        file_id: fileId,
        original_name: originalName,
        source_language: sourceLanguage,
        target_language: targetLanguage
      });
      
      console.log(`Respuesta de procesamiento para ${file.name}:`, processResponse.data);
      
      // Guardar el job_id para polling
      const jobId = processResponse.data.job_id;
      
      // Actualizar la información del archivo de forma segura
      setProcessingFiles(prevFiles => {
        if (prevFiles.length <= fileIndex) return prevFiles;
        
        const newUpdatedFiles = [...prevFiles];
        newUpdatedFiles[fileIndex] = {
          ...newUpdatedFiles[fileIndex],
          jobId: jobId,
          processingStage: 'Procesando traducción...',
          stats: processResponse.data.stats
        };
        
        return newUpdatedFiles;
      });
      
      // Configurar intervalo para verificar el estado cada 2 segundos
      if (jobId) {
        pollingRefs.current[jobId] = setInterval(() => {
          checkJobStatus(jobId, fileIndex);
        }, 2000);
      }
      
    } catch (err) {
      console.error(`Error en procesamiento del archivo ${file.name}:`, err);
      
      // Actualizar estado de error para este archivo de forma segura
      setProcessingFiles(prevFiles => {
        if (prevFiles.length <= fileIndex) return prevFiles;
        
        let errorMsg = 'Error al procesar el archivo';
        if (axios.isAxiosError(err)) {
          errorMsg = err.response?.data?.detail || err.message || errorMsg;
        }
        
        const updatedFiles = [...prevFiles];
        updatedFiles[fileIndex] = {
          ...updatedFiles[fileIndex],
          status: 'error',
          error: errorMsg,
          processingStage: 'Error en la traducción',
          stats: undefined
        };
        
        return updatedFiles;
      });
      
      // Procesar el siguiente archivo aunque este haya fallado
      processNextFile(fileIndex + 1);
    }
  };

  // Inicia el procesamiento de todos los archivos
  const handleProcessAll = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setError('Por favor seleccione al menos un archivo PPTX');
      return;
    }

    if (sourceLanguage === targetLanguage) {
      setError('El idioma de origen y destino no pueden ser iguales');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    // Inicializar estados para todos los archivos
    const initialStates: ProcessingFile[] = selectedFiles.map(file => ({
      originalFile: file,
      jobId: null,
      progress: 0,
      status: 'idle',
      error: null,
      result: null,
      processingStage: 'En espera...',
      stats: undefined
    }));
    
    setProcessingFiles(initialStates);
    
    // Empezar a procesar el primer archivo con pequeño retraso 
    // para asegurar que el estado se ha actualizado correctamente
    setTimeout(() => {
      processNextFile(0);
    }, 100);
  };

  // Descarga un archivo específico
  const handleDownloadFile = (url: string, filename: string) => {
    // Construir URL completa
    const fullUrl = `${API_BASE_URL}${url}`;
    console.log(`Descargando archivo desde: ${fullUrl}`);
    
    // Crear un enlace temporal para forzar la descarga
    const link = document.createElement('a');
    link.href = fullUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Descarga todos los archivos procesados en un ZIP
  const handleDownloadAll = async () => {
    try {
      const completedFiles = processingFiles.filter(file => file.status === 'processed' && file.result);
      
      if (completedFiles.length === 0) {
        setError('No hay archivos completados para descargar');
        return;
      }
      
      // Extraer información de los archivos
      const fileIds = [];
      const fileNames = [];
      
      for (const file of completedFiles) {
        // URL formato: /api/translate/files/{file_id}/{filename}
        const urlParts = file.result!.url.split('/');
        const fileId = urlParts[4]; // El file_id está en la posición 4
        
        fileIds.push(fileId);
        fileNames.push(file.result!.name);
        
        console.log(`Preparando archivo para ZIP: ID=${fileId}, Nombre=${file.result!.name}`);
      }
      
      // Construir URL con parámetros para GET
      const downloadUrl = `${API_BASE_URL}/api/translate/download-all-files?file_ids=${fileIds.join(',')}&filenames=${fileNames.join(',')}`;
      console.log('URL de descarga:', downloadUrl);
      
      // Descargar directamente con enlace para evitar problemas con Blob/responseType
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', `traducciones_${new Date().toISOString().slice(0, 10)}.zip`);
      document.body.appendChild(link);
      link.click();
      
      // Pequeña pausa antes de limpiar
      setTimeout(() => {
        document.body.removeChild(link);
      }, 1000);
      
    } catch (err) {
      console.error('Error al descargar todos los archivos:', err);
      
      let errorMessage = 'Error al crear el archivo ZIP para descarga';
      if (axios.isAxiosError(err)) {
        const responseData = err.response?.data;
        if (responseData && typeof responseData === 'object') {
          errorMessage += `: ${responseData.detail || JSON.stringify(responseData)}`;
        }
      }
      
      setError(errorMessage);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta de Traducción</h1>
        <p className="text-primary-700">
          Esta herramienta traduce el texto de las presentaciones PowerPoint al idioma seleccionado.
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
                  <p className="text-xs text-gray-500 text-center">Archivos PPTX (múltiples)</p>
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

          {/* Selectores de idioma */}
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Idioma de origen */}
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Idioma de origen:
                </label>
                <select
                  value={sourceLanguage}
                  onChange={handleSourceLanguageChange}
                  disabled={isLoading}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="es">Español</option>
                  <option value="en">Inglés</option>
                  <option value="fr">Francés</option>
                  <option value="de">Alemán</option>
                  <option value="it">Italiano</option>
                  <option value="pt">Portugués</option>
                </select>
              </div>
              
              {/* Idioma de destino */}
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Idioma de destino:
                </label>
                <select
                  value={targetLanguage}
                  onChange={handleTargetLanguageChange}
                  disabled={isLoading}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="en">Inglés</option>
                  <option value="es">Español</option>
                  <option value="fr">Francés</option>
                  <option value="de">Alemán</option>
                  <option value="it">Italiano</option>
                  <option value="pt">Portugués</option>
                </select>
              </div>
            </div>
          </div>
          
          {/* Lista de archivos en proceso */}
          {processingFiles.length > 0 && (
            <div className="mb-6">
              <div className="bg-white p-4 rounded-lg border border-primary-200 mb-4">
                <h3 className="text-primary-700 font-medium mb-3">
                  Estado de procesamiento {isLoading ? `(${currentFileIndex + 1}/${selectedFiles?.length})` : ''}
                </h3>
                <div className="space-y-4">
                  {processingFiles.map((file, index) => (
                    <div key={index} className="border border-primary-100 rounded-lg p-3 bg-primary-50">
                      <div className="flex justify-between mb-2">
                        <span className="font-medium text-sm truncate" style={{ maxWidth: '70%' }}>
                          {file.originalFile.name}
                        </span>
                        <span className="text-sm font-medium">
                          {file.status === 'processed' ? '100%' : file.status === 'error' ? 'Error' : `${file.progress.toFixed(0)}%`}
                </span>
              </div>
                      
                      {/* Barra de progreso */}
                      <div className="w-full bg-gray-200 rounded-full h-4 shadow-inner overflow-hidden">
                        <div 
                          className={`h-4 rounded-full transition-all duration-300 relative ${
                            file.status === 'error' 
                              ? 'bg-red-500' 
                              : 'bg-gradient-to-r from-[#c79b6d] to-[#daaa7c]'
                          }`}
                          style={{ width: file.status === 'error' ? '100%' : `${file.progress}%` }}
                        >
                          {file.status !== 'error' && file.status !== 'processed' && (
                            <div className="absolute inset-0 bg-white bg-opacity-20 overflow-hidden flex">
                              <div className="h-full w-8 bg-white bg-opacity-30 transform -skew-x-30 animate-shimmer"></div>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Mensaje de estado */}
                      <p className="text-xs text-gray-600 mt-1">
                        {file.error || file.processingStage || 'En espera...'}
                      </p>
                      
                      {/* Botones de acción */}
                      <div className="mt-2 flex justify-end">
                        {file.status === 'processing' && (
                          <button
                            onClick={() => handleCancelFile(index)}
                            className="px-3 py-1.5 text-xs text-white bg-gradient-to-b from-[#e07a7a] to-[#c55757] hover:from-[#c55757] hover:to-[#b54545] rounded-md flex items-center shadow-sm"
                          >
                            Cancelar
                          </button>
                        )}
                        
                        {file.status === 'processed' && file.result && (
                          <button
                            onClick={() => handleDownloadFile(file.result!.url, file.result!.name)}
                            className="px-3 py-1.5 text-xs text-white bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] rounded-md flex items-center shadow-sm"
                          >
                            <FaDownload className="mr-1 text-xs" /> Descargar
                          </button>
                        )}
                      </div>
                      
                      {/* Resumen individual del archivo cuando está procesado */}
                      {file.status === 'processed' && file.stats && (
                        <div className="mt-3 pt-2 border-t border-primary-100 text-xs text-gray-600">
                          <div className="flex justify-between items-center mb-2">
                            <h4 className="font-medium text-primary-700">Resumen de procesamiento</h4>
                            <button 
                              onClick={() => setExpandedStats(prev => ({
                                ...prev, 
                                [index]: !prev[index]
                              }))}
                              className="text-primary-600 hover:text-primary-800 text-xs flex items-center"
                            >
                              {expandedStats[index] ? 'Ocultar detalles' : 'Ver detalles'}
                            </button>
                          </div>
                          
                          {/* Estadísticas básicas siempre visibles */}
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            <div className="flex justify-between">
                              <span>Diapositivas:</span>
                              <span className="font-medium">{file.stats.slides_processed}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Textos:</span>
                              <span className="font-medium">{file.stats.texts_translated}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Tiempo:</span>
                              <span className="font-medium">{file.stats.total_time.toFixed(2)}s</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Costo:</span>
                              <span className="font-medium">${file.stats.total_cost.toFixed(4)}</span>
                            </div>
                          </div>
                          
                          {/* Estadísticas detalladas (expandibles) */}
                          {expandedStats[index] && (
                            <div className="mt-2 pt-2 border-t border-primary-50">
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                                <div className="flex justify-between">
                                  <span>Llamadas API:</span>
                                  <span className="font-medium">{file.stats.api_calls}</span>
                                </div>
                                
                                <div className="flex justify-between">
                                  <span>Diapos/seg:</span>
                                  <span className="font-medium">{file.stats.processing_speed?.toFixed(2) || '0.00'}</span>
                                </div>
                                
                                {/* Estadísticas de caché */}
                                {(file.stats.cache_hits > 0 || file.stats.cache_misses > 0) && (
                                  <>
                                    <div className="flex justify-between">
                                      <span>Caché:</span>
                                      <span className="font-medium">
                                        {file.stats.cache_hits} hits, {file.stats.cache_misses} misses
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>% Caché:</span>
                                      <span className="font-medium">
                                        {file.stats.cache_hit_rate?.toFixed(1) || 
                                          (file.stats.cache_hits + file.stats.cache_misses > 0 ? 
                                            (file.stats.cache_hits / (file.stats.cache_hits + file.stats.cache_misses) * 100).toFixed(1) : 0)
                                        }%
                                      </span>
                                    </div>
                                  </>
                                )}
                                
                                {/* Estadísticas de reintentos */}
                                {file.stats.rate_limit_retries > 0 && (
                                  <div className="flex justify-between">
                                    <span>Reintentos:</span>
                                    <span className="font-medium">{file.stats.rate_limit_retries}</span>
                                  </div>
                                )}
                                
                                {/* Estadísticas de tokens */}
                                <div className="col-span-2 mt-1 pt-1 border-t border-primary-50">
                                  <div className="font-medium mb-1">Tokens:</div>
                                  <div className="grid grid-cols-2 gap-x-4">
                                    <div className="flex justify-between">
                                      <span>Input:</span>
                                      <span>{file.stats.input_tokens.toLocaleString()}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Output:</span>
                                      <span>{file.stats.output_tokens.toLocaleString()}</span>
                                    </div>
                                    {file.stats.cached_tokens > 0 && (
                                      <div className="flex justify-between">
                                        <span>Caché:</span>
                                        <span>{file.stats.cached_tokens.toLocaleString()}</span>
                                      </div>
                                    )}
                                    <div className="flex justify-between">
                                      <span>Tokens/seg:</span>
                                      <span>{file.stats.tokens_per_second?.toFixed(1) || '0.0'}</span>
                                    </div>
                                  </div>
                                </div>
                                
                                {/* Costos detallados */}
                                <div className="col-span-2 mt-1 pt-1 border-t border-primary-50">
                                  <div className="font-medium mb-1">Costos:</div>
                                  <div className="grid grid-cols-2 gap-x-4">
                                    <div className="flex justify-between">
                                      <span>Input:</span>
                                      <span>${file.stats.input_cost.toFixed(4)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Output:</span>
                                      <span>${file.stats.output_cost.toFixed(4)}</span>
                                    </div>
                                    {file.stats.cached_cost > 0 && (
                                      <div className="flex justify-between">
                                        <span>Caché:</span>
                                        <span>${file.stats.cached_cost.toFixed(4)}</span>
                                      </div>
                                    )}
                                    <div className="flex justify-between font-medium">
                                      <span>Total:</span>
                                      <span>${file.stats.total_cost.toFixed(4)}</span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                
                {/* Botones de acción global */}
                <div className="mt-4 flex justify-center">
                  {isLoading && (
                    <button
                      onClick={handleCancelAll}
                      className="px-4 py-2 text-sm text-white bg-gradient-to-b from-[#e07a7a] to-[#c55757] hover:from-[#c55757] hover:to-[#b54545] rounded-lg shadow-sm transition-colors"
                    >
                      Cancelar todo
                    </button>
                  )}
                </div>
                
                {/* Resumen de estadísticas de procesamiento */}
                {processingFiles.some(file => file.status === 'processed' && file.stats) && (
                  <div className="mt-6 bg-primary-50 rounded-lg border border-primary-100 p-4">
                    <h3 className="text-primary-700 font-medium mb-3 flex items-center">
                      <FaCheckCircle className="text-green-500 mr-2" /> Resumen de procesamiento
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {/* Archivos procesados */}
                      <div className="bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Archivos procesados</h4>
                        <div className="flex justify-between">
                          <span className="font-bold text-lg">{processingFiles.filter(f => f.status === 'processed').length}</span>
                          <span className="text-xs text-gray-500 self-end">Total archivos</span>
                        </div>
                      </div>
                      
                      {/* Diapositivas procesadas */}
                      <div className="bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Diapositivas procesadas</h4>
                        <div className="flex justify-between">
                          <span className="font-bold text-lg">
                            {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.slides_processed || 0), 0)}
                          </span>
                          <span className="text-xs text-gray-500 self-end">Total</span>
                        </div>
                        {processingFiles.filter(f => f.status === 'processed' && f.stats && f.stats.slides_per_second).length > 0 && (
                          <div className="text-xs text-gray-500 mt-1">
                            Velocidad media: {(processingFiles.filter(f => f.status === 'processed' && f.stats)
                              .reduce((sum, f) => sum + (f.stats?.slides_per_second || 0), 0) / 
                              processingFiles.filter(f => f.status === 'processed' && f.stats && f.stats.slides_per_second).length
                            ).toFixed(2)} diap./seg.
                          </div>
                        )}
                      </div>
                      
                      {/* Textos traducidos */}
                      <div className="bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Textos traducidos</h4>
                        <div className="flex justify-between">
                          <span className="font-bold text-lg">
                            {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.texts_translated || 0), 0)}
                          </span>
                          <span className="text-xs text-gray-500 self-end">Total</span>
                        </div>
                      </div>
                      
                      {/* Llamadas a la API */}
                      <div className="bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Llamadas a la API</h4>
                        <div className="flex justify-between">
                          <span className="font-bold text-lg">
                            {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.api_calls || 0), 0)}
                          </span>
                          <span className="text-xs text-gray-500 self-end">Total</span>
                        </div>
                      </div>
                      
                      {/* Caché */}
                      <div className="bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Caché</h4>
                        <div className="flex flex-col">
                          <div className="flex justify-between text-sm">
                            <span>Hits:</span>
                            <span className="font-medium">
                              {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.cache_hits || 0), 0)}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span>Misses:</span>
                            <span className="font-medium">
                              {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.cache_misses || 0), 0)}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm mt-1 pt-1 border-t border-gray-100">
                            <span>Efectividad:</span>
                            <span className="font-medium">
                              {(() => {
                                const hits = processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.cache_hits || 0), 0);
                                const misses = processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.cache_misses || 0), 0);
                                const total = hits + misses;
                                if (total === 0) return '0%';
                                return `${(hits / total * 100).toFixed(1)}%`;
                              })()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      {/* Tiempo total */}
                      <div className="bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Tiempo total</h4>
                        <div className="flex justify-between">
                          <span className="font-bold text-lg">
                            {(processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.total_time || 0), 0)).toFixed(2)}s
                          </span>
                          <span className="text-xs text-gray-500 self-end">Total</span>
                        </div>
                      </div>
                      
                      {/* Estadísticas de tokens */}
                      <div className="col-span-1 md:col-span-2 lg:col-span-3 bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Tokens consumidos</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm">Input:</span>
                            <span className="text-sm font-medium">
                              {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.input_tokens || 0), 0).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Output:</span>
                            <span className="text-sm font-medium">
                              {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.output_tokens || 0), 0).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Caché:</span>
                            <span className="text-sm font-medium">
                              {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.cached_tokens || 0), 0).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex justify-between font-medium">
                            <span className="text-sm">Total:</span>
                            <span className="text-sm">
                              {processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (
                                (file.stats?.total_tokens) ||  
                                ((file.stats?.input_tokens || 0) + (file.stats?.output_tokens || 0) + (file.stats?.cached_tokens || 0))
                              ), 0).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      {/* Costos */}
                      <div className="col-span-1 md:col-span-2 lg:col-span-3 bg-white p-3 rounded-lg border border-primary-100 shadow-sm">
                        <h4 className="text-primary-600 text-sm font-medium mb-2">Costos estimados</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm">Input:</span>
                            <span className="text-sm font-medium">
                              ${processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.input_cost || 0), 0).toFixed(4)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Output:</span>
                            <span className="text-sm font-medium">
                              ${processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.output_cost || 0), 0).toFixed(4)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Caché:</span>
                            <span className="text-sm font-medium">
                              ${processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.cached_cost || 0), 0).toFixed(4)}
                            </span>
                          </div>
                          <div className="flex justify-between font-medium">
                            <span className="text-sm">Total:</span>
                            <span className="text-sm text-primary-700">
                              ${processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.total_cost || 0), 0).toFixed(4)}
                            </span>
                          </div>
                        </div>
                        
                        {/* Métricas de rendimiento */}
                        <div className="mt-2 pt-2 border-t border-primary-100 grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1">
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-500">Costo por diapositiva:</span>
                            <span className="text-xs font-medium">
                              ${(() => {
                                const totalCost = processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.total_cost || 0), 0);
                                const totalSlides = processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.slides_processed || 0), 0);
                                if (totalSlides === 0) return '0.0000';
                                return (totalCost / totalSlides).toFixed(4);
                              })()}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-500">Costo por 1000 tokens:</span>
                            <span className="text-xs font-medium">
                              ${(() => {
                                const totalCost = processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (file.stats?.total_cost || 0), 0);
                                const totalTokens = processingFiles.filter(f => f.status === 'processed' && f.stats).reduce((sum, file) => sum + (
                                  (file.stats?.total_tokens) ||  
                                  ((file.stats?.input_tokens || 0) + (file.stats?.output_tokens || 0) + (file.stats?.cached_tokens || 0))
                                ), 0);
                                if (totalTokens === 0) return '0.0000';
                                return ((totalCost * 1000) / totalTokens).toFixed(4);
                              })()}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="mt-3 text-xs text-gray-500 text-right">
                      Calculado según pricing actual de GPT-4o: $3.75/1M (input), $15.00/1M (output), $1.875/1M (cached)
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          <div className="space-y-4">
            {!isLoading && !processingFiles.some(file => file.status === 'processed') && (
              <button
                onClick={handleProcessAll}
                disabled={!selectedFiles || isLoading}
                className={`w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
                  !selectedFiles ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
                }`}
              >
                <MdGTranslate className="mr-2" />
                Traducir {selectedFiles && selectedFiles.length > 1 ? 'archivos' : 'archivo'}
              </button>
            )}
            
            {processingFiles.some(file => file.status === 'processed') && 
             !processingFiles.some(file => file.status === 'processing' || file.status === 'idle') && (
              <button
                onClick={handleDownloadAll}
                className="w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]"
              >
                <FaFileArchive className="mr-2" />
                Descargar todos (ZIP)
              </button>
            )}
            
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl flex items-center">
                <FaExclamationTriangle className="mr-2" />
                {error}
              </div>
            )}
          </div>
        </div>
      </div>
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué traducir presentaciones?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Permite divulgar contenidos en audiencias internacionales</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Facilita la comprensión para participantes de distintos países</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Ahorra tiempo comparado con la traducción manual</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Mantiene el formato y diseño original de la presentación</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Conferencias y eventos internacionales</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Materiales educativos para estudiantes extranjeros</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Documentación técnica para equipos multinacionales</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Marketing y presentaciones comerciales en mercados globales</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranslationTools; 