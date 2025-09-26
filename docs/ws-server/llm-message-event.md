# LLM_MESSAGE WebSocket Event Documentation

## Overview

The `LLM_MESSAGE` event is an optional WebSocket event that provides complete conversation history to the frontend client when an agent completes its execution. This event contains all messages exchanged during the conversation in a structured format, enabling clients to display, analyze, or store the complete interaction history.

## Event Configuration

### Environment Variable
The LLM_MESSAGE event is controlled by the `SEND_LLM_MESSAGE` environment variable:

```bash
# Enable LLM_MESSAGE events
export SEND_LLM_MESSAGE=true

# Other valid values: 1, yes, on
# Any other value or unset variable disables the feature
```

### When Event is Sent
- **Trigger**: When an agent completes execution (reaches FINISHED state)
- **Timing**: After final summary generation, before agent cleanup
- **Frequency**: Once per agent session completion

## Event Structure

### Basic Event Format
```json
{
  "event": "agent.llm_message",
  "session_id": "uuid-string",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "content": {
    "messages": [...],
    "total_messages": 15
  },
  "metadata": {
    "agent_name": "toolcall",
    "agent_state": "FINISHED",
    "final_response": "Task completed successfully..."
  }
}
```

### Content Structure
```json
{
  "messages": [
    // Array of message objects (see Message Schema below)
  ],
  "total_messages": 15  // Total count of messages
}
```

### Metadata Structure
```json
{
  "agent_name": "toolcall",        // Name of the agent that completed
  "agent_state": "FINISHED",       // Final state of the agent
  "final_response": "..."          // Agent's final response (optional)
}
```

## Message Schema

Each message in the `messages` array follows this structure:

### Basic Message Properties
```json
{
  "role": "user|assistant|tool|system",
  "content": "Message content text",
  "base64_image": "base64-encoded-image-data"  // Optional
}
```

### Role-Specific Message Types

#### 1. User Messages
```json
{
  "role": "user",
  "content": "What's the weather like today?",
  "base64_image": "optional-base64-image"
}
```

#### 2. Assistant Messages (Simple)
```json
{
  "role": "assistant",
  "content": "I'll help you check the weather."
}
```

#### 3. Assistant Messages (with Tool Calls)
```json
{
  "role": "assistant",
  "content": "I'll check the weather for you.",
  "tool_calls": [
    {
      "id": "call_123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"location\": \"New York\"}"
      }
    }
  ]
}
```

#### 4. Tool Messages
```json
{
  "role": "tool",
  "content": "Weather data: sunny, 22°C",
  "name": "get_weather",
  "tool_call_id": "call_123"
}
```

#### 5. System Messages
```json
{
  "role": "system",
  "content": "You are a helpful assistant."
}
```

## Frontend Integration Guide

### 1. Event Listener Setup
```javascript
// WebSocket connection setup
const ws = new WebSocket('ws://localhost:8889');

ws.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event === 'agent.llm_message') {
    handleLLMMessage(data);
  }
});

function handleLLMMessage(eventData) {
  const { content, metadata } = eventData;
  const { messages, total_messages } = content;
  
  console.log(`Received ${total_messages} messages from agent: ${metadata.agent_name}`);
  displayConversationHistory(messages);
}
```

### 2. Message Display Implementation

#### React Component Example
```jsx
import React from 'react';

const ConversationHistory = ({ messages }) => {
  return (
    <div className="conversation-history">
      <h3>Complete Conversation</h3>
      {messages.map((message, index) => (
        <MessageComponent key={index} message={message} />
      ))}
    </div>
  );
};

const MessageComponent = ({ message }) => {
  const { role, content, tool_calls, base64_image } = message;
  
  return (
    <div className={`message message-${role}`}>
      <div className="message-role">{role}</div>
      
      {/* Text content */}
      {content && (
        <div className="message-content">{content}</div>
      )}
      
      {/* Image content */}
      {base64_image && (
        <img 
          src={`data:image/jpeg;base64,${base64_image}`}
          alt="Message attachment"
          className="message-image"
        />
      )}
      
      {/* Tool calls */}
      {tool_calls && (
        <div className="tool-calls">
          {tool_calls.map((call, i) => (
            <div key={i} className="tool-call">
              <strong>Tool:</strong> {call.function.name}
              <pre>{call.function.arguments}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

#### Vue Component Example
```vue
<template>
  <div class="conversation-history">
    <h3>Complete Conversation</h3>
    <div 
      v-for="(message, index) in messages" 
      :key="index"
      :class="['message', `message-${message.role}`]"
    >
      <div class="message-role">{{ message.role }}</div>
      
      <!-- Text content -->
      <div v-if="message.content" class="message-content">
        {{ message.content }}
      </div>
      
      <!-- Image content -->
      <img 
        v-if="message.base64_image"
        :src="`data:image/jpeg;base64,${message.base64_image}`"
        alt="Message attachment"
        class="message-image"
      />
      
      <!-- Tool calls -->
      <div v-if="message.tool_calls" class="tool-calls">
        <div 
          v-for="(call, i) in message.tool_calls" 
          :key="i" 
          class="tool-call"
        >
          <strong>Tool:</strong> {{ call.function.name }}
          <pre>{{ call.function.arguments }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConversationHistory',
  props: {
    messages: {
      type: Array,
      required: true
    }
  }
};
</script>
```

### 3. Message Processing Utilities

#### Message Type Detection
```javascript
function getMessageType(message) {
  if (message.tool_calls) return 'assistant_tool_call';
  if (message.tool_call_id) return 'tool_response';
  return message.role;
}

function isToolSequence(messages, startIndex) {
  const message = messages[startIndex];
  if (!message.tool_calls) return false;
  
  // Check if subsequent messages are tool responses
  for (let i = startIndex + 1; i < messages.length; i++) {
    const nextMsg = messages[i];
    if (nextMsg.role === 'tool') continue;
    break;
  }
  return true;
}
```

#### Content Formatting
```javascript
function formatMessageContent(message) {
  switch (message.role) {
    case 'user':
      return {
        type: 'user',
        content: message.content,
        hasImage: !!message.base64_image
      };
      
    case 'assistant':
      return {
        type: message.tool_calls ? 'assistant_thinking' : 'assistant_response',
        content: message.content,
        toolCalls: message.tool_calls || []
      };
      
    case 'tool':
      return {
        type: 'tool_result',
        content: message.content,
        toolName: message.name,
        callId: message.tool_call_id
      };
      
    case 'system':
      return {
        type: 'system',
        content: message.content
      };
  }
}
```

### 4. Advanced Features

#### Conversation Export
```javascript
function exportConversation(eventData) {
  const { messages, total_messages } = eventData.content;
  const { agent_name, final_response } = eventData.metadata;
  
  const exportData = {
    timestamp: new Date().toISOString(),
    agent: agent_name,
    total_messages,
    final_response,
    conversation: messages
  };
  
  // Download as JSON
  const blob = new Blob([JSON.stringify(exportData, null, 2)], 
    { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = `conversation-${Date.now()}.json`;
  a.click();
  
  URL.revokeObjectURL(url);
}
```

#### Message Search and Filter
```javascript
function searchMessages(messages, query) {
  return messages.filter(message => 
    message.content && 
    message.content.toLowerCase().includes(query.toLowerCase())
  );
}

function filterByRole(messages, role) {
  return messages.filter(message => message.role === role);
}

function getToolInteractions(messages) {
  const interactions = [];
  let currentTool = null;
  
  for (const message of messages) {
    if (message.tool_calls) {
      currentTool = {
        thinking: message.content,
        calls: message.tool_calls,
        results: []
      };
    } else if (message.role === 'tool' && currentTool) {
      currentTool.results.push({
        name: message.name,
        content: message.content,
        call_id: message.tool_call_id
      });
      
      // If all tool calls have results, add to interactions
      if (currentTool.results.length === currentTool.calls.length) {
        interactions.push(currentTool);
        currentTool = null;
      }
    }
  }
  
  return interactions;
}
```

## CSS Styling Examples

```css
.conversation-history {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.message {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 8px;
  border-left: 4px solid;
}

.message-user {
  background-color: #e3f2fd;
  border-left-color: #2196f3;
}

.message-assistant {
  background-color: #f3e5f5;
  border-left-color: #9c27b0;
}

.message-tool {
  background-color: #e8f5e8;
  border-left-color: #4caf50;
  font-family: monospace;
}

.message-system {
  background-color: #fff3e0;
  border-left-color: #ff9800;
  font-style: italic;
}

.message-role {
  font-weight: bold;
  text-transform: uppercase;
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.message-content {
  line-height: 1.5;
  white-space: pre-wrap;
}

.message-image {
  max-width: 300px;
  max-height: 200px;
  border-radius: 4px;
  margin-top: 10px;
}

.tool-calls {
  margin-top: 10px;
  padding: 10px;
  background-color: rgba(0,0,0,0.05);
  border-radius: 4px;
}

.tool-call {
  margin-bottom: 5px;
}

.tool-call pre {
  background-color: #f5f5f5;
  padding: 5px;
  border-radius: 3px;
  font-size: 12px;
  margin-top: 5px;
}
```

## Error Handling

```javascript
function handleLLMMessage(eventData) {
  try {
    // Validate event structure
    if (!eventData.content || !eventData.content.messages) {
      throw new Error('Invalid LLM_MESSAGE event structure');
    }
    
    const { messages, total_messages } = eventData.content;
    
    // Validate message count
    if (messages.length !== total_messages) {
      console.warn(`Message count mismatch: received ${messages.length}, expected ${total_messages}`);
    }
    
    // Validate message structure
    const validMessages = messages.filter(validateMessage);
    
    if (validMessages.length !== messages.length) {
      console.warn(`Filtered ${messages.length - validMessages.length} invalid messages`);
    }
    
    displayConversationHistory(validMessages);
    
  } catch (error) {
    console.error('Error processing LLM_MESSAGE event:', error);
  }
}

function validateMessage(message) {
  return message && 
         typeof message === 'object' && 
         message.role && 
         ['user', 'assistant', 'tool', 'system'].includes(message.role);
}
```

## Testing

### Mock Event Data
```javascript
const mockLLMMessageEvent = {
  event: "agent.llm_message",
  session_id: "test-session-123",
  timestamp: "2024-01-15T10:30:45.123Z",
  content: {
    messages: [
      {
        role: "user",
        content: "What's the weather like in New York?"
      },
      {
        role: "assistant",
        content: "I'll check the weather for you.",
        tool_calls: [{
          id: "call_123",
          type: "function",
          function: {
            name: "get_weather",
            arguments: '{"location": "New York"}'
          }
        }]
      },
      {
        role: "tool",
        content: "Weather: Sunny, 22°C",
        name: "get_weather",
        tool_call_id: "call_123"
      },
      {
        role: "assistant",
        content: "The weather in New York is sunny with a temperature of 22°C."
      }
    ],
    total_messages: 4
  },
  metadata: {
    agent_name: "weather_agent",
    agent_state: "FINISHED",
    final_response: "The weather in New York is sunny with a temperature of 22°C."
  }
};

// Test the event handler
handleLLMMessage(mockLLMMessageEvent);
```

This documentation provides complete guidance for frontend developers to integrate and display LLM_MESSAGE events effectively.