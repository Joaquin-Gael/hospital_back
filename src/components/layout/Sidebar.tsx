import React from 'react'
import { 
  Home, 
  Users, 
  Calendar, 
  FileText, 
  Settings, 
  Activity,
  Stethoscope,
  UserCheck,
  ClipboardList,
  BarChart3,
  X
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  activeItem?: string
  onItemClick?: (item: string) => void
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: Home },
  { id: 'patients', label: 'Pacientes', icon: Users },
  { id: 'appointments', label: 'Citas', icon: Calendar },
  { id: 'doctors', label: 'Médicos', icon: Stethoscope },
  { id: 'staff', label: 'Personal', icon: UserCheck },
  { id: 'records', label: 'Historiales', icon: FileText },
  { id: 'reports', label: 'Reportes', icon: BarChart3 },
  { id: 'inventory', label: 'Inventario', icon: ClipboardList },
  { id: 'monitoring', label: 'Monitoreo', icon: Activity },
  { id: 'settings', label: 'Configuración', icon: Settings },
]

export function Sidebar({ isOpen, onClose, activeItem = 'dashboard', onItemClick }: SidebarProps) {
  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside className={cn(
        "fixed left-0 top-0 h-full w-64 glass-card border-r border-white/10 transform transition-transform duration-300 ease-in-out z-50",
        isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-white/10">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-medical-400 to-medical-600 flex items-center justify-center animate-pulse-glow">
                <div className="w-4 h-4 bg-white rounded-sm" />
              </div>
              <span className="text-lg font-bold text-white">Hospital SDLG</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="lg:hidden text-white hover:bg-white/10"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon
              const isActive = activeItem === item.id
              
              return (
                <button
                  key={item.id}
                  onClick={() => onItemClick?.(item.id)}
                  className={cn(
                    "w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all duration-300 group",
                    isActive 
                      ? "bg-white/20 text-white shadow-lg" 
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <Icon className={cn(
                    "h-5 w-5 transition-all duration-300",
                    isActive 
                      ? "text-medical-400" 
                      : "group-hover:text-medical-400"
                  )} />
                  <span className="font-medium">{item.label}</span>
                  {isActive && (
                    <div className="ml-auto w-2 h-2 bg-medical-400 rounded-full animate-pulse" />
                  )}
                </button>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-white/10">
            <div className="glass rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-success-400 to-success-600 flex items-center justify-center">
                  <Activity className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Sistema Activo</p>
                  <p className="text-xs text-white/60">Todos los servicios operativos</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}