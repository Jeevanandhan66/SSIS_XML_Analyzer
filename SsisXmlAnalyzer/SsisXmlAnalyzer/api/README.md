# SSIS XML Analyzer - API

Python FastAPI server for parsing SSIS DTSX XML files.

## Structure

```
api/
├── api_server.py     # FastAPI application
├── requirements.txt  # Python dependencies
└── pyproject.toml   # Python project configuration
```

## Prerequisites

- **Python** (v3.11 or higher)
- **pip** or **uv**

## Installation

### Option 1: Using pip

```bash
cd api
pip install -r requirements.txt
```

### Option 2: Using uv

```bash
cd api
uv sync
```

## Running the API Server

```bash
cd api
python api_server.py
```

The server will start on **port 8000**.

## API Endpoints

### POST /api/parse-dtsx

Upload and parse a DTSX XML file.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: `file` (DTSX XML file)

**Response:**
```json
{
  "success": true,
  "message": "Successfully parsed X activities",
  "data": {
    "metadata": { ... },
    "connectionManagers": [ ... ],
    "activities": [ ... ]
  }
}
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Access the API

- **API Base URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/api/health

## Dependencies

- FastAPI >= 0.121.2
- lxml >= 6.0.2
- python-multipart >= 0.0.20
- uvicorn >= 0.38.0

## Development

The API server runs independently and can be accessed directly or through the UI server proxy.

## CORS

CORS is enabled for all origins to allow the UI server to make requests.

