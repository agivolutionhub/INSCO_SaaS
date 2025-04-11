import SplitPptx from '../../components/SplitPptx';

const SplitPptxPage = () => {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta Dividir</h1>
        <p className="text-primary-700">
          Esta herramienta divide presentaciones PPTX grandes en múltiples archivos más pequeños.
        </p>
      </div>
      
      <SplitPptx />
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">¿Por qué dividir presentaciones?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Ventajas</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Facilita el manejo de presentaciones muy extensas</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Mejora el rendimiento al trabajar con archivos más pequeños</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Permite distribuir partes específicas de una presentación</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">✓</span>
                <span>Útil para dividir presentaciones por módulos o temas</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-50 p-4 rounded-lg">
            <h3 className="font-medium text-primary-600 mb-2">Usos habituales</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Separar presentaciones extensas de cursos y webinars</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Crear subconjuntos temáticos de una presentación principal</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Organizar el contenido por niveles o etapas</span>
              </li>
              <li className="flex items-start">
                <span className="text-primary-500 mr-2">•</span>
                <span>Reducir el tamaño para compartir por correo electrónico</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SplitPptxPage; 