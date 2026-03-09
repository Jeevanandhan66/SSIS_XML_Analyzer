# SSIS XML Analyzer - UI

React + TypeScript frontend with Node.js/Express server for the SSIS Workflow Analyzer.

## Structure

```
ui/
├── client/          # React frontend application
│   ├── src/         # Source code
│   └── index.html   # Entry HTML
├── server/          # Node.js/Express server
│   ├── index.ts     # Main server file
│   ├── routes.ts    # API routes (proxies to Python API)
│   └── vite.ts      # Vite integration
└── shared/          # Shared TypeScript schemas
```

## Prerequisites

- **Node.js** (v18 or higher)
- **npm**

## Installation

```bash
cd ui
npm install
```

## Running the UI Server

### Development Mode

```bash
npm run dev
```

This starts the Node.js server on **port 5000** and serves the React UI.

**Note:** The Python API server must be running separately on port 8000.

### Access the Application

Open http://localhost:5000 in your browser.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run check` - Type check TypeScript

## Configuration

- **Port**: Set via `PORT` environment variable (default: 5000)
- **Python API URL**: Configured in `server/routes.ts` (default: http://localhost:8000)

## Dependencies

- React 18
- TypeScript
- Vite
- Express
- Tailwind CSS
- Radix UI components

## Development

The UI server proxies `/api/parse-dtsx` requests to the Python FastAPI server running on port 8000.

Make sure the Python API server is running before using the UI:
```bash
cd ../api
python api_server.py
```

