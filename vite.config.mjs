import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import fs from 'fs';
import { spawn } from 'child_process';
import readline from 'readline';

function razerBridgeDevPlugin() {
  let pyProcess = null;
  let pyReader = null;
  let reqCounter = 0;
  const pendingRequests = new Map();
  const scriptPath = path.resolve(import.meta.dirname, 'src/bridge/bridge.py');

  function ensureBridge() {
    if (pyProcess && !pyProcess.killed) return;
    pyProcess = spawn('python3', ['-u', scriptPath], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    pyReader = readline.createInterface({
      input: pyProcess.stdout,
      terminal: false
    });

    pyReader.on('line', (line) => {
      line = line.trim();
      if (!line) return;
      try {
        const data = JSON.parse(line);
        if (data && data.id !== undefined && pendingRequests.has(data.id)) {
          const { resolve, reject } = pendingRequests.get(data.id);
          pendingRequests.delete(data.id);
          if (data.error) reject(new Error(data.error));
          else resolve(data.result);
        }
      } catch (e) {
        console.error('Bridge response parse error:', e, line);
      }
    });

    pyProcess.on('exit', () => {
      for (const [, req] of pendingRequests.entries()) {
        req.reject(new Error('Bridge terminated'));
      }
      pendingRequests.clear();
      pyProcess = null;
    });
  }

  function callBridge(action, params = {}) {
    ensureBridge();
    return new Promise((resolve, reject) => {
      const id = ++reqCounter;
      pendingRequests.set(id, { resolve, reject });
      pyProcess.stdin.write(JSON.stringify({ id, action, params }) + '\n');
    });
  }

  return {
    name: 'razer-bridge-middleware',
    configureServer(server) {
      // Auto-restart bridge process whenever bridge.py changes on disk
      fs.watchFile(scriptPath, { interval: 1000 }, () => {
        if (pyProcess && !pyProcess.killed) {
          pyProcess.kill();
          pyProcess = null;
        }
      });
      server.middlewares.use('/api/bridge', async (req, res) => {
        if (req.method === 'POST') {
          let body = '';
          req.on('data', chunk => { body += chunk; });
          req.on('end', async () => {
            try {
              const { action, params } = JSON.parse(body || '{}');
              const result = await callBridge(action, params);
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ result }));
            } catch (err) {
              res.statusCode = 500;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: err.message }));
            }
          });
        } else {
          res.statusCode = 404;
          res.end();
        }
      });
    }
  };
}

export default defineConfig({
  plugins: [vue(), razerBridgeDevPlugin()],
  root: path.resolve(import.meta.dirname, 'src/renderer'),
  base: './',
  build: {
    outDir: path.resolve(import.meta.dirname, 'dist'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
