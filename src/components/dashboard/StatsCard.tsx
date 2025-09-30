import React from 'react'
import { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface StatsCardProps {
  title: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon: LucideIcon
  variant?: 'default' | 'medical' | 'success' | 'warning' | 'danger'
  className?: string
}

export function StatsCard({
  title,
  value,
  change,
  changeType = 'neutral',
  icon: Icon,
  variant = 'default',
  className
}: StatsCardProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'medical':
        return 'from-medical-500/20 to-medical-600/20 border-medical-500/30'
      case 'success':
        return 'from-success-500/20 to-success-600/20 border-success-500/30'
      case 'warning':
        return 'from-warning-500/20 to-warning-600/20 border-warning-500/30'
      case 'danger':
        return 'from-danger-500/20 to-danger-600/20 border-danger-500/30'
      default:
        return 'from-white/10 to-white/5 border-white/20'
    }
  }

  const getIconColor = () => {
    switch (variant) {
      case 'medical':
        return 'text-medical-400'
      case 'success':
        return 'text-success-400'
      case 'warning':
        return 'text-warning-400'
      case 'danger':
        return 'text-danger-400'
      default:
        return 'text-white'
    }
  }

  const getChangeColor = () => {
    switch (changeType) {
      case 'positive':
        return 'text-success-400'
      case 'negative':
        return 'text-danger-400'
      default:
        return 'text-white/60'
    }
  }

  return (
    <Card className={cn(
      'glass-card hover-lift bg-gradient-to-br',
      getVariantStyles(),
      className
    )}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-white/80">{title}</p>
            <p className="text-3xl font-bold text-white">{value}</p>
            {change && (
              <Badge 
                variant="glass" 
                className={cn("text-xs", getChangeColor())}
              >
                {change}
              </Badge>
            )}
          </div>
          <div className={cn(
            "p-3 rounded-xl bg-white/10 backdrop-blur-sm",
            getIconColor()
          )}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}