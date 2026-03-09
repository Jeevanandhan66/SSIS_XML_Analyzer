import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Cross-platform Python command
const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

// Start Python FastAPI server
console.log('Starting Python FastAPI server on port 8000...');
const pythonProcess = spawn(pythonCmd, ['api_server.py'], {
  stdio: 'inherit',
  cwd: __dirname,
  shell: process.platform === 'win32'
});

pythonProcess.on('error', (err) => {
  console.error('Failed to start Python server:', err);
  process.exit(1);
});

// Wait a bit for Python server to start
setTimeout(() => {
  console.log('Starting Node.js development server...');
  const nodeProcess = spawn('npm', ['run', 'dev'], {
    stdio: 'inherit',
    cwd: __dirname,
    shell: true,
    env: { ...process.env, NODE_ENV: 'development' }
  });

  nodeProcess.on('error', (err) => {
    console.error('Failed to start Node server:', err);
    pythonProcess.kill();
    process.exit(1);
  });

  // Handle cleanup
  process.on('SIGINT', () => {
    console.log('\nShutting down servers...');
    pythonProcess.kill();
    nodeProcess.kill();
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    pythonProcess.kill();
    nodeProcess.kill();
    process.exit(0);
  });
}, 2000);
