import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { 
  MessageSquare,
  Send,
  User,
  RotateCcw,
  Mic,
  MicOff,
  Brain,
  Stethoscope,
  Activity,
  Download
} from 'lucide-react';
import { cn } from '../lib/utils';

const predefinedQueries = [
  {
    title: 'Patient Risk Assessment',
    query: 'Analyze current patients for potential health risks based on their medical history and recent vitals',
    category: 'diagnostics'
  },
  {
    title: 'Drug Interaction Check',
    query: 'Check for potential drug interactions for patient with multiple medications',
    category: 'medication'
  },
  {
    title: 'Appointment Optimization',
    query: 'Suggest optimal appointment scheduling for next week based on patient needs and availability',
    category: 'scheduling'
  },
  {
    title: 'Emergency Protocol',
    query: 'What is the standard protocol for cardiac emergency in the ICU?',
    category: 'emergency'
  },
  {
    title: 'Lab Results Analysis',
    query: 'Interpret abnormal lab results for patient showing symptoms of diabetes',
    category: 'diagnostics'
  },
  {
    title: 'Treatment Guidelines',
    query: 'Latest treatment guidelines for hypertension in elderly patients',
    category: 'treatment'
  }
];

const chatHistory = [
  {
    id: 1,
    type: 'user',
    message: 'What are the key symptoms of diabetes that I should monitor in patients?',
    timestamp: '2:30 PM'
  },
  {
    id: 2,
    type: 'ai',
    message: 'Key diabetes symptoms to monitor include:\n\n• **Polyuria** - Excessive urination (>3L/day)\n• **Polydipsia** - Increased thirst\n• **Unexplained weight loss** (especially in Type 1)\n• **Fatigue and weakness**\n• **Blurred vision**\n• **Slow-healing wounds**\n• **Frequent infections**\n\nFor patients over 45 or with risk factors (obesity, family history, hypertension), I recommend regular HbA1c screening. Would you like me to scan current patients with these symptoms?',
    timestamp: '2:31 PM'
  },
  {
    id: 3,
    type: 'user',
    message: 'Yes, please scan our current patient database for potential diabetes cases',
    timestamp: '2:32 PM'
  },
  {
    id: 4,
    type: 'ai',
    message: '**Patient Screening Results:**\n\n🔍 **Found 3 patients requiring attention:**\n\n• **Patient #1234 (John Doe)** - Recent 15lb weight loss, fatigue complaints\n• **Patient #5678 (Jane Smith)** - Recurrent UTIs, increased thirst reported\n• **Patient #9012 (Bob Johnson)** - Family history + borderline glucose (110 mg/dL)\n\n📋 **Recommendations:**\n- Schedule HbA1c tests for all three\n- Consider glucose tolerance test for Patient #9012\n- Follow up on symptom progression\n\nWould you like me to generate automated appointment requests?',
    timestamp: '2:33 PM'
  }
];

const aiCapabilities = [
  {
    title: 'Diagnostic Support',
    description: 'AI-powered symptom analysis, differential diagnosis suggestions, and medical literature references.',
    icon: Stethoscope
  },
  {
    title: 'Drug Interaction Analysis',
    description: 'Real-time medication interaction warnings and dosage recommendations based on patient history.',
    icon: Activity
  },
  {
    title: 'Clinical Decision Support',
    description: 'Evidence-based treatment recommendations and protocol guidance for various medical conditions.',
    icon: Brain
  }
];

function QueryCard({ query, onSelect }) {
  return (
    <Button
      variant="ghost"
      className="w-full h-auto justify-start p-4 text-left border border-border hover:bg-accent/50"
      onClick={() => onSelect(query.query)}
    >
      <div className="space-y-2">
        <div className="font-medium text-sm">{query.title}</div>
        <div className="text-xs text-muted-foreground line-clamp-2">{query.query}</div>
        <div className="text-xs text-primary capitalize">{query.category}</div>
      </div>
    </Button>
  );
}

function ChatMessage({ message }) {
  const isUser = message.type === 'user';
  
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={cn(
        "max-w-[80%] rounded-lg px-4 py-3 space-y-2",
        isUser 
          ? "bg-primary text-primary-foreground" 
          : "bg-secondary text-secondary-foreground"
      )}>
        {!isUser && (
          <div className="flex items-center space-x-2 mb-2">
            <div className="w-6 h-6 bg-accent rounded-full flex items-center justify-center">
              <Brain className="w-4 h-4" />
            </div>
            <span className="text-xs font-medium opacity-70">Medical AI Assistant</span>
          </div>
        )}
        <div className="text-sm whitespace-pre-line">{message.message}</div>
        <div className="text-xs opacity-70">{message.timestamp}</div>
      </div>
    </div>
  );
}

export function AIChat() {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const handleSendMessage = () => {
    if (!message.trim()) return;
    setIsLoading(true);
    // Simulate AI response
    setTimeout(() => {
      setIsLoading(false);
      setMessage('');
    }, 2000);
  };

  const handlePredefinedQuery = (query) => {
    setMessage(query);
  };

  const toggleVoiceInput = () => {
    setIsListening(!isListening);
    // Implement voice recognition here
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight flex items-center">
            <MessageSquare className="mr-3 h-8 w-8" />
            AI Medical Assistant
          </h1>
          <p className="text-muted-foreground">
            Advanced medical AI for clinical decision support, diagnostics, and hospital operations.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm">
            <RotateCcw className="mr-2 h-4 w-4" />
            New Session
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export Chat
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Sidebar with Quick Queries */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Quick Medical Queries</CardTitle>
            <CardDescription>
              Common clinical and administrative questions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {predefinedQueries.map((query, index) => (
              <QueryCard
                key={index}
                query={query}
                onSelect={handlePredefinedQuery}
              />
            ))}
          </CardContent>
        </Card>

        {/* Main Chat Interface */}
        <div className="lg:col-span-3 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Brain className="h-5 w-5" />
                  <span>Medical AI Assistant</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <div className="status-dot status-online" />
                  <span>Connected to Hospital MCP</span>
                </div>
              </CardTitle>
              <CardDescription>
                Real-time access to patient data, medical knowledge base, and clinical decision support
              </CardDescription>
            </CardHeader>
            
            {/* Chat Messages */}
            <CardContent className="space-y-6">
              <div className="h-96 overflow-y-auto space-y-4 p-4 border rounded-lg bg-background/50">
                {chatHistory.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-secondary text-secondary-foreground rounded-lg px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <div className="loading-dots">
                          <div></div>
                          <div></div>
                          <div></div>
                        </div>
                        <span className="text-sm">AI is analyzing...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="flex space-x-2">
                <div className="flex-1 relative">
                  <Input
                    placeholder="Ask about patients, medications, procedures, protocols, or clinical guidelines..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                    className="pr-12"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-1/2 -translate-y-1/2"
                    onClick={toggleVoiceInput}
                  >
                    {isListening ? (
                      <MicOff className="h-4 w-4 text-red-500" />
                    ) : (
                      <Mic className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <Button 
                  onClick={handleSendMessage} 
                  disabled={!message.trim() || isLoading}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>

              {/* AI Capabilities Info */}
              <div className="grid gap-3 md:grid-cols-3 text-xs text-muted-foreground border-t pt-4">
                <div className="flex items-center space-x-2">
                  <User className="h-4 w-4" />
                  <span>Patient Data Access</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Brain className="h-4 w-4" />
                  <span>Medical Knowledge Base</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Activity className="h-4 w-4" />
                  <span>Real-time Analytics</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* AI Capabilities */}
          <div className="grid gap-4 md:grid-cols-3">
            {aiCapabilities.map((capability, index) => {
              const Icon = capability.icon;
              return (
                <Card key={index} className="card-hover">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center space-x-2">
                      <Icon className="h-5 w-5" />
                      <span>{capability.title}</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {capability.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}