import React from 'react';
import { Link, useLocation } from 'react-router-dom';
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
    <aside className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-logo-container">
          <div className="sidebar-logo">
            <Stethoscope />
          </div>
          <div className="sidebar-title-container">
            <h2 className="sidebar-title">Hospital Admin</h2>
            <p className="sidebar-subtitle">AI-Powered System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-title">
          Main Menu
        </div>
        <div className="sidebar-nav-items">
          {sidebarItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            
            return (
              <Link
                key={item.href}
                to={item.href}
                className={`sidebar-nav-link ${isActive ? 'active' : ''}`}
              >
                <Icon />
                <div className="sidebar-nav-content">
                  <span className="sidebar-nav-text">{item.title}</span>
                  <span className="sidebar-nav-description">
                    {item.description}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* AI Status Indicator */}
      <div className="sidebar-footer">
        <div className="sidebar-ai-status">
          <div className="sidebar-ai-status-container">
            <div className="sidebar-ai-indicator">
              <span className="sidebar-ai-indicator-ping"></span>
              <span className="sidebar-ai-indicator-dot"></span>
            </div>
            <div>
              <span className="truncate text-sm font-medium">AI Assistant</span>
              <span className="block truncate text-xs text-muted-foreground">Connected to MCP</span>
            </div>
          </div>
        </div>

        {/* User Info */}
        <div className="sidebar-user-info">
          <div className="sidebar-user-avatar">
            <User />
          </div>
          <div className="sidebar-user-details">
            <p className="sidebar-user-name">Admin User</p>
            <p className="sidebar-user-email">admin@hospital.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
}