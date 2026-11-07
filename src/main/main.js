const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const readline = require('readline');

app.setName('razerd');
if (process.platform === 'linux' && typeof app.setDesktopName === 'function') {
  app.setDesktopName('razerd.desktop');
}

const startMinimized = process.argv.some((arg) =>
  ['--minimized', '--autostart', '--hidden'].includes(arg)
);

let mainWindow = null;
let tray = null;
let isQuitting = false;
let pyProcess = null;
let pyReader = null;
let reqCounter = 0;
let lastMutationAt = 0;
let inFlightMutations = 0;
const pendingRequests = new Map();

const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    showMainWindow();
  });
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow(false);
    return;
  }
  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.focus();
}

function startPythonBridge() {
  const scriptPath = path.join(__dirname, '..', 'bridge', 'bridge.py');
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
  const isMutation = action !== 'list_devices' && action !== 'get_status';
  if (isMutation) {
    inFlightMutations++;
    lastMutationAt = Date.now();
  }
  return new Promise((resolve, reject) => {
    if (!pyProcess || pyProcess.killed) {
      if (isMutation) {
        inFlightMutations = Math.max(0, inFlightMutations - 1);
      }
      return reject(new Error('Bridge is not running'));
    }
    const id = ++reqCounter;
    pendingRequests.set(id, {
      resolve: (val) => {
        if (isMutation) {
          inFlightMutations = Math.max(0, inFlightMutations - 1);
          lastMutationAt = Date.now();
        }
        resolve(val);
      },
      reject: (err) => {
        if (isMutation) {
          inFlightMutations = Math.max(0, inFlightMutations - 1);
          lastMutationAt = Date.now();
        }
        reject(err);
      }
    });
    const payload = JSON.stringify({ id, action, params }) + '\n';
    pyProcess.stdin.write(payload);
  });
}

function createTray() {
  if (tray) return;
  const trayIconPath = path.join(__dirname, '..', '..', 'assets', 'razerd-tray.png');
  const fallbackIconPath = path.join(__dirname, '..', '..', 'assets', 'razerd.png');
  const targetIcon = fs.existsSync(trayIconPath) ? trayIconPath : fallbackIconPath;

  let img = nativeImage.createFromPath(targetIcon);
  if (!img.isEmpty()) {
    img = img.resize({ width: 22, height: 22 });
  }

  tray = new Tray(img);
  tray.setToolTip('RazerD — Razer Hardware & Chroma Control');

  tray.on('click', () => {
    if (mainWindow && !mainWindow.isDestroyed() && mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      showMainWindow();
    }
  });

  updateTrayMenu();
}

async function updateTrayMenu() {
  if (!tray) return;
  let autostartEnabled = true;
  try {
    const res = await callBridge('get_autostart');
    if (res && typeof res.enabled === 'boolean') {
      autostartEnabled = res.enabled;
    }
  } catch {}

  const contextMenu = Menu.buildFromTemplate([
    { label: 'RazerD Telemetry Suite', enabled: false },
    { type: 'separator' },
    {
      label: 'Open RazerD',
      click: () => showMainWindow()
    },
    {
      label: 'Hide to System Tray',
      click: () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.hide();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Start Minimized on Login',
      type: 'checkbox',
      checked: autostartEnabled,
      click: async (menuItem) => {
        try {
          await callBridge('set_autostart', {
            enabled: menuItem.checked,
            start_minimized: true
          });
          updateTrayMenu();
        } catch {}
      }
    },
    { type: 'separator' },
    {
      label: 'Quit RazerD',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
}

function createWindow(hidden = false) {
  const pngIconPath = path.join(__dirname, '..', '..', 'assets', 'razerd.png');
  const svgIconPath = path.join(__dirname, '..', '..', 'assets', 'razerd.svg');
  const iconPath = fs.existsSync(pngIconPath) ? pngIconPath : svgIconPath;
  Menu.setApplicationMenu(null);
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: '#000000',
    title: 'razerd',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    show: false,
    frame: true,
    autoHideMenuBar: true,
    titleBarStyle: 'default',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });
  mainWindow.removeMenu();
  mainWindow.setMenuBarVisibility(false);

  // Load renderer
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', '..', 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    if (!hidden) {
      mainWindow.show();
    }
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting && tray) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('razer:call', async (_event, action, params) => {
  const res = await callBridge(action, params);
  if (action === 'set_autostart') {
    updateTrayMenu();
  }
  return res;
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
    if (inFlightMutations > 0 || Date.now() - lastMutationAt < 4000) {
      return;
    }
    if (mainWindow && !mainWindow.isDestroyed()) {
      try {
        const devices = await callBridge('list_devices');
        if (inFlightMutations === 0 && Date.now() - lastMutationAt >= 4000 && mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('razer:deviceUpdate', devices);
        }
      } catch {}
    }
  }, 4500);
}

app.whenReady().then(() => {
  startPythonBridge();
  createTray();
  createWindow(startMinimized);
  startDevicePolling();

  app.on('activate', () => {
    showMainWindow();
  });
});

app.on('window-all-closed', () => {
  if (!isQuitting && tray) {
    return;
  }
  if (pollTimer) clearInterval(pollTimer);
  if (pyProcess) {
    pyProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  if (pollTimer) clearInterval(pollTimer);
  if (pyProcess) {
    pyProcess.kill();
  }
});
