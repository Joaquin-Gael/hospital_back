import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { Dashboard } from './pages/Dashboard';
import { AIChat } from './pages/AIChat';
import './App.css';

// Placeholder components for other routes
const Patients = () => (
  <div className="space-y-6">
    <h1 className="text-3xl font-bold">Patients</h1>
    <p className="text-muted-foreground">Patient management system coming soon...</p>
  </div>
);

const Appointments = () => (
  <div className="space-y-6">
    <h1 className="text-3xl font-bold">Appointments</h1>
    <p className="text-muted-foreground">Appointment scheduling system coming soon...</p>
  </div>
);

const Records = () => (
  <div className="space-y-6">
    <h1 className="text-3xl font-bold">Medical Records</h1>
    <p className="text-muted-foreground">Medical records management coming soon...</p>
  </div>
);

const Activity = () => (
  <div className="space-y-6">
    <h1 className="text-3xl font-bold">Activity Log</h1>
    <p className="text-muted-foreground">System activity monitoring coming soon...</p>
  </div>
);

const Settings = () => (
  <div className="space-y-6">
    <h1 className="text-3xl font-bold">Settings</h1>
    <p className="text-muted-foreground">System configuration coming soon...</p>
  </div>
);

function App() {
  return (
    <Router>
      <div className="h-[100vh] flex bg-background text-foreground">
        {/* Sidebar */}
        <Sidebar />
        
        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <Header />
          
          {/* Page Content */}
          <main className="flex-1 overflow-y-auto p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/ai-chat" element={<AIChat />} />
              <Route path="/patients" element={<Patients />} />
              <Route path="/appointments" element={<Appointments />} />
              <Route path="/records" element={<Records />} />
              <Route path="/activity" element={<Activity />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
