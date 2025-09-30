# Hospital Admin Panel

Un panel de administración moderno y escalable para gestión hospitalaria con integración de asistente IA y servicios MCP.

## 🚀 Características

### ✨ Interfaz de Usuario
- **Diseño Moderno**: Interfaz minimalista con esquema de colores negro y blanco
- **Componentes Radix UI**: Componentes de alta calidad y accesibles
- **Responsive**: Adaptable a diferentes tamaños de pantalla
- **Bordes Redondeados**: Diseño moderno con esquinas redondeadas
- **Animaciones Fluidas**: Transiciones suaves para mejor experiencia de usuario

### 🤖 Asistente IA
- **Chat Interactivo**: Interfaz de chat para comunicación con el asistente IA
- **Consultas Predefinidas**: Preguntas comunes para diagnóstico y administración
- **Análisis de Riesgo**: Evaluación automática de pacientes de alto riesgo
- **Verificación de Medicamentos**: Detección de interacciones farmacológicas
- **Entrada por Voz**: Soporte para comandos de voz

### 🏥 Funcionalidades Hospitalarias
- **Dashboard**: Vista general con métricas clave y alertas IA
- **Gestión de Pacientes**: Sistema de administración de pacientes (próximamente)
- **Citas Médicas**: Programación y gestión de citas (próximamente)
- **Historial Médico**: Manejo de registros médicos (próximamente)
- **Registro de Actividad**: Monitoreo de actividades del sistema
- **Configuración**: Panel de configuración del sistema

## 🛠️ Tecnologías

- **React 18**: Framework de interfaz de usuario
- **Vite**: Herramienta de construcción rápida
- **React Router**: Navegación entre páginas
- **Radix UI**: Componentes de UI primitivos
- **CSS Variables**: Sistema de temas personalizable
- **JavaScript**: Lenguaje de programación principal

## 📦 Instalación

```bash
# Instalar dependencias
npm install

# Ejecutar en modo desarrollo
npm run dev

# Construir para producción
npm run build

# Vista previa de construcción
npm run preview
```

## 🎨 Sistema de Temas

El proyecto utiliza un sistema de variables CSS personalizado con esquema de colores negro y blanco:

```css
:root {
  --background: #000000;
  --foreground: #ffffff;
  --card: #111111;
  --primary: #ffffff;
  --secondary: #1a1a1a;
  --border: #262626;
  --radius: 0.75rem;
}
```

## 🧩 Estructura de Componentes

```
src/
├── components/
│   ├── ui/              # Componentes UI base (botones, cards, etc.)
│   └── layout/          # Componentes de layout (sidebar, header)
├── pages/               # Páginas de la aplicación
├── hooks/               # Hooks personalizados (futuro)
├── utils/               # Utilidades y helpers (futuro)
├── App.jsx              # Componente principal
└── main.jsx             # Punto de entrada
```

## 🔮 Características Futuras

### 🤖 Integración MCP
- Conexión directa con servicios MCP del hospital
- Sincronización en tiempo real de datos de pacientes
- Análisis predictivo con IA
- Alertas automáticas basadas en datos médicos

### 📊 Analytics Avanzados
- Dashboard de métricas en tiempo real
- Reportes automáticos
- Visualización de datos médicos
- Alertas de rendimiento

### 🔐 Seguridad
- Autenticación robusta
- Control de acceso basado en roles
- Auditoría de acciones
- Cifrado de datos sensibles

### 📱 Aplicación Móvil
- PWA (Progressive Web App)
- Notificaciones push
- Acceso offline limitado
- Sincronización automática

## 🚀 Desarrollo

### Agregar Nueva Página
1. Crear componente en `src/pages/`
2. Agregar ruta en `App.jsx`
3. Actualizar navegación en `Sidebar.jsx`

### Crear Componente UI
1. Crear archivo en `src/components/ui/`
2. Usar Radix UI como base
3. Aplicar estilos con clsx para consistencia
4. Exportar para uso en toda la aplicación

### Personalizar Tema
- Modificar variables CSS en `src/index.css`
- Actualizar colores en `--background`, `--foreground`, etc.
- Ajustar `--radius` para cambiar redondez de bordes

## 📝 Licencia

Este proyecto es parte del sistema hospitalario y está sujeto a las políticas de privacidad y seguridad de la institución.

## 🤝 Contribución

Para contribuir al proyecto:
1. Seguir las convenciones de código existentes
2. Mantener la coherencia en el diseño
3. Documentar nuevas características
4. Realizar pruebas exhaustivas

---

*Desarrollado para el futuro de la gestión hospitalaria con IA*