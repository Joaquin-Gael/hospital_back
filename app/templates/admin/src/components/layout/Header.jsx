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
import { cn } from '../../lib/utils';
import { Link } from 'react-router-dom';

export function Header() {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-card px-6 shadow-sm">
      {/* Search Section */}
      <div className="flex items-center space-x-4 flex-1 max-w-md">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search patients, appointments, records..."
            className="w-full pl-10 pr-4 h-9"
          />
        </div>
      </div>

      {/* Action Items */}
      <div className="flex items-center space-x-3">
        {/* AI Assistant Quick Access */}
        <Button variant="outline" size="sm" className="hidden sm:flex" asChild>
          <Link to="/ai-chat">
            <Brain className="mr-2 h-4 w-4" />
            AI Assistant
          </Link>
        </Button>

        {/* Dashboard Quick Access */}
        <Button variant="outline" size="sm" className="hidden md:flex" asChild>
          <Link to="/">
            <Activity className="mr-2 h-4 w-4" />
            Dashboard
          </Link>
        </Button>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-destructive flex items-center justify-center">
                <span className="animate-pulse absolute inset-0 rounded-full bg-destructive opacity-75"></span>
                <span className="sr-only">3 notifications</span>
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Notifications</span>
              <span className="text-xs font-medium bg-destructive text-destructive-foreground px-2 py-0.5 rounded">3 new</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            
            <div className="space-y-1 max-h-[300px] overflow-y-auto">
              <DropdownMenuItem className="flex flex-col items-start space-y-1 p-3 hover:bg-accent/50 cursor-pointer">
                <div className="flex w-full items-start justify-between">
                  <div className="font-medium">New appointment scheduled</div>
                  <div className="text-xs text-muted-foreground shrink-0 ml-2">5m</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  John Doe - Today 3:00 PM
                </div>
              </DropdownMenuItem>
              
              <DropdownMenuItem className="flex flex-col items-start space-y-1 p-3 hover:bg-accent/50 cursor-pointer">
                <div className="flex w-full items-start justify-between">
                  <div className="font-medium text-destructive">AI Alert: Critical vitals</div>
                  <div className="text-xs text-muted-foreground shrink-0 ml-2">15m</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  Patient #1234 requires immediate attention
                </div>
              </DropdownMenuItem>
              
              <DropdownMenuItem className="flex flex-col items-start space-y-1 p-3 hover:bg-accent/50 cursor-pointer">
                <div className="flex w-full items-start justify-between">
                  <div className="font-medium">Record updated</div>
                  <div className="text-xs text-muted-foreground shrink-0 ml-2">1h</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  Medical record updated for Jane Smith
                </div>
              </DropdownMenuItem>
            </div>
            
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-center text-primary hover:text-primary hover:underline cursor-pointer">
              View all notifications
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary border border-border">
                <User className="h-4 w-4" />
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">Admin User</p>
                <p className="text-xs text-muted-foreground">admin@hospital.com</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer">
              Profile Settings
            </DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer">
              AI Configuration
            </DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer">
              System Preferences
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive cursor-pointer">
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}