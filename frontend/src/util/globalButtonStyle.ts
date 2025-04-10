// Estilos comunes para los botones naranja de la aplicación
export const getButtonStyle = (isDisabled: boolean) => {
  return `flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
    isDisabled
      ? 'bg-gray-400 cursor-not-allowed'
      : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
  }`;
};

export const getSmallButtonStyle = (isDisabled: boolean) => {
  return `flex items-center px-3 py-2 rounded-lg text-white text-sm shadow-md ${
    isDisabled
      ? 'bg-gray-400 cursor-not-allowed'
      : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
  }`;
};

export const getFullWidthButtonStyle = (isDisabled: boolean) => {
  return `w-full flex items-center justify-center py-3 px-4 rounded-lg text-white font-medium shadow-md ${
    isDisabled
      ? 'bg-gray-400 cursor-not-allowed'
      : 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] hover:from-[#c79b6d] hover:to-[#b78c5e]'
  }`;
};

export const getOutlineButtonStyle = (isDisabled: boolean) => {
  return `flex items-center justify-center py-2 px-4 rounded-lg font-medium shadow-sm border ${
    isDisabled
      ? 'bg-gray-200 border-gray-300 text-gray-500 cursor-not-allowed'
      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-100'
  }`;
};

// Constantes de colores para mantener consistencia
export const BUTTON_COLORS = {
  primaryGradient: {
    from: '#daaa7c',
    to: '#c79b6d',
    hoverFrom: '#c79b6d',
    hoverTo: '#b78c5e'
  },
  disabled: {
    bg: 'bg-gray-400',
    text: 'text-gray-300'
  }
};

export const globalButtonStyle = {
  primary: 'bg-gradient-to-b from-[#c29e74] to-[#a78559] hover:from-[#a78559] hover:to-[#937448] text-white shadow-md'
};

export const globalHeaderStyle = {
  primary: 'bg-gradient-to-b from-[#c29e74] to-[#a78559] text-white shadow-md'
}; 