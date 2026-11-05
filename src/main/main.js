const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const readline = require('readline');

let mainWindow = null;
let tray = null;
let pyProcess = null;
let pyReader = null;
let reqCounter = 0;
const pendingRequests = new Map();

function startPythonBridge() {
  const scriptPath = path.join(__dirname, '..', 'bridge', 'bridge.py');
  pyProcess = spawn('python3', [scriptPath], {
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
      const data = jsonParseSafe(line);
      if (data && data.id !== undefined && pendingRequests.has(data.id)) {
        const { resolve, reject } = pendingRequests.get(data.id);
        pendingRequests.delete(data.id);
        if (data.error) {
          reject(new Error(data.error));
        } else {
          resolve(data.result);
        }
      }
    } catch (e) {
      console.error('Error handling bridge message:', e, line);
    }
  });

  pyProcess.stderr.on('data', (data) => {
    console.error(`[Bridge stderr]: ${data.toString()}`);
  });

  pyProcess.on('exit', (code, signal) => {
    console.warn(`Python bridge process exited (code ${code}, signal ${signal})`);
    for (const [id, req] of pendingRequests.entries()) {
      req.reject(new Error('Python bridge process terminated'));
    }
    pendingRequests.clear();
  });
}

function jsonParseSafe(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

function callBridge(action, params = {}) {
  return new Promise((resolve, reject) => {
    if (!pyProcess || pyProcess.killed) {
      return reject(new Error('Bridge is not running'));
    }
    const id = ++reqCounter;
    pendingRequests.set(id, { resolve, reject });
    const payload = JSON.stringify({ id, action, params }) + '\n';
    pyProcess.stdin.write(payload);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: '#000000',
    title: 'razerd',
    show: false,
    frame: true,
    titleBarStyle: 'default',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  // Load renderer
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', '..', 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('razer:call', async (_event, action, params) => {
  return callBridge(action, params);
});

ipcMain.on('window:minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  }
});

ipcMain.on('window:close', () => {
  if (mainWindow) mainWindow.close();
});

ipcMain.handle('window:isMaximized', () => {
  return mainWindow ? mainWindow.isMaximized() : false;
});

// Periodic background polling for battery / hotplug
let pollTimer = null;
function startDevicePolling() {
  pollTimer = setInterval(async () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      try {
        const devices = await callBridge('list_devices');
        mainWindow.webContents.send('razer:deviceUpdate', devices);
      } catch {}
    }
  }, 3500);
}

app.whenReady().then(() => {
  startPythonBridge();
  createWindow();
  startDevicePolling();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (pollTimer) clearInterval(pollTimer);
  if (pyProcess) {
    pyProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (pyProcess) {
    pyProcess.kill();
  }
});
