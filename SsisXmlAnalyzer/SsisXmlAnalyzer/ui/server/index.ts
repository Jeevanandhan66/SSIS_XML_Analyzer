import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";

const app = express();

// Note: Python API server should be started separately from the api/ folder
// Check if Python server is running
async function checkPythonServer() {
  try {
    const response = await fetch('http://localhost:8000/api/health');
    if (response.ok) {
      log("✓ Python FastAPI server is running on port 8000");
      return true;
    }
  } catch (error) {
    log("⚠ Python FastAPI server not detected on port 8000");
    log("  Start it separately: cd ../api && python api_server.py");
    return false;
  }
  return false;
}

// Check Python server on startup
checkPythonServer();

declare module 'http' {
  interface IncomingMessage {
    rawBody: unknown
  }
}
// Increase body size limit for large SSIS packages (50MB)
app.use(express.json({
  limit: '50mb',
  verify: (req, _res, buf) => {
    req.rawBody = buf;
  }
}));
app.use(express.urlencoded({ extended: false, limit: '50mb' }));

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "…";
      }

      log(logLine);
    }
  });

  next();
});

(async () => {
  const server = await registerRoutes(app);

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    res.status(status).json({ message });
    throw err;
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  // Default to development mode if NODE_ENV is not explicitly set to "production"
  const isDevelopment = process.env.NODE_ENV !== "production";
  log(`Environment: ${process.env.NODE_ENV || "development (default)"}, isDevelopment: ${isDevelopment}`);
  if (isDevelopment) {
    log("Setting up Vite dev server...");
    await setupVite(app, server);
  } else {
    log("Serving static files from dist/public...");
    serveStatic(app);
  }

  // ALWAYS serve the app on the port specified in the environment variable PORT
  // Other ports are firewalled. Default to 5000 if not specified.
  // this serves both the API and the client.
  // It is the only port that is not firewalled.
  const port = parseInt(process.env.PORT || '5000', 10);
  
  // reusePort is not supported on Windows, only use it on Linux/Mac
  const listenOptions: any = {
    port,
    host: "0.0.0.0",
  };
  
  // Only set reusePort on non-Windows platforms
  if (process.platform !== 'win32') {
    listenOptions.reusePort = true;
  }
  
  server.listen(listenOptions, () => {
    log(`serving on port ${port}`);
  });
})();
