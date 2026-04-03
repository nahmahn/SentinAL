import { contextBridge, ipcRenderer } from 'electron';
contextBridge.exposeInMainWorld('electronAPI', {
    navigate: (url) => ipcRenderer.invoke('browser-navigate', url),
    goBack: () => ipcRenderer.invoke('browser-go-back'),
    goForward: () => ipcRenderer.invoke('browser-go-forward'),
    reload: () => ipcRenderer.invoke('browser-reload'),
    setWebviewVisible: (visible) => {
        console.log('[Preload] setWebviewVisible called with:', visible);
        // Send via both channels for maximum reliability
        ipcRenderer.send('set-webview-visible', visible);
        return ipcRenderer.invoke('toggle-webview', visible);
    },
    // Event listeners
    onLoading: (callback) => {
        ipcRenderer.on('browser-loading', (_, loading) => callback(loading));
    },
    onUrlChange: (callback) => {
        ipcRenderer.on('browser-url-changed', (_, url) => callback(url));
    },
    onTitleChange: (callback) => {
        ipcRenderer.on('browser-title-changed', (_, title) => callback(title));
    },
});
