# Quick Start Guide - Separated Structure

The project is now split into two separate folders: `ui/` and `api/`.

## Running the Application

### Step 1: Install Dependencies

**UI (Node.js):**
```bash
cd ui
npm install
```

**API (Python):**
```bash
cd api
pip install -r requirements.txt
```

### Step 2: Start Both Servers

**Terminal 1 - Start Python API:**
```bash
cd api
python api_server.py
```

**Terminal 2 - Start UI Server:**
```bash
cd ui
npm run dev
```

### Step 3: Access the Application

- **Frontend UI**: http://localhost:5000
- **API Health**: http://localhost:8000/api/health

## Project Structure

```
SsisXmlAnalyzer/
├── ui/              # Frontend (React + Node.js)
│   ├── client/      # React app
│   ├── server/      # Express server
│   └── shared/      # TypeScript schemas
│
└── api/             # Backend (Python)
    └── api_server.py
```

## Benefits of Separation

✅ **Independent Development**: Work on UI and API separately  
✅ **Clear Structure**: Easy to understand what belongs where  
✅ **Separate Deployment**: Deploy UI and API independently  
✅ **Better Organization**: No mixing of Node.js and Python files  

## Documentation

- **UI Documentation**: [ui/README.md](ui/README.md)
- **API Documentation**: [api/README.md](api/README.md)

