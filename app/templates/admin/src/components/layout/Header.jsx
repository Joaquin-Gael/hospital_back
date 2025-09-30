import React from 'react';
import { Bell, Search, MessageSquare, User } from 'lucide-react';
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

export function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      {/* Search Section */}
      <div className="flex items-center space-x-4 flex-1 max-w-md">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search patients, appointments, records..."
            className="w-full pl-10 pr-4"
          />
        </div>
      </div>

      {/* Action Items */}
      <div className="flex items-center space-x-4">
        {/* AI Assistant Quick Access */}
        <Button variant="outline" size="sm" className="hidden sm:flex">
          <MessageSquare className="mr-2 h-4 w-4" />
          Ask AI
        </Button>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-destructive">
                <span className="sr-only">3 notifications</span>
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Notifications</span>
              <span className="text-xs text-muted-foreground">3 new</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            
            <div className="space-y-1">
              <DropdownMenuItem className="flex flex-col items-start space-y-1 p-3">
                <div className="flex w-full items-start justify-between">
                  <div className="font-medium">New appointment scheduled</div>
                  <div className="text-xs text-muted-foreground">5m</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  John Doe - Today 3:00 PM
                </div>
              </DropdownMenuItem>
              
              <DropdownMenuItem className="flex flex-col items-start space-y-1 p-3">
                <div className="flex w-full items-start justify-between">
                  <div className="font-medium text-destructive">AI Alert: Critical vitals</div>
                  <div className="text-xs text-muted-foreground">15m</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  Patient #1234 requires immediate attention
                </div>
              </DropdownMenuItem>
              
              <DropdownMenuItem className="flex flex-col items-start space-y-1 p-3">
                <div className="flex w-full items-start justify-between">
                  <div className="font-medium">Record updated</div>
                  <div className="text-xs text-muted-foreground">1h</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  Medical record updated for Jane Smith
                </div>
              </DropdownMenuItem>
            </div>
            
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-center">
              View all notifications
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
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
            <DropdownMenuItem>
              Profile Settings
            </DropdownMenuItem>
            <DropdownMenuItem>
              AI Configuration
            </DropdownMenuItem>
            <DropdownMenuItem>
              System Preferences
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}