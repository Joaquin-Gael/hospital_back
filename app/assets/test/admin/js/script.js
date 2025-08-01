import { Chart } from "@/components/ui/chart"
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

// Inicialización de la aplicación
document.addEventListener("DOMContentLoaded", () => {
  initializeEventListeners()
  loadPromptHistory()
  initializeStaticComponents() // Initialize static components
  updateEmptyState()
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
  messageDiv.className = `chat-message p-3 rounded-lg ${sender === "user" ? "user-message ml-8" : "ai-message bg-gray-50"}`

  const time = new Date().toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  })

  messageDiv.innerHTML = `
        <div class="flex items-center mb-2">
            <i class="fas fa-${sender === "user" ? "user" : "robot"} mr-2"></i>
            <span class="font-semibold">${sender === "user" ? "Tú" : "Asistente IA"}</span>
            <span class="text-xs opacity-70 ml-auto">${time}</span>
        </div>
        <p>${message}</p>
    `

  messagesContainer.appendChild(messageDiv)
  messagesContainer.scrollTop = messagesContainer.scrollHeight
}

function generateAIResponse(message) {
  const lowerMessage = message.toLowerCase()

  // Respuestas inteligentes basadas en palabras clave
  if (lowerMessage.includes("gráfico") || lowerMessage.includes("chart")) {
    return {
      text: "¡Perfecto! He creado un gráfico para ti. Puedes arrastrarlo y redimensionarlo como gustes.",
      component: "chart",
    }
  } else if (lowerMessage.includes("tabla") || lowerMessage.includes("table")) {
    return {
      text: "He generado una tabla con datos de ejemplo. Puedes moverla por el dashboard.",
      component: "table",
    }
  } else if (lowerMessage.includes("card") || lowerMessage.includes("tarjeta")) {
    return {
      text: "Aquí tienes una card informativa. ¡Perfecta para mostrar métricas importantes!",
      component: "card",
    }
  } else if (lowerMessage.includes("información") || lowerMessage.includes("info")) {
    return {
      text: "He creado un panel de información para ti. Puedes personalizarlo como necesites.",
      component: "info",
    }
  } else if (lowerMessage.includes("ayuda") || lowerMessage.includes("help")) {
    return {
      text: "Puedo ayudarte a crear diferentes componentes: gráficos, tablas, cards informativas y paneles de información. Solo dime qué necesitas y lo crearé automáticamente. También puedes usar los botones del sidebar para agregar componentes rápidamente.",
      component: null,
    }
  } else {
    const responses = [
      "Interesante. ¿Te gustaría que cree algún componente específico para visualizar esa información?",
      "Entiendo. ¿Qué tipo de componente te ayudaría mejor: un gráfico, tabla, card o panel informativo?",
      "Perfecto. Puedo crear componentes visuales para ayudarte con eso. ¿Prefieres un gráfico o una tabla?",
      "Excelente idea. ¿Te gustaría que genere algún componente para el dashboard?",
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
    promptDiv.className = "prompt-item p-2 rounded text-sm border border-gray-200 hover:border-blue-300"
    promptDiv.innerHTML = `
            <p class="text-gray-700 mb-1">${item.text}</p>
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

// Funciones para crear componentes
function createComponent(type) {
  componentCounter++
  const component = document.createElement("div")
  component.className = "draggable-window"
  component.id = `component-${componentCounter}`
  component.style.left = `${50 + componentCounter * 20}px`
  component.style.top = `${50 + componentCounter * 20}px`
  component.style.width = "400px"
  component.style.height = "300px"
  component.style.zIndex = 100 + componentCounter

  let title, content

  switch (type) {
    case "chart":
      title = "Gráfico de Ventas"
      content = createChartContent()
      break
    case "table":
      title = "Tabla de Datos"
      content = createTableContent()
      break
    case "card":
      title = "Métricas"
      content = createCardContent()
      break
    case "info":
      title = "Panel de Información"
      content = createInfoContent()
      break
    default:
      title = "Componente"
      content = "<p>Contenido del componente</p>"
  }

  component.innerHTML = `
        <div class="window-header">
            <span class="font-semibold">${title}</span>
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
    setTimeout(() => initializeChart(component.id), 100)
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
            <table class="w-full text-sm">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="p-2 text-left">Producto</th>
                        <th class="p-2 text-left">Ventas</th>
                        <th class="p-2 text-left">Estado</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="border-t">
                        <td class="p-2">Producto A</td>
                        <td class="p-2">$1,234</td>
                        <td class="p-2"><span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">Activo</span></td>
                    </tr>
                    <tr class="border-t">
                        <td class="p-2">Producto B</td>
                        <td class="p-2">$2,567</td>
                        <td class="p-2"><span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">Pendiente</span></td>
                    </tr>
                    <tr class="border-t">
                        <td class="p-2">Producto C</td>
                        <td class="p-2">$3,890</td>
                        <td class="p-2"><span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">Activo</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
    `
}

function createCardContent() {
  return `
        <div class="grid grid-cols-2 gap-4 h-full">
            <div class="metric-card">
                <i class="fas fa-users text-2xl mb-2"></i>
                <h3 class="text-lg font-bold">1,234</h3>
                <p class="text-sm opacity-90">Usuarios</p>
            </div>
            <div class="metric-card">
                <i class="fas fa-dollar-sign text-2xl mb-2"></i>
                <h3 class="text-lg font-bold">$45,678</h3>
                <p class="text-sm opacity-90">Ingresos</p>
            </div>
            <div class="metric-card">
                <i class="fas fa-chart-line text-2xl mb-2"></i>
                <h3 class="text-lg font-bold">+23%</h3>
                <p class="text-sm opacity-90">Crecimiento</p>
            </div>
            <div class="metric-card">
                <i class="fas fa-star text-2xl mb-2"></i>
                <h3 class="text-lg font-bold">4.8</h3>
                <p class="text-sm opacity-90">Rating</p>
            </div>
        </div>
    `
}

function createInfoContent() {
  return `
        <div class="info-panel">
            <h3 class="text-lg font-bold text-gray-800 mb-3">
                <i class="fas fa-info-circle text-blue-500 mr-2"></i>
                Información Importante
            </h3>
            <p class="text-gray-600 mb-4">
                Este es un panel de información personalizable. Puedes agregar cualquier contenido relevante aquí.
            </p>
            <ul class="space-y-2 text-sm text-gray-600">
                <li class="flex items-center">
                    <i class="fas fa-check text-green-500 mr-2"></i>
                    Funcionalidad completada
                </li>
                <li class="flex items-center">
                    <i class="fas fa-clock text-yellow-500 mr-2"></i>
                    Tarea en progreso
                </li>
                <li class="flex items-center">
                    <i class="fas fa-exclamation text-red-500 mr-2"></i>
                    Requiere atención
                </li>
            </ul>
        </div>
    `
}

function initializeChart(componentId) {
  const canvas = document.getElementById(`chart-${componentId.split("-")[1]}`)
  if (!canvas) return

  new Chart(canvas, {
    type: "bar",
    data: {
      labels: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"],
      datasets: [
        {
          label: "Ventas",
          data: [12, 19, 3, 5, 2, 3],
          backgroundColor: [
            "rgba(255, 99, 132, 0.2)",
            "rgba(54, 162, 235, 0.2)",
            "rgba(255, 205, 86, 0.2)",
            "rgba(75, 192, 192, 0.2)",
            "rgba(153, 102, 255, 0.2)",
            "rgba(255, 159, 64, 0.2)",
          ],
          borderColor: [
            "rgba(255, 99, 132, 1)",
            "rgba(54, 162, 235, 1)",
            "rgba(255, 205, 86, 1)",
            "rgba(75, 192, 192, 1)",
            "rgba(153, 102, 255, 1)",
            "rgba(255, 159, 64, 1)",
          ],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
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

// Funcionalidad de arrastre
function makeDraggable(element) {
  const header = element.querySelector(".window-header")

  header.addEventListener("mousedown", startDrag)

  function startDrag(e) {
    if (e.target.classList.contains("window-control")) return

    draggedElement = element
    const rect = element.getBoundingClientRect()
    dragOffset.x = e.clientX - rect.left
    dragOffset.y = e.clientY - rect.top

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
      draggedElement = null
    }

    document.removeEventListener("mousemove", drag)
    document.removeEventListener("mouseup", stopDrag)
  }
}

function updateEmptyState() {
  const emptyState = document.getElementById("emptyState")
  const hasComponents = document.getElementById("componentsContainer").children.length > 0

  emptyState.style.display = hasComponents ? "none" : "flex" // Changed to flex for centering
}

// Initialize static components on load
function initializeStaticComponents() {
  const staticChart = document.getElementById("static-chart-1")
  const staticTable = document.getElementById("static-table-1")
  const staticCard = document.getElementById("static-card-1")

  if (staticChart) {
    makeDraggable(staticChart)
    initializeChart("static-chart-1") // Pass the full ID
    bringToFront(staticChart)
  }
  if (staticTable) {
    makeDraggable(staticTable)
    bringToFront(staticTable)
  }
  if (staticCard) {
    makeDraggable(staticCard)
    bringToFront(staticCard)
  }
}

// Responsive
window.addEventListener("resize", () => {
  if (window.innerWidth <= 768) {
    document.querySelectorAll(".draggable-window").forEach((window) => {
      if (!window.classList.contains("window-maximized")) {
        window.style.width = "calc(100vw - 32px)"
      }
    })
  }
})