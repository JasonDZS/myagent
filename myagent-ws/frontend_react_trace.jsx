"""
React Frontend Component for Real-time Trace Monitoring
Install dependencies: npm install react react-dom recharts lucide-react
"""

import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Brain, 
  Wrench, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Server,
  Play,
  Trash2,
  Wifi,
  WifiOff
} from 'lucide-react';

// Event type mappings for icons and colors
const EVENT_STYLES = {
  connection_established: { icon: Wifi, color: 'text-green-500', bg: 'bg-green-50' },
  trace_started: { icon: Play, color: 'text-blue-500', bg: 'bg-blue-50' },
  trace_completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50' },
  think_completed: { icon: Brain, color: 'text-purple-500', bg: 'bg-purple-50' },
  tool_completed: { icon: Wrench, color: 'text-orange-500', bg: 'bg-orange-50' },
  run_error: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50' },
  status_update: { icon: Activity, color: 'text-gray-500', bg: 'bg-gray-50' }
};

// TraceEvent Component
const TraceEvent = ({ event, timestamp }) => {
  const style = EVENT_STYLES[event.event_type] || EVENT_STYLES.status_update;
  const Icon = style.icon;
  
  return (
    <div className={`mb-4 p-4 rounded-lg border-l-4 ${style.bg} border-l-current ${style.color}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={18} className={style.color} />
          <span className="font-semibold">{getEventTitle(event)}</span>
        </div>
        <span className="text-sm text-gray-500">{timestamp}</span>
      </div>
      <div className="text-sm text-gray-700">
        {getEventContent(event)}
      </div>
      {event.data.duration_ms && (
        <div className="mt-2 text-xs text-gray-500">
          Duration: {event.data.duration_ms.toFixed(2)}ms
        </div>
      )}
    </div>
  );
};

// Helper functions
const getEventTitle = (event) => {
  const { event_type, data } = event;
  
  switch(event_type) {
    case 'connection_established':
      return 'Connection Established';
    case 'trace_started':
      return `🚀 Trace Started: ${data.agent_name}`;
    case 'trace_completed':
      return `✅ Trace Completed (${data.status})`;
    case 'think_completed':
      return '🤔 Thinking Completed';
    case 'tool_completed':
      return `🔧 Tool: ${data.name}`;
    case 'run_error':
      return `❌ Error in ${data.name}`;
    case 'status_update':
      return '📊 Status Update';
    default:
      return event_type.replace('_', ' ').toUpperCase();
  }
};

const getEventContent = (event) => {
  const { event_type, data } = event;
  
  switch(event_type) {
    case 'connection_established':
      return 'WebSocket connection established successfully';
      
    case 'trace_started':
      return (
        <div>
          <div><strong>Request:</strong> {data.request}</div>
          <div><strong>Max Steps:</strong> {data.max_steps}</div>
        </div>
      );
      
    case 'trace_completed':
      return (
        <div>
          <div><strong>Total Runs:</strong> {data.total_runs}</div>
          <div><strong>Duration:</strong> {data.duration_ms?.toFixed(2)}ms</div>
          {data.total_cost && <div><strong>Cost:</strong> ${data.total_cost.toFixed(4)}</div>}
        </div>
      );
      
    case 'think_completed':
      const thinkInput = data.inputs?.content || data.inputs?.last_user_message?.content || 'N/A';
      const thinkOutput = data.outputs?.content || data.outputs?.last_assistant_message?.content || 'N/A';
      return (
        <div>
          <div><strong>Input:</strong> {thinkInput.substring(0, 150)}...</div>
          <div><strong>Response:</strong> {thinkOutput.substring(0, 150)}...</div>
        </div>
      );
      
    case 'tool_completed':
      const toolInputs = Object.keys(data.inputs || {}).join(', ') || 'None';
      const toolOutput = data.outputs?.result || data.outputs?.output || 'No output';
      return (
        <div>
          <div><strong>Inputs:</strong> {toolInputs}</div>
          <div><strong>Result:</strong> {toolOutput.substring(0, 200)}...</div>
        </div>
      );
      
    case 'run_error':
      return (
        <div>
          <div><strong>Error:</strong> {data.error}</div>
          <div><strong>Type:</strong> {data.error_type || 'Unknown'}</div>
        </div>
      );
      
    case 'status_update':
      return (
        <div>
          <div><strong>Step:</strong> {data.current_step}/{data.max_steps}</div>
          <div><strong>State:</strong> {data.agent_state}</div>
          <div>{data.message}</div>
        </div>
      );
      
    default:
      return JSON.stringify(data, null, 2);
  }
};

// Connection Status Component
const ConnectionStatus = ({ connected, sessionId }) => (
  <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
    connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
  }`}>
    {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
    <span className="text-sm font-medium">
      {connected ? `Connected (${sessionId})` : 'Disconnected'}
    </span>
  </div>
);

// Progress Bar Component
const ProgressBar = ({ current, total, percentage }) => (
  <div className="w-full bg-gray-200 rounded-full h-2.5">
    <div 
      className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
      style={{ width: `${percentage || (current/total)*100}%` }}
    ></div>
    <div className="text-xs text-gray-500 mt-1">
      Step {current} of {total} ({((current/total)*100).toFixed(0)}%)
    </div>
  </div>
);

// Main Component
export const RealtimeTraceMonitor = () => {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [question, setQuestion] = useState('显示用户表的10条用户数据');
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [maxSteps, setMaxSteps] = useState(10);
  const [sessionId] = useState(`session_${Math.random().toString(36).substring(7)}`);
  
  const wsRef = useRef(null);
  const eventsEndRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [events]);

  // WebSocket connection
  useEffect(() => {
    const connect = () => {
      const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setConnected(true);
        addEvent({
          event_type: 'connection_established',
          data: { message: 'Connected to trace server' },
          timestamp: new Date()
        });
      };

      wsRef.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleTraceMessage(message);
      };

      wsRef.current.onclose = () => {
        setConnected(false);
        setIsRunning(false);
        addEvent({
          event_type: 'connection_closed',
          data: { message: 'Connection lost' },
          timestamp: new Date()
        });
        
        // Reconnect after 3 seconds
        setTimeout(connect, 3000);
      };

      wsRef.current.onerror = () => {
        addEvent({
          event_type: 'connection_error',
          data: { message: 'WebSocket error occurred' },
          timestamp: new Date()
        });
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId]);

  const handleTraceMessage = (message) => {
    addEvent({
      ...message,
      timestamp: new Date(message.timestamp)
    });

    // Update progress based on message type
    if (message.event_type === 'trace_started') {
      setIsRunning(true);
      setCurrentStep(0);
      setMaxSteps(message.data.max_steps || 10);
    } else if (message.event_type === 'trace_completed') {
      setIsRunning(false);
      setCurrentStep(message.data.total_runs || maxSteps);
    } else if (message.event_type.includes('completed') && isRunning) {
      setCurrentStep(prev => Math.min(prev + 1, maxSteps));
    }
  };

  const addEvent = (event) => {
    setEvents(prev => [...prev, { 
      ...event, 
      id: Date.now() + Math.random(),
      displayTime: event.timestamp.toLocaleTimeString()
    }]);
  };

  const startAgent = () => {
    if (!connected || !question.trim()) return;

    setIsRunning(true);
    setCurrentStep(0);
    
    const message = {
      action: 'start_agent',
      question: question.trim()
    };

    wsRef.current.send(JSON.stringify(message));
  };

  const clearEvents = () => {
    setEvents([]);
    setCurrentStep(0);
  };

  return (
    <div className="max-w-6xl mx-auto p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2 flex items-center gap-3">
          <Activity className="text-blue-500" />
          MyAgent Real-time Trace Monitor
        </h1>
        <p className="text-gray-600">
          Monitor AI agent execution in real-time with detailed trace information
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-center gap-4 mb-4">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Enter your question..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isRunning}
          />
          <button
            onClick={startAgent}
            disabled={!connected || isRunning || !question.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Play size={16} />
            {isRunning ? 'Running...' : 'Start Agent'}
          </button>
          <button
            onClick={clearEvents}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 flex items-center gap-2"
          >
            <Trash2 size={16} />
            Clear
          </button>
        </div>

        {/* Status and Progress */}
        <div className="flex items-center justify-between">
          <ConnectionStatus connected={connected} sessionId={sessionId.substring(8)} />
          {isRunning && (
            <div className="flex-1 max-w-xs ml-4">
              <ProgressBar current={currentStep} total={maxSteps} />
            </div>
          )}
        </div>
      </div>

      {/* Events Display */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
            <Server size={20} />
            Trace Events ({events.length})
          </h2>
        </div>
        
        <div className="p-6 max-h-96 overflow-y-auto">
          {events.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <Activity size={48} className="mx-auto mb-4 text-gray-300" />
              <p>No trace events yet. Start an agent to begin monitoring.</p>
            </div>
          ) : (
            <div>
              {events.map((event) => (
                <TraceEvent
                  key={event.id}
                  event={event}
                  timestamp={event.displayTime}
                />
              ))}
              <div ref={eventsEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 text-center text-gray-500 text-sm">
        <p>MyAgent Framework - Real-time Trace Monitoring System</p>
        <p>WebSocket connection to: ws://localhost:8000/ws/{sessionId}</p>
      </div>
    </div>
  );
};

export default RealtimeTraceMonitor;