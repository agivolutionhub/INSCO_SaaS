// Este servicio manejará las comunicaciones con el webhook del chat

interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface ChatResponse {
  message: string;
  timestamp: Date;
}

class ChatService {
  private webhookUrl: string = 'https://workflow.agivolution.com/webhook/auditor';
  
  /**
   * Establece la URL del webhook
   * @param url URL del webhook
   */
  setWebhookUrl(url: string): void {
    this.webhookUrl = url;
  }
  
  /**
   * Verifica si hay una URL de webhook configurada
   */
  isConfigured(): boolean {
    return !!this.webhookUrl;
  }
  
  /**
   * Formatea el texto para mostrarlo correctamente
   * @param text Texto a formatear
   */
  private formatText(text: string): string {
    if (!text) return "";
    
    return text
      // Reemplazar representaciones de salto de línea por saltos reales
      .replace(/\\n/g, '\n')
      .replace(/\\r\\n/g, '\n')
      .replace(/\\r/g, '\n')
      .replace(/\n1\./g, '\n\n1.') // Mejora de listas
      .replace(/\n\- /g, '\n\n- ') // Mejora de listas
      .replace(/\n\n\n+/g, '\n\n') // Eliminar múltiples saltos
      
      // Eliminar caracteres de formateo Markdown que no usaremos
      .replace(/^#{1,6}\s+/gm, '') // Eliminar títulos Markdown (###, ##, etc.)
      // NOTA: Ya no eliminamos las negritas con ** ni las cursivas con * para permitir su uso
      // .replace(/\*\*([^*]+)\*\*/g, '$1') // Eliminar negritas (**)
      // .replace(/\*([^*]+)\*/g, '$1') // Eliminar cursivas (*)
      .replace(/\_\_([^_]+)\_\_/g, '$1') // Eliminar negritas (__)
      .replace(/\_([^_]+)\_/g, '$1') // Eliminar cursivas (_)
      .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // Eliminar enlaces Markdown
      .replace(/`([^`]+)`/g, '$1') // Eliminar código inline
      .replace(/```[a-z]*\n([\s\S]*?)```/g, '$1') // Eliminar bloques de código
      
      // Normalizar etiquetas HTML que podrían estar en el texto
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<p>/gi, '\n')
      .replace(/<\/p>/gi, '')
      .replace(/<div>/gi, '\n')
      .replace(/<\/div>/gi, '')
      .replace(/<li>/gi, '\n• ')
      .replace(/<\/li>/gi, '')
      .replace(/<ul>/gi, '\n')
      .replace(/<\/ul>/gi, '\n')
      .replace(/<h[1-6]>/gi, '\n')
      .replace(/<\/h[1-6]>/gi, '\n')
      // Conservamos las etiquetas de estilo para negritas y cursivas
      // .replace(/<strong>/gi, '')
      // .replace(/<\/strong>/gi, '')
      // .replace(/<b>/gi, '')
      // .replace(/<\/b>/gi, '')
      // .replace(/<em>/gi, '')
      // .replace(/<\/em>/gi, '')
      // .replace(/<i>/gi, '')
      // .replace(/<\/i>/gi, '')
      
      // Limpiar otros elementos HTML que no queremos (pero preservando <strong>, <b>, <em>, <i>, etc.)
      .replace(/<(?!\/?(?:strong|b|em|i)(?:\s[^>]*)?>)[^>]*>/g, '');
  }
  
  /**
   * Limpia una respuesta de caracteres y estructuras JSON no deseadas
   * @param text Texto a limpiar
   */
  private cleanResponse(text: string): string {
    if (!text) return "";
    
    try {
      // Intentamos encontrar el patrón "output":"..." que parece estar en las respuestas
      const outputMatch = text.match(/"output"\s*:\s*"([^"]*)"/) || 
                          text.match(/"output"\s*:\s*'([^']*)'/) ||
                          text.match(/output\s*:\s*"([^"]*)"/) ||
                          text.match(/output\s*:\s*'([^']*)'/) ||
                          text.match(/"message"\s*:\s*"([^"]*)"/) ||
                          text.match(/"message"\s*:\s*'([^']*)'/) ||
                          text.match(/message\s*:\s*"([^"]*)"/) ||
                          text.match(/message\s*:\s*'([^']*)'/) ||
                          text.match(/:\s*"([^"]*)"/) ||
                          text.match(/:\s*'([^']*)'/) ||
                          text.match(/{["']?([\w\s]+)["']?\s*:\s*["'](.+)["']}/) ||
                          text.match(/"([^"]*)"/) ||
                          text.match(/'([^']*)'/) ||
                          null;
      
      if (outputMatch && outputMatch[1]) {
        // Si encontramos el patrón, extraemos solo el contenido
        let cleanedText = outputMatch[1]
          // Escapar secuencias especiales que el JSON podría haber escapado
          .replace(/\\"/g, '"')
          .replace(/\\'/g, "'")
          .replace(/\\\\/g, "\\");
          
        return this.formatText(cleanedText);
      }
      
      // Si parece ser un objeto JSON completo:
      if (text.trim().startsWith('{') && text.trim().endsWith('}')) {
        try {
          const jsonObj = JSON.parse(text);
          
          // Buscar algunas propiedades comunes donde podría estar el texto
          if (jsonObj.output) return this.formatText(typeof jsonObj.output === 'string' ? jsonObj.output : JSON.stringify(jsonObj.output));
          if (jsonObj.message) return this.formatText(typeof jsonObj.message === 'string' ? jsonObj.message : JSON.stringify(jsonObj.message));
          if (jsonObj.text) return this.formatText(typeof jsonObj.text === 'string' ? jsonObj.text : JSON.stringify(jsonObj.text));
          if (jsonObj.content) return this.formatText(typeof jsonObj.content === 'string' ? jsonObj.content : JSON.stringify(jsonObj.content));
          if (jsonObj.response) return this.formatText(typeof jsonObj.response === 'string' ? jsonObj.response : JSON.stringify(jsonObj.response));
          
          // Si no encontramos una propiedad específica, devolvemos el objeto completo como string
          return this.formatText(JSON.stringify(jsonObj));
        } catch (e) {
          // Si falla el parsing, continuamos con la limpieza manual
        }
      }
      
      // Eliminar estructuras tipo objeto JSON y caracteres especiales
      let cleanedText = text
        // Eliminar corchetes de apertura y cierre externos
        .replace(/^\s*{(.*)}\s*$/, '$1')
        // Eliminar estructuras de objeto comunes en la salida
        .replace(/\{".*?":\s*"(.*?)"\s*}/, '$1')
        .replace(/\{".*?":\s*'(.*?)'\s*}/, '$1')
        .replace(/\{output:\s*"(.*?)"\s*}/, '$1')
        .replace(/\{output:\s*'(.*?)'\s*}/, '$1')
        // Eliminar comillas de formato
        .replace(/^"(.*)"$/, '$1')
        .replace(/^'(.*)'$/, '$1')
        // Eliminar notación de objeto
        .replace(/\[object Object\]/g, '')
        // Limpiar casos específicos del formato que vemos en la imagen
        .replace(/\{"\s*¡Hola!\s*Parece que estamos atrapados en un saludo"\s*:/, '')
        .replace(/\{\s*Si tienes alguna consulta o tema en mente, por favor compártelo\s*:\s*/, '')
        .replace(/\{\s*Estoy aquí para ayudarte\s*:\s*/, '')
        .replace(/\{"(.*?)"\s*:/, '')
        .replace(/"output":\s*"/, '')
        .replace(/"\}\}\}\}$/, '')
        .replace(/\}\}\}\}$/, '')
        .replace(/"\}\}\}$/, '')
        .replace(/\}\}\}$/, '')
        .replace(/"\}\}$/, '')
        .replace(/\}\}$/, '')
        .replace(/"\}$/, '')
        .replace(/\}$/, '')
        // Eliminar secuencias de corchetes y comillas redundantes
        .replace(/["']+/g, '"')
        .replace(/\s*:\s*\{/g, ' ')
        .replace(/\}\s*$/g, '')
        .replace(/^\s*\{\s*/g, '')
        .trim();
      
      return this.formatText(cleanedText);
      
    } catch (e) {
      console.error("Error al limpiar la respuesta:", e);
      return this.formatText(text); // Devolvemos el texto original formateado si algo falla
    }
  }
  
  /**
   * Envía un mensaje al webhook y devuelve la respuesta
   * @param message Mensaje del usuario
   * @param conversationHistory Historial de conversación (opcional)
   */
  async sendMessage(message: string, conversationHistory: ChatMessage[] = []): Promise<ChatResponse> {
    try {
      // Creamos la URL con el mensaje como parámetro de consulta
      const url = new URL(this.webhookUrl);
      url.searchParams.append('message', message);
      
      // Añadimos el historial de conversación como contexto (opcional, según requiera el servicio)
      // Limitamos a los últimos 5 mensajes para mantener la URL en un tamaño razonable
      const recentHistory = conversationHistory.slice(-5);
      if (recentHistory.length > 0) {
        const context = recentHistory
          .map(msg => `${msg.sender === 'user' ? 'Usuario' : 'Asistente'}: ${msg.text}`)
          .join(' | ');
        url.searchParams.append('context', context);
      }
      
      console.log("Enviando petición a:", url.toString());
      
      // Realizamos la petición GET
      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Accept': 'application/json, text/plain, */*',
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error en la respuesta: ${response.status}`);
      }
      
      // Obtenemos el texto plano de la respuesta
      const rawText = await response.text();
      console.log("Respuesta raw:", rawText);
      
      // Procesamos la respuesta
      let responseText = rawText;
      
      try {
        // Si parece ser JSON, intentamos extraer la información relevante
        if (rawText.trim().startsWith('{') || rawText.includes('":') || rawText.includes("':")) {
          try {
            const data = JSON.parse(rawText);
            if (typeof data === 'object' && data !== null) {
              // Intentamos extraer el texto de varias propiedades comunes
              if (data.output) responseText = data.output;
              else if (data.message) responseText = data.message;
              else if (data.text) responseText = data.text;
              else if (data.content) responseText = data.content;
              else if (data.response) responseText = data.response;
              else responseText = rawText;
            }
          } catch (e) {
            // Si falla el parsing JSON, usamos la respuesta original
            responseText = rawText;
          }
        }
        
        // Limpiamos el texto para eliminar caracteres y estructuras JSON no deseadas
        responseText = this.cleanResponse(responseText);
        
      } catch (e) {
        console.error("Error al procesar la respuesta:", e);
        responseText = this.formatText(rawText);
      }
      
      // Última verificación para asegurarnos de que tenemos una respuesta de texto válida
      if (!responseText || responseText === "[object Object]") {
        responseText = "Lo siento, no pude procesar la respuesta correctamente. Por favor, inténtalo de nuevo.";
      }
      
      console.log("Respuesta procesada:", responseText);
      
      return {
        message: responseText,
        timestamp: new Date()
      };
      
    } catch (error) {
      console.error('Error al comunicarse con el webhook:', error);
      return this.getMockResponse(true);
    }
  }
  
  /**
   * Devuelve una respuesta simulada (para fallback o desarrollo)
   */
  private getMockResponse(isError: boolean = false): ChatResponse {
    if (isError) {
      return {
        message: 'Lo siento, parece que hay un problema de conexión. Por favor, inténtalo de nuevo más tarde.',
        timestamp: new Date()
      };
    }
    
    const responses = [
      'Gracias por tu mensaje. Actualmente estoy en modo de desarrollo y no puedo responder a consultas específicas.',
      'Pronto podré responder a tus preguntas de forma más precisa cuando se configure el webhook.',
      '¡Hola! Soy un asistente virtual y estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?',
      'Estoy procesando tu mensaje. Pronto seré capaz de proporcionarte información detallada sobre las herramientas de INSCO.'
    ];
    
    const randomResponse = responses[Math.floor(Math.random() * responses.length)];
    
    return {
      message: randomResponse,
      timestamp: new Date()
    };
  }
}

// Exportamos una instancia única del servicio
export const chatService = new ChatService();

// Exportamos también la interfaz para su uso
export type { ChatMessage, ChatResponse }; 