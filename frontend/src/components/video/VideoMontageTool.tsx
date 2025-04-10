import React, { useState, useRef, useEffect } from 'react';
import { FaUpload, FaCog, FaDownload, FaCheckCircle, FaExclamationTriangle, FaPlay, FaPause, FaTrash, FaImage, FaMusic, FaArrowUp, FaArrowDown, FaVideo } from 'react-icons/fa';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

// Interfaz para una imagen en el montaje
interface MontageImage {
  id: string;
  file: File;
  url: string;
  startTime: number; // Tiempo de inicio en segundos
}

const VideoMontageTool = () => {
  // Estados para el audio
  const [selectedAudioFile, setSelectedAudioFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [playbackRate, setPlaybackRate] = useState<number>(1);
  
  // Estados para las imágenes
  const [images, setImages] = useState<MontageImage[]>([]);
  const [currentImageIndex, setCurrentImageIndex] = useState<number>(0);
  
  // Estados para procesamiento
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'processed' | 'error'>('idle');
  const [processedFile, setProcessedFile] = useState<{url: string, name: string} | null>(null);
  
  // Referencias
  const audioRef = useRef<HTMLAudioElement>(null);
  const waveformRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Nuevo estado para el modo simulación
  const [simulationMode, setSimulationMode] = useState<boolean>(false);
  
  // Formato tiempo en mm:ss o hh:mm:ss
  const formatTime = (time: number): string => {
    const hours = Math.floor(time / 3600);
    const minutes = Math.floor((time % 3600) / 60);
    const seconds = Math.floor(time % 60);
    
    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };
  
  // Generar ID único
  const generateId = (): string => {
    return Date.now().toString(36) + Math.random().toString(36).substring(2);
  };
  
  // Verificar conexión con el backend al cargar
  useEffect(() => {
    const checkBackendConnection = async () => {
      try {
        // Intentar hacer una petición simple al backend
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        
        const response = await fetch(`${API_BASE_URL}`, { 
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
          console.log('Conexión con el backend establecida correctamente');
          setSimulationMode(false);
        } else {
          console.warn('El backend está disponible pero responde con error:', response.status);
          setSimulationMode(true);
        }
      } catch (error) {
        console.warn('No se pudo conectar con el backend, activando modo simulación:', error);
        setSimulationMode(true);
      }
    };
    
    checkBackendConnection();
  }, []);
  
  // Manejar carga del archivo de audio
  const handleAudioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedAudioFile(file);
      setStatus('idle');
      setError(null);
      
      // Crear URL para el audio
      const audioUrl = URL.createObjectURL(file);
      setAudioUrl(audioUrl);
      
      // Resetear otros estados
      setIsPlaying(false);
      setCurrentTime(0);
      
      // Si ya hay imágenes cargadas, actualizar sus posiciones de tiempo
      if (images.length > 0) {
        const audioElement = new Audio(audioUrl);
        audioElement.onloadedmetadata = () => {
          const newDuration = audioElement.duration;
          setAudioDuration(newDuration);
          
          // Mantener las posiciones relativas de las imágenes
          if (audioDuration > 0 && newDuration > 0) {
            const ratio = newDuration / audioDuration;
            setImages(images.map((img, index) => ({
              ...img,
              startTime: index === 0 ? 0 : Math.min(img.startTime * ratio, newDuration)
            })));
          }
        };
      }
    }
  };
  
  // Manejar carga de imágenes
  const handleImagesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newImages: MontageImage[] = [];
      
      // Convertir FileList a Array
      const fileArray = Array.from(e.target.files);
      
      // Procesar cada archivo
      fileArray.forEach((file, index) => {
        // Crear un objeto URL para la previsualización
        const url = URL.createObjectURL(file);
        
        // Calcular tiempo de inicio (si es la primera imagen, empieza en 0)
        const startTime = index === 0 ? 0 : 
          (index / fileArray.length) * (audioDuration > 0 ? audioDuration : 60);
        
        newImages.push({
          id: generateId(),
          file,
          url,
          startTime
        });
      });
      
      // Ordenar por tiempo de inicio
      newImages.sort((a, b) => a.startTime - b.startTime);
      
      // Actualizar estado
      setImages(newImages);
    }
  };
  
  // Agregar más imágenes a las existentes
  const handleAddMoreImages = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const additionalImages: MontageImage[] = [];
      
      // Convertir FileList a Array
      const fileArray = Array.from(e.target.files);
      
      // Procesar cada archivo
      fileArray.forEach((file) => {
        // Crear un objeto URL para la previsualización
        const url = URL.createObjectURL(file);
        
        // Por defecto, agregar al final con una distribución equitativa
        const lastImageTime = images.length > 0 ? 
          images[images.length - 1].startTime : 0;
        
        const timeGap = audioDuration > 0 ? 
          (audioDuration - lastImageTime) / (fileArray.length + 1) : 5;
        
        additionalImages.push({
          id: generateId(),
          file,
          url,
          startTime: lastImageTime + timeGap
        });
      });
      
      // Combinar con las imágenes existentes y ordenar
      const updatedImages = [...images, ...additionalImages];
      updatedImages.sort((a, b) => a.startTime - b.startTime);
      
      // Actualizar estado
      setImages(updatedImages);
    }
  };
  
  // Eliminar una imagen
  const handleRemoveImage = (id: string) => {
    setImages(images.filter(img => img.id !== id));
  };
  
  // Actualizar la posición de tiempo de una imagen
  const handleUpdateImageTime = (id: string, newTime: number) => {
    // Asegurarse de que el tiempo esté dentro de los límites válidos
    const validTime = Math.max(0, Math.min(newTime, audioDuration));
    
    // Actualizar el tiempo de la imagen
    const updatedImages = images.map(img => 
      img.id === id ? { ...img, startTime: validTime } : img
    );
    
    // Reordenar las imágenes por tiempo
    updatedImages.sort((a, b) => a.startTime - b.startTime);
    
    // Actualizar estado
    setImages(updatedImages);
  };
  
  // Mover imagen hacia arriba en la lista
  const handleMoveImageUp = (index: number) => {
    if (index <= 0) return; // No se puede mover la primera imagen
    
    const updatedImages = [...images];
    // Intercambiar posiciones en el array
    [updatedImages[index], updatedImages[index - 1]] = [updatedImages[index - 1], updatedImages[index]];
    
    // Intercambiar también los tiempos de inicio
    const tempStartTime = updatedImages[index].startTime;
    updatedImages[index].startTime = updatedImages[index - 1].startTime;
    updatedImages[index - 1].startTime = tempStartTime;
    
    // Ordenar por tiempo
    updatedImages.sort((a, b) => a.startTime - b.startTime);
    
    setImages(updatedImages);
  };
  
  // Mover imagen hacia abajo en la lista
  const handleMoveImageDown = (index: number) => {
    if (index >= images.length - 1) return; // No se puede mover la última imagen
    
    const updatedImages = [...images];
    // Intercambiar posiciones en el array
    [updatedImages[index], updatedImages[index + 1]] = [updatedImages[index + 1], updatedImages[index]];
    
    // Intercambiar también los tiempos de inicio
    const tempStartTime = updatedImages[index].startTime;
    updatedImages[index].startTime = updatedImages[index + 1].startTime;
    updatedImages[index + 1].startTime = tempStartTime;
    
    // Ordenar por tiempo
    updatedImages.sort((a, b) => a.startTime - b.startTime);
    
    setImages(updatedImages);
  };
  
  // Reproducir/pausar audio
  const togglePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };
  
  // Cambiar la velocidad de reproducción
  const changePlaybackRate = (rate: number) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };
  
  // Barra de progreso simulada
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
  
  // Procesar y generar el vídeo final
  const handleProcess = async () => {
    if (!selectedAudioFile || images.length === 0) {
      setError('Por favor cargue un archivo de audio y al menos una imagen');
      return;
    }
    
    setIsLoading(true);
    setStatus('processing');
    setError(null);
    
    // Iniciar barra de progreso
    const progressInterval = startFakeProgressBar();
    
    try {
      // Modo simulación (cuando el backend no está disponible)
      if (simulationMode) {
        console.log('Ejecutando en modo simulación (sin backend)');
        
        // Simulamos un proceso que toma tiempo
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Generar un nombre para el archivo simulado
        const simulatedFileName = `${selectedAudioFile.name.split('.')[0]}_montaje.mp4`;
        
        // Establecer un archivo simulado
        setProcessedFile({
          url: '#', // URL ficticia
          name: simulatedFileName
        });
        
        setStatus('processed');
        setProgress(100);
        
        // Terminar aquí en modo simulación
        clearInterval(progressInterval);
        setIsLoading(false);
        return;
      }
      
      // --- Modo real (con backend) ---
      
      // 1. Subir el archivo de audio
      const audioFormData = new FormData();
      audioFormData.append('file', selectedAudioFile);
      
      console.log('Subiendo archivo de audio...');
      const audioResponse = await fetch(`${API_BASE_URL}/api/upload-audio-for-montage`, {
        method: 'POST',
        body: audioFormData,
      });
      
      if (!audioResponse.ok) {
        throw new Error(`Error al subir el audio: ${audioResponse.status} ${audioResponse.statusText}`);
      }
      
      const audioResult = await audioResponse.json();
      const audioId = audioResult.file_id;
      
      if (!audioId) {
        throw new Error('La respuesta del servidor no incluyó un ID para el archivo de audio');
      }
      
      console.log('Audio subido correctamente con ID:', audioId);
      
      // 2. Subir las imágenes
      const imageIds = [];
      
      for (const image of images) {
        const imageFormData = new FormData();
        imageFormData.append('file', image.file);
        
        console.log(`Subiendo imagen ${image.file.name}...`);
        const imageResponse = await fetch(`${API_BASE_URL}/api/upload-image-for-montage`, {
          method: 'POST',
          body: imageFormData,
        });
        
        if (!imageResponse.ok) {
          throw new Error(`Error al subir la imagen ${image.file.name}: ${imageResponse.status} ${imageResponse.statusText}`);
        }
        
        const imageResult = await imageResponse.json();
        const imageId = imageResult.file_id;
        
        if (!imageId) {
          throw new Error(`La respuesta del servidor no incluyó un ID para la imagen ${image.file.name}`);
        }
        
        imageIds.push({
          id: imageId,
          startTime: image.startTime
        });
        
        console.log(`Imagen ${image.file.name} subida correctamente con ID:`, imageId);
      }
      
      // 3. Solicitar la generación del vídeo usando el endpoint específico de montaje
      console.log('Generando montaje de vídeo...');
      const montageResponse = await fetch(`${API_BASE_URL}/api/generate-montage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          audio_id: audioId,
          images: imageIds,
          original_name: selectedAudioFile.name.split('.')[0],
          output_format: 'mp4'
        }),
      });
      
      if (!montageResponse.ok) {
        const errorText = await montageResponse.text();
        throw new Error(`Error al generar el montaje: ${montageResponse.status} ${montageResponse.statusText} - ${errorText}`);
      }
      
      const result = await montageResponse.json();
      console.log('Respuesta de generación de montaje:', result);
      
      // Extraer la información del resultado
      const downloadUrl = result.download_url;
      const fileName = result.output_filename;
      
      if (!downloadUrl) {
        throw new Error('La respuesta del servidor no incluye una URL para descargar el archivo');
      }
      
      // Actualizar estado con el archivo procesado
      setProcessedFile({
        url: downloadUrl,
        name: fileName
      });
      
      setStatus('processed');
      setProgress(100);
      
    } catch (err) {
      console.error('Error en handleProcess:', err);
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      setError(`Error al procesar el montaje: ${errorMessage}`);
      setStatus('error');
    } finally {
      clearInterval(progressInterval);
      setIsLoading(false);
    }
  };
  
  // Descargar el vídeo generado
  const handleDownload = (url: string) => {
    if (simulationMode) {
      alert('Modo simulación: En un entorno real, aquí se descargaría el archivo de vídeo generado.');
      return;
    }
    
    if (url) {
      // Si la URL ya es absoluta, no añadir el API_BASE_URL
      const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
      console.log(`Descargando archivo desde: ${fullUrl}`);
      window.open(fullUrl, '_blank');
    }
  };
  
  // Dibujar la forma de onda del audio
  const drawWaveform = (audioBuffer: AudioBuffer) => {
    if (!canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Ajustar el tamaño del canvas
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    
    // Obtener los datos del canal izquierdo
    const data = audioBuffer.getChannelData(0);
    const step = Math.ceil(data.length / canvas.width);
    const amp = canvas.height / 2;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.moveTo(0, amp);
    
    // Dibujar la forma de onda
    for (let i = 0; i < canvas.width; i++) {
      let min = 1.0;
      let max = -1.0;
      
      for (let j = 0; j < step; j++) {
        const datum = data[(i * step) + j];
        if (datum < min) min = datum;
        if (datum > max) max = datum;
      }
      
      ctx.lineTo(i, (1 + min) * amp);
      ctx.lineTo(i, (1 + max) * amp);
    }
    
    ctx.strokeStyle = '#c29e74';
    ctx.stroke();
  };
  
  // Efecto para manejar la reproducción de audio y actualizar la imagen actual
  useEffect(() => {
    const audio = audioRef.current;
    
    if (audio && audioUrl) {
      const handleTimeUpdate = () => {
        setCurrentTime(audio.currentTime);
        
        // Determinar la imagen actual
        let activeIndex = 0;
        for (let i = images.length - 1; i >= 0; i--) {
          if (audio.currentTime >= images[i].startTime) {
            activeIndex = i;
            break;
          }
        }
        setCurrentImageIndex(activeIndex);
      };
      
      const handleEnded = () => {
        setIsPlaying(false);
        setCurrentTime(0);
      };
      
      const handleLoadedMetadata = () => {
        setAudioDuration(audio.duration);
        
        // Si no hay imágenes o sólo hay una, no hacer nada más
        if (images.length <= 1) return;
        
        // Distribuir equitativamente las imágenes a lo largo del audio
        const newImages = [...images];
        newImages.forEach((img, index) => {
          if (index === 0) {
            img.startTime = 0; // La primera imagen siempre empieza en 0
          } else {
            img.startTime = (index / (images.length)) * audio.duration;
          }
        });
        
        setImages(newImages);
      };
      
      // Añadir event listeners
      audio.addEventListener('timeupdate', handleTimeUpdate);
      audio.addEventListener('ended', handleEnded);
      audio.addEventListener('loadedmetadata', handleLoadedMetadata);
      
      // Limpiar event listeners
      return () => {
        audio.removeEventListener('timeupdate', handleTimeUpdate);
        audio.removeEventListener('ended', handleEnded);
        audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      };
    }
  }, [audioUrl, images.length]);
  
  // Efecto para cargar el archivo de audio y analizar su forma de onda
  useEffect(() => {
    if (audioUrl && canvasRef.current) {
      // Crear un contexto de audio
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      // Cargar el archivo de audio
      fetch(audioUrl)
        .then(response => response.arrayBuffer())
        .then(arrayBuffer => audioContext.decodeAudioData(arrayBuffer))
        .then(audioBuffer => {
          // Dibujar la forma de onda
          drawWaveform(audioBuffer);
        })
        .catch(error => {
          console.error('Error al cargar el audio:', error);
        });
    }
  }, [audioUrl, canvasRef.current]);
  
  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
        <h2 className="text-white font-medium text-center">Herramienta Montaje</h2>
      </div>
      
      <div className="p-6 bg-primary-50">
        <div className="text-center text-gray-700 mb-4">
          Esta herramienta permite crear un vídeo combinando audio con una secuencia de imágenes.
        </div>
        
        {/* 1. Previsualización (ahora en la parte superior) */}
        {images.length > 0 && (
          <div className="mb-6">
            <div className="bg-[#f3efe7] p-4 rounded-lg">
              <h3 className="text-sm font-medium text-[#8d6e4c] mb-3 flex items-center">
                <FaVideo className="mr-2" /> Previsualización
              </h3>
              
              <div className="rounded-lg overflow-hidden bg-black aspect-video mb-4">
                <img 
                  src={images[currentImageIndex]?.url || ''} 
                  alt="Previsualización actual" 
                  className="w-full h-full object-contain"
                />
              </div>
              
              <div className="text-xs text-center text-gray-600">
                Reproducir el audio para previsualizar las transiciones de imágenes
              </div>
            </div>
          </div>
        )}
        
        {/* 2. Reproductor de audio con forma de onda */}
        <div className="mb-6">
          <h4 className="text-[#8d6e4c] font-medium mb-2 flex items-center">
            <FaMusic className="mr-2" /> Audio para el montaje
          </h4>
          
          {!audioUrl ? (
            <div className="flex items-center justify-center w-full">
              <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-[#e2d5c3] rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
                <div className="flex flex-col items-center justify-center pt-4 pb-5">
                  <FaUpload className="w-6 h-6 mb-2 text-[#c29e74]" />
                  <p className="mb-1 text-sm text-gray-700 text-center">
                    <span className="font-semibold">Haga clic para cargar audio</span>
                  </p>
                  <p className="text-xs text-gray-500 text-center">MP3, WAV, M4A</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept="audio/*"
                  onChange={handleAudioChange}
                  disabled={isLoading}
                />
              </label>
            </div>
          ) : (
            <div>
              <div className="text-xs text-gray-600 mb-2 flex items-center">
                <span className="bg-[#f3efe7] px-2 py-1 rounded">
                  {selectedAudioFile?.name}
                </span>
                <button
                  onClick={() => {
                    setAudioUrl(null);
                    setSelectedAudioFile(null);
                    setAudioDuration(0);
                    setCurrentTime(0);
                  }}
                  className="text-xs flex items-center text-red-600 hover:text-red-700 ml-2"
                >
                  <FaTrash size={10} />
                </button>
              </div>
              
              {/* Reproductor de audio con forma de onda */}
              <div className="bg-gray-50 rounded-lg p-2">
                <div className="flex items-center mb-2">
                  <button 
                    onClick={togglePlayPause}
                    className="bg-[#c29e74] text-white rounded-full p-3 mr-3 hover:bg-[#b08c62] flex-shrink-0 shadow-sm"
                  >
                    {isPlaying ? <FaPause size={18} /> : <FaPlay size={18} />}
                  </button>
                  
                  <div ref={waveformRef} className="relative flex-grow">
                    <canvas ref={canvasRef} className="w-full h-16"></canvas>
                    <div 
                      className="absolute top-0 left-0 h-full w-0.5 bg-red-500"
                      style={{ 
                        left: `${(currentTime / audioDuration) * 100}%`,
                        transition: 'left 0.1s linear'
                      }}
                    ></div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between mt-1">
                  <div className="text-xs text-gray-600">{formatTime(currentTime)}</div>
                  
                  <div className="flex space-x-1">
                    {[1, 1.5, 2].map(rate => (
                      <button 
                        key={rate}
                        onClick={() => changePlaybackRate(rate)}
                        className={`text-xs px-2 py-1 rounded ${
                          playbackRate === rate
                            ? 'bg-[#c29e74] text-white'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        x{rate}
                      </button>
                    ))}
                  </div>
                  
                  <div className="text-xs text-gray-600">{formatTime(audioDuration)}</div>
                </div>
                
                <audio 
                  ref={audioRef}
                  src={audioUrl}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onEnded={() => setIsPlaying(false)}
                  onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime || 0)}
                  className="hidden"
                ></audio>
              </div>
            </div>
          )}
        </div>
        
        {/* 3. Sección de sliders y posicionamiento de imágenes */}
        <div className="mb-6">
          <h4 className="text-[#8d6e4c] font-medium mb-2 flex items-center">
            <FaImage className="mr-2" /> Imágenes para el montaje
          </h4>
          
          {images.length === 0 ? (
            <div className="flex items-center justify-center w-full">
              <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-[#e2d5c3] rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
                <div className="flex flex-col items-center justify-center pt-4 pb-5">
                  <FaUpload className="w-6 h-6 mb-2 text-[#c29e74]" />
                  <p className="mb-1 text-sm text-gray-700 text-center">
                    <span className="font-semibold">Haga clic para cargar imágenes</span>
                  </p>
                  <p className="text-xs text-gray-500 text-center">JPG, PNG, WEBP (múltiples)</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept="image/*"
                  multiple
                  onChange={handleImagesChange}
                  disabled={isLoading}
                />
              </label>
            </div>
          ) : (
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-gray-600 bg-[#f3efe7] px-2 py-1 rounded">
                  {images.length} {images.length === 1 ? 'imagen' : 'imágenes'}
                </span>
                
                <label className="text-xs cursor-pointer flex items-center bg-[#f3efe7] hover:bg-[#e9e1d4] text-[#8d6e4c] px-2 py-1 rounded">
                  <FaUpload className="mr-1" size={10} /> Añadir más
                  <input
                    type="file"
                    className="hidden"
                    accept="image/*"
                    multiple
                    onChange={handleAddMoreImages}
                    disabled={isLoading}
                  />
                </label>
              </div>
              
              <div className="overflow-y-auto max-h-40 pr-1 bg-gray-50 rounded-lg p-1">
                {images.map((image, index) => (
                  <div 
                    key={image.id}
                    className={`flex items-center border-b border-gray-100 py-1 ${
                      index === currentImageIndex && isPlaying
                        ? 'bg-[#f3efe7]'
                        : ''
                    }`}
                  >
                    <div className="w-6 h-6 flex-shrink-0 mr-2 bg-gray-100 rounded overflow-hidden">
                      <img src={image.url} alt={`Imagen ${index + 1}`} className="w-full h-full object-cover" />
                    </div>
                    
                    <div className="flex-grow">
                      <div className="flex items-center">
                        <div className="text-xs text-[#8d6e4c] w-12 flex-shrink-0">
                          {formatTime(image.startTime)}
                        </div>
                        
                        <input 
                          type="range"
                          min="0"
                          max={audioDuration}
                          step="0.1"
                          value={image.startTime}
                          onChange={(e) => handleUpdateImageTime(image.id, parseFloat(e.target.value))}
                          disabled={index === 0} // La primera imagen siempre empieza en 0
                          className={`flex-grow h-1 rounded-lg appearance-none cursor-pointer ${
                            index === 0 ? 'bg-gray-300' : 'bg-gray-200'
                          }`}
                        />
                      </div>
                    </div>
                    
                    <div className="flex space-x-1 ml-1">
                      <button
                        onClick={() => handleMoveImageUp(index)}
                        disabled={index === 0}
                        className={`p-0.5 rounded-full ${
                          index === 0
                            ? 'text-gray-300 cursor-not-allowed'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        <FaArrowUp size={8} />
                      </button>
                      
                      <button
                        onClick={() => handleMoveImageDown(index)}
                        disabled={index === images.length - 1}
                        className={`p-0.5 rounded-full ${
                          index === images.length - 1
                            ? 'text-gray-300 cursor-not-allowed'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        <FaArrowDown size={8} />
                      </button>
                      
                      <button
                        onClick={() => handleRemoveImage(image.id)}
                        disabled={isLoading}
                        className="p-0.5 text-red-500 hover:text-red-700 rounded-full hover:bg-gray-100"
                      >
                        <FaTrash size={8} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Barra de progreso */}
        {isLoading && (
          <div className="mb-6 mt-2">
            <div className="flex justify-between text-sm text-[#8d6e4c] mb-2">
              <span className="font-medium flex items-center">
                <FaCog className="animate-spin mr-2" />
                Procesando montaje...
              </span>
              <span className="font-medium">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 shadow-inner">
              <div 
                className="bg-[#c29e74] h-4 rounded-full transition-all duration-300 flex items-center justify-end"
                style={{ width: `${progress}%` }}
              >
                <div className="bg-[#a78559] h-2 w-10 rounded-full animate-pulse mx-2" 
                     style={{ display: progress < 10 ? 'none' : 'block' }}></div>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              {progress < 30 && "Preparando archivos..."}
              {progress >= 30 && progress < 60 && "Creando secuencia de imágenes..."}
              {progress >= 60 && progress < 90 && "Generando vídeo final..."}
              {progress >= 90 && "Finalizando proceso..."}
            </p>
          </div>
        )}
        
        {/* Botón de acción */}
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3">
            <button
              onClick={handleProcess}
              disabled={isLoading || !selectedAudioFile || images.length === 0}
              className={`flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
                isLoading || !selectedAudioFile || images.length === 0
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-b from-[#c29e74] to-[#a78559] hover:bg-gradient-to-b hover:from-[#b08c62] hover:to-[#967547]'
              }`}
            >
              {isLoading ? (
                <>
                  <FaCog className="animate-spin mr-2" />
                  Procesando...
                </>
              ) : (
                <>
                  <FaVideo className="mr-2" /> Realizar montaje
                </>
              )}
            </button>
          </div>
          
          {/* Archivo procesado */}
          {processedFile && (
            <div className="mt-4 bg-[#f3efe7] p-5 rounded-xl border border-[#e2d5c3]">
              <div className="mb-4 border-b border-[#e2d5c3] pb-3">
                <h3 className="text-lg font-medium text-[#8d6e4c] text-center">Archivo generado:</h3>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-[#e2d5c3]">
                  <span className="text-[#8d6e4c] font-medium truncate pr-4" style={{ flex: '1 1 auto', minWidth: 0 }}>
                    {processedFile.name}
                  </span>
                  <button
                    onClick={() => handleDownload(processedFile.url)}
                    className="bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white px-3 py-2 rounded-lg text-sm flex items-center flex-shrink-0 shadow-md"
                  >
                    <FaDownload className="mr-2" /> Descargar
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Mensajes de error y éxito */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg flex items-center justify-center border border-red-200">
            <FaExclamationTriangle className="mr-2" /> {error}
          </div>
        )}
        
        {status === 'processed' && processedFile && (
          <div className="mt-4 p-3 bg-green-50 text-green-600 rounded-lg flex items-center justify-center border border-green-200">
            <FaCheckCircle className="mr-2" /> Vídeo generado correctamente. Listo para descargar.
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoMontageTool; 