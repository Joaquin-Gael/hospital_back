import {
  Chart,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartStyle
} from "@/components/ui/chart"
// Variables globales
let componentCounter = 0
let activeWindow = null
let draggedElement = null
const dragOffset = { x: 0, y: 0 }
let promptHistory = JSON.parse(localStorage.getItem("promptHistory")) || []

// Estado global de la aplicación
const AppState = {
  components: [],
  isChatOpen: false,
  isSidebarOpen: true,
}

// Datos empresariales para los componentes
const enterpriseData = {
  salesChart: {
    labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
    datasets: [{
      label: 'Ventas 2024',
      data: [65000, 78000, 82000, 91000, 87000, 95000, 102000, 98000, 105000, 112000, 108000, 125000],
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderColor: 'rgba(59, 130, 246, 1)',
      borderWidth: 3,
      fill: true,
      tension: 0.4
    }]
  },
  revenueChart: {
    labels: ['Q1', 'Q2', 'Q3', 'Q4'],
    datasets: [{
      label: 'Ingresos por Trimestre',
      data: [225000, 267000, 305000, 345000],
      backgroundColor: [
        'rgba(16, 185, 129, 0.8)',
        'rgba(59, 130, 246, 0.8)',
        'rgba(139, 92, 246, 0.8)',
        'rgba(245, 158, 11, 0.8)'
      ],
      borderWidth: 0
    }]
  },
  ordersTable: [
    { id: '#ORD-001', cliente: 'Empresa ABC S.A.', monto: '$45,250.00', estado: 'Completado', fecha: '2024-01-15' },
    { id: '#ORD-002', cliente: 'Tech Solutions Ltd.', monto: '$32,800.00', estado: 'Procesando', fecha: '2024-01-14' },
    { id: '#ORD-003', cliente: 'Global Industries', monto: '$67,500.00', estado: 'Enviado', fecha: '2024-01-13' },
    { id: '#ORD-004', cliente: 'StartUp Innovation', monto: '$28,900.00', estado: 'Pendiente', fecha: '2024-01-12' },
    { id: '#ORD-005', cliente: 'Corporate Partners', monto: '$89,200.00', estado: 'Completado', fecha: '2024-01-11' },
    { id: '#ORD-006', cliente: 'Digital Dynamics', monto: '$41,750.00', estado: 'Cancelado', fecha: '2024-01-10' }
  ],
  customersTable: [
    { id: 'CUST-001', nombre: 'María González', empresa: 'Tech Corp', valor: '$125,000', segmento: 'Enterprise' },
    { id: 'CUST-002', nombre: 'Carlos Rodríguez', empresa: 'StartUp Inc', valor: '$45,000', segmento: 'SMB' },
    { id: 'CUST-003', nombre: 'Ana Martínez', empresa: 'Global Ltd', valor: '$89,500', segmento: 'Mid-Market' },
    { id: 'CUST-004', nombre: 'Luis Fernández', empresa: 'Innovation Co', valor: '$67,200', segmento: 'Mid-Market' },
    { id: 'CUST-005', nombre: 'Sofia López', empresa: 'Enterprise Solutions', valor: '$156,800', segmento: 'Enterprise' }
  ],
  kpiMetrics: [
    { icon: 'fas fa-users', value: '2,847', label: 'Clientes Activos', color: 'bg-gradient-blue', change: '+12%' },
    { icon: 'fas fa-dollar-sign', value: '$1.2M', label: 'Ingresos Mensuales', color: 'bg-gradient-green', change: '+8.5%' },
    { icon: 'fas fa-chart-line', value: '94.2%', label: 'Satisfacción Cliente', color: 'bg-gradient-purple', change: '+2.1%' },
    { icon: 'fas fa-shopping-cart', value: '1,456', label: 'Pedidos Procesados', color: 'bg-gradient-orange', change: '+15.3%' }
  ]
}

// Inicialización de la aplicación
document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM loaded, initializing app...")

  initializeEventListeners()
  loadPromptHistory()

  // Crear componentes estáticos con un pequeño delay para asegurar que el DOM esté listo
  setTimeout(() => {
    createStaticComponents()
    updateEmptyState()
  }, 500)

  // Añadir animaciones de entrada a elementos existentes
  const sidebar = document.getElementById("sidebar")
  if (sidebar) {
    sidebar.classList.add("slide-up")
  }

  // Efectos de hover mejorados para botones
  document.querySelectorAll("button").forEach(button => {
    button.addEventListener("mouseenter", () => {
      button.style.transform = "translateY(-2px)"
    })

    button.addEventListener("mouseleave", () => {
      button.style.transform = "translateY(0)"
    })
  })
})

// Event Listeners
function initializeEventListeners() {
  // Sidebar toggle
  document.getElementById("openSidebar").addEventListener("click", () => {
    document.getElementById("sidebar").classList.remove("-translate-x-full")
    document.getElementById("sidebarOverlay").classList.remove("hidden")
  })

  document.getElementById("toggleSidebar").addEventListener("click", closeSidebar)
  document.getElementById("sidebarOverlay").addEventListener("click", closeSidebar)

  // Chat toggle
  document.getElementById("openChat").addEventListener("click", () => {
    document.getElementById("chatPanel").classList.remove("translate-x-full")
  })

  document.getElementById("toggleChat").addEventListener("click", () => {
    document.getElementById("chatPanel").classList.add("translate-x-full")
  })

  // Chat functionality
  document.getElementById("sendMessage").addEventListener("click", sendMessage)
  document.getElementById("chatInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      sendMessage()
    }
  })

  // Global click handler para z-index
  document.addEventListener("click", (e) => {
    const window = e.target.closest(".draggable-window")
    if (window) {
      bringToFront(window)
    }
  })
}

function closeSidebar() {
  document.getElementById("sidebar").classList.add("-translate-x-full")
  document.getElementById("sidebarOverlay").classList.add("hidden")
}

// Crear componentes estáticos al cargar
function createStaticComponents() {
  // Limpiar el contenedor primero
  const container = document.getElementById('componentsContainer')
  container.innerHTML = ''

  // Gráfico de ventas mensuales
  setTimeout(() => {
    createStaticChart('sales-chart', 'Ventas Mensuales 2024', 100, 80, 520, 360, 'line')
  }, 100)

  // Gráfico de ingresos por trimestre
  setTimeout(() => {
    createStaticChart('revenue-chart', 'Ingresos por Trimestre', 650, 80, 480, 360, 'doughnut')
  }, 200)

  // Tabla de pedidos
  setTimeout(() => {
    createStaticTable('orders-table', 'Últimos Pedidos', 100, 480, 600, 320, enterpriseData.ordersTable, ['ID Pedido', 'Cliente', 'Monto', 'Estado', 'Fecha'])
  }, 300)

  // Tabla de clientes
  setTimeout(() => {
    createStaticTable('customers-table', 'Clientes Principales', 750, 480, 550, 320, enterpriseData.customersTable, ['ID', 'Nombre', 'Empresa', 'Valor', 'Segmento'])
  }, 400)

  // Métricas KPI
  setTimeout(() => {
    createStaticMetrics('kpi-metrics', 'Métricas Principales', 1200, 80, 400, 280)
  }, 500)

  // Panel de información
  setTimeout(() => {
    createStaticInfo('info-panel', 'Resumen Ejecutivo', 1200, 400, 400, 400)
  }, 600)
}

function createStaticChart(id, title, x, y, width, height, type) {
  const chartWindow = document.createElement('div')
  chartWindow.className = 'draggable-window fade-in'
  chartWindow.id = id
  chartWindow.style.left = `${x}px`
  chartWindow.style.top = `${y}px`
  chartWindow.style.width = `${width}px`
  chartWindow.style.height = `${height}px`
  chartWindow.style.zIndex = 100 + componentCounter++

  chartWindow.innerHTML = `
    <div class="window-header">
      <span class="window-title">
        <i class="fas fa-chart-${type === 'line' ? 'line' : type === 'doughnut' ? 'pie' : 'bar'}"></i>
        ${title}
      </span>
      <div class="window-controls">
        <button class="window-control minimize" onclick="minimizeWindow('${id}')"></button>
        <button class="window-control maximize" onclick="maximizeWindow('${id}')"></button>
        <button class="window-control close" onclick="closeWindow('${id}')"></button>
      </div>
    </div>
    <div class="window-content">
      <div class="chart-container">
        <canvas id="chart-${id}"></canvas>
      </div>
    </div>
  `

  makeDraggable(chartWindow)
  document.getElementById('componentsContainer').appendChild(chartWindow)

  // Inicializar gráfico después de un breve delay
  setTimeout(() => {
    initializeChart(id, type)
  }, 100)
}

function createStaticTable(id, title, x, y, width, height, data, headers) {
  const tableWindow = document.createElement('div')
  tableWindow.className = 'draggable-window fade-in'
  tableWindow.id = id
  tableWindow.style.left = `${x}px`
  tableWindow.style.top = `${y}px`
  tableWindow.style.width = `${width}px`
  tableWindow.style.height = `${height}px`
  tableWindow.style.zIndex = 100 + componentCounter++

  const tableRows = data.map(row => {
    const values = Object.values(row)
    return `
      <tr>
        ${values.map((value, index) => {
          if (index === 3 && typeof value === 'string' && (value.includes('Completado') || value.includes('Procesando') || value.includes('Enviado') || value.includes('Pendiente') || value.includes('Cancelado') || value.includes('Enterprise') || value.includes('SMB') || value.includes('Mid-Market'))) {
            const statusClass = value.includes('Completado') || value.includes('Enterprise') ? 'bg-green-100 text-green-800' :
                               value.includes('Procesando') || value.includes('Mid-Market') ? 'bg-blue-100 text-blue-800' :
                               value.includes('Enviado') || value.includes('SMB') ? 'bg-yellow-100 text-yellow-800' :
                               value.includes('Pendiente') ? 'bg-orange-100 text-orange-800' :
                               'bg-red-100 text-red-800'
            return `<td><span class="status-badge ${statusClass}">${value}</span></td>`
          }
          return `<td>${value}</td>`
        }).join('')}
      </tr>
    `
  }).join('')

  tableWindow.innerHTML = `
    <div class="window-header">
      <span class="window-title">
        <i class="fas fa-table"></i>
        ${title}
      </span>
      <div class="window-controls">
        <button class="window-control minimize" onclick="minimizeWindow('${id}')"></button>
        <button class="window-control maximize" onclick="maximizeWindow('${id}')"></button>
        <button class="window-control close" onclick="closeWindow('${id}')"></button>
      </div>
    </div>
    <div class="window-content">
      <div class="table-container">
        <table class="enterprise-table">
          <thead>
            <tr>
              ${headers.map(header => `<th>${header}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${tableRows}
          </tbody>
        </table>
      </div>
    </div>
  `

  makeDraggable(tableWindow)
  document.getElementById('componentsContainer').appendChild(tableWindow)
}

function createStaticMetrics(id, title, x, y, width, height) {
  const metricsWindow = document.createElement('div')
  metricsWindow.className = 'draggable-window fade-in'
  metricsWindow.id = id
  metricsWindow.style.left = `${x}px`
  metricsWindow.style.top = `${y}px`
  metricsWindow.style.width = `${width}px`
  metricsWindow.style.height = `${height}px`
  metricsWindow.style.zIndex = 100 + componentCounter++

  const metricsCards = enterpriseData.kpiMetrics.map(metric => `
    <div class="metric-card ${metric.color}">
      <i class="${metric.icon} text-2xl mb-2"></i>
      <div class="metric-value">${metric.value}</div>
      <div class="metric-label">${metric.label}</div>
      <div class="text-xs mt-1 opacity-80">${metric.change} vs mes anterior</div>
    </div>
  `).join('')

  metricsWindow.innerHTML = `
    <div class="window-header">
      <span class="window-title">
        <i class="fas fa-tachometer-alt"></i>
        ${title}
      </span>
      <div class="window-controls">
        <button class="window-control minimize" onclick="minimizeWindow('${id}')"></button>
        <button class="window-control maximize" onclick="maximizeWindow('${id}')"></button>
        <button class="window-control close" onclick="closeWindow('${id}')"></button>
      </div>
    </div>
    <div class="window-content">
      <div class="grid grid-cols-2 gap-4 h-full">
        ${metricsCards}
      </div>
    </div>
  `

  makeDraggable(metricsWindow)
  document.getElementById('componentsContainer').appendChild(metricsWindow)
}

function createStaticInfo(id, title, x, y, width, height) {
  const infoWindow = document.createElement('div')
  infoWindow.className = 'draggable-window fade-in'
  infoWindow.id = id
  infoWindow.style.left = `${x}px`
  infoWindow.style.top = `${y}px`
  infoWindow.style.width = `${width}px`
  infoWindow.style.height = `${height}px`
  infoWindow.style.zIndex = 100 + componentCounter++

  infoWindow.innerHTML = `
    <div class="window-header">
      <span class="window-title">
        <i class="fas fa-info-circle"></i>
        ${title}
      </span>
      <div class="window-controls">
        <button class="window-control minimize" onclick="minimizeWindow('${id}')"></button>
        <button class="window-control maximize" onclick="maximizeWindow('${id}')"></button>
        <button class="window-control close" onclick="closeWindow('${id}')"></button>
      </div>
    </div>
    <div class="window-content">
      <div class="info-panel">
        <div class="mb-6">
          <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
            <i class="fas fa-chart-line text-blue-600 mr-2"></i>
            Rendimiento del Negocio
          </h3>
          <p class="text-gray-600 mb-4">
            El dashboard muestra un crecimiento sostenido en todas las métricas clave durante el último trimestre.
          </p>
        </div>

        <div class="space-y-4">
          <div class="flex items-center p-3 bg-green-50 rounded-lg">
            <i class="fas fa-arrow-up text-green-600 mr-3"></i>
            <div>
              <div class="font-semibold text-green-800">Ventas en Alza</div>
              <div class="text-sm text-green-600">Incremento del 15.3% respecto al mes anterior</div>
            </div>
          </div>

          <div class="flex items-center p-3 bg-blue-50 rounded-lg">
            <i class="fas fa-users text-blue-600 mr-3"></i>
            <div>
              <div class="font-semibold text-blue-800">Base de Clientes</div>
              <div class="text-sm text-blue-600">2,847 clientes activos (+12% crecimiento)</div>
            </div>
          </div>

          <div class="flex items-center p-3 bg-purple-50 rounded-lg">
            <i class="fas fa-star text-purple-600 mr-3"></i>
            <div>
              <div class="font-semibold text-purple-800">Satisfacción</div>
              <div class="text-sm text-purple-600">94.2% de satisfacción del cliente</div>
            </div>
          </div>

          <div class="flex items-center p-3 bg-orange-50 rounded-lg">
            <i class="fas fa-clock text-orange-600 mr-3"></i>
            <div>
              <div class="font-semibold text-orange-800">Próximas Metas</div>
              <div class="text-sm text-orange-600">Alcanzar 3,000 clientes para fin de trimestre</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `

  makeDraggable(infoWindow)
  document.getElementById('componentsContainer').appendChild(infoWindow)
}

function initializeChart(componentId, type) {
  const canvas = document.getElementById(`chart-${componentId}`)
  if (!canvas) {
    console.error(`Canvas not found for ${componentId}`)
    return
  }

  let chartData, chartOptions

  if (componentId === 'sales-chart') {
    chartData = enterpriseData.salesChart
    chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 20
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return '$' + (value / 1000) + 'K'
            }
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          }
        },
        x: {
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          }
        }
      }
    }
  } else if (componentId === 'revenue-chart') {
    chartData = enterpriseData.revenueChart
    chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            usePointStyle: true,
            padding: 15
          }
        }
      }
    }
  }

  try {
    new Chart(canvas, {
      type: type,
      data: chartData,
      options: chartOptions
    })
    console.log(`Chart ${componentId} initialized successfully`)
  } catch (error) {
    console.error(`Error initializing chart ${componentId}:`, error)
  }
}

// Funciones del chat
function sendMessage() {
  const input = document.getElementById("chatInput")
  const message = input.value.trim()

  if (!message) return

  // Agregar mensaje del usuario
  addChatMessage(message, "user")

  // Guardar en historial
  addToPromptHistory(message)

  // Limpiar input
  input.value = ""

  // Simular respuesta de IA
  setTimeout(() => {
    const response = generateAIResponse(message)
    addChatMessage(response.text, "ai")

    // Crear componente si la IA lo sugiere
    if (response.component) {
      createComponent(response.component)
    }
  }, 1000)
}

function addChatMessage(message, sender) {
  const messagesContainer = document.getElementById("chatMessages")
  const messageDiv = document.createElement("div")
  messageDiv.className = `chat-message p-4 rounded-xl ${sender === "user" ? "user-message ml-8" : "ai-message bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100"}`

  const time = new Date().toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  })

  messageDiv.innerHTML = `
    <div class="flex items-center mb-2">
      <i class="fas fa-${sender === "user" ? "user" : "robot"} mr-2 ${sender === "user" ? "text-white" : "text-blue-600"}"></i>
      <span class="font-semibold ${sender === "user" ? "text-white" : "text-blue-800"}">${sender === "user" ? "Tú" : "Asistente IA"}</span>
      <span class="text-xs opacity-70 ml-auto">${time}</span>
    </div>
    <p class="${sender === "user" ? "text-white" : "text-gray-700"}">${message}</p>
  `

  messagesContainer.appendChild(messageDiv)
  messagesContainer.scrollTop = messagesContainer.scrollHeight
}

function generateAIResponse(message) {
  const lowerMessage = message.toLowerCase()

  // Respuestas inteligentes basadas en palabras clave
  if (lowerMessage.includes("gráfico") || lowerMessage.includes("chart")) {
    return {
      text: "¡Excelente! He creado un gráfico empresarial para ti. Puedes arrastrarlo, redimensionarlo y personalizarlo según tus necesidades de análisis.",
      component: "chart",
    }
  } else if (lowerMessage.includes("tabla") || lowerMessage.includes("table")) {
    return {
      text: "He generado una tabla profesional con datos empresariales. Perfecta para análisis detallado de tu información de negocio.",
      component: "table",
    }
  } else if (lowerMessage.includes("métricas") || lowerMessage.includes("kpi")) {
    return {
      text: "Aquí tienes un panel de métricas KPI empresariales. Ideal para monitorear el rendimiento de tu negocio en tiempo real.",
      component: "card",
    }
  } else if (lowerMessage.includes("información") || lowerMessage.includes("resumen")) {
    return {
      text: "He creado un panel de información ejecutiva para ti. Perfecto para obtener insights rápidos sobre el estado de tu negocio.",
      component: "info",
    }
  } else if (lowerMessage.includes("ayuda") || lowerMessage.includes("help")) {
    return {
      text: "Soy tu asistente de dashboard empresarial. Puedo crear gráficos de ventas, tablas de datos, métricas KPI y paneles informativos. También puedo ayudarte con análisis de tendencias y reportes ejecutivos. ¿Qué tipo de visualización necesitas?",
      component: null,
    }
  } else {
    const responses = [
      "Interesante análisis. ¿Te gustaría que cree un gráfico para visualizar mejor esos datos empresariales?",
      "Perfecto para el dashboard. ¿Prefieres una tabla detallada o métricas KPI para esa información?",
      "Excelente insight de negocio. ¿Qué tipo de componente te ayudaría mejor a presentar estos datos?",
      "Gran punto estratégico. ¿Te gustaría que genere un panel informativo o gráfico de tendencias para eso?",
    ]
    return {
      text: responses[Math.floor(Math.random() * responses.length)],
      component: null,
    }
  }
}

// Funciones del historial de prompts
function addToPromptHistory(prompt) {
  const historyItem = {
    text: prompt,
    timestamp: new Date().toLocaleString("es-ES"),
  }

  promptHistory.unshift(historyItem)

  // Mantener solo los últimos 20 prompts
  if (promptHistory.length > 20) {
    promptHistory = promptHistory.slice(0, 20)
  }

  localStorage.setItem("promptHistory", JSON.stringify(promptHistory))
  loadPromptHistory()
}

function loadPromptHistory() {
  const historyContainer = document.getElementById("promptHistory")
  historyContainer.innerHTML = ""

  if (promptHistory.length === 0) {
    historyContainer.innerHTML = '<p class="text-gray-500 text-sm">No hay prompts recientes</p>'
    return
  }

  promptHistory.forEach((item, index) => {
    const promptDiv = document.createElement("div")
    promptDiv.className = "prompt-item p-3 rounded-xl text-sm border border-gray-200 hover:border-blue-300"
    promptDiv.innerHTML = `
      <p class="text-gray-700 mb-1 font-medium">${item.text}</p>
      <p class="text-xs text-gray-500">${item.timestamp}</p>
    `

    promptDiv.addEventListener("click", () => {
      document.getElementById("chatInput").value = item.text
      document.getElementById("chatPanel").classList.remove("translate-x-full")
    })

    historyContainer.appendChild(promptDiv)
  })
}

function clearHistory() {
  if (confirm("¿Estás seguro de que quieres limpiar el historial?")) {
    promptHistory = []
    localStorage.removeItem("promptHistory")
    loadPromptHistory()
  }
}

// Funciones para crear componentes dinámicos
function createComponent(type) {
  componentCounter++
  const component = document.createElement("div")
  component.className = "draggable-window fade-in"
  component.id = `component-${componentCounter}`
  component.style.left = `${50 + componentCounter * 30}px`
  component.style.top = `${50 + componentCounter * 30}px`
  component.style.width = "450px"
  component.style.height = "350px"
  component.style.zIndex = 100 + componentCounter

  let title, content, icon

  switch (type) {
    case "chart":
      title = "Análisis de Rendimiento"
      icon = "fas fa-chart-line"
      content = createChartContent()
      break
    case "table":
      title = "Datos Empresariales"
      icon = "fas fa-table"
      content = createTableContent()
      break
    case "card":
      title = "Métricas KPI"
      icon = "fas fa-tachometer-alt"
      content = createCardContent()
      break
    case "info":
      title = "Panel Informativo"
      icon = "fas fa-info-circle"
      content = createInfoContent()
      break
    default:
      title = "Componente Empresarial"
      icon = "fas fa-window-maximize"
      content = "<p>Contenido del componente</p>"
  }

  component.innerHTML = `
    <div class="window-header">
      <span class="window-title">
        <i class="${icon}"></i>
        ${title}
      </span>
      <div class="window-controls">
        <button class="window-control minimize" onclick="minimizeWindow('${component.id}')"></button>
        <button class="window-control maximize" onclick="maximizeWindow('${component.id}')"></button>
        <button class="window-control close" onclick="closeWindow('${component.id}')"></button>
      </div>
    </div>
    <div class="window-content">
      ${content}
    </div>
  `

  // Agregar funcionalidad de arrastre
  makeDraggable(component)

  document.getElementById("componentsContainer").appendChild(component)

  // Si es un gráfico, inicializarlo
  if (type === "chart") {
    setTimeout(() => initializeDynamicChart(component.id), 100)
  }

  updateEmptyState()
  bringToFront(component)
}

function createChartContent() {
  return `
    <div class="chart-container">
      <canvas id="chart-${componentCounter}"></canvas>
    </div>
  `
}

function createTableContent() {
  return `
    <div class="table-container">
      <table class="enterprise-table">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Ventas</th>
            <th>Crecimiento</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Producto Premium</td>
            <td>$45,230</td>
            <td>+12.5%</td>
            <td><span class="status-badge bg-green-100 text-green-800">Activo</span></td>
          </tr>
          <tr>
            <td>Servicio Empresarial</td>
            <td>$32,890</td>
            <td>+8.2%</td>
            <td><span class="status-badge bg-blue-100 text-blue-800">En Desarrollo</span></td>
          </tr>
          <tr>
            <td>Solución Corporativa</td>
            <td>$67,450</td>
            <td>+15.7%</td>
            <td><span class="status-badge bg-green-100 text-green-800">Activo</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  `
}

function createCardContent() {
  return `
    <div class="grid grid-cols-2 gap-4 h-full">
      <div class="metric-card bg-gradient-blue">
        <i class="fas fa-users text-2xl mb-2"></i>
        <div class="metric-value">3,247</div>
        <div class="metric-label">Usuarios Activos</div>
        <div class="text-xs mt-1 opacity-80">+18% vs mes anterior</div>
      </div>
      <div class="metric-card bg-gradient-green">
        <i class="fas fa-dollar-sign text-2xl mb-2"></i>
        <div class="metric-value">$89.2K</div>
        <div class="metric-label">Ingresos</div>
        <div class="text-xs mt-1 opacity-80">+12.5% vs mes anterior</div>
      </div>
      <div class="metric-card bg-gradient-purple">
        <i class="fas fa-chart-line text-2xl mb-2"></i>
        <div class="metric-value">96.8%</div>
        <div class="metric-label">Satisfacción</div>
        <div class="text-xs mt-1 opacity-80">+3.2% vs mes anterior</div>
      </div>
      <div class="metric-card bg-gradient-orange">
        <i class="fas fa-star text-2xl mb-2"></i>
        <div class="metric-value">4.9</div>
        <div class="metric-label">Rating Promedio</div>
        <div class="text-xs mt-1 opacity-80">+0.3 vs mes anterior</div>
      </div>
    </div>
  `
}

function createInfoContent() {
  return `
    <div class="info-panel">
      <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
        <i class="fas fa-chart-bar text-blue-600 mr-2"></i>
        Resumen Ejecutivo
      </h3>
      <p class="text-gray-600 mb-4">
        Panel informativo con insights clave del negocio y métricas de rendimiento actualizadas.
      </p>
      <div class="space-y-3">
        <div class="flex items-center p-3 bg-blue-50 rounded-lg">
          <i class="fas fa-trending-up text-blue-600 mr-3"></i>
          <div>
            <div class="font-semibold text-blue-800">Crecimiento Sostenido</div>
            <div class="text-sm text-blue-600">Incremento constante en todas las métricas</div>
          </div>
        </div>
        <div class="flex items-center p-3 bg-green-50 rounded-lg">
          <i class="fas fa-check-circle text-green-600 mr-3"></i>
          <div>
            <div class="font-semibold text-green-800">Objetivos Alcanzados</div>
            <div class="text-sm text-green-600">95% de las metas trimestrales completadas</div>
          </div>
        </div>
        <div class="flex items-center p-3 bg-orange-50 rounded-lg">
          <i class="fas fa-exclamation-triangle text-orange-600 mr-3"></i>
          <div>
            <div class="font-semibold text-orange-800">Áreas de Mejora</div>
            <div class="text-sm text-orange-600">Optimizar procesos de conversión</div>
          </div>
        </div>
      </div>
    </div>
  `
}

function initializeDynamicChart(componentId) {
  const canvas = document.getElementById(`chart-${componentId.split("-")[1]}`)
  if (!canvas) return

  new Chart(canvas, {
    type: "line",
    data: {
      labels: ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
      datasets: [
        {
          label: "Rendimiento",
          data: [65, 78, 82, 91, 87, 95],
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          borderColor: "rgba(59, 130, 246, 1)",
          borderWidth: 3,
          fill: true,
          tension: 0.4
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top'
        }
      },
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  })
}

// Funciones de control de ventanas
function minimizeWindow(windowId) {
  const window = document.getElementById(windowId)
  window.classList.toggle("window-minimized")
}

function maximizeWindow(windowId) {
  const window = document.getElementById(windowId)
  window.classList.toggle("window-maximized")
}

function closeWindow(windowId) {
  const window = document.getElementById(windowId)
  window.remove()
  updateEmptyState()
}

function bringToFront(window) {
  if (activeWindow) {
    activeWindow.classList.remove("active")
  }

  window.classList.add("active")
  window.style.zIndex = 1000 + componentCounter++
  activeWindow = window
}

// Funcionalidad de arrastre mejorada
function makeDraggable(element) {
  const header = element.querySelector(".window-header")

  header.addEventListener("mousedown", startDrag)

  function startDrag(e) {
    if (e.target.classList.contains("window-control")) return

    draggedElement = element
    const rect = element.getBoundingClientRect()
    dragOffset.x = e.clientX - rect.left
    dragOffset.y = e.clientY - rect.top

    // Añadir clase de arrastre para efectos visuales
    element.classList.add("dragging")

    document.addEventListener("mousemove", drag)
    document.addEventListener("mouseup", stopDrag)

    element.style.cursor = "grabbing"
    bringToFront(element)
  }

  function drag(e) {
    if (!draggedElement) return

    const x = e.clientX - dragOffset.x
    const y = e.clientY - dragOffset.y

    draggedElement.style.left = Math.max(0, x) + "px"
    draggedElement.style.top = Math.max(0, y) + "px"
  }

  function stopDrag() {
    if (draggedElement) {
      draggedElement.style.cursor = "default"
      draggedElement.classList.remove("dragging")
      draggedElement = null
    }

    document.removeEventListener("mousemove", drag)
    document.removeEventListener("mouseup", stopDrag)
  }
}

function updateEmptyState() {
  const emptyState = document.getElementById("emptyState")
  const container = document.getElementById("componentsContainer")
  const hasComponents = container && container.children.length > 0

  if (emptyState) {
    emptyState.style.display = hasComponents ? "none" : "flex"
  }

  console.log(`Components count: ${container ? container.children.length : 0}`)
}

// Responsive mejorado
window.addEventListener("resize", () => {
  if (window.innerWidth <= 768) {
    document.querySelectorAll(".draggable-window").forEach((window) => {
      if (!window.classList.contains("window-maximized")) {
        window.style.width = "calc(100vw - 32px)"
        window.style.left = "16px"
      }
    })
  }
})