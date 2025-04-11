import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { FaUpload, FaSpinner, FaLanguage, FaDownload } from 'react-icons/fa';

const VideoTranslateTool = () => {
  // Estados para controlar el flujo de la aplicación
  const [file, setFile] = useState<File | null>(null);
  const [fileId, setFileId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [textPreview, setTextPreview] = useState<string>('');
  const [translatedText, setTranslatedText] = useState<string>('');
  const [translationId, setTranslationId] = useState<string | null>(null);
  const [sourceLanguage, setSourceLanguage] = useState<string>('Spanish');
  const [targetLanguage, setTargetLanguage] = useState<string>('English');
  const [languages, setLanguages] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isTranslating, setIsTranslating] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  // Cargar idiomas disponibles
  useEffect(() => {
    const fetchLanguages = async () => {
      try {
        const response = await axios.get('/api/video-translate/languages');
        if (response.data && response.data.languages) {
          setLanguages(response.data.languages);
        }
      } catch (err) {
        console.error('Error al cargar idiomas:', err);
        setLanguages([
          'English', 'Spanish', 'French', 'German', 'Italian', 
          'Portuguese', 'Chinese', 'Japanese', 'Russian'
        ]);
      }
    };

    fetchLanguages();
  }, []);

  // Manejar el click en la zona de carga
  const handleClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Manejar drag enter
  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropZoneRef.current) {
      dropZoneRef.current.classList.add('bg-[#fcfaf7]');
    }
  };

  // Manejar drag leave
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropZoneRef.current) {
      dropZoneRef.current.classList.remove('bg-[#fcfaf7]');
    }
  };

  // Manejar drag over
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  // Manejar drop
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (dropZoneRef.current) {
      dropZoneRef.current.classList.remove('bg-[#fcfaf7]');
    }
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  // Manejar cambio de archivo
  const handleFileChange = (selectedFile: File) => {
    const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase();
    
    if (fileExtension !== 'txt' && fileExtension !== 'json') {
      setError('Solo se permiten archivos de texto (.txt) o JSON (.json)');
      return;
    }
    
    setFile(selectedFile);
    setFileName(selectedFile.name);
    setError(null);
    setSuccess(false);
    setTranslatedText('');
    setTranslationId(null);
    
    // Subir el archivo automáticamente
    uploadFile(selectedFile);
  };

  // Subir archivo
  const uploadFile = async (selectedFile: File) => {
    setIsLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
      const response = await axios.post('/api/upload-text-for-translation', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      if (response.data) {
        setFileId(response.data.file_id);
        setTextPreview(response.data.text_preview || '');
        setIsLoading(false);
      }
    } catch (err: any) {
      console.error('Error al subir archivo:', err);
      setError(err.response?.data?.detail || 'Error al subir el archivo');
      setIsLoading(false);
    }
  };

  // Traducir texto
  const translateText = async () => {
    if (!fileId) {
      setError('No hay archivo para traducir');
      return;
    }
    
    setIsTranslating(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('target_language', targetLanguage);
    formData.append('original_language', sourceLanguage);
    
    try {
      const response = await axios.post('/api/translate-file', formData);
      
      if (response.data) {
        setTranslatedText(response.data.translated_text || '');
        setTranslationId(response.data.translation_id || null);
        setSuccess(true);
      }
    } catch (err: any) {
      console.error('Error al traducir:', err);
      setError(err.response?.data?.detail || 'Error al traducir el texto');
    } finally {
      setIsTranslating(false);
    }
  };

  // Guardar cambios en la traducción
  const saveTranslation = async () => {
    if (!translatedText) {
      setError('No hay texto para guardar');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('translated_text', translatedText);
    formData.append('target_language', targetLanguage);
    if (translationId) {
      formData.append('translation_id', translationId);
    }
    if (fileName) {
      formData.append('original_name', fileName.split('.')[0]);
    }
    
    try {
      const response = await axios.post('/api/save-edited-translation', formData);
      
      if (response.data) {
        setTranslationId(response.data.translation_id || null);
        setSuccess(true);
      }
    } catch (err: any) {
      console.error('Error al guardar traducción:', err);
      setError(err.response?.data?.detail || 'Error al guardar la traducción');
    } finally {
      setIsLoading(false);
    }
  };

  // Descargar traducción
  const downloadTranslation = () => {
    if (translationId) {
      window.open(`/api/download-translation/${translationId}`, '_blank');
    } else if (translatedText) {
      // Si no hay ID pero hay texto, crear un archivo para descargar
      const blob = new Blob([translatedText], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `traduccion_${targetLanguage.toLowerCase()}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } else {
      setError('No hay traducción para descargar');
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      {/* Barra de título superior con color marrón */}
      <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
        <h2 className="font-medium text-white text-center">Seleccionar archivo de transcripción</h2>
      </div>
      
      <div className="p-6 bg-primary-50">
        {/* Primera sección: Selección de archivo */}
        <div className="mb-6">
          <div
            ref={dropZoneRef}
            onClick={handleClick}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className="border-2 border-dashed border-primary-200 rounded-lg p-12 text-center hover:border-primary-400 transition-colors cursor-pointer bg-white"
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept=".txt,.json" 
              onChange={(e) => e.target.files && handleFileChange(e.target.files[0])} 
            />
            
            <div className="flex flex-col items-center justify-center">
              <FaUpload className="text-3xl text-primary-500 mb-3" />
              <p className="mb-2 text-sm text-gray-700 text-center">
                <span className="font-semibold">Haga clic para cargar</span> o arrastre y suelte
              </p>
              <p className="text-xs text-gray-500 text-center">Archivos de texto (.txt) o JSON (.json)</p>
            </div>
          </div>
          
          {error && (
            <div className="mt-3 p-2 bg-red-50 text-red-700 rounded-md text-sm">
              {error}
            </div>
          )}
          
          {isLoading && (
            <div className="mt-3 flex items-center justify-center">
              <FaSpinner className="animate-spin text-primary-500 mr-2" />
              <span className="text-gray-700 text-sm">Procesando archivo...</span>
            </div>
          )}
          
          {file && fileId && !isLoading && (
            <div className="mt-3 p-3 bg-green-50 text-green-700 rounded-md text-sm">
              <p className="font-semibold">Archivo cargado: {fileName}</p>
              {textPreview && (
                <div className="mt-2">
                  <p className="font-semibold mb-1">Vista previa:</p>
                  <p className="text-sm italic bg-white p-2 rounded border border-green-200 max-h-24 overflow-y-auto">
                    {textPreview}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Segunda sección: Opciones de traducción */}
        {fileId && (
          <div className="mb-5">
            <h2 className="text-base font-semibold text-primary-800 mb-3">
              Opciones de traducción
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-700 mb-1 text-sm" htmlFor="sourceLanguage">
                  Idioma de origen:
                </label>
                <select
                  id="sourceLanguage"
                  value={sourceLanguage}
                  onChange={(e) => setSourceLanguage(e.target.value)}
                  className="w-full p-2 border border-primary-200 rounded text-gray-700 focus:outline-none focus:ring-1 focus:ring-primary-500 text-sm"
                >
                  {languages.map((lang) => (
                    <option key={`source-${lang}`} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-gray-700 mb-1 text-sm" htmlFor="targetLanguage">
                  Idioma de destino:
                </label>
                <select
                  id="targetLanguage"
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  className="w-full p-2 border border-primary-200 rounded text-gray-700 focus:outline-none focus:ring-1 focus:ring-primary-500 text-sm"
                >
                  {languages.map((lang) => (
                    <option key={`target-${lang}`} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <button
              onClick={translateText}
              disabled={isTranslating}
              className="mt-4 w-full bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white py-2 px-4 rounded-md text-sm flex items-center justify-center transition-colors disabled:bg-gray-400"
            >
              {isTranslating ? (
                <>
                  <FaSpinner className="animate-spin mr-2" />
                  Traduciendo...
                </>
              ) : (
                <>
                  <FaLanguage className="mr-2" />
                  Traducir texto
                </>
              )}
            </button>
          </div>
        )}
        
        {/* Tercera sección: Resultado de la traducción */}
        {translatedText && (
          <div>
            <h2 className="text-base font-semibold text-primary-800 mb-3">
              Resultado de la traducción
            </h2>
            
            <textarea
              value={translatedText}
              onChange={(e) => setTranslatedText(e.target.value)}
              className="w-full h-48 p-2 border border-primary-200 rounded-md text-gray-700 focus:outline-none focus:ring-1 focus:ring-primary-500 text-sm bg-white"
            />
            
            <div className="mt-3 flex flex-wrap gap-2 justify-center">
              <button
                onClick={saveTranslation}
                className="bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white py-2 px-3 rounded-md flex items-center transition-colors text-sm"
              >
                <FaUpload className="mr-2" />
                Guardar cambios
              </button>
              
              <button
                onClick={downloadTranslation}
                className="bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white py-2 px-3 rounded-md flex items-center transition-colors text-sm"
              >
                <FaDownload className="mr-2" />
                Descargar traducción
              </button>
            </div>
            
            {success && !error && (
              <div className="mt-3 p-2 bg-green-50 text-green-700 rounded-md text-sm">
                Traducción completada y guardada correctamente
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoTranslateTool; 