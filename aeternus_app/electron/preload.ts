import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
    navigate: (url: string) => ipcRenderer.invoke('browser-navigate', url),
    goBack: () => ipcRenderer.invoke('browser-go-back'),
    goForward: () => ipcRenderer.invoke('browser-go-forward'),
    reload: () => ipcRenderer.invoke('browser-reload'),
    setWebviewVisible: (visible: boolean) => {
        console.log('[Preload] setWebviewVisible called with:', visible);
        // Send via both channels for maximum reliability
        ipcRenderer.send('set-webview-visible', visible);
        return ipcRenderer.invoke('toggle-webview', visible);
    },
    // Event listeners
    onLoading: (callback: (loading: boolean) => void) => {
        ipcRenderer.on('browser-loading', (_, loading) => callback(loading));
    },
    onUrlChange: (callback: (url: string) => void) => {
        ipcRenderer.on('browser-url-changed', (_, url) => callback(url));
    },
    onTitleChange: (callback: (title: string) => void) => {
        ipcRenderer.on('browser-title-changed', (_, title) => callback(title));
    },
});
