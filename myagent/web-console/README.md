# MyAgent Web Console

A modern Vue.js-based web management interface for the MyAgent WebSocket management system.

## Features

- **Dashboard**: Real-time overview with system statistics and charts
- **Service Management**: Create, start, stop, restart, and delete agent services
- **Connection Monitoring**: Real-time connection tracking with auto-refresh
- **Routing Management**: Configure routing rules with visual interface
- **Real-time Updates**: Auto-refresh functionality for live monitoring

## Tech Stack

- **Frontend**: Vue 3 + TypeScript
- **UI Framework**: Element Plus
- **Charts**: ECharts (vue-echarts)
- **State Management**: Pinia
- **Build Tool**: Vite
- **HTTP Client**: Axios

## Getting Started

### Prerequisites

- Node.js 16+ and npm/yarn
- MyAgent API server running on port 8080

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The web console will be available at `http://localhost:3000`.

### API Integration

The web console connects to the MyAgent API server at `http://localhost:8080/api/v1`. 

Make sure the API server is running:

```bash
# From the main myagent directory
python -m myagent.manager.cli.api --port 8080
```

### Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint and fix code
npm run lint

# Type checking
npm run type-check
```

## Project Structure

```
src/
├── components/          # Reusable Vue components
├── views/              # Page components
│   ├── Dashboard.vue   # System overview dashboard
│   ├── Services.vue    # Service management interface
│   ├── Connections.vue # Connection monitoring
│   └── Routing.vue     # Routing rules management
├── stores/             # Pinia stores for state management
│   ├── services.ts     # Services state
│   ├── connections.ts  # Connections state
│   ├── routing.ts      # Routing rules state
│   └── stats.ts        # System statistics
├── types/              # TypeScript type definitions
│   └── api.ts          # API response types
├── utils/              # Utility functions
│   └── api.ts          # API client
├── router/             # Vue Router configuration
└── main.ts             # Application entry point
```

## Features Detail

### Dashboard
- System overview cards showing key metrics
- Real-time charts for service status and connection trends
- Service health status table
- Auto-refresh with configurable intervals

### Service Management
- Create new services with agent factory files
- Start, stop, restart, and delete services
- Real-time status updates
- Service configuration with tags and settings

### Connection Monitoring
- Real-time connection tracking
- Filter connections by status
- Connection duration and activity tracking
- Force disconnect functionality

### Routing Management
- Create and edit routing rules
- Priority-based rule ordering
- Multiple routing strategies (Round Robin, Least Connections, Hash-based)
- Conditional routing based on client attributes
- Enable/disable rules dynamically

## API Integration

The web console communicates with the MyAgent API server through RESTful endpoints:

- `GET /api/v1/services` - List all services
- `POST /api/v1/services` - Create new service
- `POST /api/v1/services/{id}/start` - Start service
- `POST /api/v1/services/{id}/stop` - Stop service
- `GET /api/v1/connections` - List active connections
- `GET /api/v1/routing/rules` - List routing rules
- `GET /api/v1/stats` - Get system statistics

## Configuration

### Proxy Configuration

The development server is configured to proxy API requests to the backend:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true
    }
  }
}
```

### Environment Variables

Create a `.env.local` file for local development settings:

```env
VITE_API_BASE_URL=http://localhost:8080
```

## Production Deployment

### Build

```bash
npm run build
```

### Serve Static Files

The built files in `dist/` can be served by any static file server or integrated with the Python backend.

### Integration with Python Backend

You can serve the web console directly from the Python API server by placing the built files in a static directory and configuring FastAPI to serve them.

## Development Guidelines

### Code Style
- Use TypeScript for type safety
- Follow Vue 3 Composition API patterns
- Use Pinia for state management
- Implement proper error handling
- Add loading states for async operations

### Component Structure
- Keep components focused and reusable
- Use props and events for component communication
- Implement proper TypeScript types
- Add appropriate comments for complex logic

### API Integration
- Use the centralized API client in `utils/api.ts`
- Handle errors gracefully with user feedback
- Implement loading states for better UX
- Use reactive stores for state management

## Troubleshooting

### API Connection Issues
- Ensure the MyAgent API server is running on port 8080
- Check browser console for CORS errors
- Verify API endpoints are accessible

### Build Issues
- Clear node_modules and reinstall dependencies
- Check TypeScript errors with `npm run type-check`
- Verify all imports are correct

### Development Server Issues
- Check port 3000 is available
- Clear browser cache
- Restart the development server