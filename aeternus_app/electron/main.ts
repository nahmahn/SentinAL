import { app, BrowserWindow, BrowserView, ipcMain, globalShortcut } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let mainWindow: BrowserWindow | null = null;
let webView: BrowserView | null = null;
let webViewVisible = true;

const SIDEBAR_WIDTH = 380;
const NAV_HEIGHT = 80;

console.log('[Main] Aeternus Electron Core v2.0 Starting...');

function showWebView() {
  if (!mainWindow || !webView) return;
  webViewVisible = true;
  mainWindow.addBrowserView(webView);
  const contentBounds = mainWindow.getContentBounds();
  webView.setBounds({
    x: 0,
    y: NAV_HEIGHT,
    width: contentBounds.width - SIDEBAR_WIDTH,
    height: contentBounds.height - NAV_HEIGHT
  });
  console.log('[Main] WebView SHOWN');
}

function hideWebView() {
  if (!mainWindow || !webView) return;
  webViewVisible = false;
  try { mainWindow.removeBrowserView(webView); } catch(e) {}
  console.log('[Main] WebView HIDDEN');
}

// IPC handler using ipcMain.on + ipcRenderer.send (most reliable pattern)
ipcMain.on('set-webview-visible', (event, visible: boolean) => {
  console.log('[Main] IPC received set-webview-visible:', visible);
  if (visible) {
    showWebView();
  } else {
    hideWebView();
  }
});

// Also register as handle for invoke pattern (belt and suspenders)
ipcMain.handle('toggle-webview', async (event, visible: boolean) => {
  console.log('[Main] IPC handle toggle-webview:', visible);
  if (visible) {
    showWebView();
  } else {
    hideWebView();
  }
  return true;
});

ipcMain.handle('browser-navigate', (event, url) => {
  if (webView) webView.webContents.loadURL(url);
});

ipcMain.handle('browser-go-back', () => {
  if (webView?.webContents.canGoBack()) webView.webContents.goBack();
});

ipcMain.handle('browser-go-forward', () => {
  if (webView?.webContents.canGoForward()) webView.webContents.goForward();
});

ipcMain.handle('browser-reload', () => {
  if (webView) webView.webContents.reload();
});

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#f7f9fc',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  const isDev = !app.isPackaged;
  const devUrl = 'http://localhost:5173';

  if (isDev) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Create the BrowserView for web content
  webView = new BrowserView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    }
  });

  // Initial attachment
  mainWindow.addBrowserView(webView);

  // Start visible with Google
  webView.webContents.loadURL('https://google.com');
  
  // Set initial bounds when ready
  mainWindow.webContents.on('did-finish-load', () => {
    showWebView();
  });

  // Watch for title changes from React to toggle visibility
  // React sets document.title = 'aeternus:screen:dashboard' etc.
  mainWindow.webContents.on('page-title-updated', (event: any, title: string) => {
    if (title.startsWith('aeternus:screen:')) {
      const screen = title.split(':')[2];
      console.log('[Main] Title signal received, screen:', screen);
      if (screen === 'webview') {
        showWebView();
      } else {
        hideWebView();
      }
      event.preventDefault(); // Don't actually change the window title bar
    }
  });

  // Re-calculate bounds on resize (only if visible)
  mainWindow.on('resize', () => {
    if (webViewVisible) {
      showWebView();
    }
  });

  // Send events to React
  webView.webContents.on('did-start-loading', () => {
    mainWindow?.webContents.send('browser-loading', true);
  });

  webView.webContents.on('did-stop-loading', () => {
    mainWindow?.webContents.send('browser-loading', false);
  });

  webView.webContents.on('did-navigate', (event: any, url: string) => {
    mainWindow?.webContents.send('browser-url-changed', url);
  });

  webView.webContents.on('did-navigate-in-page', (event: any, url: string) => {
    mainWindow?.webContents.send('browser-url-changed', url);
  });

  webView.webContents.on('page-title-updated', (event: any, title: string) => {
    mainWindow?.webContents.send('browser-title-changed', title);
  });

  // Register global shortcut for emergency toggle
  globalShortcut.register('CommandOrControl+Shift+H', () => {
    console.log('[Main] Global shortcut triggered');
    if (webViewVisible) {
      hideWebView();
    } else {
      showWebView();
    }
  });
}

// Heartbeat
setInterval(() => {
  if (mainWindow) {
    const views = mainWindow.getBrowserViews?.() || [];
    console.log('[Heartbeat] visible:', webViewVisible, '| views attached:', views.length);
  }
}, 3000);

// Enable Remote Debugging Port for CDP
app.commandLine.appendSwitch('remote-debugging-port', '9333');

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
