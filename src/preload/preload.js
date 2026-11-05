const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('razerAPI', {
  call: (action, params) => ipcRenderer.invoke('razer:call', action, params),
  onStatus: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('razer:status', handler);
    return () => ipcRenderer.removeListener('razer:status', handler);
  },
  onDeviceUpdate: (callback) => {
    const handler = (_event, data) => callback(data);
    ipcRenderer.on('razer:deviceUpdate', handler);
    return () => ipcRenderer.removeListener('razer:deviceUpdate', handler);
  },
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:isMaximized')
});
