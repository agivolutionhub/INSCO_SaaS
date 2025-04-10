import React, { useState, useRef, useEffect } from 'react';
import { FaUpload, FaCog, FaDownload, FaCheckCircle, FaExclamationTriangle, FaMicrophone, FaPlay, FaPause, FaSave, FaMagic, FaCheck, FaTimes, FaUndo, FaRedo } from 'react-icons/fa';

// URL base para las solicitudes API
const API_BASE_URL = 'http://localhost:8088';

// Interfaz para segmentos
interface TranscriptionSegment {
  id: number;
  start: number;
  end: number;
  text: string;
}

// Interfaz para sugerencias de mejora
interface Suggestion {
  id: string;
  originalText: string;
  improvedText: string;
  startPos: number;
  endPos: number;
  cost: number;
  hasChanges: boolean;  // Indica si hay cambios significativos en esta sugerencia
  status: 'pending' | 'applied' | 'rejected';  // Estado de la sugerencia
}

// Interfaz para estadísticas de corrección
interface CorrectionStats {
  totalCorrections: number;
  appliedCorrections: number;
  inputTokens: number;
  outputTokens: number;
  modelName: string;
  inputCost: number;
  outputCost: number;
  totalCost: number;
  processingTime: number;
  lastUpdateTime: number;
}

// Función auxiliar para calcular la distancia de Levenshtein (similitud de cadenas)
const levenshteinDistance = (a: string, b: string): number => {
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;

  const matrix = Array(b.length + 1).fill(null).map(() => Array(a.length + 1).fill(null));

  for (let i = 0; i <= a.length; i++) {
    matrix[0][i] = i;
  }

  for (let j = 0; j <= b.length; j++) {
    matrix[j][0] = j;
  }

  for (let j = 1; j <= b.length; j++) {
    for (let i = 1; i <= a.length; i++) {
      const substitutionCost = a[i - 1] === b[j - 1] ? 0 : 1;
      matrix[j][i] = Math.min(
        matrix[j][i - 1] + 1, // deletion
        matrix[j - 1][i] + 1, // insertion
        matrix[j - 1][i - 1] + substitutionCost // substitution
      );
    }
  }

  return matrix[b.length][a.length];
};

const VideoTranscribeTool = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [processedFiles, setProcessedFiles] = useState<Array<{url: string, name: string}>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'processed' | 'error'>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [transcriptionText, setTranscriptionText] = useState<string>('');
  const [segments, setSegments] = useState<TranscriptionSegment[]>([]);
  const [uploadedFileInfo, setUploadedFileInfo] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);
  const [isImprovingText, setIsImprovingText] = useState<boolean>(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showContextMenu, setShowContextMenu] = useState<boolean>(false);
  const [contextMenuPosition, setContextMenuPosition] = useState<{top: number, left: number}>({top: 0, left: 0});
  const [selectedText, setSelectedText] = useState<{text: string, startPos: number, endPos: number} | null>(null);
  const [totalCost, setTotalCost] = useState<number>(0);
  const [correctionStats, setCorrectionStats] = useState<CorrectionStats>({
    totalCorrections: 0,
    appliedCorrections: 0,
    inputTokens: 0,
    outputTokens: 0,
    modelName: 'gpt-4o',
    inputCost: 0,
    outputCost: 0,
    totalCost: 0,
    processingTime: 0,
    lastUpdateTime: Date.now()
  });
  const [improvedRegions, setImprovedRegions] = useState<{start: number, end: number}[]>([]);
  
  // Referencias para el textarea
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const editorRef = useRef<HTMLDivElement | null>(null);

  // Formatear el texto con saltos de línea para cada oración
  const formatTranscriptionText = (text: string) => {
    if (!text) return '';
    
    // Patrones para detectar final de oración - mejorado con expresiones regulares
    const sentenceRegex = /([.!?])\s+(?=[A-ZÁÉÍÓÚÑ])/g;
    
    // Reemplazar finales de oración con salto de línea
    let formattedText = text;
    
    // Primero limpiamos cualquier salto de línea existente para asegurar un formato consistente
    formattedText = formattedText.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
    
    // Luego reemplazamos cada final de oración con un salto de línea doble
    formattedText = formattedText.replace(sentenceRegex, '$1\n\n');
    
    // Añadir salto de línea al final si termina con un símbolo de puntuación
    if (/[.!?]$/.test(formattedText) && !formattedText.endsWith('\n\n')) {
      formattedText += '\n\n';
    }
    
    return formattedText;
  };

  // Función auxiliar para determinar si una mejora es significativa
  const isSignificantImprovement = (original: string, improved: string): boolean => {
    // Si son iguales, obviamente no hay mejora
    if (original === improved) return false;
    
    // Calcular la similitud entre textos
    const similarity = 1 - (levenshteinDistance(original, improved) / 
                           Math.max(original.length, improved.length));
    
    // Si la similitud es muy alta (>98%), verificar si los cambios son triviales
    if (similarity > 0.98) {
      // Verificar si la única diferencia son signos de puntuación o espacios
      const normalizedOriginal = original.replace(/[,;:.!?"\s]+/g, ' ').trim().toLowerCase();
      const normalizedImproved = improved.replace(/[,;:.!?"\s]+/g, ' ').trim().toLowerCase();
      
      // Si después de normalizar son iguales, los cambios son triviales
      if (normalizedOriginal === normalizedImproved) {
        return false;
      }
      
      // Verificar si el único cambio es una palabra trivial (artículos, preposiciones)
      const trivialWords = ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 
                           'y', 'e', 'o', 'u', 'a', 'ante', 'bajo', 'con', 'de', 
                           'desde', 'en', 'entre', 'hacia', 'hasta', 'para', 'por', 
                           'según', 'sin', 'sobre', 'tras'];
      
      // Separar en palabras
      const originalWords = normalizedOriginal.split(/\s+/);
      const improvedWords = normalizedImproved.split(/\s+/);
      
      // Si tienen diferente número de palabras, hay cambios no triviales
      if (originalWords.length !== improvedWords.length) {
        return true;
      }
      
      // Contar cuántas palabras son diferentes
      let differentWords = 0;
      let onlyTrivialChanges = true;
      
      for (let i = 0; i < originalWords.length; i++) {
        if (originalWords[i] !== improvedWords[i]) {
          differentWords++;
          
          // Si alguna de las palabras diferentes no es trivial, es un cambio significativo
          if (!trivialWords.includes(originalWords[i]) && !trivialWords.includes(improvedWords[i])) {
            onlyTrivialChanges = false;
          }
        }
      }
      
      // Si solo hay una o dos palabras diferentes y todas son triviales, no es significativo
      if (differentWords <= 2 && onlyTrivialChanges) {
        return false;
      }
    }
    
    // En otros casos, consideramos que hay una mejora significativa
    return true;
  };

  // Función para aplicar una sugerencia
  const applySuggestion = (suggestion: Suggestion) => {
    // Si la sugerencia ya está aplicada, no hacer nada
    if (suggestion.status === 'applied') return;
    
    const newText = 
      transcriptionText.substring(0, suggestion.startPos) + 
      suggestion.improvedText + 
      transcriptionText.substring(suggestion.endPos);
    
    setTranscriptionText(newText);
    
    // Actualizar el costo total
    setTotalCost(prevCost => prevCost + suggestion.cost);
    
    // Actualizar estadísticas de corrección
    setCorrectionStats(prev => ({
      ...prev,
      appliedCorrections: prev.appliedCorrections + 1,
      totalCost: prev.totalCost + suggestion.cost,
      lastUpdateTime: Date.now()
    }));
    
    // Registrar esta región como mejorada
    // Ajustar el cálculo para manejar correctamente los desplazamientos de texto
    const lengthDiff = suggestion.improvedText.length - suggestion.originalText.length;
    
    // Añadir la nueva región mejorada
    setImprovedRegions(prevRegions => {
      // Primero, ajustamos las regiones existentes para reflejar el cambio de longitud
      const adjustedRegions = prevRegions.map(region => {
        if (region.start > suggestion.endPos) {
          // Esta región está después de la edición, ajustar posición
          return {
            start: region.start + lengthDiff,
            end: region.end + lengthDiff
          };
        } else if (region.end > suggestion.startPos && region.start < suggestion.startPos) {
          // La región comienza antes pero termina dentro o después de la edición
          return {
            start: region.start,
            end: Math.max(suggestion.startPos, region.end + lengthDiff)
          };
        }
        return region;
      });
      
      // Luego añadimos la nueva región mejorada
      return [...adjustedRegions, {
        start: suggestion.startPos,
        end: suggestion.startPos + suggestion.improvedText.length
      }];
    });
    
    // Actualizar el estado de la sugerencia a 'aplicada'
    setSuggestions(prevSuggestions => 
      prevSuggestions.map(s => 
        s.id === suggestion.id ? { ...s, status: 'applied' } : s
      )
    );
    
    setHasUnsavedChanges(true);
  };

  // Función para deshacer una sugerencia aplicada
  const undoSuggestion = (suggestion: Suggestion) => {
    // Solo podemos deshacer sugerencias aplicadas
    if (suggestion.status !== 'applied') return;
    
    // Revertir el texto a su versión original
    const newText = 
      transcriptionText.substring(0, suggestion.startPos) + 
      suggestion.originalText + 
      transcriptionText.substring(suggestion.startPos + suggestion.improvedText.length);
    
    setTranscriptionText(newText);
    
    // Restar el costo
    setTotalCost(prevCost => Math.max(0, prevCost - suggestion.cost));
    
    // Actualizar estadísticas de corrección
    setCorrectionStats(prev => ({
      ...prev,
      appliedCorrections: Math.max(0, prev.appliedCorrections - 1),
      totalCost: Math.max(0, prev.totalCost - suggestion.cost),
      lastUpdateTime: Date.now()
    }));
    
    // Eliminar esta región de las regiones mejoradas
    setImprovedRegions(prevRegions => 
      prevRegions.filter(region => 
        !(region.start === suggestion.startPos && 
          region.end === suggestion.startPos + suggestion.improvedText.length)
      )
    );
    
    // Actualizar el estado de la sugerencia a 'pendiente' nuevamente
    setSuggestions(prevSuggestions => 
      prevSuggestions.map(s => 
        s.id === suggestion.id ? { ...s, status: 'pending' } : s
      )
    );
    
    setHasUnsavedChanges(true);
  };

  // Función para rechazar una sugerencia
  const rejectSuggestion = (suggestionId: string) => {
    setSuggestions(prevSuggestions => 
      prevSuggestions.map(s => 
        s.id === suggestionId ? { ...s, status: 'rejected' } : s
      )
    );
  };

  // Mostrar menú contextual al seleccionar texto
  const handleTextSelection = () => {
    if (textareaRef.current) {
      const selection = window.getSelection();
      
      if (selection && selection.toString().trim().length > 0) {
        // Obtener la posición de la selección
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        
        // Obtener la posición relativa al editor
        const editorRect = editorRef.current?.getBoundingClientRect() || { top: 0, left: 0 };
        
        setContextMenuPosition({
          top: rect.bottom - editorRect.top + 10,
          left: rect.left - editorRect.left
        });
        
        // Guardar el texto seleccionado y su posición
        const start = textareaRef.current.selectionStart;
        const end = textareaRef.current.selectionEnd;
        
        setSelectedText({
          text: selection.toString(),
          startPos: start,
          endPos: end
        });
        
        setShowContextMenu(true);
      } else {
        setShowContextMenu(false);
      }
    }
  };

  // Mejorar texto seleccionado con IA
  const improveSelectedTextWithAI = async () => {
    if (!selectedText) return;
    
    try {
      setIsImprovingText(true);
      setShowContextMenu(false);
      
      const startTime = Date.now();
      
      // Preparar la solicitud
      const payload = {
        text: selectedText.text,
        context: transcriptionText,
        segment_id: -1
      };
      
      // Enviar solicitud al backend
      const response = await fetch(`${API_BASE_URL}/api/improve-text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al mejorar el texto');
      }
      
      const result = await response.json();
      const processingTime = (Date.now() - startTime) / 1000;
      
      // Calcular la similitud entre el texto original y el mejorado
      const similarity = 1 - (levenshteinDistance(selectedText.text, result.improved_text) / 
                            Math.max(selectedText.text.length, result.improved_text.length));
      
      // Solo sugerir si el cambio es significativo
      if (similarity > 0.7 && selectedText.text !== result.improved_text && 
          isSignificantImprovement(selectedText.text, result.improved_text)) {
        // Crear nueva sugerencia
        const newSuggestion: Suggestion = {
          id: Date.now().toString(),
          originalText: selectedText.text,
          improvedText: result.improved_text,
          startPos: selectedText.startPos,
          endPos: selectedText.endPos,
          cost: result.cost.total_cost || 0,
          hasChanges: true,
          status: 'pending'
        };
        
        // Añadir la sugerencia
        setSuggestions(prev => [...prev, newSuggestion]);
        
        // Actualizar estadísticas de corrección
        setCorrectionStats(prev => ({
          ...prev,
          totalCorrections: prev.totalCorrections + 1,
          inputTokens: prev.inputTokens + (result.tokens?.prompt || 0),
          outputTokens: prev.outputTokens + (result.tokens?.completion || 0),
          inputCost: prev.inputCost + (result.cost?.input_cost || 0),
          outputCost: prev.outputCost + (result.cost?.output_cost || 0),
          totalCost: prev.totalCost + (result.cost?.total_cost || 0),
          processingTime: prev.processingTime + processingTime,
          lastUpdateTime: Date.now()
        }));
      } else if (selectedText.text === result.improved_text) {
        // Si no hay cambios, mostrar un mensaje
        setError('No se encontraron mejoras para aplicar al texto seleccionado');
      } else {
        // Si el cambio es trivial, mostrar mensaje específico
        setError('Las mejoras propuestas son demasiado sutiles para justificar un cambio');
      }
      
    } catch (err: any) {
      console.error('Error al mejorar texto:', err);
      setError(err.message || 'Error al mejorar el texto');
    } finally {
      setIsImprovingText(false);
    }
  };

  // Mejorar todo el texto con IA
  const improveFullTextWithAI = async () => {
    try {
      setIsImprovingText(true);
      
      const startTime = Date.now();
      
      // Extraer todas las oraciones del texto
      const sentenceRegex = /([^.!?]+[.!?]+\s*)/g;
      const originalMatches = transcriptionText.match(sentenceRegex) || [];
      const originalSentences = originalMatches.map((s: string) => s.trim()).filter(s => s.length > 0);
      
      if (originalSentences.length === 0) {
        setError('No se encontraron oraciones para mejorar en el texto');
        setIsImprovingText(false);
        return;
      }
      
      // Registrar la posición de cada oración en el texto completo
      const sentencePositions: Array<{id: number, text: string, startPos: number, endPos: number}> = [];
      let searchPosition = 0;
      
      for (let i = 0; i < originalSentences.length; i++) {
        const sentence = originalSentences[i];
        const startPos = transcriptionText.indexOf(sentence, searchPosition);
        
        if (startPos !== -1) {
          const endPos = startPos + sentence.length;
          sentencePositions.push({
            id: i,
            text: sentence,
            startPos,
            endPos
          });
          searchPosition = endPos;
        }
      }
      
      // Preparar la solicitud con todas las oraciones
      const payload = {
        sentences: sentencePositions,
        context: transcriptionText
      };
      
      // Enviar solicitud al nuevo endpoint que procesa múltiples oraciones
      const response = await fetch(`${API_BASE_URL}/api/improve-multiple-sentences`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al mejorar el texto');
      }
      
      const result = await response.json();
      const processingTime = (Date.now() - startTime) / 1000;
      
      // Crear sugerencias para cada oración procesada
      let newSuggestions: Suggestion[] = [];
      let totalChanges = 0;
      
      // Limpiar sugerencias actuales
      setSuggestions([]);
      
      for (const sentenceResult of result.results) {
        // Obtener la información de posición para esta oración
        const originalSentence = sentenceResult.original_text;
        const improvedSentence = sentenceResult.improved_text;
        const hasChanges = sentenceResult.is_improved;
        const sentenceInfo = sentencePositions.find(p => p.id === sentenceResult.id);
        
        if (!sentenceInfo) continue;
        
        // Verificar si la mejora es significativa
        const isSignificantChange = hasChanges && isSignificantImprovement(originalSentence, improvedSentence);
        
        if (isSignificantChange) {
          totalChanges++;
        }
        
        // Crear sugerencia para esta oración
        const suggestion: Suggestion = {
          id: `suggestion-${Date.now()}-${sentenceResult.id}`,
          originalText: originalSentence,
          improvedText: improvedSentence,
          startPos: sentenceInfo.startPos,
          endPos: sentenceInfo.endPos,
          cost: hasChanges ? (result.cost.total_cost || 0) / result.results.length : 0,
          hasChanges: isSignificantChange,
          status: 'pending'
        };
        
        newSuggestions.push(suggestion);
      }
      
      // Actualizar las sugerencias
      setSuggestions(newSuggestions);
      
      // Actualizar estadísticas de corrección
      setCorrectionStats(prev => ({
        ...prev,
        totalCorrections: prev.totalCorrections + totalChanges,
        inputTokens: prev.inputTokens + (result.tokens?.prompt || 0),
        outputTokens: prev.outputTokens + (result.tokens?.completion || 0),
        inputCost: prev.inputCost + (result.cost?.input_cost || 0),
        outputCost: prev.outputCost + (result.cost?.output_cost || 0),
        totalCost: prev.totalCost + (result.cost?.total_cost || 0),
        processingTime: prev.processingTime + processingTime,
        lastUpdateTime: Date.now()
      }));
      
      setHasUnsavedChanges(true);
      
      // Mostrar mensaje si no hay mejoras
      if (totalChanges === 0) {
        setError('No se encontraron mejoras significativas para aplicar al texto');
      }
      
    } catch (err: any) {
      console.error('Error al mejorar texto:', err);
      setError(err.message || 'Error al mejorar el texto');
    } finally {
      setIsImprovingText(false);
    }
  };

  // Procesar cada oración una por una para asegurar la correspondencia
  const processTextSentenceByOne = async (sentences: string[]) => {
    let position = 0;
    let newSuggestions: Suggestion[] = [];
    let totalChanges = 0;
    let totalTokensInput = 0;
    let totalTokensOutput = 0;
    let totalCostValue = 0;
    let totalProcessingTime = 0;
    
    // Mostrar un indicador de progreso para procesamiento por oraciones
    const totalSentences = sentences.length;
    let processedSentences = 0;
    
    for (const sentence of sentences) {
      if (sentence.trim().length === 0) continue;
      
      const startPos = transcriptionText.indexOf(sentence, position);
      if (startPos === -1) continue;
      
      const endPos = startPos + sentence.length;
      position = endPos;
      
      // Procesar esta oración individualmente
      const startTime = Date.now();
      
      try {
        // Preparar solicitud para una sola oración
        const payload = {
          text: sentence,
          context: transcriptionText, // Contexto completo para mejor coherencia
          segment_id: -1
        };
        
        // Enviar solicitud al backend
        const response = await fetch(`${API_BASE_URL}/api/improve-text`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
        
        if (!response.ok) {
          continue; // Saltar esta oración si hay error
        }
        
        const result = await response.json();
        const processingTime = (Date.now() - startTime) / 1000;
        
        // Registrar métricas
        totalTokensInput += result.tokens?.prompt || 0;
        totalTokensOutput += result.tokens?.completion || 0;
        totalCostValue += result.cost?.total_cost || 0;
        totalProcessingTime += processingTime;
        
        // Verificar si es una mejora significativa
        const improvedSentence = result.improved_text;
        const hasSignificantChanges = isSignificantImprovement(sentence, improvedSentence);
        
        // Crear sugerencia para esta oración
        const suggestion: Suggestion = {
          id: `suggestion-${Date.now()}-${processedSentences}`,
          originalText: sentence,
          improvedText: hasSignificantChanges ? improvedSentence : sentence,
          startPos: startPos,
          endPos: endPos,
          cost: result.cost?.total_cost || 0,
          hasChanges: hasSignificantChanges,
          status: 'pending'
        };
        
        if (hasSignificantChanges) {
          totalChanges++;
        }
        
        newSuggestions.push(suggestion);
        
      } catch (error) {
        console.error('Error procesando oración:', error);
      }
      
      processedSentences++;
    }
    
    // Actualizar las sugerencias
    setSuggestions(newSuggestions);
    
    // Actualizar estadísticas de corrección
    setCorrectionStats(prev => ({
      ...prev,
      totalCorrections: prev.totalCorrections + totalChanges,
      inputTokens: prev.inputTokens + totalTokensInput,
      outputTokens: prev.outputTokens + totalTokensOutput,
      inputCost: prev.inputCost + (totalCostValue / 2), // Aproximado
      outputCost: prev.outputCost + (totalCostValue / 2), // Aproximado
      totalCost: prev.totalCost + totalCostValue,
      processingTime: prev.processingTime + totalProcessingTime,
      lastUpdateTime: Date.now()
    }));
    
    setHasUnsavedChanges(true);
    
    // Mostrar mensaje si no hay mejoras
    if (totalChanges === 0) {
      setError('No se encontraron mejoras significativas para aplicar al texto');
    }
  };

  // Función para verificar si dos oraciones están relacionadas semánticamente
  const checkSentenceSimilarity = (sentence1: string, sentence2: string): boolean => {
    // Si son idénticas, obviamente están relacionadas
    if (sentence1 === sentence2) return true;
    
    // Extraer palabras clave (sustantivos y verbos principalmente)
    const getKeywords = (text: string): string[] => {
      return text.toLowerCase()
        .replace(/[^\wáéíóúüñ\s]/g, '') // Eliminar puntuación
        .split(/\s+/) // Dividir por espacios
        .filter(word => word.length > 3) // Palabras con más de 3 caracteres (probablemente no son artículos/preposiciones)
        .filter(word => !['para', 'como', 'este', 'esta', 'estos', 'estas', 'aquel', 'aquella'].includes(word)); // Eliminar algunas palabras comunes
    };
    
    const keywords1 = getKeywords(sentence1);
    const keywords2 = getKeywords(sentence2);
    
    if (keywords1.length === 0 || keywords2.length === 0) return true; // No podemos determinar
    
    // Contar cuántas palabras clave coinciden
    let matchCount = 0;
    for (const word of keywords1) {
      if (keywords2.includes(word)) {
        matchCount++;
      }
    }
    
    // Calcular porcentaje de coincidencia
    const matchPercentage = matchCount / Math.min(keywords1.length, keywords2.length);
    
    // Consideramos que están relacionadas si coinciden al menos un 30% de las palabras clave
    return matchPercentage >= 0.3;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setError(null);
      setStatus('idle');
      setProcessedFiles([]);
      setProgress(0);
      setTranscriptionText('');
      setSegments([]);
      setStats(null);
      setHasUnsavedChanges(false);
      setSuggestions([]);
      setTotalCost(0);
      setImprovedRegions([]);
      setCorrectionStats({
        totalCorrections: 0,
        appliedCorrections: 0,
        inputTokens: 0,
        outputTokens: 0,
        modelName: 'gpt-4o',
        inputCost: 0,
        outputCost: 0,
        totalCost: 0,
        processingTime: 0,
        lastUpdateTime: Date.now()
      });
      
      // Crear URL para el video/audio
      const fileUrl = URL.createObjectURL(file);
      setVideoUrl(fileUrl);
      setIsPlaying(false);
    }
  };

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
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
      setError('Por favor seleccione un archivo de vídeo o audio para transcribir');
      return;
    }

    setIsLoading(true);
    setStatus('processing');
    setError(null);
    setProgress(0);
    setSegments([]);
    setHasUnsavedChanges(false);
    setSuggestions([]);
    setTotalCost(0);
    setImprovedRegions([]);
    setCorrectionStats({
      totalCorrections: 0,
      appliedCorrections: 0,
      inputTokens: 0,
      outputTokens: 0,
      modelName: 'gpt-4o',
      inputCost: 0,
      outputCost: 0,
      totalCost: 0,
      processingTime: 0,
      lastUpdateTime: Date.now()
    });
    
    // Iniciar la simulación de progreso inmediatamente
    const progressInterval = startFakeProgressBar();

    try {
      console.log("Iniciando transcripción...");
      
      // Paso 1: Subir el archivo al servidor
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const uploadResponse = await fetch(`${API_BASE_URL}/api/upload-video-for-transcription`, {
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
      
      // Paso 2: Iniciar la transcripción
      const transcribeFormData = new FormData();
      transcribeFormData.append('file_id', uploadResult.file_id);
      transcribeFormData.append('original_name', uploadResult.original_name);
      transcribeFormData.append('model_name', 'gpt-4o-transcribe');
      transcribeFormData.append('formats', 'txt,json');
      
      const transcribeResponse = await fetch(`${API_BASE_URL}/api/transcribe-video`, {
        method: 'POST',
        body: transcribeFormData,
      });
      
      if (!transcribeResponse.ok) {
        const errorData = await transcribeResponse.json();
        throw new Error(errorData.detail || 'Error al transcribir el archivo');
      }
      
      const transcribeResult = await transcribeResponse.json();
      console.log("Transcripción completada:", transcribeResult);
      
      // Guardar el texto de la transcripción y los archivos generados
      setTranscriptionText(formatTranscriptionText(transcribeResult.text || ''));
      
      // Si hay segmentos en la respuesta, usarlos
      if (transcribeResult.segments && transcribeResult.segments.length > 0) {
        setSegments(transcribeResult.segments);
      }
      
      // Verificar y formatear los archivos procesados
      if (transcribeResult.files && transcribeResult.files.length > 0) {
        // Asegurar que cada URL comienza correctamente
        const formattedFiles = transcribeResult.files.map((file: any) => ({
          ...file,
          url: file.url.startsWith('/') ? file.url : `/${file.url}`
        }));
        setProcessedFiles(formattedFiles);
      } else {
        setProcessedFiles([]);
      }
      
      setStats(transcribeResult.stats || {});
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
      
      setError(err.message || 'Error al transcribir el archivo');
      setStatus('error');
      setIsLoading(false);
    }
  };

  // Guardar las correcciones en el servidor
  const handleSaveCorrections = async () => {
    if (!uploadedFileInfo || !transcriptionText) {
      setError('No hay correcciones para guardar');
      return;
    }

    setIsSaving(true);
    
    try {
      // Crear un objeto con los datos de la transcripción corregida
      const correctedData = {
        file_id: uploadedFileInfo.file_id,
        original_name: uploadedFileInfo.original_name,
        text: transcriptionText,
        segments: segments
      };
      
      // Enviar las correcciones al servidor
      const response = await fetch(`${API_BASE_URL}/api/update-transcription`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(correctedData),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al guardar las correcciones');
      }
      
      const result = await response.json();
      console.log("Correcciones guardadas:", result);
      
      // Actualizar los archivos procesados con los nuevos
      if (result.files) {
        setProcessedFiles(result.files);
      }
      
      setHasUnsavedChanges(false);
      setSavedSuccess(true);
      
    } catch (err: any) {
      console.error('Error al guardar correcciones:', err);
      setError(err.message || 'Error al guardar las correcciones');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownload = (url: string) => {
    if (url) {
      // Corrección: Construir la URL correctamente para manejar el endpoint de descarga
      const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
      console.log(`Intentando descargar archivo desde: ${fullUrl}`);
      
      // Si hay cambios sin guardar, mostrar advertencia
      if (hasUnsavedChanges) {
        if (!window.confirm('Hay cambios sin guardar en la transcripción. ¿Desea guardarlos antes de descargar?')) {
          // El usuario decidió no guardar, procedemos con la descarga
          downloadFile(fullUrl);
          return;
        }
        
        // El usuario quiere guardar primero
        handleSaveCorrections().then(() => {
          downloadFile(fullUrl);
        });
      } else {
        // No hay cambios, procedemos con la descarga
        downloadFile(fullUrl);
      }
    }
  };

  // Función para descargar un archivo
  const downloadFile = (url: string) => {
    console.log(`Iniciando descarga desde: ${url}`);
    
    // Extraer y mostrar más información sobre la URL
    try {
      const parsedUrl = new URL(url);
      console.log(`Ruta: ${parsedUrl.pathname}`);
      
      // Extraer el file_id y filename de la URL (asumiendo formato /api/download-transcript/{file_id}/{filename})
      const parts = parsedUrl.pathname.split('/');
      if (parts.length >= 4) {
        console.log(`API: ${parts[1]}/${parts[2]}`);
        console.log(`file_id: ${parts[3]}`);
        console.log(`filename: ${parts[4]}`);
      }
    } catch (error) {
      console.error("Error analizando URL:", error);
    }

    fetch(url)
      .then(response => {
        if (!response.ok) {
          console.error(`Error en la descarga: ${response.status} ${response.statusText}`);
          throw new Error(`Error al descargar el archivo (${response.status})`);
        }
        console.log('Respuesta recibida correctamente, procesando blob...');
        return response.blob();
      })
      .then(blob => {
        console.log(`Blob recibido: ${blob.type}, ${blob.size} bytes`);
        
        // Crear un elemento <a> temporal
        const a = document.createElement('a');
        const blobUrl = URL.createObjectURL(blob);
        a.href = blobUrl;
        
        // Extraer el nombre del archivo de la URL
        const urlPath = new URL(url).pathname;
        const filename = urlPath.split('/').pop() || 'archivo_descargado';
        console.log(`Nombre de archivo para descarga: ${filename}`);
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        console.log('Descarga iniciada por el navegador');
        
        // Limpiar
        setTimeout(() => {
          document.body.removeChild(a);
          URL.revokeObjectURL(blobUrl);
          console.log('Recursos liberados');
        }, 0);
      })
      .catch(error => {
        console.error('Error al descargar:', error);
        setError(`Error al descargar el archivo: ${error.message}`);
      });
  };

  // Cerrar el menú contextual cuando se hace clic fuera
  useEffect(() => {
    const handleClickOutside = () => {
      setShowContextMenu(false);
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Resetear el estado de guardado después de unos segundos
  useEffect(() => {
    if (savedSuccess) {
      const timer = setTimeout(() => {
        setSavedSuccess(false);
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [savedSuccess]);

  // Verificar si debemos mostrar el botón de transcripción
  const showTranscribeButton = videoUrl && (status === 'idle' || status === 'error');

  // Función para renderizar el texto con las regiones mejoradas subrayadas
  const renderFormattedText = (text: string, regions: {start: number, end: number}[]) => {
    if (!text || regions.length === 0) {
      return <>{text}</>;
    }
    
    // Ordenar las regiones por posición de inicio
    const sortedRegions = [...regions].sort((a, b) => a.start - b.start);
    
    // Crear los fragmentos de texto
    const fragments = [];
    let lastEnd = 0;
    
    for (const region of sortedRegions) {
      // Añadir texto normal antes de la región mejorada
      if (region.start > lastEnd) {
        fragments.push(
          <span key={`normal-${lastEnd}`}>
            {text.substring(lastEnd, region.start)}
          </span>
        );
      }
      
      // Añadir texto mejorado con subrayado verde
      fragments.push(
        <span 
          key={`improved-${region.start}`} 
          className="border-b-2 border-green-500"
        >
          {text.substring(region.start, region.end)}
        </span>
      );
      
      lastEnd = region.end;
    }
    
    // Añadir texto normal después de la última región mejorada
    if (lastEnd < text.length) {
      fragments.push(
        <span key={`normal-${lastEnd}`}>
          {text.substring(lastEnd)}
        </span>
      );
    }
    
    return <>{fragments}</>;
  };

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md p-4">
        <h2 className="text-white font-medium text-center">Herramienta Transcribir</h2>
      </div>
      
      <div className="p-6 bg-primary-50">
        {!videoUrl && (
          <p className="text-center text-gray-700 mb-4">
            Esta herramienta convierte el audio de videos y archivos de audio en texto escrito.
          </p>
        )}
        {!videoUrl ? (
          <div className="mb-6">
            <div className="flex items-center justify-center w-full">
              <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-primary-200 border-dashed rounded-xl cursor-pointer bg-white hover:bg-gray-50">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <FaUpload className="w-8 h-8 mb-3 text-primary-500" />
                  <p className="mb-2 text-sm text-gray-700 text-center">
                    <span className="font-semibold">Haga clic para cargar</span> o arrastre y suelte
                  </p>
                  <p className="text-xs text-gray-500 text-center">Archivos de vídeo o audio (MP4, MP3, WAV)</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept="video/*,audio/*"
                  onChange={handleFileChange}
                  disabled={isLoading}
                />
              </label>
            </div>
          </div>
        ) : null}
        
        {selectedFile && !videoUrl && (
          <div className="mt-3 text-sm text-gray-600 text-center mb-4">
            Archivo seleccionado: {selectedFile.name}
          </div>
        )}
        
        {/* Reproductor de video */}
        {videoUrl && (
          <div className="mb-6">
            <div className="text-sm text-gray-600 text-center mb-2">
              Archivo seleccionado: <span className="font-medium">{selectedFile?.name}</span>
            </div>
            <div className="border border-primary-200 rounded-xl overflow-hidden bg-black shadow-md">
              <div className="relative" style={{ paddingTop: '56.25%' }}> {/* Formato 16:9 */}
                {selectedFile?.type.startsWith('video/') ? (
                  <video 
                    ref={videoRef}
                    className="absolute top-0 left-0 w-full h-full object-contain"
                    src={videoUrl}
                    controls={true}
                    onEnded={() => setIsPlaying(false)}
                  ></video>
                ) : (
                  <div className="absolute top-0 left-0 w-full h-full flex items-center justify-center bg-gray-800">
                    <div className="text-white text-center p-4">
                      <FaMicrophone className="w-12 h-12 mx-auto mb-2 text-primary-400" />
                      <p className="text-sm">Archivo de audio</p>
                    </div>
                  </div>
                )}
                {selectedFile?.type.startsWith('audio/') && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <button 
                      onClick={togglePlayPause}
                      className="w-16 h-16 bg-primary-500 bg-opacity-80 hover:bg-opacity-100 rounded-full flex items-center justify-center transition-all duration-300 focus:outline-none shadow-lg"
                    >
                      {isPlaying ? (
                        <FaPause className="text-white w-6 h-6" />
                      ) : (
                        <FaPlay className="text-white w-6 h-6 ml-1" />
                      )}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Barra de progreso mejorada */}
        {isLoading && (
          <div className="mb-6 mt-2">
            <div className="flex justify-between text-sm text-primary-700 mb-2">
              <span className="font-medium flex items-center">
                <FaCog className="animate-spin mr-2" />
                Procesando transcripción...
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
              {progress < 30 && "Analizando audio..."}
              {progress >= 30 && progress < 60 && "Transcribiendo contenido..."}
              {progress >= 60 && progress < 90 && "Generando formatos de salida..."}
              {progress >= 90 && "Finalizando proceso..."}
            </p>
          </div>
        )}
        
        {/* Área de texto con la transcripción */}
        {transcriptionText && (
          <div className="mt-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-primary-800">Transcripción del audio:</h3>
              
              <button
                onClick={improveFullTextWithAI}
                disabled={isImprovingText || !transcriptionText}
                className={`flex items-center justify-center py-2 px-4 rounded-lg text-white font-medium shadow-md ${
                  isImprovingText || !transcriptionText
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-b from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700'
                }`}
              >
                {isImprovingText ? (
                  <>
                    <FaCog className="animate-spin mr-2" />
                    Mejorando...
                  </>
                ) : (
                  <>
                    <FaMagic className="mr-2" /> Mejorar con IA
                  </>
                )}
              </button>
            </div>
            
            <div className="mb-4 relative border border-primary-200 rounded-lg" ref={editorRef}>
              {/* Editor con el texto formateado (solo para visualización) */}
              <div 
                aria-hidden="true"
                className="w-full p-4 min-h-[400px] text-gray-700 whitespace-pre-wrap overflow-auto"
                style={{
                  zIndex: 1,
                  fontFamily: 'inherit',
                  fontSize: 'inherit',
                  lineHeight: 'inherit'
                }}
              >
                {renderFormattedText(transcriptionText, improvedRegions)}
              </div>
              
              {/* Textarea real (para edición) */}
              <textarea
                ref={textareaRef}
                className="absolute top-0 left-0 w-full h-full p-4 focus:border-primary-500 focus:ring focus:ring-primary-200 focus:ring-opacity-50"
                value={transcriptionText}
                onChange={(e) => {
                  setTranscriptionText(e.target.value);
                  // Al editar manualmente, se resetean las regiones mejoradas
                  if (transcriptionText !== e.target.value) {
                    setImprovedRegions([]);
                  }
                  setHasUnsavedChanges(true);
                }}
                onMouseUp={handleTextSelection}
                onKeyUp={handleTextSelection}
                placeholder="La transcripción del audio aparecerá aquí..."
                style={{
                  resize: 'none',
                  minHeight: '400px',
                  zIndex: 2,
                  color: 'transparent',
                  caretColor: 'black',
                  background: 'transparent',
                  border: 'none',
                  outline: 'none'
                }}
                spellCheck={true}
                lang="es"
              />
              
              {/* Menú contextual */}
              {showContextMenu && selectedText && (
                <div 
                  className="absolute bg-white border border-primary-200 rounded-lg shadow-lg z-10 p-2"
                  style={{ top: `${contextMenuPosition.top}px`, left: `${contextMenuPosition.left}px` }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={improveSelectedTextWithAI}
                    className="flex items-center space-x-2 p-2 hover:bg-primary-50 rounded w-full text-left"
                  >
                    <FaMagic className="text-purple-500" />
                    <span>Mejorar selección con IA</span>
                  </button>
                </div>
              )}
            </div>
            
            {/* Sugerencias de mejora - Diseño mejorado */}
            {suggestions.length > 0 && (
              <div className="mt-4 border border-primary-200 rounded-lg p-4 bg-white">
                <h4 className="text-base font-medium text-primary-700 mb-3">Sugerencias de mejora:</h4>
                
                <div className="space-y-4">
                  {suggestions
                    .filter(s => s.status !== 'rejected' || (s.status === 'rejected' && s.hasChanges))
                    .map(suggestion => (
                    <div 
                      key={suggestion.id} 
                      className={`border rounded-lg overflow-hidden ${
                        suggestion.status === 'applied' 
                          ? 'border-blue-200' 
                          : suggestion.status === 'rejected' 
                            ? 'border-gray-200 opacity-60' 
                            : 'border-primary-100'
                      }`}
                    >
                      {/* Cabecera */}
                      <div className={`p-3 border-b flex justify-between items-center ${
                        suggestion.status === 'applied' 
                          ? 'bg-blue-50 border-blue-200' 
                          : suggestion.status === 'rejected'
                            ? 'bg-gray-50 border-gray-200'
                            : 'bg-primary-50 border-primary-100'
                      }`}>
                        <span className={`font-medium ${
                          suggestion.status === 'applied' 
                            ? 'text-blue-800'
                            : suggestion.status === 'rejected'
                              ? 'text-gray-500'
                              : 'text-primary-800'
                        }`}>
                          {suggestion.status === 'applied' 
                            ? 'Mejora aplicada'
                            : suggestion.status === 'rejected'
                              ? 'Sugerencia rechazada'
                              : 'Sugerencia de mejora'}
                        </span>
                        <span className="text-xs text-gray-500">Coste: ${suggestion.cost.toFixed(8)} USD</span>
                      </div>
                      
                      {/* Contenido en formato de comparación lado a lado */}
                      <div className="p-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Texto original */}
                          <div className={`border rounded p-3 ${
                            suggestion.status === 'applied'
                              ? 'border-blue-200 bg-blue-50'
                              : 'border-gray-200 bg-gray-50'
                          }`}>
                            <div className={`font-medium mb-2 text-sm border-b pb-1 ${
                              suggestion.status === 'applied'
                                ? 'text-blue-700 border-blue-200'
                                : 'text-gray-700 border-gray-200'
                            }`}>
                              Texto original:
                            </div>
                            <p className={`text-sm whitespace-pre-wrap ${
                              suggestion.status === 'applied'
                                ? 'text-blue-600'
                                : 'text-gray-700'
                            }`}>
                              {suggestion.originalText}
                            </p>
                          </div>
                          
                          {/* Texto mejorado */}
                          <div className={`border rounded p-3 ${
                            suggestion.status === 'applied'
                              ? 'border-blue-200 bg-blue-50'
                              : suggestion.hasChanges
                                ? 'border-green-200 bg-green-50'
                                : 'border-gray-200 bg-gray-100'
                          }`}>
                            <div className={`font-medium mb-2 text-sm border-b pb-1 ${
                              suggestion.status === 'applied'
                                ? 'text-blue-700 border-blue-200'
                                : suggestion.hasChanges
                                  ? 'text-green-700 border-green-200'
                                  : 'text-gray-500 border-gray-200'
                            }`}>
                              {suggestion.hasChanges 
                                ? suggestion.status === 'applied' ? 'Texto aplicado:' : 'Texto mejorado:'
                                : 'Sin mejoras disponibles:'}
                            </div>
                            <p className={`text-sm whitespace-pre-wrap ${
                              suggestion.status === 'applied'
                                ? 'text-blue-600'
                                : suggestion.hasChanges
                                  ? 'text-green-700'
                                  : 'text-gray-500 italic'
                            }`}>
                              {suggestion.hasChanges 
                                ? suggestion.improvedText 
                                : 'No se encontraron mejoras significativas para este fragmento de texto.'}
                            </p>
                          </div>
                        </div>
                        
                        {/* Botones de acción según el estado */}
                        <div className="flex justify-end space-x-2 mt-3">
                          {suggestion.status === 'pending' && suggestion.hasChanges && (
                            <>
                              <button
                                onClick={() => rejectSuggestion(suggestion.id)}
                                className="flex items-center justify-center py-1 px-3 rounded text-red-600 border border-red-200 hover:bg-red-50"
                              >
                                <FaTimes className="mr-1" /> Rechazar
                              </button>
                              <button
                                onClick={() => applySuggestion(suggestion)}
                                className="flex items-center justify-center py-1 px-3 rounded text-white bg-green-500 hover:bg-green-600"
                              >
                                <FaCheck className="mr-1" /> Aplicar
                              </button>
                            </>
                          )}
                          
                          {suggestion.status === 'applied' && (
                            <button
                              onClick={() => undoSuggestion(suggestion)}
                              className="flex items-center justify-center py-1 px-3 rounded text-white bg-blue-500 hover:bg-blue-600"
                            >
                              <FaUndo className="mr-1" /> Deshacer
                            </button>
                          )}
                          
                          {suggestion.status === 'rejected' && suggestion.hasChanges && (
                            <button
                              onClick={() => setSuggestions(prev => 
                                prev.map(s => s.id === suggestion.id ? {...s, status: 'pending'} : s)
                              )}
                              className="flex items-center justify-center py-1 px-3 rounded text-gray-600 border border-gray-200 hover:bg-gray-100"
                            >
                              <FaRedo className="mr-1" /> Reconsiderar
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Mostrar costo total si hay alguno */}
            {totalCost > 0 && (
              <div className="text-sm text-right mt-4 mb-2 text-primary-600">
                Coste total de mejoras aplicadas: ${totalCost.toFixed(6)} USD
              </div>
            )}
            
            {/* Botón para guardar correcciones */}
            <div className="mt-4 flex justify-center space-x-3">
              <button
                onClick={handleSaveCorrections}
                disabled={isSaving || !hasUnsavedChanges}
                className={`flex items-center justify-center py-2 px-4 rounded-lg text-white font-medium shadow-md ${
                  isSaving || !hasUnsavedChanges
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-b from-green-500 to-green-600 hover:from-green-600 hover:to-green-700'
                }`}
              >
                {isSaving ? (
                  <>
                    <FaCog className="animate-spin mr-2" />
                    Guardando...
                  </>
                ) : (
                  <>
                    <FaSave className="mr-2" /> Guardar cambios
                  </>
                )}
              </button>
              
              <button
                onClick={() => {
                  setSelectedFile(null);
                  setVideoUrl(null);
                  setTranscriptionText('');
                  setSegments([]);
                  setStatus('idle');
                  setProcessedFiles([]);
                  setStats(null);
                  setHasUnsavedChanges(false);
                  setError(null);
                  setSuggestions([]);
                  setTotalCost(0);
                  setImprovedRegions([]);
                  setCorrectionStats({
                    totalCorrections: 0,
                    appliedCorrections: 0,
                    inputTokens: 0,
                    outputTokens: 0,
                    modelName: 'gpt-4o',
                    inputCost: 0,
                    outputCost: 0,
                    totalCost: 0,
                    processingTime: 0,
                    lastUpdateTime: Date.now()
                  });
                }}
                className="flex items-center justify-center py-2 px-4 rounded-lg text-white font-medium shadow-md bg-gradient-to-b from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700"
              >
                <FaUpload className="mr-2" /> Nuevo archivo
              </button>
              
              {savedSuccess && (
                <div className="ml-3 text-green-600 flex items-center">
                  <FaCheckCircle className="mr-1" /> Cambios guardados
                </div>
              )}
            </div>
            
            {stats && (
              <div className="mt-4 bg-primary-50 p-4 rounded-lg border border-primary-200">
                <h4 className="text-base font-medium text-primary-700 mb-2">Estadísticas de transcripción:</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Duración</span>
                    <span>{stats.duración_audio || "N/A"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Minutos transcritos</span>
                    <span>{stats.minutos_transcritos || "0"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Palabras</span>
                    <span>{stats.palabras || "0"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Modelo</span>
                    <span>{stats.modelo_utilizado || "N/A"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Coste por minuto</span>
                    <span>{stats.coste_por_minuto || "0€"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Coste total</span>
                    <span>{stats.coste_total || "0€"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Tiempo proceso</span>
                    <span>{stats.tiempo_proceso || "N/A"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Velocidad</span>
                    <span>{stats.velocidad_procesamiento || "0x"}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-primary-100">
                    <span className="font-medium block text-primary-800">Oraciones</span>
                    <span>{segments.length}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Estadísticas de corrección con IA */}
            {correctionStats.totalCorrections > 0 && (
              <div className="mt-4 bg-purple-50 p-4 rounded-lg border border-purple-200">
                <h4 className="text-base font-medium text-purple-700 mb-2">Estadísticas de corrección:</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Modelo</span>
                    <span>{correctionStats.modelName}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Correcciones sugeridas</span>
                    <span>{correctionStats.totalCorrections}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Correcciones aplicadas</span>
                    <span>{correctionStats.appliedCorrections}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Tokens entrada</span>
                    <span>{correctionStats.inputTokens}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Tokens salida</span>
                    <span>{correctionStats.outputTokens}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Tiempo proceso</span>
                    <span>{correctionStats.processingTime.toFixed(2)}s</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Coste entrada</span>
                    <span>${correctionStats.inputCost.toFixed(6)} USD</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Coste salida</span>
                    <span>${correctionStats.outputCost.toFixed(6)} USD</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-purple-100">
                    <span className="font-medium block text-purple-800">Coste total</span>
                    <span>${correctionStats.totalCost.toFixed(6)} USD</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        <div className="space-y-4">
          {/* Mostrar el botón solo cuando sea necesario */}
          {showTranscribeButton && (
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
                  <FaMicrophone className="mr-2" /> Transcribir audio
                </>
              )}
            </button>
          )}
          
          {/* Sección de archivos generados con un nuevo diseño */}
          {processedFiles.length > 0 && (
            <div className="mt-4 bg-primary-50 p-5 rounded-xl border border-primary-200">
              <h3 className="text-lg font-medium text-primary-800 text-center mb-4">Archivos generados:</h3>
              
              <div className="space-y-3">
                {processedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between bg-white p-3 rounded-lg border border-primary-200">
                    <span className="text-primary-700 font-medium truncate pr-4">{file.name}</span>
                    <button
                      onClick={() => handleDownload(file.url)}
                      className="bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white px-4 py-2 rounded-lg flex items-center shadow-md transition-colors"
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
            <FaCheckCircle className="mr-2" /> Transcripción completada. Lista para descargar.
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoTranscribeTool; 