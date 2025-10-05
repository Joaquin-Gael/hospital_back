import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Link } from 'react-router-dom';
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
      className="ai-chat-query-button"
      onClick={() => onSelect(query.query)}
    >
      <div className="ai-chat-query-content">
        <div className="ai-chat-query-title">{query.title}</div>
        <div className="ai-chat-query-text">{query.query}</div>
        <div className="ai-chat-query-category">{query.category}</div>
      </div>
    </Button>
  );
}

function ChatMessage({ message }) {
  const isUser = message.type === 'user';
  
  return (
    <div className={isUser ? "chat-message-container chat-message-container-user" : "chat-message-container chat-message-container-ai"}>
      <div className={isUser ? "chat-message chat-message-user" : "chat-message chat-message-ai"}>
        {!isUser && (
          <div className="chat-message-header">
            <div className="chat-message-avatar">
              <Brain className="chat-message-avatar-icon" />
            </div>
            <span className="chat-message-name">Medical AI Assistant</span>
          </div>
        )}
        <div className="chat-message-text">{message.message}</div>
        <div className="chat-message-time">{message.timestamp}</div>
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
    <div className="ai-chat-container">
      {/* Header */}
      <div className="ai-chat-header">
        <div className="ai-chat-title-container">
          <h1 className="ai-chat-title">
            <Brain className="ai-chat-title-icon" />
            AI Medical Assistant
          </h1>
          <p className="ai-chat-subtitle">
            Advanced medical AI for clinical decision support, diagnostics, and hospital operations.
          </p>
        </div>
        <div className="ai-chat-actions">
          <Button variant="outline" size="sm" as={Link} to="/" className="ai-chat-action-button">
            <Activity className="ai-chat-action-icon" />
            Dashboard
          </Button>
          <Button variant="outline" size="sm" className="ai-chat-action-button">
            <RotateCcw className="ai-chat-action-icon" />
            New Session
          </Button>
          <Button variant="outline" size="sm" className="ai-chat-action-button">
            <Download className="ai-chat-action-icon" />
            Export Chat
          </Button>
        </div>
      </div>

      <div className="ai-chat-layout">
        {/* Sidebar with Quick Queries */}
        <Card>
          <CardHeader>
            <CardTitle className="card-title-with-icon">
              <MessageSquare className="card-title-icon" />
              Quick Medical Queries
            </CardTitle>
            <CardDescription>
              Common clinical and administrative questions
            </CardDescription>
          </CardHeader>
          <CardContent className="ai-chat-queries-container">
            {predefinedQueries.map((query, index) => (
              <QueryCard key={index} query={query} onSelect={handlePredefinedQuery} />
            ))}
          </CardContent>
        </Card>

        {/* Main Chat Area */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="card-title-with-icon">
                <Brain className="card-title-icon" />
                Medical AI Conversation
              </CardTitle>
              <CardDescription>
                Ask medical questions, request patient analysis, or get clinical guidance
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Chat Messages */}
              <div className="ai-chat-conversation">
                {chatHistory.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
              </div>
              
              {/* Input Area */}
              <div className="ai-chat-input-container">
                <Input
                  className="ai-chat-input"
                  placeholder="Type your medical query or patient question..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <Button 
                  variant="outline" 
                  size="icon"
                  className="ai-chat-input-button"
                  onClick={toggleVoiceInput}
                >
                  {isListening ? (
                    <MicOff className="ai-chat-input-icon" />
                  ) : (
                    <Mic className="ai-chat-input-icon" />
                  )}
                </Button>
                <Button 
                  className="ai-chat-input-button"
                  onClick={handleSendMessage}
                  disabled={!message.trim() || isLoading}
                >
                  {isLoading ? (
                    <div className="ai-chat-input-icon pulse">...</div>
                  ) : (
                    <Send className="ai-chat-input-icon" />
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* AI Capabilities */}
          <div className="ai-capabilities-grid">
            {aiCapabilities.map((capability, index) => {
              const Icon = capability.icon;
              return (
                <div key={index} className="ai-capability-card">
                  <div className="ai-capability-icon-container">
                    <Icon className="ai-capability-icon" />
                  </div>
                  <div className="ai-capability-title">{capability.title}</div>
                  <div className="ai-capability-description">{capability.description}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}