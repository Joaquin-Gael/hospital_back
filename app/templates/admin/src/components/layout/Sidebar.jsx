import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { 
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
    <aside className="fixed inset-y-0 left-0 z-20 flex h-screen w-64 flex-col overflow-y-auto border-r bg-card">
      {/* Header */}
      <div className="sticky top-0 flex h-16 shrink-0 items-center border-b bg-card px-4">
        <div className="flex w-full items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="overflow-hidden">
            <h2 className="truncate text-base font-semibold tracking-tight">Hospital Admin</h2>
            <p className="truncate text-xs text-muted-foreground">AI-Powered System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3">
        <div className="mb-2 px-2">
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Main Menu
          </h3>
        </div>
        <div className="space-y-1">
          {sidebarItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            
            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all",
                  "hover:bg-accent hover:text-accent-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground"
                )}
              >
                <Icon className={cn(
                  "h-5 w-5 shrink-0",
                  isActive ? "text-primary-foreground" : "text-muted-foreground"
                )} />
                <div className="min-w-0 flex-1">
                  <span className="block truncate">{item.title}</span>
                  <span className={cn(
                    "block truncate text-xs",
                    isActive ? "text-primary-foreground/70" : "text-muted-foreground/70"
                  )}>
                    {item.description}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* AI Status Indicator */}
      <div className="shrink-0 border-t p-3">
        <div className="rounded-md bg-secondary/50 p-2">
          <div className="flex items-center gap-2">
            <div className="relative flex h-2 w-2 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
            </div>
            <div className="min-w-0">
              <span className="block truncate text-sm font-medium">AI Assistant</span>
              <span className="block truncate text-xs text-muted-foreground">Connected to MCP</span>
            </div>
          </div>
        </div>
      </div>

      {/* User Info */}
      <div className="shrink-0 border-t p-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
            <User className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">Admin User</p>
            <p className="truncate text-xs text-muted-foreground">admin@hospital.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
}