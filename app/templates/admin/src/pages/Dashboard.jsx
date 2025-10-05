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
    <Card className="stat-card card-hover">
      <CardHeader className="stat-card-header">
        <CardTitle className="stat-card-title">{stat.title}</CardTitle>
        <Icon className="stat-card-icon" />
      </CardHeader>
      <CardContent className="stat-card-content">
        <div className="stat-card-value">{stat.value}</div>
        <div className="stat-card-details">
          <span className={
            stat.changeType === 'positive' ? 'stat-change-positive' : 
            stat.changeType === 'negative' ? 'stat-change-negative' : 
            'stat-change-neutral'
          }>
            {stat.change}
          </span>
          <span className="stat-separator">•</span>
          <span className="stat-description">{stat.description}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityItem({ activity }) {
  const Icon = activity.icon;
  
  return (
    <div className="activity-item">
      <div className={
        "activity-icon-container " + 
        (activity.status === 'warning' ? 'activity-icon-warning' :
        activity.status === 'success' ? 'activity-icon-success' :
        activity.status === 'error' ? 'activity-icon-error' :
        'activity-icon-info')
      }>
        <Icon className="activity-icon" />
      </div>
      <div className="activity-content">
        <p className="activity-title">{activity.title}</p>
        <p className="activity-description">{activity.description}</p>
        <div className="activity-time">
          <Clock className="activity-time-icon" />
          {activity.time}
        </div>
      </div>
    </div>
  );
}

function InsightCard({ insight }) {
  const Icon = insight.icon;
  
  return (
    <div className="insight-card">
      <div className="insight-content">
        <div className={
          "insight-icon-container " + 
          (insight.priority === 'high' ? 'insight-icon-high' :
          insight.priority === 'medium' ? 'insight-icon-medium' :
          'insight-icon-low')
        }>
          <Icon className="insight-icon" />
        </div>
        <div className="insight-text">
          <p className="insight-title">{insight.title}</p>
          <p className="insight-description">{insight.description}</p>
        </div>
      </div>
      <div className="insight-actions">
        <div className={
          "priority-indicator " + 
          (insight.priority === 'high' ? 'priority-high' :
          insight.priority === 'medium' ? 'priority-medium' :
          'priority-low')
        } />
        <Button variant="outline" size="sm">
          {insight.action}
        </Button>
      </div>
    </div>
  );
}

export function Dashboard() {
  return (
    <div className="dashboard-container">
      {/* Header Section */}
      <div className="dashboard-header">
        <div className="dashboard-title-container">
          <h1 className="dashboard-title">Dashboard</h1>
          <p className="dashboard-subtitle">
            Welcome back! Here's your hospital overview powered by AI intelligence.
          </p>
        </div>
        <div className="dashboard-actions">
          <Button variant="outline" className="dashboard-button">
            <Activity className="dashboard-button-icon" />
            System Health
          </Button>
          <Button as={Link} to="/ai-chat" className="dashboard-button">
            <Brain className="dashboard-button-icon" />
            Open AI Assistant
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="dashboard-stats-grid">
        {stats.map((stat, index) => (
          <StatCard key={index} stat={stat} />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-content-grid">
        {/* AI Insights - Takes 2 columns on large screens */}
        <Card>
          <CardHeader>
            <CardTitle className="card-title-with-icon">
              <Brain className="card-title-icon" />
              <span>AI Insights & Recommendations</span>
            </CardTitle>
            <CardDescription>
              Intelligent suggestions powered by medical AI to improve patient care and operations
            </CardDescription>
          </CardHeader>
          <CardContent className="insights-container">
            {aiInsights.map((insight, index) => (
              <InsightCard key={index} insight={insight} />
            ))}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="card-title-with-icon">
              <Activity className="card-title-icon" />
              <span>Recent Activity</span>
            </CardTitle>
            <CardDescription>
              Latest system updates and alerts
            </CardDescription>
          </CardHeader>
          <CardContent className="activity-list">
            {recentActivities.map((activity) => (
              <ActivityItem key={activity.id} activity={activity} />
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="card-title-with-icon">
            <Zap className="card-title-icon" />
            <span>Quick Actions</span>
          </CardTitle>
          <CardDescription>
            Frequently used tools and shortcuts for efficient workflow
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="quick-actions-grid">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <Button
                  key={index}
                  variant="outline"
                  className="quick-action-button card-hover"
                >
                  <Icon className="quick-action-icon" />
                  <div className="quick-action-text">
                    <div className="quick-action-title">{action.title}</div>
                    <div className="quick-action-description">{action.description}</div>
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