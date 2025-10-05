import React from 'react';
import { Bell, Search, MessageSquare, User, Brain, Activity } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '../ui/dropdown';
import { Link } from 'react-router-dom';

export function Header() {
  return (
    <header className="header">
      {/* Search Section */}
      <div className="header-search">
        <div className="search-container">
          <Search className="search-icon" />
          <Input
            type="search"
            placeholder="Search patients, appointments, records..."
            className="search-input"
          />
        </div>
      </div>

      {/* Action Items */}
      <div className="header-actions">
        {/* AI Assistant Quick Access */}
        <Button variant="outline" size="sm" className="header-button header-button-ai" asChild>
          <Link to="/ai-chat">
            <Brain className="button-icon" />
            AI Assistant
          </Link>
        </Button>

        {/* Dashboard Quick Access */}
        <Button variant="outline" size="sm" className="header-button header-button-dashboard" asChild>
          <Link to="/">
            <Activity className="button-icon" />
            Dashboard
          </Link>
        </Button>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="notification-button">
              <Bell className="notification-icon" />
              <span className="notification-badge">
                <span className="notification-badge-pulse"></span>
                <span className="sr-only">3 notifications</span>
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="notification-dropdown">
            <DropdownMenuLabel className="notification-header">
              <span>Notifications</span>
              <span className="notification-count">3 new</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            
            <div className="notification-list">
              <DropdownMenuItem className="notification-item">
                <div className="notification-item-header">
                  <div className="notification-title">New appointment scheduled</div>
                  <div className="notification-time">5m</div>
                </div>
                <div className="notification-description">
                  John Doe - Today 3:00 PM
                </div>
              </DropdownMenuItem>
              
              <DropdownMenuItem className="notification-item">
                <div className="notification-item-header">
                  <div className="notification-title notification-title-alert">AI Alert: Critical vitals</div>
                  <div className="notification-time">15m</div>
                </div>
                <div className="notification-description">
                  Patient #1234 requires immediate attention
                </div>
              </DropdownMenuItem>
              
              <DropdownMenuItem className="notification-item">
                <div className="notification-item-header">
                  <div className="notification-title">Record updated</div>
                  <div className="notification-time">1h</div>
                </div>
                <div className="notification-description">
                  Medical record updated for Jane Smith
                </div>
              </DropdownMenuItem>
            </div>
            
            <DropdownMenuSeparator />
            <DropdownMenuItem className="notification-view-all">
              View all notifications
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="user-menu-button">
              <div className="user-avatar">
                <User className="user-icon" />
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="user-dropdown">
            <DropdownMenuLabel className="user-dropdown-header">
              <div className="user-info">
                <p className="user-name">Admin User</p>
                <p className="user-email">admin@hospital.com</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="user-dropdown-item">
              Profile Settings
            </DropdownMenuItem>
            <DropdownMenuItem className="user-dropdown-item">
              AI Configuration
            </DropdownMenuItem>
            <DropdownMenuItem className="user-dropdown-item">
              System Preferences
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="user-dropdown-item user-dropdown-item-signout">
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}