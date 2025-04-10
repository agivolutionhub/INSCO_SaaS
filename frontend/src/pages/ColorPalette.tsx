import React, { useState } from 'react';
import '../assets/colors.css';

const ColorCard = ({ color, name, hex }: { color: string, name: string, hex: string }) => {
  const [copied, setCopied] = useState(false);
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="flex flex-col items-center bg-white rounded-xl shadow-sm p-3 hover:shadow-md transition-all">
      <div 
        className="w-16 h-16 rounded-lg shadow-md mb-2" 
        style={{ backgroundColor: color }}
      ></div>
      <div className="text-xs font-medium text-center">{name}</div>
      <div className="text-xs text-gray-500">{hex}</div>
      
      {/* Ejemplos de uso */}
      <div className="mt-4 w-full">
        <div className="flex flex-col gap-2 border-t pt-2">
          <div className="text-xs mb-1">Ejemplos:</div>
          <div className="flex justify-between items-center">
            <div className="text-xs py-1 px-2 rounded-lg" style={{ backgroundColor: color }}>Fondo</div>
            <div className="text-xs py-1 px-2 rounded-lg border" style={{ color }}>Texto</div>
            <div className="text-xs py-1 px-2 rounded-lg" style={{ border: `2px solid ${color}` }}>Borde</div>
          </div>
          <button 
            onClick={() => copyToClipboard(color)}
            className="mt-2 w-full text-xs py-1 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            {copied ? '¡Copiado!' : 'Copiar color'}
          </button>
          <button 
            onClick={() => copyToClipboard(`/* ${name} */\ncolor: ${color}; /* texto */\nbackground-color: ${color}; /* fondo */\nborder-color: ${color}; /* bordes */`)}
            className="w-full text-xs py-1 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            {copied ? '¡Copiado!' : 'Copiar CSS'}
          </button>
        </div>
      </div>
    </div>
  );
};

const ColorCategory = ({ title, colors }: { title: string, colors: Array<{name: string, hex: string, color: string}> }) => (
  <div className="bg-white p-6 rounded-xl shadow-md w-full mb-8">
    <h2 className="text-lg font-semibold mb-4">{title}</h2>
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-7 gap-4">
      {colors.map((color) => (
        <ColorCard key={color.name} {...color} />
      ))}
    </div>
  </div>
);

const ColorPalette = () => {
  // Colores primarios
  const primaryColors = [
    { name: 'primary-50', hex: '#f8f6f4', color: 'var(--primary-50)' },
    { name: 'primary-100', hex: '#ebe6df', color: 'var(--primary-100)' },
    { name: 'primary-200', hex: '#d8cdc1', color: 'var(--primary-200)' },
    { name: 'primary-300', hex: '#c2af9d', color: 'var(--primary-300)' },
    { name: 'primary-400', hex: '#aa947c', color: 'var(--primary-400)' },
    { name: 'primary-500', hex: '#81694c', color: 'var(--primary-500)' },
    { name: 'primary-600', hex: '#735d45', color: 'var(--primary-600)' },
    { name: 'primary-700', hex: '#5f4c3a', color: 'var(--primary-700)' },
    { name: 'primary-800', hex: '#4e3e30', color: 'var(--primary-800)' },
    { name: 'primary-900', hex: '#41352a', color: 'var(--primary-900)' },
    { name: 'primary-950', hex: '#231c16', color: 'var(--primary-950)' }
  ];

  // Marrones cálidos
  const warmBrowns = [
    { name: 'warm-brown-1', hex: '#e6d2b5', color: 'var(--warm-brown-1)' },
    { name: 'warm-brown-2', hex: '#d9bc91', color: 'var(--warm-brown-2)' },
    { name: 'warm-brown-3', hex: '#c49e6c', color: 'var(--warm-brown-3)' },
    { name: 'warm-brown-4', hex: '#b58b4c', color: 'var(--warm-brown-4)' },
    { name: 'warm-brown-5', hex: '#9c7a43', color: 'var(--warm-brown-5)' }
  ];

  // Marrones fríos
  const coolBrowns = [
    { name: 'cool-brown-1', hex: '#d9c5b4', color: 'var(--cool-brown-1)' },
    { name: 'cool-brown-2', hex: '#b4a594', color: 'var(--cool-brown-2)' },
    { name: 'cool-brown-3', hex: '#8c7b6b', color: 'var(--cool-brown-3)' },
    { name: 'cool-brown-4', hex: '#6e5f50', color: 'var(--cool-brown-4)' },
    { name: 'cool-brown-5', hex: '#514538', color: 'var(--cool-brown-5)' }
  ];

  // Marrones especiales
  const specialBrowns = [
    { name: 'cappuccino', hex: '#b38b6d', color: 'var(--cappuccino)' },
    { name: 'mocha', hex: '#93806c', color: 'var(--mocha)' },
    { name: 'coffee', hex: '#6f4e37', color: 'var(--coffee)' },
    { name: 'chocolate', hex: '#7b3f00', color: 'var(--chocolate)' },
    { name: 'caramel', hex: '#c19a6b', color: 'var(--caramel)' },
    { name: 'hazelnut', hex: '#ae8964', color: 'var(--hazelnut)' },
    { name: 'cinnamon', hex: '#966842', color: 'var(--cinnamon)' }
  ];

  return (
    <div className="py-8 px-4 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-primary-800 mb-6 text-center">Paleta de Colores Marrones</h1>
      
      <ColorCategory title="Escala de Colores Primary" colors={primaryColors} />
      <ColorCategory title="Marrones Cálidos" colors={warmBrowns} />
      <ColorCategory title="Marrones Fríos" colors={coolBrowns} />
      <ColorCategory title="Variantes Especiales" colors={specialBrowns} />
    </div>
  );
};

export default ColorPalette; 