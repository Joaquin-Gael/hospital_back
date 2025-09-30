import React from 'react'
import { Plus, Calendar, Users, FileText, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const quickActions = [
  {
    id: 'new-patient',
    label: 'Nuevo Paciente',
    icon: Plus,
    variant: 'medical' as const,
    description: 'Registrar nuevo paciente'
  },
  {
    id: 'schedule-appointment',
    label: 'Agendar Cita',
    icon: Calendar,
    variant: 'success' as const,
    description: 'Programar nueva cita'
  },
  {
    id: 'view-staff',
    label: 'Ver Personal',
    icon: Users,
    variant: 'warning' as const,
    description: 'Gestionar personal médico'
  },
  {
    id: 'generate-report',
    label: 'Generar Reporte',
    icon: FileText,
    variant: 'default' as const,
    description: 'Crear informe médico'
  },
  {
    id: 'emergency',
    label: 'Emergencia',
    icon: Activity,
    variant: 'danger' as const,
    description: 'Protocolo de emergencia'
  }
]

export function QuickActions() {
  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="text-white">Acciones Rápidas</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-3">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Button
                key={action.id}
                variant={action.variant}
                className="h-auto p-4 flex flex-col items-start space-y-2 hover-lift"
                onClick={() => console.log(`Action: ${action.id}`)}
              >
                <div className="flex items-center space-x-2 w-full">
                  <Icon className="h-5 w-5" />
                  <span className="font-medium">{action.label}</span>
                </div>
                <span className="text-xs opacity-80 text-left">
                  {action.description}
                </span>
              </Button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}