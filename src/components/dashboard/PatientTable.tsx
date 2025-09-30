import React from 'react'
import { MoreHorizontal, Eye, Edit, Trash2 } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Patient {
  id: string
  name: string
  email: string
  phone: string
  lastVisit: string
  status: 'active' | 'inactive' | 'critical'
  avatar?: string
}

const mockPatients: Patient[] = [
  {
    id: '1',
    name: 'María González',
    email: 'maria.gonzalez@email.com',
    phone: '+34 666 123 456',
    lastVisit: '2024-01-15',
    status: 'active',
  },
  {
    id: '2',
    name: 'Carlos Rodríguez',
    email: 'carlos.rodriguez@email.com',
    phone: '+34 666 789 012',
    lastVisit: '2024-01-10',
    status: 'critical',
  },
  {
    id: '3',
    name: 'Ana Martínez',
    email: 'ana.martinez@email.com',
    phone: '+34 666 345 678',
    lastVisit: '2024-01-08',
    status: 'inactive',
  },
  {
    id: '4',
    name: 'Luis Fernández',
    email: 'luis.fernandez@email.com',
    phone: '+34 666 901 234',
    lastVisit: '2024-01-12',
    status: 'active',
  },
]

export function PatientTable() {
  const getStatusBadge = (status: Patient['status']) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Activo</Badge>
      case 'critical':
        return <Badge variant="danger">Crítico</Badge>
      case 'inactive':
        return <Badge variant="outline">Inactivo</Badge>
      default:
        return <Badge variant="outline">Desconocido</Badge>
    }
  }

  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="text-white">Pacientes Recientes</CardTitle>
      </CardHeader>
      <CardContent>
        <Table glass>
          <TableHeader>
            <TableRow>
              <TableHead className="text-white/80">Paciente</TableHead>
              <TableHead className="text-white/80">Contacto</TableHead>
              <TableHead className="text-white/80">Última Visita</TableHead>
              <TableHead className="text-white/80">Estado</TableHead>
              <TableHead className="text-white/80 w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockPatients.map((patient) => (
              <TableRow key={patient.id} className="hover:bg-white/5">
                <TableCell>
                  <div className="flex items-center space-x-3">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={patient.avatar} />
                      <AvatarFallback className="bg-medical-500 text-white text-xs">
                        {patient.name.split(' ').map(n => n[0]).join('')}
                      </AvatarFallback>
                    </Avatar>
                    <span className="font-medium text-white">{patient.name}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="space-y-1">
                    <p className="text-sm text-white">{patient.email}</p>
                    <p className="text-xs text-white/60">{patient.phone}</p>
                  </div>
                </TableCell>
                <TableCell className="text-white/80">
                  {new Date(patient.lastVisit).toLocaleDateString('es-ES')}
                </TableCell>
                <TableCell>
                  {getStatusBadge(patient.status)}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="text-white hover:bg-white/10">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="glass-morphism-strong border-white/20" align="end">
                      <DropdownMenuItem className="text-white hover:bg-white/10">
                        <Eye className="mr-2 h-4 w-4" />
                        Ver Detalles
                      </DropdownMenuItem>
                      <DropdownMenuItem className="text-white hover:bg-white/10">
                        <Edit className="mr-2 h-4 w-4" />
                        Editar
                      </DropdownMenuItem>
                      <DropdownMenuItem className="text-white hover:bg-white/10">
                        <Trash2 className="mr-2 h-4 w-4" />
                        Eliminar
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}