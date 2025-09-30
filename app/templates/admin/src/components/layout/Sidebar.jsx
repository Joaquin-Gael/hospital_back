import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { 
  Home, 
  User, 
  Activity,
  MessageSquare,
  Settings,
  LayoutDashboard,
  FileText,
  Calendar,
  Stethoscope
} from 'lucide-react';

const sidebarItems = [
  {
    title: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    description: 'Overview and metrics'
  },
  {
    title: 'AI Assistant',
    href: '/ai-chat',
    icon: MessageSquare,
    description: 'Medical AI support'
  },
  {
    title: 'Patients',
    href: '/patients',
    icon: User,
    description: 'Patient management'
  },
  {
    title: 'Appointments',
    href: '/appointments',
    icon: Calendar,
    description: 'Schedule management'
  },
  {
    title: 'Medical Records',
    href: '/records',
    icon: FileText,
    description: 'Patient records'
  },
  {
    title: 'Activity Log',
    href: '/activity',
    icon: Activity,
    description: 'System monitoring'
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'System configuration'
  },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      {/* Header */}
      <div className="flex h-16 items-center border-b px-6">
        <div className="flex items-center space-x-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="flex flex-col">
            <h2 className="text-lg font-semibold tracking-tight">Hospital Admin</h2>
            <p className="text-xs text-muted-foreground">AI-Powered System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-2 p-4">
        <div className="mb-4">
          <h3 className="px-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Main Menu
          </h3>
        </div>
        {sidebarItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.href;
          
          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "flex items-center space-x-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                "hover:bg-accent hover:text-accent-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground"
              )}
            >
              <Icon className={cn(
                "h-5 w-5 flex-shrink-0",
                isActive ? "text-primary-foreground" : "text-muted-foreground"
              )} />
              <div className="flex flex-col">
                <span>{item.title}</span>
                <span className={cn(
                  "text-xs",
                  isActive ? "text-primary-foreground/70" : "text-muted-foreground/70"
                )}>
                  {item.description}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* AI Status Indicator */}
      <div className="border-t p-4">
        <div className="rounded-lg bg-secondary/50 p-3">
          <div className="flex items-center space-x-2">
            <div className="status-dot status-online" />
            <div className="flex flex-col">
              <span className="text-sm font-medium">AI Assistant</span>
              <span className="text-xs text-muted-foreground">Connected to MCP</span>
            </div>
          </div>
        </div>
      </div>

      {/* User Info */}
      <div className="border-t p-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
            <User className="h-4 w-4" />
          </div>
          <div className="flex flex-1 flex-col">
            <p className="text-sm font-medium">Admin User</p>
            <p className="text-xs text-muted-foreground">admin@hospital.com</p>
          </div>
        </div>
      </div>
    </div>
  );
}