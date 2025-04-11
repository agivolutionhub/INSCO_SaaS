import React, { useState, useRef, useEffect } from 'react';
import { FaUpload, FaCog, FaDownload, FaCheckCircle, FaExclamationTriangle, FaCut, FaUndo } from 'react-icons/fa';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

const VideoCutTool = () => {
  // Estados básicos para el funcionamiento mínimo
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState<number>(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [startTime, setStartTime] = useState<number>(0);
  const [endTime, setEndTime] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [processedFiles, setProcessedFiles] = useState<Array<{url: string, name: string}>>([]);
  const [status, setStatus] = useState<'idle' | 'processing' | 'processed' | 'error'>('idle');
  const [progress, setProgress] = useState<number>(0);
  
  // Referencias
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Añadir esto en la parte superior del componente para manejar el estado del arrastre
  const [isDraggingStart, setIsDraggingStart] = useState<boolean>(false);
  const [isDraggingEnd, setIsDraggingEnd] = useState<boolean>(false);
  const sliderRef = useRef<HTMLDivElement>(null);
  
  // Manejar cambio de archivo
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      console.log("Archivo seleccionado:", file.name);
      
      // Resetear estados
      setSelectedFile(file);
      setError(null);
      setStatus('idle');
      setProcessedFiles([]);
      
      // Crear URL para el video
      const fileUrl = URL.createObjectURL(file);
      setVideoUrl(fileUrl);
      
      // Inicializar tiempos
      setStartTime(0);
      setEndTime(0);
      setDuration(0);
    }
  };
  
  // Formatear tiempo en mm:ss
  const formatTime = (time: number): string => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };
  
  // Establecer preview al punto inicial
  const setPreviewToStartPoint = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTime;
    }
  };
  
  // Establecer preview al punto final
  const setPreviewToEndPoint = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = endTime;
    }
  };
  
  // Restablecer selección
  const handleUndoSelection = () => {
    setStartTime(0);
    setEndTime(duration);
    
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
    }
  };
  
  // Función para simular la barra de progreso
  const startFakeProgressBar = () => {
    setProgress(0);
    const maxProgress = 90;
    const interval = setInterval(() => {
      setProgress(current => {
        if (current < maxProgress) {
          return current + 1;
        }
        return current;
      });
    }, 100);
    return interval;
  };

  // Añadir estas funciones para manejar el slider de rango
  const handleSliderMouseDown = (e: React.MouseEvent, isStartThumb: boolean) => {
    e.preventDefault();
    if (isStartThumb) {
      setIsDraggingStart(true);
    } else {
      setIsDraggingEnd(true);
    }
  };

  const handleSliderMouseMove = (e: MouseEvent) => {
    if (!isDraggingStart && !isDraggingEnd) return;
    if (!sliderRef.current) return;
    
    const rect = sliderRef.current.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, offsetX / rect.width));
    const newTime = percentage * duration;
    
    if (isDraggingStart) {
      // Asegurar que el punto de inicio no supere al final menos un margen
      const newStartTime = Math.min(newTime, endTime - 0.5);
      setStartTime(newStartTime);
      if (videoRef.current) {
        videoRef.current.currentTime = newStartTime;
      }
    } else if (isDraggingEnd) {
      // Asegurar que el punto final no sea menor que el inicio más un margen
      const newEndTime = Math.max(newTime, startTime + 0.5);
      setEndTime(newEndTime);
      if (videoRef.current) {
        videoRef.current.currentTime = newEndTime;
      }
    }
  };

  const handleSliderMouseUp = () => {
    setIsDraggingStart(false);
    setIsDraggingEnd(false);
  };

  // Actualizar las funciones para manejar eventos táctiles
  const handleSliderTouchMove = (e: TouchEvent) => {
    if (!isDraggingStart && !isDraggingEnd) return;
    if (!sliderRef.current || !e.touches[0]) return;
    
    const rect = sliderRef.current.getBoundingClientRect();
    const offsetX = e.touches[0].clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, offsetX / rect.width));
    const newTime = percentage * duration;
    
    if (isDraggingStart) {
      // Asegurar que el punto de inicio no supere al final menos un margen
      const newStartTime = Math.min(newTime, endTime - 0.5);
      setStartTime(newStartTime);
      if (videoRef.current) {
        videoRef.current.currentTime = newStartTime;
      }
    } else if (isDraggingEnd) {
      // Asegurar que el punto final no sea menor que el inicio más un margen
      const newEndTime = Math.max(newTime, startTime + 0.5);
      setEndTime(newEndTime);
      if (videoRef.current) {
        videoRef.current.currentTime = newEndTime;
      }
    }
  };

  const handleSliderTouchEnd = () => {
    setIsDraggingStart(false);
    setIsDraggingEnd(false);
  };

  // Actualizar el efecto para incluir eventos táctiles
  useEffect(() => {
    document.addEventListener('mousemove', handleSliderMouseMove);
    document.addEventListener('mouseup', handleSliderMouseUp);
    document.addEventListener('touchmove', handleSliderTouchMove, { passive: false });
    document.addEventListener('touchend', handleSliderTouchEnd);
    
    return () => {
      document.removeEventListener('mousemove', handleSliderMouseMove);
      document.removeEventListener('mouseup', handleSliderMouseUp);
      document.removeEventListener('touchmove', handleSliderTouchMove);
      document.removeEventListener('touchend', handleSliderTouchEnd);
    };
  }, [isDraggingStart, isDraggingEnd, startTime, endTime, duration]);

  // Procesar el video (cortar)
  const handleProcess = async () => {
    if (!selectedFile) {
      setError('Por favor seleccione un archivo de vídeo para cortar');
      return;
    }
    
    if (startTime >= endTime) {
      setError('El punto de inicio debe ser anterior al punto final');
      return;
    }
    
    setIsLoading(true);
    setStatus('processing');
    setError(null);
    
    // Iniciar barra de progreso
    const progressInterval = startFakeProgressBar();
    
    try {
      // Construir FormData para la solicitud
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      // Subir el archivo
      const uploadResponse = await fetch(`${API_BASE_URL}/api/upload-video-for-cut`, {
        method: 'POST',
        body: formData,
      });
      
      if (!uploadResponse.ok) {
        throw new Error('Error al subir el archivo');
      }
      
      const uploadResult = await uploadResponse.json();
      const fileId = uploadResult.file_id;
      
      // Solicitar el corte
      const cutResponse = await fetch(`${API_BASE_URL}/api/cut-video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_id: fileId,
          start_time: startTime,
          end_time: endTime,
          original_name: selectedFile.name.split('.')[0]
        }),
      });
      
      if (!cutResponse.ok) {
        throw new Error('Error al procesar el vídeo');
      }
      
      const result = await cutResponse.json();
      
      // Actualizar estado con el archivo procesado
      setProcessedFiles([{
        url: result.download_url,
        name: result.output_filename
      }]);
      
      setStatus('processed');
      setProgress(100);
      
    } catch (err) {
      console.error('Error en handleProcess:', err);
      setError(`Error al procesar el vídeo: ${err instanceof Error ? err.message : 'Error desconocido'}`);
      setStatus('error');
    } finally {
      clearInterval(progressInterval);
      setIsLoading(false);
    }
  };
  
  // Descargar archivo procesado
  const handleDownload = (url: string) => {
    if (url) {
      const fullUrl = `${API_BASE_URL}${url}`;
      console.log(`Descargando archivo desde: ${fullUrl}`);
      window.open(fullUrl, '_blank');
    }
  };
  
  // Escuchar eventos del video
  useEffect(() => {
    const video = videoRef.current;
    
    if (video && videoUrl) {
      console.log("Configurando eventos del vídeo");
      
      const handleTimeUpdate = () => {
        setCurrentTime(video.currentTime);
      };
      
      const handleLoadedMetadata = () => {
        console.log("Vídeo cargado, duración:", video.duration);
        if (video.duration && video.duration > 0) {
          setDuration(video.duration);
          setEndTime(video.duration);
        }
      };
      
      // Registrar eventos
      video.addEventListener('timeupdate', handleTimeUpdate);
      video.addEventListener('loadedmetadata', handleLoadedMetadata);
      
      // Limpiar eventos al desmontar
      return () => {
        video.removeEventListener('timeupdate', handleTimeUpdate);
        video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      };
    }
  }, [videoUrl]);
  
  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
        <h2 className="text-white font-medium text-center">Herramienta Cortar</h2>
      </div>
      
      <div className="p-6 bg-primary-50">
        {!videoUrl ? (
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
          </div>
        ) : null}
        
        {/* Reproductor de video */}
        {videoUrl && (
          <div className="mb-3">
            <div className="text-sm text-gray-600 text-center mb-2">
              Archivo seleccionado: <span className="font-medium">{selectedFile?.name}</span>
            </div>
            
            {/* Contenedor del vídeo */}
            <div className="border border-primary-200 rounded-xl overflow-hidden bg-black shadow-md">
              <div className="relative" style={{ paddingTop: '56.25%' }}> {/* Formato 16:9 */}
                <video 
                  ref={videoRef}
                  className="absolute top-0 left-0 w-full h-full object-contain"
                  src={videoUrl}
                  controls
                  preload="metadata"
                  onLoadedMetadata={(e) => {
                    console.log("Video cargado, duración:", e.currentTarget.duration);
                  }}
                ></video>
              </div>
            </div>
            
            {/* Selector de rango de corte simplificado */}
            <div className="mt-5 bg-white p-4 rounded-xl border border-primary-200 mb-4">
              <h3 className="text-sm font-medium text-primary-700 mb-3">Selección de segmento a cortar:</h3>
              
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-primary-600">Inicio: {formatTime(startTime)}</span>
                <span className="text-xs text-gray-500">hasta</span>
                <span className="text-xs text-primary-600">Final: {formatTime(endTime)}</span>
              </div>
              
              <div className="mt-4 mb-6 relative h-12" ref={sliderRef}>
                {/* Barra base */}
                <div className="absolute top-1/2 left-0 right-0 h-2 bg-gray-200 rounded-full transform -translate-y-1/2"></div>
                
                {/* Barra de selección */}
                <div 
                  className="absolute top-1/2 h-2 bg-primary-500 rounded-full transform -translate-y-1/2"
                  style={{
                    left: `${(startTime / duration) * 100}%`,
                    right: `${100 - (endTime / duration) * 100}%`
                  }}
                ></div>
                
                {/* Control deslizante de inicio */}
                <div 
                  className="absolute top-1/2 transform -translate-y-1/2 -translate-x-1/2 w-6 h-6 bg-primary-500 border-2 border-white rounded-full shadow-md cursor-grab touch-none z-10"
                  style={{ left: `${(startTime / duration) * 100}%` }}
                  onMouseDown={(e) => handleSliderMouseDown(e, true)}
                  onTouchStart={(e) => {
                    // Prevenir el comportamiento por defecto que puede causar problemas en móviles
                    e.preventDefault();
                    setIsDraggingStart(true);
                  }}
                ></div>
                
                {/* Control deslizante de fin */}
                <div 
                  className="absolute top-1/2 transform -translate-y-1/2 -translate-x-1/2 w-6 h-6 bg-primary-500 border-2 border-white rounded-full shadow-md cursor-grab touch-none z-10"
                  style={{ left: `${(endTime / duration) * 100}%` }}
                  onMouseDown={(e) => handleSliderMouseDown(e, false)}
                  onTouchStart={(e) => {
                    // Prevenir el comportamiento por defecto que puede causar problemas en móviles
                    e.preventDefault();
                    setIsDraggingEnd(true);
                  }}
                ></div>
              </div>
              
              <div className="text-xs text-center text-gray-500 mb-4">
                Duración del segmento seleccionado: {formatTime(endTime - startTime)}
              </div>
              
              <div className="flex justify-between">
                <button 
                  onClick={setPreviewToStartPoint}
                  className="text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-2 rounded"
                >
                  Ir a punto inicial
                </button>
                <button 
                  onClick={setPreviewToEndPoint}
                  className="text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-2 rounded"
                >
                  Ir a punto final
                </button>
              </div>
              
              {/* Botón para deshacer selección */}
              {(startTime > 0 || endTime < duration) && (
                <div className="mt-3 flex justify-center">
                  <button
                    onClick={handleUndoSelection}
                    className="flex items-center justify-center py-1 px-3 text-xs rounded-lg text-primary-700 bg-primary-100 hover:bg-primary-200"
                  >
                    <FaUndo className="mr-1" /> Restablecer selección
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Barra de progreso */}
        {isLoading && (
          <div className="mb-6 mt-2">
            <div className="flex justify-between text-sm text-primary-700 mb-2">
              <span className="font-medium flex items-center">
                <FaCog className="animate-spin mr-2" />
                Procesando vídeo...
              </span>
              <span className="font-medium">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 shadow-inner overflow-hidden">
              <div 
                className={`h-4 rounded-full transition-all duration-300 relative ${
                  error ? 'bg-red-500' : 'bg-gradient-to-r from-[#c79b6d] to-[#daaa7c]'
                }`}
                style={{ width: error ? '100%' : `${progress}%` }}
              >
                {!error && progress < 100 && (
                  <div className="absolute inset-0 bg-white bg-opacity-20 overflow-hidden flex">
                    <div className="h-full w-8 bg-white bg-opacity-30 transform -skew-x-30 animate-shimmer"></div>
                  </div>
                )}
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              {progress < 30 && "Analizando vídeo..."}
              {progress >= 30 && progress < 60 && "Cortando segmentos..."}
              {progress >= 60 && progress < 90 && "Generando archivo final..."}
              {progress >= 90 && "Finalizando proceso..."}
            </p>
          </div>
        )}
        
        {/* Botones de acción */}
        {videoUrl && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3">
              <button
                onClick={handleProcess}
                disabled={isLoading || startTime >= endTime}
                className={`flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
                  isLoading || startTime >= endTime
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
                    <FaCut className="mr-2" /> Cortar vídeo
                  </>
                )}
              </button>
            </div>
            
            {/* Lista de archivos procesados */}
            {processedFiles.length > 0 && (
              <div className="mt-4 bg-primary-100 p-5 rounded-xl border border-primary-200">
                <div className="mb-4 border-b border-primary-200 pb-3">
                  <h3 className="text-lg font-medium text-primary-800 text-center">Archivo generado:</h3>
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
              </div>
            )}
          </div>
        )}
        
        {/* Mensajes de error y éxito */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg flex items-center justify-center border border-red-200">
            <FaExclamationTriangle className="mr-2" /> {error}
          </div>
        )}
        
        {status === 'processed' && processedFiles.length > 0 && (
          <div className="mt-4 p-3 bg-green-50 text-green-600 rounded-lg flex items-center justify-center border border-green-200">
            <FaCheckCircle className="mr-2" /> Vídeo procesado correctamente. Listo para descargar.
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoCutTool; 