import React, { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import AgentSidebar from './AgentSidebar';
import Dashboard from './internal/Dashboard';
import TransactionHistory from './internal/TransactionHistory';
import InvestmentPortfolio from './internal/InvestmentPortfolio';
import SecuritySettings from './internal/SecuritySettings';

type ScreenType = 'dashboard' | 'assets' | 'transactions' | 'security' | 'webview';

const BrowserShell = () => {
    const [activeScreen, setActiveScreen] = useState<ScreenType>('webview');
    const [urlInput, setUrlInput] = useState('https://google.com');
    const [isLoading, setIsLoading] = useState(false);

    // Electron API Sync
    useEffect(() => {
        const api = (window as any).electronAPI;
        if (api) {
            api.onLoading?.((loading: boolean) => setIsLoading(loading));
            api.onUrlChange?.((url: string) => setUrlInput(url));
        }
    }, []);

    // Signal the main process via document.title changes
    // This bypasses the preload IPC which appears to be silently failing
    useEffect(() => {
        document.title = `aeternus:screen:${activeScreen}`;
    }, [activeScreen]);

    const handleUrlSubmit = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            let url = urlInput.trim();
            if (!url) return;
            if (!url.startsWith('http')) {
                url = url.includes('.') ? 'https://' + url : 'https://google.com/search?q=' + encodeURIComponent(url);
            }
            setActiveScreen('webview');
            (window as any).electronAPI?.navigate(url);
        }
    };

    const navigateTo = (screen: ScreenType) => {
        setActiveScreen(screen);
    };

    const isWebview = activeScreen === 'webview';

    return (
        <div className="flex flex-col h-screen w-screen bg-surface font-sans overflow-hidden select-none">
            {/* Top Navigation Bar */}
            <nav className="grid grid-cols-3 items-center h-20 w-full px-6 pt-4 bg-surface/90 backdrop-blur-xl border-b border-surface-container shadow-[0_4px_30px_rgba(0,26,69,0.05)] z-50 relative">
                {/* Left: Branding & Tabs */}
                <div className="flex items-center gap-8 min-w-0">
                    <span className="text-xl font-bold tracking-tighter text-primary whitespace-nowrap flex-shrink-0">SentinAL</span>
                    
                    <div className="flex gap-6 overflow-x-auto no-scrollbar min-w-0 pr-4">
                        {[
                            { id: 'webview', label: 'Browse' },
                            { id: 'dashboard', label: 'Dashboard' },
                            { id: 'assets', label: 'Assets' },
                            { id: 'transactions', label: 'Transactions' },
                            { id: 'security', label: 'Security' },
                        ].map((item) => (
                            <button
                                key={item.id}
                                onClick={() => navigateTo(item.id as ScreenType)}
                                className={clsx(
                                    "text-sm font-bold tracking-tight transition-all duration-300 pb-1 border-b-2 whitespace-nowrap flex-shrink-0",
                                    activeScreen === item.id 
                                        ? "text-secondary border-secondary opacity-100" 
                                        : "text-on-surface-variant border-transparent opacity-60 hover:opacity-100 hover:text-primary"
                                )}
                            >
                                {item.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Center: Address Bar (Strictly Centered) */}
                <div className="flex justify-center px-4">
                    <div className="w-full max-w-[450px] flex items-center gap-3 bg-surface-container-lowest px-4 py-2 rounded-xl shadow-[0_4px_12px_rgba(0,26,69,0.04)] group transition-all duration-300 hover:shadow-[0_8px_20px_rgba(0,26,69,0.1)] border border-outline-variant/10">
                        <span className={clsx(
                            "material-symbols-outlined text-lg transition-colors",
                            isLoading ? "text-secondary animate-spin" : "text-secondary"
                        )}>
                            {isLoading ? 'progress_activity' : (isWebview ? 'lock' : 'shield')}
                        </span>
                        <input
                            type="text"
                            value={isWebview ? urlInput : `sentinal.ai/finance/${activeScreen}`}
                            onChange={(e) => setUrlInput(e.target.value)}
                            onFocus={() => { if (!isWebview) setUrlInput(''); }}
                            onKeyDown={handleUrlSubmit}
                            className="text-sm font-medium text-on-surface-variant flex-1 bg-transparent border-none focus:ring-0 p-0 outline-none"
                            placeholder="Search or type URL"
                        />
                        {isWebview && (
                            <button 
                                onClick={() => (window as any).electronAPI?.reload()}
                                className="material-symbols-outlined text-on-surface-variant text-lg hover:text-primary transition-colors"
                            >
                                refresh
                            </button>
                        )}
                    </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center justify-end gap-3 flex-shrink-0">
                    <button className="p-2 rounded-full hover:bg-surface-container transition-all duration-300">
                        <span className="material-symbols-outlined text-on-surface-variant">account_circle</span>
                    </button>
                    <button className="p-2 rounded-full hover:bg-surface-container transition-all duration-300">
                        <span className="material-symbols-outlined text-on-surface-variant">settings</span>
                    </button>
                </div>
            </nav>

            {/* Main Content Area */}
            <div className="flex flex-1 overflow-hidden relative">
                {/* Content Canvas (only shows when NOT in webview mode) */}
                {!isWebview && (
                    <div className="flex-1 flex overflow-hidden" style={{ marginRight: SIDEBAR_WIDTH }}>
                        <AnimatePresence mode="wait">
                            {activeScreen === 'dashboard' && <Dashboard key="dashboard" />}
                            {activeScreen === 'assets' && <InvestmentPortfolio key="assets" />}
                            {activeScreen === 'transactions' && <TransactionHistory key="transactions" />}
                            {activeScreen === 'security' && <SecuritySettings key="security" />}
                        </AnimatePresence>
                    </div>
                )}

                {/* When in webview mode, the BrowserView (native Electron) covers this area.
                    We just need an empty space holder so the sidebar stays on the right. */}
                {isWebview && (
                    <div className="flex-1" style={{ marginRight: SIDEBAR_WIDTH }} />
                )}

                {/* Agent Sidebar — always visible */}
                <AgentSidebar />
            </div>
        </div>
    );
};

const SIDEBAR_WIDTH = 380;

export default BrowserShell;
