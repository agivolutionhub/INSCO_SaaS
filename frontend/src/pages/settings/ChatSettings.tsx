import React, { useState, useEffect } from 'react';
import { chatService } from '../../services/ChatService';
import { FaSave, FaSync, FaInfoCircle, FaRedo } from 'react-icons/fa';

const ChatSettings: React.FC = () => {
  const [webhookUrl, setWebhookUrl] = useState('https://workflow.agivolution.com/webhook/2497811d-dbf1-4538-9b43-f76463cfc1ef');
  const [isSaved, setIsSaved] = useState(false);
  const [isError, setIsError] = useState(false);
  const [testMessage, setTestMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Cargar la URL actual desde el localStorage al montar el componente
  useEffect(() => {
    const savedUrl = localStorage.getItem('chatWebhookUrl') || 'https://workflow.agivolution.com/webhook/2497811d-dbf1-4538-9b43-f76463cfc1ef';
    setWebhookUrl(savedUrl);
    
    // Si hay una URL guardada, configurarla en el servicio
    if (savedUrl) {
      chatService.setWebhookUrl(savedUrl);
    }
  }, []);

  const handleSave = () => {
    try {
      // Validar que sea una URL válida
      if (webhookUrl && !isValidUrl(webhookUrl)) {
        setIsError(true);
        setTimeout(() => setIsError(false), 3000);
        return;
      }
      
      // Guardar en localStorage y en el servicio
      localStorage.setItem('chatWebhookUrl', webhookUrl);
      chatService.setWebhookUrl(webhookUrl);
      
      // Mostrar mensaje de éxito
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 3000);
    } catch (error) {
      console.error('Error al guardar la URL del webhook:', error);
      setIsError(true);
      setTimeout(() => setIsError(false), 3000);
    }
  };

  const handleTest = async () => {
    if (!webhookUrl) return;
    
    setIsLoading(true);
    
    try {
      const response = await chatService.sendMessage('Mensaje de prueba');
      setTestMessage(response.message);
      setTimeout(() => setTestMessage(''), 5000);
    } catch (error) {
      console.error('Error al probar el webhook:', error);
      setTestMessage('Error al probar la conexión con el webhook');
      setTimeout(() => setTestMessage(''), 5000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    const defaultUrl = 'https://workflow.agivolution.com/webhook/2497811d-dbf1-4538-9b43-f76463cfc1ef';
    setWebhookUrl(defaultUrl);
    localStorage.setItem('chatWebhookUrl', defaultUrl);
    chatService.setWebhookUrl(defaultUrl);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  const isValidUrl = (url: string) => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Configuración del Chat</h1>
        <p className="text-primary-700">
          Configura la URL del webhook para conectar el asistente con tu backend.
        </p>
      </div>
      
      <div className="bg-white p-6 rounded-xl shadow-md">
        <div className="space-y-4">
          <div>
            <label htmlFor="webhook-url" className="block text-sm font-medium text-gray-700 mb-1">
              URL del Webhook
            </label>
            <div className="flex items-start">
              <input
                id="webhook-url"
                type="text"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://workflow.agivolution.com/webhook/2497811d-dbf1-4538-9b43-f76463cfc1ef"
                className={`flex-grow px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                  isError 
                    ? 'border-red-300 focus:ring-red-500' 
                    : 'border-gray-300 focus:ring-orange-500'
                }`}
              />
            </div>
            <p className="mt-1 text-xs text-gray-500 flex items-center">
              <FaInfoCircle className="mr-1" />
              La URL por defecto es: https://workflow.agivolution.com/webhook/2497811d-dbf1-4538-9b43-f76463cfc1ef
            </p>
          </div>
          
          <div className="flex flex-wrap gap-3 mt-4">
            <button
              onClick={handleSave}
              className="bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e] text-white font-medium px-4 py-2 rounded-lg inline-flex items-center shadow-md"
            >
              <FaSave className="mr-2" /> Guardar URL
            </button>
            
            <button
              onClick={handleTest}
              disabled={!webhookUrl || isLoading}
              className={`font-medium px-4 py-2 rounded-lg inline-flex items-center ${
                !webhookUrl || isLoading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-primary-600 hover:bg-primary-700 text-white'
              }`}
            >
              <FaSync className={`mr-2 ${isLoading ? 'animate-spin' : ''}`} /> Probar Conexión
            </button>

            <button
              onClick={handleReset}
              className="bg-gray-500 hover:bg-gray-600 text-white font-medium px-4 py-2 rounded-lg inline-flex items-center"
            >
              <FaRedo className="mr-2" /> Restaurar por defecto
            </button>
          </div>
          
          {isSaved && (
            <div className="mt-4 p-3 bg-green-50 text-green-700 rounded-lg border border-green-100">
              ✓ La URL del webhook se ha guardado correctamente.
            </div>
          )}
          
          {isError && (
            <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-100">
              ✕ Por favor ingresa una URL válida.
            </div>
          )}
          
          {testMessage && (
            <div className="mt-4 p-3 bg-blue-50 text-blue-700 rounded-lg border border-blue-100">
              <p className="font-medium">Respuesta del webhook:</p>
              <p className="mt-1">{testMessage}</p>
            </div>
          )}
        </div>
      </div>
      
      <div className="mt-8 bg-white p-6 rounded-xl shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">Formato de la Petición</h2>
        
        <div className="text-sm space-y-4">
          <p>
            El webhook funciona con peticiones GET y espera el siguiente formato:
          </p>
          
          <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto">
{`// Request
GET https://workflow.agivolution.com/webhook/2497811d-dbf1-4538-9b43-f76463cfc1ef?message=Mensaje del usuario&context=Historial de conversación`}
          </pre>
          
          <p>
            Donde:
          </p>
          
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>message</strong>: El mensaje del usuario</li>
            <li><strong>context</strong> (opcional): Historial de la conversación para dar contexto</li>
          </ul>
          
          <p className="mt-4">
            La respuesta del webhook será el texto de la respuesta del asistente.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatSettings; 