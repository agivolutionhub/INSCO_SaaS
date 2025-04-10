import React, { useState, useRef, useEffect } from 'react';
import { FaUpload, FaCog, FaDownload, FaCheckCircle, FaExclamationTriangle, FaVolumeUp, FaPlay, FaPause } from 'react-icons/fa';
import { MdRecordVoiceOver } from 'react-icons/md';
import { TbPlayerSkipForward, TbPlayerSkipBack } from 'react-icons/tb';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

interface Voice {
  id: string;
  description: string;
  gender: string;
}

const AudioGenerateTool = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'processed' | 'error'>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>('echo');
  const [processedFile, setProcessedFile] = useState<{url: string, name: string} | null>(null);
  const [speedValue] = useState<number>(1.0);
  const [pauseDuration, setPauseDuration] = useState<number>(1300);
  const [audioStats, setAudioStats] = useState<any>(null);
  const [currentSegment, setCurrentSegment] = useState<number>(0);
  const [totalSegments, setTotalSegments] = useState<number>(0);
  const [segmentInfo, setSegmentInfo] = useState<{duration: string, chars: number} | null>(null);
  const [progressMessage, setProgressMessage] = useState<string>("Preparando proceso...");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef<number | null>(null);
  const [uploadedFileInfo, setUploadedFileInfo] = useState<any>(null);

  // Cargar voces disponibles al iniciar
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/voices`)
      .then(response => response.json())
      .then(data => {
        if (data.voices && Array.isArray(data.voices)) {
          setVoices(data.voices);
        }
      })
      .catch(err => {
        console.error('Error al cargar voces:', err);
      });
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      
      // Verificar si es un archivo JSON o TXT
      if (!file.name.endsWith('.json') && !file.name.endsWith('.txt')) {
        setError('Por favor seleccione un archivo JSON o TXT');
        return;
      }
      
      setSelectedFile(file);
      setError(null);
      setStatus('idle');
      setProgress(0);
      setAudioUrl(null);
      setProcessedFile(null);
    }
  };

  // Función para simular la barra de progreso con estimación más realista
  const startFakeProgressBar = () => {
    setProgress(0);
    setProgressMessage("Analizando texto...");
    
    // Estimar el número de segmentos basado en el tamaño del archivo
    const fileSize = selectedFile?.size || 0;
    const estimatedSegments = Math.max(10, Math.ceil(fileSize / 1000)); // ~1KB por segmento como estimación
    setTotalSegments(estimatedSegments);
    
    // Calcular el progreso máximo por segmento (reservando 10% para la finalización)
    const maxProgressPerSegment = 90 / estimatedSegments;
    
    // Inicializar variables para controlar la simulación
    let simulatedSegment = 0;
    let currentProgress = 0;
    let intervalId: number;
    
    console.log(`Archivo de ${fileSize} bytes. Estimado: ~${estimatedSegments} segmentos`);
    
    // Función para simular el procesamiento de un segmento
    const processSegment = () => {
      // Si ya alcanzamos el 90%, mantener ese valor hasta que el proceso termine realmente
      if (currentProgress >= 90) {
        clearInterval(intervalId);
        setProgressMessage("Finalizando proceso...");
        return;
      }
      
      // Incrementar el segmento simulado
      simulatedSegment++;
      setCurrentSegment(simulatedSegment);
      
      // Simular información del segmento
      const avgCharsPerSegment = Math.ceil(fileSize / estimatedSegments / 2);
      const randomChars = avgCharsPerSegment + Math.floor(Math.random() * avgCharsPerSegment);
      const randomDuration = (1 + Math.random() * 3).toFixed(2);
      
      setSegmentInfo({
        duration: randomDuration + "s",
        chars: randomChars
      });
      
      // Actualizar mensaje de progreso
      setProgressMessage(`Segmento ${simulatedSegment}/${estimatedSegments}: ~${randomDuration}s | ~${randomChars} caracteres`);
      
      // Calcular el nuevo progreso basado en el número de segmentos estimados
      // Avanzar un poco más lento que la estimación real para evitar llegar al 90% demasiado rápido
      const segmentProgress = maxProgressPerSegment * 0.7; // 70% del avance estimado por segmento
      currentProgress = Math.min(
        90, // Nunca superar el 90%
        currentProgress + segmentProgress + (Math.random() * segmentProgress * 0.3) // Añadir algo de variabilidad
      );
      
      setProgress(Math.floor(currentProgress));
      
      // Si hemos procesado todos los segmentos estimados pero no llegamos al 90%,
      // ralentizar drásticamente el avance para evitar llegar al 90% demasiado pronto
      if (simulatedSegment >= estimatedSegments && currentProgress < 85) {
        clearInterval(intervalId);
        setProgressMessage("Aplicando efectos de audio y normalizando...");
        // Continuar con incrementos muy pequeños
        const slowInterval = setInterval(() => {
          currentProgress = Math.min(85, currentProgress + 0.1);
          setProgress(Math.floor(currentProgress));
          
          if (currentProgress >= 85) {
            clearInterval(slowInterval);
            setProgressMessage("Preparando audio final...");
          }
        }, 1000); // Cada segundo
      }
    };
    
    // Simular tiempo inicial de preparación (2 segundos) antes de empezar con los segmentos
    setTimeout(() => {
      setProgress(5); // Mostrar algo de progreso inicial
      setProgressMessage("Generando primer segmento de audio...");
      
      // Iniciar procesamiento de segmentos simulados
      intervalId = setInterval(processSegment, 4000); // ~4 segundos por segmento como estimación
    }, 2000);
    
    // Devolver un identificador de intervalo para poder limpiarlo posteriormente
    const cleanupInterval = setInterval(() => {}, 10000);
    return cleanupInterval;
  };

  const handleProcess = async () => {
    if (!selectedFile) {
      setError('Por favor seleccione un archivo de transcripción para generar audio');
      return;
    }

    setIsLoading(true);
    setStatus('processing');
    setError(null);
    setProgress(0);
    
    // Iniciar la simulación de progreso
    const progressInterval = startFakeProgressBar();

    try {
      console.log("Iniciando generación de audio...");
      
      // Paso 1: Subir el archivo al servidor
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const uploadResponse = await fetch(`${API_BASE_URL}/api/upload-transcript-for-audio`, {
        method: 'POST',
        body: formData,
      });
      
      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json();
        throw new Error(errorData.detail || 'Error al subir el archivo');
      }
      
      const uploadResult = await uploadResponse.json();
      console.log("Archivo subido:", uploadResult);
      setUploadedFileInfo(uploadResult);
      
      // Paso 2: Iniciar la generación de audio
      const generateData = {
        file_id: uploadResult.file_id,
        original_name: uploadResult.original_name,
        voice: selectedVoice,
        model: "gpt-4o-mini-tts",
        speed: speedValue,
        pause_duration_ms: pauseDuration
      };
      
      const generateResponse = await fetch(`${API_BASE_URL}/api/generate-audio`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(generateData),
      });
      
      if (!generateResponse.ok) {
        const errorData = await generateResponse.json();
        throw new Error(errorData.detail || 'Error al generar el audio');
      }
      
      const generateResult = await generateResponse.json();
      console.log("Audio generado:", generateResult);
      
      // Guardar la URL del audio generado
      if (generateResult.download_url) {
        const audioFullUrl = `${API_BASE_URL}${generateResult.download_url}`;
        setAudioUrl(audioFullUrl);
        setProcessedFile({
          url: generateResult.download_url,
          name: `${generateResult.original_name}.mp3`
        });
        
        // Guardar las estadísticas
        setAudioStats({
          caracteres: generateResult.characters,
          oraciones: generateResult.segments_count,
          duracion: formatTime(generateResult.duration),
          duracion_segundos: generateResult.duration,
          minutos: (generateResult.duration / 60).toFixed(2) + "m",
          pausas_total: generateResult.number_of_pauses,
          duracion_pausas: formatTime(generateResult.total_pause_duration),
          duracion_sin_pausas: formatTime(generateResult.duration_without_pauses),
          tamaño_archivo: (generateResult.file_size / 1024 / 1024).toFixed(2) + " MB",
          coste: "$" + generateResult.cost.toFixed(6) + " USD",
          velocidad: speedValue.toFixed(1) + "x",
          pausa_ms: pauseDuration + "ms"
        });
      }
      
      setStatus('processed');
      
      // Completar la barra de progreso
      setProgress(100);
      
      // Esperar un momento antes de ocultar la barra de progreso
      setTimeout(() => {
        setIsLoading(false);
      }, 500);
      
    } catch (err: any) {
      console.error('Error en handleProcess:', err);
      
      // Limpiar el intervalo de progreso en caso de error
      clearInterval(progressInterval);
      
      setError(err.message || 'Error al generar el audio');
      setStatus('error');
      setIsLoading(false);
    }
  };

  const togglePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
    }
  };

  const skipForward = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.min(audioRef.current.currentTime + 10, audioRef.current.duration);
    }
  };

  const skipBackward = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(audioRef.current.currentTime - 10, 0);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setAudioDuration(audioRef.current.duration);
    }
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
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
  }, [audioUrl]);

  // Visualización del espectro de audio
  useEffect(() => {
    if (!audioRef.current || !audioUrl) return;

    const audio = audioRef.current;
    
    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };
    
    const handleEnded = () => {
      setIsPlaying(false);
    };
    
    const handleLoadedMetadata = () => {
      setAudioDuration(audio.duration);
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
  }, [audioUrl]);

  const handleDownload = (url: string) => {
    if (url) {
      const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
      console.log(`Descargando audio desde: ${fullUrl}`);
      
      // Crear un enlace temporal para la descarga
      const a = document.createElement('a');
      a.href = fullUrl;
      a.download = processedFile?.name || 'audio_generado.mp3';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
        <h2 className="text-white font-medium text-center">Generar Audio</h2>
      </div>
      
      <div className="p-6 bg-primary-50">
        {!selectedFile ? (
          <div className="mb-6">
            <div className="flex items-center justify-center w-full">
              <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-primary-200 border-dashed rounded-xl cursor-pointer bg-white hover:bg-gray-50">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <FaUpload className="w-8 h-8 mb-3 text-primary-500" />
                  <p className="mb-2 text-sm text-gray-700 text-center">
                    <span className="font-semibold">Haga clic para cargar</span> o arrastre y suelte
                  </p>
                  <p className="text-xs text-gray-500 text-center">Archivos de texto (.txt) o JSON (.json)</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".txt,.json"
                  onChange={handleFileChange}
                  disabled={isLoading}
                />
              </label>
            </div>
          </div>
        ) : null}
        
        {selectedFile && !audioUrl && (
          <div className="mt-3 text-sm text-gray-600 text-center mb-4">
            Archivo seleccionado: <span className="font-medium">{selectedFile.name}</span>
            
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Selector de voz - Primera columna */}
              <div>
                <label className="block text-gray-700 text-sm font-medium mb-2">
                  Seleccionar voz:
                </label>
                <select
                  className="w-full p-2 border border-primary-200 rounded-lg focus:border-primary-500 focus:ring focus:ring-primary-200 focus:ring-opacity-50"
                  value={selectedVoice}
                  onChange={(e) => setSelectedVoice(e.target.value)}
                  disabled={isLoading}
                >
                  {voices.map(voice => (
                    <option key={voice.id} value={voice.id}>
                      {voice.id} - {voice.description} ({voice.gender})
                    </option>
                  ))}
                </select>
              </div>

              {/* Slider de pausa - Segunda columna */}
              <div>
                <label className="block text-gray-700 text-sm font-medium mb-2">
                  Pausa entre oraciones (ms):
                </label>
                <div className="flex items-center">
                  <span className="text-xs mr-2">500</span>
                  <input
                    type="range"
                    min="500"
                    max="2500"
                    step="100"
                    value={pauseDuration}
                    onChange={(e) => setPauseDuration(parseInt(e.target.value))}
                    className="w-full"
                    disabled={isLoading}
                  />
                  <span className="text-xs ml-2">2500</span>
                  <span className="ml-2 bg-primary-100 text-primary-700 px-2 py-1 rounded text-xs font-medium">
                    {pauseDuration}ms
                  </span>
                </div>
              </div>
            </div>
            
            <button
              onClick={handleProcess}
              disabled={isLoading}
              className={`mt-4 w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
                isLoading 
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
                  <MdRecordVoiceOver className="mr-2" /> Generar Audio
                </>
              )}
            </button>
          </div>
        )}
        
        {/* Barra de progreso */}
        {isLoading && (
          <div className="mb-6 mt-2">
            <div className="flex justify-between text-sm text-primary-700 mb-2">
              <span className="font-medium flex items-center">
                <FaCog className="animate-spin mr-2" />
                Generando audio...
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
              {progressMessage}
              {progress >= 90 && " - Audio generado, preparando reproductor..."}
            </p>
            {currentSegment > 0 && progress < 90 && (
              <div className="mt-1 text-xs text-center">
                <span className="inline-block px-2 py-1 bg-primary-100 text-primary-800 rounded-full">
                  {Math.floor((currentSegment / totalSegments) * 100)}% completado
                </span>
              </div>
            )}
          </div>
        )}
        
        {/* Reproductor de audio */}
        {audioUrl && (
          <div className="mt-6">
            <div className="bg-white rounded-xl border border-primary-200 overflow-hidden shadow-md p-4">
              <div className="bg-gray-50 rounded-lg p-2">
                <div className="flex items-center mb-2">
                  <button 
                    onClick={togglePlayPause}
                    className="bg-[#c29e74] text-white rounded-full p-3 mr-3 hover:bg-[#b08c62] flex-shrink-0 shadow-sm"
                  >
                    {isPlaying ? <FaPause size={18} /> : <FaPlay size={18} />}
                  </button>
                  
                  <div className="relative flex-grow">
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
                  
                  <div className="flex space-x-4">
                    <button 
                      onClick={skipBackward}
                      className="p-1 text-primary-700 hover:text-primary-900 focus:outline-none"
                    >
                      <TbPlayerSkipBack className="w-4 h-4" />
                    </button>
                    
                    <button 
                      onClick={skipForward}
                      className="p-1 text-primary-700 hover:text-primary-900 focus:outline-none"
                    >
                      <TbPlayerSkipForward className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="text-xs text-gray-600">{formatTime(audioDuration)}</div>
                </div>
                
                <audio 
                  ref={audioRef}
                  src={audioUrl}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onEnded={() => setIsPlaying(false)}
                  className="hidden"
                ></audio>
              </div>
            </div>
            
            {/* Estadísticas de audio generado */}
            {audioStats && (
              <div className="mt-4 bg-primary-50 p-4 rounded-lg border border-primary-200">
                <h4 className="text-base font-medium text-primary-700 mb-2">Estadísticas de generación:</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Duración</span>
                    <span>{audioStats.duracion} ({audioStats.minutos})</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Caracteres</span>
                    <span>{audioStats.caracteres.toLocaleString()}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Oraciones</span>
                    <span>{audioStats.oraciones}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Pausas</span>
                    <span>{audioStats.pausas_total} ({audioStats.duracion_pausas})</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Audio sin pausas</span>
                    <span>{audioStats.duracion_sin_pausas}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Tamaño archivo</span>
                    <span>{audioStats.tamaño_archivo}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Velocidad voz</span>
                    <span>{audioStats.velocidad}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Pausa entre oraciones</span>
                    <span>{audioStats.pausa_ms}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Coste total</span>
                    <span>{audioStats.coste}</span>
                  </div>
                </div>
              </div>
            )}
            
            {processedFile && (
              <div className="mt-4 flex justify-center">
                <button
                  onClick={() => handleDownload(processedFile.url)}
                  className="bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white px-6 py-2 rounded-lg flex items-center shadow-md transition-colors"
                >
                  <FaDownload className="mr-2" /> Descargar Locución
                </button>
              </div>
            )}
          </div>
        )}
        
        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg flex items-center justify-center border border-red-200">
            <FaExclamationTriangle className="mr-2" /> {error}
          </div>
        )}
        
        {status === 'processed' && !audioUrl && (
          <div className="mt-4 p-3 bg-green-50 text-green-600 rounded-lg flex items-center justify-center border border-green-200">
            <FaCheckCircle className="mr-2" /> Audio generado correctamente.
          </div>
        )}
      </div>
    </div>
  );
};

export default AudioGenerateTool; 