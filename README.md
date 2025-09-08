# Hospital SDLG - Frontend

Un frontend moderno y elegante para el sistema de gestión hospitalaria, construido con React, TypeScript, Tailwind CSS y Radix UI.

## 🚀 Características

### Diseño y UX
- **Glass UI**: Efectos de vidrio translúcido con sombras suaves
- **Animaciones suaves**: Transiciones elegantes y microinteracciones
- **Responsive**: Adaptativo para escritorio, tablet y móvil
- **Tema hospitalario**: Paleta de colores profesional y seria
- **Iconos animados**: Efectos visuales en elementos interactivos

### Tecnologías
- **React 18** con TypeScript
- **Tailwind CSS** para estilos
- **Radix UI** para componentes accesibles
- **Framer Motion** para animaciones
- **Lucide React** para iconos
- **Vite** como bundler

### Componentes
- Cards con efecto glass
- Tablas interactivas
- Formularios estilizados
- Modales y diálogos
- Sistema de notificaciones (Toast)
- Botones con animaciones
- Badges y progress bars
- Avatares y dropdowns

## 🛠️ Instalación

```bash
# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev

# Construir para producción
npm run build

# Vista previa de producción
npm run preview
```

## 📁 Estructura del Proyecto

```
src/
├── components/
│   ├── ui/              # Componentes base de UI
│   ├── layout/          # Componentes de layout
│   └── dashboard/       # Componentes específicos del dashboard
├── pages/               # Páginas de la aplicación
├── hooks/               # Custom hooks
├── lib/                 # Utilidades y helpers
└── styles/              # Estilos globales
```

## 🎨 Sistema de Diseño

### Colores
- **Medical**: Azul médico profesional
- **Success**: Verde para estados positivos
- **Warning**: Naranja para advertencias
- **Danger**: Rojo para errores y estados críticos

### Componentes Glass
Todos los componentes principales utilizan el efecto "glass morphism":
- Fondo translúcido
- Blur backdrop
- Bordes sutiles
- Sombras suaves

### Animaciones
- Hover effects en botones y cards
- Transiciones suaves entre estados
- Animaciones de entrada (fade-in, slide-in)
- Efectos de pulsación y flotación

## 🔧 Personalización

### Tailwind Config
El archivo `tailwind.config.js` incluye:
- Colores personalizados del tema hospitalario
- Animaciones custom
- Utilidades para glass morphism
- Breakpoints responsive

### Componentes UI
Los componentes en `src/components/ui/` son totalmente personalizables y siguen los patrones de Radix UI con estilos de Tailwind.

## 📱 Responsive Design

- **Mobile First**: Diseño optimizado para móviles
- **Breakpoints**: sm, md, lg, xl, 2xl
- **Sidebar adaptativo**: Overlay en móvil, fijo en desktop
- **Grid responsive**: Layouts que se adaptan al tamaño de pantalla

## 🚀 Integración con Backend

El frontend está preparado para integrarse con el backend FastAPI:

```typescript
// Ejemplo de configuración de API
const API_BASE_URL = 'http://localhost:8000'

// Los componentes incluyen props para datos dinámicos
<StatsCard
  title="Total Pacientes"
  value={patientsData.total}
  change={patientsData.change}
  // ...
/>
```

## 🎯 Próximas Características

- [ ] Autenticación y autorización
- [ ] Formularios de pacientes
- [ ] Calendario de citas
- [ ] Gestión de personal médico
- [ ] Reportes y analytics
- [ ] Modo oscuro/claro
- [ ] Internacionalización (i18n)

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👥 Equipo

Desarrollado para Hospital SDLG con amor y tecnología moderna.