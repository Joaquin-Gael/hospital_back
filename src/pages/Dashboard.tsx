import React from 'react'
import { Users, Calendar, Activity, TrendingUp, Heart, UserCheck } from 'lucide-react'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { PatientTable } from '@/components/dashboard/PatientTable'
import { AppointmentChart } from '@/components/dashboard/AppointmentChart'
import { QuickActions } from '@/components/dashboard/QuickActions'

export function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">
              Bienvenido al Dashboard
            </h1>
            <p className="text-white/70">
              Gestiona tu hospital de manera eficiente y moderna
            </p>
          </div>
          <div className="hidden md:block">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-medical-400 to-medical-600 flex items-center justify-center animate-pulse-glow">
              <Heart className="h-8 w-8 text-white" />
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Pacientes"
          value="2,847"
          change="+12% vs mes anterior"
          changeType="positive"
          icon={Users}
          variant="medical"
        />
        <StatsCard
          title="Citas Hoy"
          value="156"
          change="+8% vs ayer"
          changeType="positive"
          icon={Calendar}
          variant="success"
        />
        <StatsCard
          title="Personal Activo"
          value="89"
          change="2 en descanso"
          changeType="neutral"
          icon={UserCheck}
          variant="warning"
        />
        <StatsCard
          title="Ocupación"
          value="94.2%"
          change="+2.1% vs semana anterior"
          changeType="positive"
          icon={TrendingUp}
          variant="danger"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Patient Table - Takes 2 columns */}
        <div className="lg:col-span-2">
          <PatientTable />
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          <AppointmentChart />
          <QuickActions />
        </div>
      </div>

      {/* Activity Feed */}
      <div className="glass-card p-6">
        <h3 className="text-xl font-semibold text-white mb-4 flex items-center">
          <Activity className="h-5 w-5 mr-2 text-medical-400" />
          Actividad Reciente
        </h3>
        <div className="space-y-4">
          {[
            { time: '10:30', action: 'Nueva cita programada', patient: 'María González', type: 'appointment' },
            { time: '10:15', action: 'Paciente dado de alta', patient: 'Carlos Rodríguez', type: 'discharge' },
            { time: '09:45', action: 'Resultado de laboratorio', patient: 'Ana Martínez', type: 'lab' },
            { time: '09:30', action: 'Ingreso de emergencia', patient: 'Luis Fernández', type: 'emergency' },
          ].map((activity, index) => (
            <div key={index} className="flex items-center space-x-4 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
              <div className="text-sm text-white/60 min-w-[50px]">
                {activity.time}
              </div>
              <div className="flex-1">
                <p className="text-sm text-white">{activity.action}</p>
                <p className="text-xs text-white/60">{activity.patient}</p>
              </div>
              <div className={`w-2 h-2 rounded-full ${
                activity.type === 'emergency' ? 'bg-danger-400' :
                activity.type === 'appointment' ? 'bg-success-400' :
                activity.type === 'discharge' ? 'bg-warning-400' :
                'bg-medical-400'
              }`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}