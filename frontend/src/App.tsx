import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Home from './pages/Home';
import AutofitTool from './pages/slides/AutofitTool';
import BatchProcessTool from './pages/slides/BatchProcessTool';
import Dictionary from './pages/docs/Dictionary';
import Tutorials from './pages/docs/Tutorials';
import ColorPalette from './pages/ColorPalette';
import TranslationTools from './pages/slides/TranslationTools';
import CapturesTools from './pages/slides/CapturesTools';
import SplitPptxPage from './pages/slides/SplitPptxPage';
import VideoCutPage from './pages/video/VideoCutPage';
import VideoTranscribePage from './pages/video/VideoTranscribePage';
import VideoTranslatePage from './pages/video/VideoTranslatePage';
import VideoMontagePage from './pages/video/VideoMontagePage';
import AudioGeneratePage from './pages/video/AudioGeneratePage';
import ChatSettings from './pages/settings/ChatSettings';
import ChatBubble from './components/chat/ChatBubble';
import { FaPalette, FaSearch, FaQuestion, FaBell, FaUser, FaHome } from 'react-icons/fa';

function App() {
  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar - Fijo */}
      <div className="w-64 h-screen flex-shrink-0">
        <Sidebar />
      </div>
      
      {/* Contenedor principal */}
      <div className="flex flex-col flex-1 relative">
        {/* Header Superior - Fijo */}
        <div className="bg-gradient-to-b from-[#c29e74] to-[#a78559] border-b border-[#b9a682] h-[60px] flex items-center px-4 z-10 shadow-md sticky top-0">
          {/* Contenedor flexible con tres secciones */}
          <div className="flex w-full items-center">
            {/* Sección izquierda (vacía o para otros elementos) */}
            <div className="w-1/4"></div>
            
            {/* Búsqueda global (centrada) */}
            <div className="w-2/4 flex justify-center">
              <div className="relative w-full max-w-sm">
                <input 
                  type="text" 
                  placeholder="Buscar..." 
                  className="bg-white bg-opacity-75 text-gray-800 pl-8 pr-4 py-1.5 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-[#b9a682] w-full"
                />
                <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-sm" />
              </div>
            </div>
            
            {/* Botones de acción rápida (derecha) */}
            <div className="w-1/4 flex justify-end space-x-2">
              <Link to="/" className="p-2 rounded-full hover:bg-[#e8a06e] text-white">
                <FaHome title="Inicio" size={16} />
              </Link>
              <button className="p-2 rounded-full hover:bg-[#e8a06e] text-white">
                <FaQuestion title="Ayuda" size={16} />
              </button>
              <button className="p-2 rounded-full hover:bg-[#e8a06e] text-white">
                <FaBell title="Notificaciones" size={16} />
              </button>
              <button className="p-2 rounded-full hover:bg-[#e8a06e] text-white">
                <FaUser title="Perfil de usuario" size={16} />
              </button>
            </div>
          </div>
        </div>
        
        {/* Contenido de la página con footer integrado - Scrolleable */}
        <div className="overflow-y-auto h-[calc(100vh-60px)]">
          <div className="flex flex-col min-h-full">
            {/* Contenido principal - Crece para llenar el espacio */}
            <div className="flex-grow">
              <div className="max-w-6xl mx-auto px-6 py-4">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/slides/autofit" element={<AutofitTool />} />
                  <Route path="/slides/batch" element={<BatchProcessTool />} />
                  <Route path="/docs/dictionary" element={<Dictionary />} />
                  <Route path="/docs/tutorials" element={<Tutorials />} />
                  <Route path="/colors" element={<ColorPalette />} />
                  <Route path="/slides/translation" element={<TranslationTools />} />
                  <Route path="/slides/captures" element={<CapturesTools />} />
                  <Route path="/slides/split" element={<SplitPptxPage />} />
                  
                  {/* Nuevas rutas para las herramientas de vídeo */}
                  <Route path="/video/cut" element={<VideoCutPage />} />
                  <Route path="/video/transcribe" element={<VideoTranscribePage />} />
                  <Route path="/video/translate" element={<VideoTranslatePage />} />
                  <Route path="/video/montage" element={<VideoMontagePage />} />
                  <Route path="/video/generate" element={<AudioGeneratePage />} />
                  
                  {/* Rutas de configuración */}
                  <Route path="/settings" element={<ChatSettings />} />
                </Routes>
              </div>
            </div>
            
            {/* Footer global - Al final del contenido scrolleable */}
            <div className="w-full px-4 flex items-center justify-center h-[45px] text-xs text-gray-700 bg-gradient-to-b from-[#e6dcbf] to-[#d4c9a7] border-t border-[#b9a682] shadow-md mt-auto">
              Design by Creativek © {new Date().getFullYear()} INSCO Project 1.0 beta
            </div>
          </div>
        </div>
      </div>
      
      {/* Chat Bubble - Fijo en la esquina inferior derecha */}
      <ChatBubble />
    </div>
  );
}

export default App; 