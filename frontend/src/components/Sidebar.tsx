import React from 'react';
import { 
  FaFileImport, FaCamera,
  FaFileVideo, FaCut, FaVolumeUp,
  FaBook, FaPalette, FaVideo, FaCog,
  FaSearch, FaUser, FaBell, FaQuestion,
  FaObjectGroup, FaEdit, FaMicrophone,
  FaPen, FaLanguage, FaFilm
} from 'react-icons/fa';
import { MdGTranslate } from 'react-icons/md';
import { Link, useLocation } from 'react-router-dom';
import logoImage from '../assets/logo.png';

type CategoryProps = {
  title: string;
  tools: {
    id: string;
    name: string;
    icon: React.ReactNode;
    path: string;
  }[];
  currentPath: string;
};

const Category: React.FC<CategoryProps> = ({ title, tools, currentPath }) => {
  return (
    <div className="mb-6">
      <div className="text-white mb-3 pl-4 font-semibold uppercase text-sm tracking-wider">
        {title}
      </div>
      <div className="space-y-1">
        {tools.map((tool) => {
          const isActive = currentPath === tool.path;
          return (
            <Link
              key={tool.id}
              to={tool.path}
              className={`flex items-center ${
                isActive 
                  ? 'bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md' 
                  : 'text-gray-200 hover:bg-primary-600'
              } px-4 py-2 rounded-lg transition-colors`}
            >
              <div className={`w-6 h-6 flex items-center justify-center ${isActive ? 'text-white' : 'text-gray-300'}`}>
                {tool.icon}
              </div>
              <span className="ml-3 text-sm">{tool.name}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
};

const Sidebar = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  const slidesTools = [
    {
      id: 'autofit',
      name: 'Autofit',
      icon: <FaFileImport size={16} />,
      path: '/slides/autofit',
    },
    {
      id: 'split',
      name: 'Dividir',
      icon: <FaCut size={16} />,
      path: '/slides/split',
    },
    {
      id: 'translation',
      name: 'Traducir',
      icon: <MdGTranslate size={16} />,
      path: '/slides/translation',
    },
    {
      id: 'captures',
      name: 'Capturas',
      icon: <FaCamera size={16} />,
      path: '/slides/captures',
    },
  ];

  const audioTools = [
    {
      id: 'transcribe',
      name: 'Transcribir',
      icon: <FaMicrophone size={16} />,
      path: '/video/transcribe',
    },
    {
      id: 'translate',
      name: 'Traducir',
      icon: <MdGTranslate size={16} />,
      path: '/video/translate',
    },
    {
      id: 'generate',
      name: 'Generar',
      icon: <FaVolumeUp size={16} />,
      path: '/video/generate',
    },
  ];

  const videoTools = [
    {
      id: 'cut',
      name: 'Cortar',
      icon: <FaCut size={16} />,
      path: '/video/cut',
    },
    {
      id: 'montage',
      name: 'Montaje',
      icon: <FaFilm size={16} />,
      path: '/video/montage',
    },
  ];

  const docsTools = [
    {
      id: 'dictionary',
      name: 'Diccionario',
      icon: <FaBook size={16} />,
      path: '/docs/dictionary',
    },
    {
      id: 'tutorials',
      name: 'Tutoriales',
      icon: <FaVideo size={16} />,
      path: '/docs/tutorials',
    },
  ];

  return (
    <div className="h-full flex flex-col shadow-md bg-primary-700">
      <div className="px-4 py-0 flex justify-center items-center bg-gradient-to-b from-[#c29e74] to-[#a78559] border-b border-[#b9a682] h-[60px]">
        <Link to="/" className="cursor-pointer">
          <img 
            src={logoImage} 
            alt="INSCO Logo" 
            className="h-12 object-contain w-auto hover:opacity-90 transition-opacity"
          />
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-6">
        <Category
          title="Diapositivas"
          tools={slidesTools}
          currentPath={currentPath}
        />
        
        <Category
          title="Audio"
          tools={audioTools}
          currentPath={currentPath}
        />
        
        <Category
          title="Vídeo"
          tools={videoTools}
          currentPath={currentPath}
        />

        <Category
          title="Documentación"
          tools={docsTools}
          currentPath={currentPath}
        />
      </div>

      <div className="border-t border-primary-600">
        <Link
          to="/settings"
          className={`flex items-center ${
            currentPath === '/settings' 
              ? 'bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md' 
              : 'text-gray-200 hover:bg-primary-600'
          } px-4 py-3 transition-colors`}
        >
          <FaCog className={`w-4 h-4 ${currentPath === '/settings' ? 'text-white' : 'text-gray-300'}`} />
          <span className="ml-3 text-sm">Ajustes</span>
        </Link>
      </div>
    </div>
  );
};

export default Sidebar; 