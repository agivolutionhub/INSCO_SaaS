import React, { useState, useRef, useEffect } from 'react';
import { FaComment, FaTimes, FaPaperPlane, FaPlus, FaMinus } from 'react-icons/fa';
import { chatService, ChatMessage } from '../../services/ChatService';

const ChatBubble: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      text: '¡Hola! Soy el asistente virtual de INSCO. ¿En qué puedo ayudarte?',
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [typingText, setTypingText] = useState('');
  const [fullResponse, setFullResponse] = useState('');
  const [typingSpeed, setTypingSpeed] = useState(20); // ms por caracter
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const typingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-scroll al último mensaje
  useEffect(() => {
    if (isOpen && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isTyping, typingText]);

  // Focus en el input cuando se abre el chat
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Efecto de typing progresivo
  useEffect(() => {
    if (fullResponse && isTyping) {
      let currentPos = 0;
      
      const simulateTyping = () => {
        if (currentPos <= fullResponse.length) {
          setTypingText(fullResponse.substring(0, currentPos));
          currentPos += 1;
          
          // Velocidad variable para simular escritura más realista
          const randomSpeed = typingSpeed + Math.floor(Math.random() * 10);
          typingTimer.current = setTimeout(simulateTyping, randomSpeed);
        } else {
          // Finalizar el efecto de typing y añadir mensaje completo
          finishTypingEffect();
        }
      };
      
      simulateTyping();
      
      return () => {
        if (typingTimer.current) {
          clearTimeout(typingTimer.current);
        }
      };
    }
  }, [fullResponse, isTyping]);

  const finishTypingEffect = () => {
    if (typingTimer.current) {
      clearTimeout(typingTimer.current);
    }
    
    // Añadir el mensaje completo al historial
    const botMessage: ChatMessage = {
      id: Date.now().toString(),
      text: fullResponse,
      sender: 'bot',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, botMessage]);
    setIsTyping(false);
    setTypingText('');
    setFullResponse('');
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    // Añadir mensaje del usuario
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };
    
    // Limpiar el input y mostrar estado de carga
    setInputText('');
    setIsLoading(true);
    setMessages(prev => [...prev, userMessage]);
    
    // Activar estado de typing
    setIsTyping(true);

    try {
      // Usar el historial de mensajes existente
      const response = await chatService.sendMessage(userMessage.text, messages);
      
      // Mínima pausa para una experiencia más natural
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Guardar la respuesta completa para el efecto de typing
      setFullResponse(response.message);
      
    } catch (error) {
      console.error('Error al enviar mensaje:', error);
      
      // En caso de error, mostrar un mensaje sin efecto de typing
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        text: 'Lo siento, ha ocurrido un error al procesar tu mensaje.',
        sender: 'bot',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
      setIsTyping(false);
    } finally {
      setIsLoading(false);
    }
  };

  // Función para iniciar una nueva conversación
  const startNewConversation = () => {
    // Detener cualquier efecto de typing en curso
    if (typingTimer.current) {
      clearTimeout(typingTimer.current);
    }
    
    // Reiniciar estados
    setTypingText('');
    setFullResponse('');
    setIsTyping(false);
    setIsLoading(false);
    
    // Establecer nuevo mensaje de bienvenida
    setMessages([
      {
        id: Date.now().toString(),
        text: '¡Hola! Soy el asistente virtual de INSCO. ¿En qué puedo ayudarte?',
        sender: 'bot',
        timestamp: new Date()
      }
    ]);
    
    // Focus en el input para empezar a escribir
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  // Función para configurar el webhook (para uso futuro)
  const configureWebhook = (url: string) => {
    chatService.setWebhookUrl(url);
  };

  // Componente para la animación de "escribiendo..."
  const TypingIndicator = () => (
    <div className="flex justify-start mb-2">
      <div className="text-gray-500 rounded-lg px-4 py-2 rounded-bl-none max-w-3/4">
        <div className="flex items-center space-x-1">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
    </div>
  );

  // Formatea el texto con saltos de línea y formato markdown básico
  const formatMessageText = (text: string) => {
    if (!text) return null;
    
    // Procesar negritas y cursivas con expresiones regulares
    const processedText = text.split('\n').map((line, i) => {
      let processedLine = line;
      
      // Primero procesamos las negritas (doble asterisco)
      processedLine = processedLine.replace(/\*\*([^*]+)\*\*/g, (_, content) => {
        return `<strong>${content}</strong>`;
      });
      
      // Después procesamos las cursivas (un solo asterisco)
      // Solo procesamos asteriscos que tengan emparejamiento
      processedLine = processedLine.replace(/\*([^*]+)\*/g, (_, content) => {
        return `<em>${content}</em>`;
      });
      
      // Finalmente, eliminamos asteriscos solitarios que puedan haber quedado
      // (como en el caso del ejemplo donde solo hay asterisco inicial)
      let asteriskCount = (processedLine.match(/\*/g) || []).length;
      if (asteriskCount % 2 !== 0) {
        processedLine = processedLine.replace(/\*/g, '');
      }
      
      return (
        <React.Fragment key={i}>
          <span dangerouslySetInnerHTML={{ __html: processedLine }} />
          {i < text.split('\n').length - 1 && <br />}
        </React.Fragment>
      );
    });
    
    return processedText;
  };

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {/* Ventana de chat - Ahora con mucha más altura */}
      {isOpen ? (
        <div className="bg-[#faf8f5] rounded-xl shadow-xl w-80 sm:w-96 flex flex-col animate-fadeIn overflow-hidden border border-gray-200" style={{ maxHeight: 'calc(100vh - 140px)' }}>
          {/* Header - Degradado para coincidir con el resto de la interfaz */}
          <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white p-3 flex justify-between items-center">
            <button 
              onClick={startNewConversation}
              className="text-white hover:text-gray-200 transition-colors flex items-center"
              aria-label="Nueva conversación"
              title="Nueva conversación"
            >
              <FaPlus size={16} />
            </button>
            <h3 className="font-medium text-center flex-1">Asistente INSCO</h3>
            <button 
              onClick={toggleChat}
              className="text-white hover:text-gray-200 transition-colors"
              aria-label="Cerrar chat"
              title="Minimizar chat"
            >
              <FaMinus />
            </button>
          </div>

          {/* Mensajes - Ahora con mucha más altura */}
          <div className="flex-1 p-3 overflow-y-auto" style={{ height: '70vh', minHeight: '500px' }}>
            <div className="space-y-3">
              {messages.map((message) => (
                <div 
                  key={message.id} 
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-3/4 rounded-lg px-4 py-2 ${
                      message.sender === 'user' 
                        ? 'bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white rounded-br-none' 
                        : 'text-gray-800 rounded-bl-none'
                    }`}
                  >
                    <div className="text-sm">{formatMessageText(message.text)}</div>
                    <div className="text-xs text-right mt-1 opacity-70">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Efecto de typing en tiempo real */}
              {isTyping && typingText && (
                <div className="flex justify-start">
                  <div className="text-gray-800 rounded-lg px-4 py-2 rounded-bl-none max-w-3/4">
                    <div className="text-sm">{formatMessageText(typingText)}</div>
                    <div className="text-xs text-right mt-1 opacity-70">
                      {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Indicador de "escribiendo..." solo si no hay texto de typing aún */}
              {isTyping && !typingText && <TypingIndicator />}
              
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input - Estilizado para coincidir con la imagen de referencia */}
          <div className="border-t border-gray-200 p-3 flex bg-[#faf8f5]">
            <div className="flex border border-[#c29e74] rounded-full overflow-hidden flex-1">
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe un mensaje..."
                disabled={isLoading || isTyping}
                className="flex-1 px-4 py-2.5 focus:outline-none disabled:bg-gray-100 border-none bg-white"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputText.trim() || isLoading || isTyping}
                className={`px-4 py-2 ${
                  !inputText.trim() || isLoading || isTyping
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                    : 'bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white hover:from-[#a78559] hover:to-[#937448]'
                }`}
                aria-label="Enviar mensaje"
              >
                <FaPaperPlane />
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Burbuja flotante - Solo se muestra cuando la ventana está cerrada */
        <button
          onClick={toggleChat}
          className="bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white rounded-full w-14 h-14 flex items-center justify-center shadow-lg transition-all duration-200 hover:scale-105 hover:from-[#a78559] hover:to-[#937448]"
          aria-label="Abrir chat"
        >
          <FaComment size={24} />
        </button>
      )}
    </div>
  );
};

export default ChatBubble; 