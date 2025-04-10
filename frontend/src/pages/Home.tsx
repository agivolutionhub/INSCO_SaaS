import { useState, useEffect } from 'react';
import { getDirectories } from '../services/api';
import { FaChartBar, FaFileAlt, FaClock, FaCoins, FaLanguage, FaCalendarAlt, FaServer, FaHistory, FaRocket, FaChartLine, FaChartPie } from 'react-icons/fa';
import { IoDocumentText } from 'react-icons/io5';
import { MdGTranslate, MdOndemandVideo } from 'react-icons/md';
import { Link } from 'react-router-dom';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  Cell,
  PieChart,
  Pie,
  ComposedChart,
  Legend,
  RadialBarChart,
  RadialBar
} from 'recharts';

// Datos simulados para el dashboard
const mockData = {
  totalFiles: 127,
  totalSlides: 1584,
  translatedTexts: 8942,
  apiCalls: 342,
  totalProcessingTime: "03:47:15",
  estimatedCosts: 4.85,
  tokensConsumed: {
    input: 31465,
    output: 37823,
    cached: 12876,
    total: 82164
  },
  cacheStats: {
    hits: 347,
    misses: 142,
    efficiency: 71
  },
  weeklyActivity: [
    { day: 'Lun', count: 12 },
    { day: 'Mar', count: 23 },
    { day: 'Mié', count: 8 },
    { day: 'Jue', count: 17 },
    { day: 'Vie', count: 31 },
    { day: 'Sáb', count: 4 },
    { day: 'Dom', count: 2 }
  ],
  monthlyTrend: [
    { month: 'Ene', files: 45 },
    { month: 'Feb', files: 58 },
    { month: 'Mar', files: 72 },
    { month: 'Abr', files: 64 },
    { month: 'May', files: 82 },
    { month: 'Jun', files: 95 }
  ],
  categoryUsage: [
    { category: 'Diapositivas', percentage: 58 },
    { category: 'Audio', percentage: 26 },
    { category: 'Vídeo', percentage: 16 }
  ],
  toolUsage: [
    // Diapositivas
    { category: 'Diapositivas', tool: 'Traducir', count: 42 },
    { category: 'Diapositivas', tool: 'Autofit', count: 24 },
    { category: 'Diapositivas', tool: 'Dividir', count: 16 },
    { category: 'Diapositivas', tool: 'Capturas', count: 8 },
    // Audio
    { category: 'Audio', tool: 'Transcribir', count: 18 },
    { category: 'Audio', tool: 'Traducir', count: 14 },
    { category: 'Audio', tool: 'Generar', count: 6 },
    // Vídeo
    { category: 'Vídeo', tool: 'Cortar', count: 12 },
    { category: 'Vídeo', tool: 'Montaje', count: 8 }
  ],
  recentActivity: [
    { id: 1, action: 'Traducción completada', item: 'Presentación Q1.pptx', time: 'Hace 2h', status: 'success', size: '2.4MB', slides: 24, duration: '1:45' },
    { id: 2, action: 'Procesamiento por lotes', item: '12 archivos', time: 'Ayer 16:45', status: 'success', size: '18.7MB', slides: 132, duration: '15:20' },
    { id: 3, action: 'Error de traducción', item: 'Informe2023.pptx', time: 'Ayer 14:22', status: 'error', size: '4.1MB', slides: 37, duration: 'N/A' },
    { id: 4, action: 'Vídeo procesado', item: 'Demo_producto.mp4', time: 'Hace 2 días', status: 'success', size: '78.5MB', slides: 'N/A', duration: '4:35' },
    { id: 5, action: 'Traducción completada', item: 'Manual_usuario.pptx', time: 'Hace 3 días', status: 'success', size: '5.2MB', slides: 48, duration: '3:12' },
    { id: 6, action: 'Dividir presentación', item: 'Curso_completo.pptx', time: 'Hace 4 días', status: 'success', size: '12.8MB', slides: 94, duration: '2:45' }
  ]
};

export default function Home() {
  const [directories, setDirectories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Agregar estilos personalizados para la scrollbar
  useEffect(() => {
    const styleElement = document.createElement('style');
    styleElement.textContent = `
      .custom-scrollbar::-webkit-scrollbar {
        width: 6px;
      }
      .custom-scrollbar::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
      }
      .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #d1b78e;
        border-radius: 10px;
      }
      .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #c79b6d;
      }
    `;
    document.head.appendChild(styleElement);
    return () => {
      document.head.removeChild(styleElement);
    };
  }, []);
  
  useEffect(() => {
    const fetchDirectories = async () => {
      try {
        setLoading(true);
        // Simulamos obtener directorios hasta que la API esté completamente configurada
        // const response = await getDirectories();
        // setDirectories(response.directories);
        // Datos de ejemplo para desarrollo
        setDirectories(['WEBINARS', 'CURSOS', 'EJEMPLOS']);
      } catch (err) {
        setError('Error cargando directorios');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchDirectories();
  }, []);

  // Componente para tarjetas principales de estadísticas
  const StatCard = ({ icon, title, value, subtitle, color }: { icon: React.ReactNode, title: string, value: string | number, subtitle?: string, color?: string }) => (
    <div className="bg-white rounded-xl overflow-hidden shadow-md hover:shadow-lg transition-shadow duration-300">
      <div className="p-4">
        <div className="flex items-start">
          <div className={`rounded-full p-3 ${color || 'bg-gradient-to-b from-[#daaa7c] to-[#c79b6d]'} text-white mr-3`}>
            {icon}
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">{title}</h3>
            <div className="text-2xl font-semibold text-gray-800 mt-1">{value}</div>
            {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
          </div>
        </div>
      </div>
    </div>
  );

  // Componente para gráfico de barras semanal con Recharts
  const WeeklyBarChart = ({ data }: { data: {day: string, count: number}[] }) => {
    // Personalización del tooltip
    const CustomTooltip = ({ active, payload, label }: any) => {
      if (active && payload && payload.length) {
        return (
          <div className="bg-white p-2 border border-[#c79b6d] rounded-md shadow-md">
            <p className="text-xs text-gray-700">{`${label}`}</p>
            <p className="text-sm font-semibold text-[#c79b6d]">{`${payload[0].value} actividades`}</p>
          </div>
        );
      }
      return null;
    };
    
    return (
      <div className="h-56 pt-2 pb-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
          >
            <defs>
              <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#daaa7c" />
                <stop offset="100%" stopColor="#c79b6d" />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
            <XAxis 
              dataKey="day" 
              tickLine={false}
              axisLine={false}
              tick={{ fill: '#888', fontSize: 12 }}
            />
            <YAxis hide={true} />
            <Tooltip content={CustomTooltip} />
            <Bar 
              dataKey="count" 
              fill="url(#barGradient)" 
              radius={[4, 4, 0, 0]} 
              barSize={30}
              animationDuration={1000}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };
  
  // Componente para gráfico de línea para tendencia mensual con Recharts
  const MonthlyTrendChart = ({ data }: { data: {month: string, files: number}[] }) => {
    // Formatear los datos para Recharts
    const chartData = data.map(item => ({
      name: item.month,
      value: item.files
    }));
    
    // Personalización del tooltip
    const CustomTooltip = ({ active, payload, label }: any) => {
      if (active && payload && payload.length) {
        return (
          <div className="bg-white p-2 border border-[#c79b6d] rounded-md shadow-md">
            <p className="text-xs text-gray-700">{`${label}`}</p>
            <p className="text-sm font-semibold text-[#c79b6d]">{`${payload[0].value} archivos`}</p>
          </div>
        );
      }
      return null;
    };
    
    return (
      <div className="h-56 pt-2 pb-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 5, left: 5, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorFiles" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#c79b6d" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#c79b6d" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="name" 
              tickLine={false}
              axisLine={false}
              tick={{ fill: '#888', fontSize: 12 }}
            />
            <YAxis 
              hide={true}
            />
            <Tooltip content={CustomTooltip} />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke="#c79b6d" 
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#colorFiles)"
              activeDot={{ r: 6, fill: "#c79b6d", stroke: "white", strokeWidth: 2 }}
              dot={{ 
                r: 4, 
                fill: "white", 
                stroke: "#c79b6d", 
                strokeWidth: 2 
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    );
  };
  
  // Componente para gráfico circular (donut) con Recharts
  const CategoryDonutChart = ({ data }: { data: {type: string, percentage: number}[] }) => {
    // Preparar datos para Recharts con valor numérico
    const chartData = data.map(item => ({
      name: item.type,
      value: item.percentage
    }));
    
    // Colores para las secciones (usando los colores de distribución de tokens)
    const COLORS = ["#c78d6d", "#6d9ac7", "#a2c76d"];
    
    // Personalización del tooltip
    const CustomTooltip = ({ active, payload }: any) => {
      if (active && payload && payload.length) {
        return (
          <div className="bg-white p-2 border border-[#c79b6d] rounded-md shadow-md">
            <p className="text-xs text-gray-700">{`${payload[0].name}`}</p>
            <p className="text-sm font-semibold text-[#c79b6d]">{`${payload[0].value}%`}</p>
          </div>
        );
      }
      return null;
    };
    
    return (
      <div className="h-[300px] mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={false}
              innerRadius={70}
              outerRadius={100}
              paddingAngle={0}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="white" strokeWidth={1} />
              ))}
            </Pie>
            <Tooltip content={CustomTooltip} />
            <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle">
              <tspan x="50%" dy="-5" className="text-3xl font-bold fill-gray-800">{mockData.totalFiles}</tspan>
              <tspan x="50%" dy="20" className="text-sm fill-gray-500">archivos totales</tspan>
            </text>
          </PieChart>
        </ResponsiveContainer>
        <div className="flex justify-center space-x-6 mt-2">
          {chartData.map((item, index) => (
            <div key={index} className="flex items-center text-sm">
              <div 
                className="w-4 h-4 rounded-full mr-2" 
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              ></div>
              <span>{item.name} ({item.value}%)</span>
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  // Componente para gráfico de barras horizontal con Recharts
  const ToolsBarChart = ({ data, maxBars = 11 }: { data: {category: string, tool: string, count: number}[], maxBars?: number }) => {
    // Ordenar datos de mayor a menor y limitar la cantidad
    const sortedData = [...data].sort((a, b) => b.count - a.count).slice(0, maxBars);
    
    // Colores para las categorías
    const getCategoryColor = (category: string) => {
      switch(category) {
        case 'Diapositivas': return '#c79b6d';
        case 'Audio': return '#7db0c7';
        case 'Vídeo': return '#c77d7d';
        default: return '#gray-400';
      }
    };
    
    // Personalización del tooltip
    const CustomTooltip = ({ active, payload, label }: any) => {
      if (active && payload && payload.length) {
        return (
          <div className="bg-white p-2 border border-[#c79b6d] rounded-md shadow-md">
            <p className="text-xs text-gray-700">
              <span className="font-medium">{payload[0].payload.tool}</span>
              <span className="text-xs ml-1 opacity-75">({payload[0].payload.category})</span>
            </p>
            <p className="text-sm font-semibold" style={{ color: getCategoryColor(payload[0].payload.category) }}>
              {`${payload[0].value} usos`}
            </p>
          </div>
        );
      }
      return null;
    };
    
    return (
      <div className="h-[320px] mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={sortedData}
            layout="vertical"
            margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f0f0f0" />
            <XAxis type="number" hide={true} />
            <YAxis 
              type="category" 
              dataKey="tool" 
              tickLine={false}
              axisLine={false}
              tick={{ fill: '#888', fontSize: 12 }}
              width={90}
            />
            <Tooltip content={CustomTooltip} />
            <Bar 
              dataKey="count" 
              barSize={18} 
              radius={[0, 4, 4, 0]}
            >
              {sortedData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={getCategoryColor(entry.category)} 
                  fillOpacity={0.9}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  // Componente para el gráfico de distribución de tokens con Recharts (barra horizontal)
  const TokenDistributionChart = ({ 
    tokensData 
  }: { 
    tokensData: { 
      input: number, 
      output: number, 
      cached: number, 
      total: number 
    } 
  }) => {
    // Preparar datos para la gráfica horizontal
    const chartData = [
      { name: 'Entrada', value: tokensData.input, percentage: ((tokensData.input / tokensData.total) * 100).toFixed(1), color: '#c78d6d' },
      { name: 'Salida', value: tokensData.output, percentage: ((tokensData.output / tokensData.total) * 100).toFixed(1), color: '#6d9ac7' },
      { name: 'Caché', value: tokensData.cached, percentage: ((tokensData.cached / tokensData.total) * 100).toFixed(1), color: '#a2c76d' }
    ];
    
    // Personalización del tooltip
    const CustomTooltip = ({ active, payload }: any) => {
      if (active && payload && payload.length) {
        const { name, value, percentage, color } = payload[0].payload;
        
        return (
          <div className="bg-white p-2 border border-[#c79b6d] rounded-md shadow-md">
            <div className="text-xs text-gray-600">{name}</div>
            <div className="text-sm font-medium" style={{ color }}>{value.toLocaleString()} tokens</div>
            <div className="text-xs">{percentage}% del total</div>
          </div>
        );
      }
      return null;
    };
    
    return (
      <div className="flex flex-col h-64">
        {/* Gráfico principal */}
        <div className="flex-grow">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 5, right: 60, left: 60, bottom: 5 }}
              barCategoryGap={15}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} vertical={false} />
              <XAxis 
                type="number" 
                hide={true}
              />
              <YAxis 
                dataKey="name" 
                type="category" 
                tick={{ fontSize: 13, fill: '#555' }}
                axisLine={false}
                tickLine={false}
                width={60}
              />
              <Tooltip content={CustomTooltip} />
              <Bar 
                dataKey="value" 
                barSize={22}
                radius={[0, 4, 4, 0] as any}
                label={{ 
                  position: 'right',
                  formatter: (value: number) => value.toLocaleString(),
                  fill: '#666',
                  fontSize: 12,
                  offset: 10
                }}
              >
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.color}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        {/* Leyenda en la parte inferior */}
        <div className="grid grid-cols-3 gap-4 mt-4">
          {chartData.map((entry, index) => (
            <div key={index} className="flex items-center justify-center">
              <div 
                className="w-3 h-3 rounded-full mr-2" 
                style={{ backgroundColor: entry.color }}
              ></div>
              <div className="text-center">
                <div className="text-xs font-medium text-gray-600">{entry.name}</div>
                <div className="text-xs text-gray-500">
                  {entry.percentage}%
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-3 text-center">
          <div className="text-sm font-medium">{tokensData.total.toLocaleString()} tokens totales</div>
          <div className="text-xs text-gray-500 mt-1">Costo aproximado: ${mockData.estimatedCosts.toFixed(2)}</div>
        </div>
      </div>
    );
  };

  // Componente para el panel de resumen con Recharts
  const SummaryChart = ({ 
    time, 
    cacheEfficiency, 
    totalTokens 
  }: { 
    time: string, 
    cacheEfficiency: number, 
    totalTokens: number 
  }) => {
    // Calcular tiempo ahorrado (estimado)
    // Asumimos que procesar 1000 tokens manualmente tomaría 2 minutos
    // Y que el procesamiento automático ya está reflejado en el tiempo total
    const tokenProcessingRate = 1000 / 120; // tokens por segundo (manual)
    const manualProcessingTime = totalTokens / tokenProcessingRate; // segundos
    
    // Convertir a formato HH:MM:SS
    const formatTime = (seconds: number) => {
      const hrs = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hrs}h ${mins}m`;
    };
    
    const timeSaved = formatTime(manualProcessingTime);
    
    // Calculando eficiencia como porcentaje
    const timeComponents = time.split(':').map(Number);
    const actualTimeInSeconds = timeComponents[0] * 3600 + timeComponents[1] * 60 + timeComponents[2];
    const efficiencyPercentage = Math.min(99, Math.round((1 - (actualTimeInSeconds / manualProcessingTime)) * 100));
    
    return (
      <div className="flex flex-col space-y-6">
        {/* Tiempo total */}
        <div className="space-y-1">
          <div className="text-sm text-gray-600">Tiempo Total</div>
          <div className="text-xl font-bold text-gray-800 flex items-center">
            <FaClock className="text-[#c79b6d] mr-2" />
            {time}
          </div>
        </div>
        
        {/* Tiempo ahorrado */}
        <div className="space-y-1">
          <div className="text-sm text-gray-600 mb-1">Tiempo Ahorrado</div>
          <div className="bg-gray-100 rounded-lg p-3">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-gray-500">Estimado</span>
              <span className="text-xs text-[#c79b6d] font-bold">{efficiencyPercentage}% más rápido</span>
            </div>
            <div className="text-xl font-bold text-[#c79b6d]">{timeSaved}</div>
            <div className="text-xs text-gray-500 mt-1">vs. procesamiento manual</div>
          </div>
        </div>
        
        {/* Tokens totales */}
        <div className="space-y-1">
          <div className="text-sm text-gray-600">Tokens Totales</div>
          <div className="text-xl font-bold text-gray-800">
            {(totalTokens / 1000).toFixed(1)}K
          </div>
        </div>
      </div>
    );
  };

  if (loading) return (
    <div className="flex justify-center items-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#c79b6d]"></div>
    </div>
  );
  
  if (error) return (
    <div className="p-4 text-red-500 bg-red-50 rounded-lg border border-red-200">
      <div className="flex">
        <FaRocket className="text-red-500 mr-2" />
        <span>{error}</span>
      </div>
    </div>
  );

  return (
    <div className="container mx-auto pt-6">
      {/* Tarjetas de estadísticas principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard 
          icon={<FaFileAlt />} 
          title="Archivos Procesados" 
          value={mockData.totalFiles} 
        />
        <StatCard 
          icon={<IoDocumentText />} 
          title="Diapositivas Traducidas" 
          value={mockData.totalSlides} 
        />
        <StatCard 
          icon={<FaServer />} 
          title="Llamadas API" 
          value={mockData.apiCalls} 
        />
        <StatCard 
          icon={<FaCoins />} 
          title="Costos Estimados" 
          value={`$${mockData.estimatedCosts.toFixed(2)}`}
          subtitle="Basado en tarifas actuales" 
        />
      </div>
      
      {/* Gráficos de actividad y estadísticas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Gráfico Circular - Uso por categoría */}
        <div className="bg-white rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
            <FaChartPie className="mr-2 text-[#c79b6d]" /> 
            Uso por Categoría
          </h2>
          <CategoryDonutChart data={mockData.categoryUsage.map(item => ({ type: item.category, percentage: item.percentage }))} />
        </div>
        
        {/* Gráfico de barras horizontal - Uso por herramienta */}
        <div className="bg-white rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
            <FaChartBar className="mr-2 text-[#c79b6d]" /> 
            Herramientas más utilizadas
          </h2>
          <ToolsBarChart data={mockData.toolUsage} />
        </div>
      </div>
      
      {/* Actividad semanal y tendencia mensual */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Gráfico de Barras - Actividad Semanal */}
        <div className="bg-white rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
            <FaCalendarAlt className="mr-2 text-[#c79b6d]" />
            Actividad Semanal
          </h2>
          <WeeklyBarChart data={mockData.weeklyActivity} />
        </div>
        
        {/* Gráfico de tendencia mensual */}
        <div className="bg-white rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-2 flex items-center">
            <FaChartLine className="mr-2 text-[#c79b6d]" />
            Tendencia Mensual
          </h2>
          <MonthlyTrendChart data={mockData.monthlyTrend} />
        </div>
      </div>
      
      {/* Panel de resumen y distribución de tokens - Invertir posiciones */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Distribución de tokens (ahora a la izquierda, ocupa 2 columnas) */}
        <div className="bg-white rounded-xl p-5 shadow-md lg:col-span-2 order-last lg:order-first">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <FaCoins className="mr-2 text-[#c79b6d]" />
            Distribución de Tokens
          </h2>
          <TokenDistributionChart tokensData={mockData.tokensConsumed} />
        </div>

        {/* Panel de estadísticas (ahora a la derecha, ocupa 1 columna) */}
        <div className="bg-white rounded-xl p-5 shadow-md order-first lg:order-last">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <FaChartBar className="mr-2 text-[#c79b6d]" />
            Resumen
          </h2>
          <SummaryChart 
            time={mockData.totalProcessingTime}
            cacheEfficiency={mockData.cacheStats.efficiency}
            totalTokens={mockData.tokensConsumed.total}
          />
        </div>
      </div>
      
      {/* Actividad reciente (pantalla completa) */}
      <div className="bg-white rounded-xl p-5 shadow-md mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center">
            <FaHistory className="mr-2 text-[#c79b6d]" />
            Actividad Reciente
          </h2>
          <div className="text-sm text-gray-500">
            <span className="font-medium">Última actualización:</span> {new Date().toLocaleString()}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase border-b">
                <th className="py-3 px-4 text-left">Estado</th>
                <th className="py-3 px-4 text-left">Acción</th>
                <th className="py-3 px-4 text-left">Archivo</th>
                <th className="py-3 px-4 text-left">Tamaño</th>
                <th className="py-3 px-4 text-left">Diapositivas</th>
                <th className="py-3 px-4 text-left">Duración</th>
                <th className="py-3 px-4 text-right">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {mockData.recentActivity.map((activity) => (
                <tr key={activity.id} className="hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <div className={`h-2.5 w-2.5 rounded-full ${
                      activity.status === 'success' ? 'bg-green-500' : 
                      activity.status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                    }`}></div>
                  </td>
                  <td className="py-3 px-4 font-medium">{activity.action}</td>
                  <td className="py-3 px-4 text-gray-600">{activity.item}</td>
                  <td className="py-3 px-4 text-gray-600">{activity.size}</td>
                  <td className="py-3 px-4 text-gray-600">{activity.slides}</td>
                  <td className="py-3 px-4 text-gray-600">{activity.duration}</td>
                  <td className="py-3 px-4 text-right text-gray-500">{activity.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="mt-4 pt-4 text-center border-t border-gray-100">
          <button className="text-[#c79b6d] hover:text-[#a78559] text-sm font-medium">
            Ver historial completo
          </button>
        </div>
      </div>
    </div>
  );
}