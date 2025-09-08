import React, { useState } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { BackgroundPattern } from '../ui/background-pattern'

interface LayoutProps {
  children: React.ReactNode
  title?: string
}

export function Layout({ children, title }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeItem, setActiveItem] = useState('dashboard')

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 relative overflow-hidden">
      <BackgroundPattern />
      
      <Sidebar 
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activeItem={activeItem}
        onItemClick={setActiveItem}
      />
      
      <div className="lg:ml-64 min-h-screen flex flex-col">
        <Header 
          onMenuClick={() => setSidebarOpen(true)}
          title={title}
        />
        
        <main className="flex-1 p-6">
          <div className="animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}