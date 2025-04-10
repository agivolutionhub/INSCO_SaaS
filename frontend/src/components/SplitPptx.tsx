import { useState, useRef } from 'react';
import { FaUpload, FaCog, FaDownload, FaFilePowerpoint, FaCut, FaNetworkWired, FaArchive } from 'react-icons/fa';
import JSZip from 'jszip';

interface FileResult {
  file_id: string;
  filename: string;
  url: string;
}

interface JobStatus {
  status: 'processing' | 'completed' | 'error';
  files?: FileResult[];
  message?: string;
}

// Eliminar el límite de tamaño o aumentarlo considerablemente
// MAX_FILE_SIZE_MB ahora solo se usa para mostrar advertencias, no para bloquear

export default function SplitPptx() {
  const [file, setFile] = useState<File | null>(null);
  const [slidesPerChunk, setSlidesPerChunk] = useState<number>(20);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pollingInterval, setPollingInterval] = useState<number | null>(null);
  const [connectionError, setConnectionError] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [isCreatingZip, setIsCreatingZip] = useState<boolean>(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    
    if (selectedFile) {
      // Validar tipo de archivo
      if (!selectedFile.name.toLowerCase().endsWith('.pptx')) {
        setError('Solo se permiten archivos PPTX');
        setFile(null);
        return;
      }
      
      setFile(selectedFile);
      setError(null);
      setConnectionError(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setError(null);
    setConnectionError(false);
    setProgress(0);
    setJobId(null);
    setJobStatus(null);
    setIsUploading(false);
    setIsCreatingZip(false);
    
    // Detener cualquier polling activo
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setError(null);
    setJobId(null);
    setJobStatus(null);
    setConnectionError(false);
    setProgress(0);
    
    // Iniciar la simulación de progreso inmediatamente
    const progressInterval = startFakeProgressBar();
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('slides_per_chunk', slidesPerChunk.toString());
      
      // Timeout más largo para archivos grandes
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minutos de timeout
      
      try {
        const response = await fetch('/api/pptx/split', {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });
        
        clearTimeout(timeoutId);
        
        // Intentar parsear la respuesta JSON con manejo de errores
        let data;
        try {
          const textResponse = await response.text();
          data = JSON.parse(textResponse);
        } catch (jsonError) {
          console.error('Error al parsear respuesta JSON:', jsonError);
          throw new Error('Error al procesar la respuesta del servidor. Formato inválido.');
        }
        
        if (!response.ok) {
          throw new Error(data.detail || 'Error al procesar el archivo');
        }
        
        setJobId(data.job_id);
        
        // Iniciar polling para verificar estado
        if (pollingInterval) clearInterval(pollingInterval);
        const interval = window.setInterval(() => checkJobStatus(data.job_id), 3000);
        setPollingInterval(interval);
      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        
        // Determinar si es un error de conexión
        if (fetchError.name === 'AbortError') {
          throw new Error('La operación ha excedido el tiempo máximo de espera. Intente nuevamente.');
        } else if (fetchError.message.includes('NetworkError') || 
                  fetchError.message.includes('Failed to fetch') ||
                  fetchError.message.includes('Network request failed')) {
          setConnectionError(true);
          throw new Error('Error de conexión. Compruebe que el servidor está funcionando correctamente.');
        } else {
          throw fetchError;
        }
      }
    } catch (err: any) {
      console.error('Error completo:', err);
      setError(err.message || 'Error al procesar el archivo');
      
      // Solo en caso de error establecemos isUploading a false
      setIsUploading(false);
      
      // Limpiar el intervalo de progreso en caso de error
      clearInterval(progressInterval);
    }
  };
  
  const checkJobStatus = async (id: string) => {
    try {
      const response = await fetch(`/api/pptx/jobs/${id}`);
      
      // Manejar errores de formato JSON en la respuesta
      let data;
      try {
        const textResponse = await response.text();
        data = JSON.parse(textResponse);
      } catch (jsonError) {
        console.error('Error al parsear respuesta JSON en checkJobStatus:', jsonError);
        setError('Error al procesar la respuesta del servidor. Intente nuevamente más tarde.');
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        setIsUploading(false); // Detener la barra de progreso en caso de error
        return;
      }
      
      setJobStatus(data);
      
      // Si ya terminó (completado o error), detener polling y completar barra de progreso
      if (data.status === 'completed' || data.status === 'error') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        setProgress(100); // Completar la barra de progreso
        
        // Esperar un momento antes de quitar la barra de progreso
        // para que el usuario vea el 100%
        setTimeout(() => {
          setIsUploading(false);
        }, 500);
      }
    } catch (err) {
      console.error('Error verificando estado del trabajo:', err);
      setError('Error al verificar el estado del proceso. Intente nuevamente más tarde.');
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
      setIsUploading(false); // Detener la barra de progreso
    }
  };

  // Función para simular la barra de progreso mientras se procesa el archivo
  const startFakeProgressBar = () => {
    setProgress(0);
    const maxProgress = 90; // Solo llega al 90% máximo, el 100% se alcanza cuando termina realmente
    const intervalStep = 300; // Más rápido: 300ms entre incrementos (antes 600ms)
    const smallStep = 1; // Incremento pequeño regular
    const initialBoost = 10; // Impulso inicial para que se vea movimiento inmediato
    const largeStepChance = 0.15; // Mayor probabilidad de incrementos grandes
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

  // Función para crear y descargar un archivo ZIP con todos los archivos
  const downloadAllFiles = async () => {
    if (!jobStatus?.files || jobStatus.files.length === 0) return;
    
    const zip = new JSZip();
    const filePromises = [];
    
    // Activar el estado de creación de ZIP
    setIsCreatingZip(true);
    
    // Añadir cada archivo al ZIP
    for (const file of jobStatus.files) {
      // Descargar el archivo
      const filePromise = fetch(file.url)
        .then(response => {
          if (!response.ok) throw new Error(`Error al descargar ${file.filename}`);
          return response.blob();
        })
        .then(blob => {
          // Añadir el archivo al ZIP
          zip.file(file.filename, blob);
          return true;
        })
        .catch(err => {
          console.error(`Error procesando archivo ${file.filename}:`, err);
          return false;
        });
      
      filePromises.push(filePromise);
    }
    
    try {
      // Esperar a que todos los archivos se añadan al ZIP
      await Promise.all(filePromises);
      
      // Generar el archivo ZIP
      const zipContent = await zip.generateAsync({ type: 'blob' });
      
      // Crear un nombre para el archivo ZIP basado en el nombre original, limpiando sufijos
      let zipName = 'presentacion_dividida.zip';
      if (file && file.name) {
        // Limpiar el nombre eliminando sufijos conocidos
        let baseName = file.name.replace(/\.pptx$/i, '');
        // Eliminar sufijos conocidos
        for (const suffix of ["_autofit", "_translated", "_parte"]) {
          if (baseName.endsWith(suffix)) {
            baseName = baseName.substring(0, baseName.lastIndexOf(suffix));
          }
        }
        // Eliminar sufijos numéricos tipo _parte1
        baseName = baseName.replace(/_parte\d+$/, '');
        
        zipName = `${baseName}_dividido.zip`;
      }
      
      // Crear un objeto URL para el archivo ZIP
      const zipUrl = URL.createObjectURL(zipContent);
      
      // Crear un enlace y simular clic para descargar
      const link = document.createElement('a');
      link.href = zipUrl;
      link.download = zipName;
      document.body.appendChild(link);
      link.click();
      
      // Limpiar
      setTimeout(() => {
        document.body.removeChild(link);
        URL.revokeObjectURL(zipUrl);
        setIsCreatingZip(false);
      }, 100);
    } catch (error) {
      console.error('Error al crear el archivo ZIP:', error);
      setError('Error al crear el archivo ZIP. Intente descargar los archivos individualmente.');
      setIsCreatingZip(false);
    }
  };

  return (
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
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pptx"
                onChange={handleFileChange}
                disabled={isUploading}
              />
            </label>
          </div>
          {file && (
            <div className="mt-3 text-sm text-gray-600 text-center">
              Archivo seleccionado: {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
            </div>
          )}
        </div>
        
        <div className="mb-6 bg-white p-4 rounded-lg border border-primary-200">
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="slides-per-chunk" className="text-primary-700 font-medium">Diapositivas por archivo</label>
            <span className="text-sm font-medium bg-primary-100 rounded-full px-3 py-1 text-primary-700">{slidesPerChunk}</span>
          </div>
          <div className="relative w-full h-2 bg-gray-200 rounded-full">
            <div
              className="absolute h-full rounded-full bg-primary-500"
              style={{ width: `${(slidesPerChunk - 5) / 45 * 100}%` }}
            />
            <input
              id="slides-per-chunk"
              type="range"
              min={5}
              max={50}
              step={5}
              value={slidesPerChunk}
              onChange={(e) => setSlidesPerChunk(Number(e.target.value))}
              disabled={isUploading}
              className="absolute inset-0 w-full h-2 opacity-0 cursor-pointer"
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Divide la presentación en archivos de {slidesPerChunk} diapositivas cada uno
          </p>
        </div>
        
        {connectionError && (
          <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
            <div className="flex items-center">
              <FaNetworkWired className="mr-2" />
              <div className="font-medium">Error de conexión</div>
            </div>
            <div className="mt-2 text-sm">
              <p>No se pudo conectar con el servidor. Verifique que:</p>
              <ul className="list-disc pl-5 mt-1 space-y-1">
                <li>El servidor backend está en ejecución</li>
                <li>No hay problemas de red o firewall</li>
                <li>Puede intentar reiniciar el servidor y volver a intentarlo</li>
              </ul>
            </div>
          </div>
        )}
        
        {error && !connectionError && (
          <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg flex items-center">
            <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}
        
        {/* Barra de progreso mejorada */}
        {isUploading && (
          <div className="mb-6 mt-2">
            <div className="flex justify-between text-sm text-primary-700 mb-2">
              <span className="font-medium flex items-center">
                <FaCog className="animate-spin mr-2" />
                Procesando presentación...
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
              {progress < 30 && "Analizando presentación..."}
              {progress >= 30 && progress < 60 && "Dividiendo diapositivas..."}
              {progress >= 60 && progress < 90 && "Generando archivos..."}
              {progress >= 90 && "Finalizando proceso..."}
            </p>
          </div>
        )}
        
        {jobStatus && (
          <div className={`mb-6 px-4 py-3 rounded-lg ${
            jobStatus.status === 'error' 
              ? 'bg-red-100 border border-red-400 text-red-700'
              : jobStatus.status === 'completed'
                ? 'bg-green-100 border border-green-400 text-green-700'
                : 'bg-blue-100 border border-blue-400 text-blue-700'
          }`}>
            <div className="font-medium mb-1">
              {jobStatus.status === 'processing' && 'Procesando presentación...'}
              {jobStatus.status === 'completed' && 'Proceso completado'}
              {jobStatus.status === 'error' && 'Error en el proceso'}
            </div>
            
            {jobStatus.status === 'error' && jobStatus.message && (
              <div className="text-sm">
                {jobStatus.message}
              </div>
            )}
            
            {isCreatingZip && (
              <div className="bg-blue-50 border border-blue-300 text-blue-800 px-4 py-3 rounded-lg my-2 flex items-center">
                <FaCog className="animate-spin mr-2" />
                <div>
                  <p className="font-medium">Creando archivo ZIP</p>
                  <p className="text-sm">Por favor espere mientras se preparan los archivos...</p>
                </div>
              </div>
            )}
            
            {jobStatus.status === 'completed' && jobStatus.files && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center">
                  <p className="font-medium">Archivos generados:</p>
                </div>
                
                <div className="bg-white rounded-lg border border-gray-200 p-3 space-y-3">
                  {jobStatus.files.map((file) => {
                    // Mostrar el nombre corto para la UI, pero mantener el nombre completo para el tooltip
                    const displayName = file.filename;
                    
                    return (
                      <div key={file.file_id} className="flex flex-col sm:flex-row items-start sm:items-center gap-2 bg-gray-50 p-3 rounded-lg">
                        <div className="flex items-center w-full overflow-hidden group">
                          <FaFilePowerpoint className="text-primary-500 text-lg min-w-[24px] mr-2 flex-shrink-0" />
                          <div className="overflow-hidden">
                            <span 
                              className="text-sm font-medium text-gray-800 block truncate hover:text-primary-600 transition-colors relative"
                              title={displayName}
                            >
                              {displayName}
                            </span>
                          </div>
                        </div>
                        <a 
                          href={file.url} 
                          className="text-sm bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white px-3 py-1 rounded-lg flex items-center justify-center whitespace-nowrap sm:ml-auto min-w-[110px] shadow-md"
                          download={displayName}
                        >
                          <FaDownload className="mr-1" /> Descargar
                        </a>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
        
        <div className="flex justify-between space-x-4">
          <button
            onClick={clearFile}
            disabled={isUploading}
            className={`flex items-center justify-center py-2 px-6 min-w-[120px] border border-transparent rounded-lg shadow-sm text-gray-700 font-medium ${
              isUploading 
                ? 'bg-gray-200 cursor-not-allowed' 
                : 'bg-white hover:bg-gray-100 border-gray-300'
            }`}
          >
            Reiniciar
          </button>
          
          {jobStatus?.status === 'completed' ? (
            <button 
              onClick={downloadAllFiles}
              disabled={isCreatingZip}
              className={`ml-2 flex items-center px-4 py-2 rounded-lg shadow-md text-white ${
                isCreatingZip ? 'bg-gray-400 cursor-not-allowed' : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
              }`}
            >
              {isCreatingZip ? (
                <>
                  <FaCog className="animate-spin mr-2" />
                  Creando ZIP...
                </>
              ) : (
                <>
                  <FaArchive className="mr-2" />
                  Descargar ZIP
                </>
              )}
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!file || isUploading}
              className={`flex-1 flex items-center justify-center py-3 px-4 border border-transparent rounded-lg shadow-md text-white font-medium ${
                !file || isUploading 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
              }`}
            >
              {isUploading ? (
                <>
                  <FaCog className="animate-spin mr-2" />
                  Procesando...
                </>
              ) : (
                <>
                  <FaCut className="mr-2" />
                  Dividir presentación
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
} 