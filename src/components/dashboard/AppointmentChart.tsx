import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

interface AppointmentData {
  department: string
  appointments: number
  capacity: number
  percentage: number
  variant: 'success' | 'warning' | 'danger' | 'default'
}

const mockData: AppointmentData[] = [
  {
    department: 'Cardiología',
    appointments: 45,
    capacity: 50,
    percentage: 90,
    variant: 'warning'
  },
  {
    department: 'Neurología',
    appointments: 32,
    capacity: 40,
    percentage: 80,
    variant: 'success'
  },
  {
    department: 'Pediatría',
    appointments: 38,
    capacity: 35,
    percentage: 108,
    variant: 'danger'
  },
  {
    department: 'Traumatología',
    appointments: 28,
    capacity: 45,
    percentage: 62,
    variant: 'default'
  },
  {
    department: 'Ginecología',
    appointments: 41,
    capacity: 50,
    percentage: 82,
    variant: 'success'
  }
]

export function AppointmentChart() {
  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="text-white">Ocupación por Departamento</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {mockData.map((item) => (
          <div key={item.department} className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white">{item.department}</span>
              <span className="text-sm text-white/60">
                {item.appointments}/{item.capacity}
              </span>
            </div>
            <Progress 
              value={Math.min(item.percentage, 100)} 
              variant={item.variant}
              className="h-2"
            />
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/60">
                {item.percentage}% ocupación
              </span>
              {item.percentage > 100 && (
                <span className="text-danger-400 font-medium">
                  Sobrecapacidad
                </span>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}