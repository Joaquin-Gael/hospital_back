import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { 
  Users, 
  Calendar, 
  FileText, 
  Activity,
  MessageSquare,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  Brain,
  Zap
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Link } from 'react-router-dom';

const stats = [
  {
    title: 'Total Patients',
    value: '2,847',
    change: '+12%',
    changeType: 'positive',
    icon: Users,
    description: 'Active patients in system'
  },
  {
    title: "Today's Appointments",
    value: '24',
    change: '3 pending',
    changeType: 'neutral',
    icon: Calendar,
    description: 'Scheduled for today'
  },
  {
    title: 'Active Records',
    value: '1,429',
    change: '+8%',
    changeType: 'positive',
    icon: FileText,
    description: 'Updated this week'
  },
  {
    title: 'AI Interactions',
    value: '156',
    change: 'Last 24h',
    changeType: 'neutral',
    icon: MessageSquare,
    description: 'Assistant queries'
  }
];

const recentActivities = [
  {
    id: 1,
    type: 'appointment',
    title: 'New appointment scheduled',
    description: 'John Doe - Today 3:00 PM',
    time: '5 minutes ago',
    icon: Calendar,
    status: 'info'
  },
  {
    id: 2,
    type: 'ai_alert',
    title: 'AI detected abnormal vitals',
    description: 'Patient #1234 requires immediate attention',
    time: '15 minutes ago',
    icon: AlertTriangle,
    status: 'warning'
  },
  {
    id: 3,
    type: 'record_update',
    title: 'Medical record updated',
    description: 'Jane Smith - Prescription renewed',
    time: '1 hour ago',
    icon: FileText,
    status: 'success'
  },
  {
    id: 4,
    type: 'ai_query',
    title: 'Drug interaction check completed',
    description: 'AI assistant helped with medication review',
    time: '2 hours ago',
    icon: Brain,
    status: 'info'
  }
];

const aiInsights = [
  {
    title: 'High-Risk Patient Alert',
    description: 'AI identified 3 patients requiring immediate follow-up based on recent vitals and symptoms.',
    action: 'Review Patients',
    priority: 'high',
    icon: AlertTriangle
  },
  {
    title: 'Schedule Optimization',
    description: 'Rescheduling 2 appointments could improve workflow efficiency by 15%.',
    action: 'View Suggestions',
    priority: 'medium',
    icon: TrendingUp
  },
  {
    title: 'Medication Reminders',
    description: '12 patients are due for medication refills within the next 3 days.',
    action: 'Send Reminders',
    priority: 'low',
    icon: Clock
  }
];

const quickActions = [
  {
    title: 'Add Patient',
    description: 'Register new patient',
    icon: Users,
    href: '/patients/new'
  },
  {
    title: 'Schedule Appointment',
    description: 'Book new appointment',
    icon: Calendar,
    href: '/appointments/new'
  },
  {
    title: 'Create Record',
    description: 'New medical record',
    icon: FileText,
    href: '/records/new'
  },
  {
    title: 'Ask AI Assistant',
    description: 'Get medical insights',
    icon: MessageSquare,
    href: '/ai-chat'
  }
];

function StatCard({ stat }) {
  const Icon = stat.icon;
  
  return (
    <Card className="card-hover">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{stat.value}</div>
        <div className="flex items-center space-x-2 text-xs">
          <span className={cn(
            stat.changeType === 'positive' ? 'text-green-500' : 
            stat.changeType === 'negative' ? 'text-red-500' : 
            'text-muted-foreground'
          )}>
            {stat.change}
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="text-muted-foreground">{stat.description}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityItem({ activity }) {
  const Icon = activity.icon;
  
  return (
    <div className="flex items-start space-x-3 p-3 rounded-lg hover:bg-accent/50 transition-colors">
      <div className={cn(
        "rounded-full p-2",
        activity.status === 'warning' ? 'bg-yellow-500/10 text-yellow-600' :
        activity.status === 'success' ? 'bg-green-500/10 text-green-600' :
        activity.status === 'error' ? 'bg-red-500/10 text-red-600' :
        'bg-blue-500/10 text-blue-600'
      )}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 space-y-1">
        <p className="text-sm font-medium leading-none">{activity.title}</p>
        <p className="text-sm text-muted-foreground">{activity.description}</p>
        <div className="flex items-center text-xs text-muted-foreground">
          <Clock className="mr-1 h-3 w-3" />
          {activity.time}
        </div>
      </div>
    </div>
  );
}

function InsightCard({ insight }) {
  const Icon = insight.icon;
  
  return (
    <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-card/50">
      <div className="flex items-start space-x-3">
        <div className={cn(
          "rounded-lg p-2",
          insight.priority === 'high' ? 'bg-red-500/10 text-red-600' :
          insight.priority === 'medium' ? 'bg-yellow-500/10 text-yellow-600' :
          'bg-green-500/10 text-green-600'
        )}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="space-y-1">
          <p className="font-medium text-sm">{insight.title}</p>
          <p className="text-xs text-muted-foreground leading-relaxed">{insight.description}</p>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        <div className={cn(
          "w-2 h-2 rounded-full",
          insight.priority === 'high' ? 'bg-red-500' :
          insight.priority === 'medium' ? 'bg-yellow-500' :
          'bg-green-500'
        )} />
        <Button variant="outline" size="sm">
          {insight.action}
        </Button>
      </div>
    </div>
  );
}

export function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here's your hospital overview powered by AI intelligence.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button variant="outline">
            <Activity className="mr-2 h-4 w-4" />
            System Health
          </Button>
          <Button as={Link} to="/ai-chat">
            <Brain className="mr-2 h-4 w-4" />
            Open AI Assistant
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <StatCard key={index} stat={stat} />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* AI Insights - Takes 2 columns on large screens */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Brain className="h-5 w-5" />
              <span>AI Insights & Recommendations</span>
            </CardTitle>
            <CardDescription>
              Intelligent suggestions powered by medical AI to improve patient care and operations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {aiInsights.map((insight, index) => (
              <InsightCard key={index} insight={insight} />
            ))}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>Recent Activity</span>
            </CardTitle>
            <CardDescription>
              Latest system updates and alerts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {recentActivities.map((activity) => (
              <ActivityItem key={activity.id} activity={activity} />
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Zap className="h-5 w-5" />
            <span>Quick Actions</span>
          </CardTitle>
          <CardDescription>
            Frequently used tools and shortcuts for efficient workflow
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <Button
                  key={index}
                  variant="outline"
                  className="h-24 flex-col space-y-2 card-hover"
                >
                  <Icon className="h-6 w-6" />
                  <div className="text-center">
                    <div className="font-medium">{action.title}</div>
                    <div className="text-xs text-muted-foreground">{action.description}</div>
                  </div>
                </Button>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}