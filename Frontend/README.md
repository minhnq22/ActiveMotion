# ActiveMotion Frontend

Security Explorer UI for visualizing and analyzing app screens and traffic flows.

## Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running on `http://localhost:8000` (see ../Backend/README.md)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file (optional, defaults to localhost:8000):
```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Development

Start the dev server:
```bash
npm run dev
```

The app will open at `http://localhost:5173` (or another port if 5173 is busy).

**Important**: Make sure the backend API is running before opening the frontend.

## Features

- **Visual Graph Editor**: View app screens as an interactive flow graph
- **Live Updates**: Real-time updates via WebSocket when new screens are captured
- **Dark Mode**: Toggle between light and dark themes
- **Screen Capture**: Record new screens via ADB (requires backend with ADB support)
- **Network Traffic**: View HTTP requests made during screen capture
- **Content Parser**: See parsed interactive elements from screens
- **Search**: Filter nodes by name, API endpoints, or content

## Build

```bash
npm run build
```

Output files will be in `dist/`

## Troubleshooting

**Blank screen?** 
- Check that the backend API is running at the configured URL
- Check browser console (F12) for errors
- The UI will show a helpful error message if the API is unreachable

