import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface HistoryPoint {
    date: string;
    close: number;
}

interface StockQuote {
    symbol: string;
    price: number;
    change_percent: number;
}

const InvestmentPortfolio: React.FC = () => {
    const [history, setHistory] = useState<HistoryPoint[]>([]);
    const [assets, setAssets] = useState<StockQuote[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const [histRes, watchlistRes] = await Promise.all([
                fetch('http://localhost:8000/api/market/history/^NSEI?period=1mo'),
                fetch('http://localhost:8000/api/market/watchlist')
            ]);

            if (histRes.ok) {
                const histData = await histRes.json();
                setHistory(histData);
            }

            if (watchlistRes.ok) {
                const watchlistData = await watchlistRes.json();
                setAssets(watchlistData);
            }
        } catch (error) {
            console.error('Error fetching portfolio data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    // Simple SVG path generator for the history
    const generatePath = () => {
        if (history.length < 2) return "";
        const min = Math.min(...history.map(p => p.close));
        const max = Math.max(...history.map(p => p.close));
        const range = max - min;
        
        return history.map((p, i) => {
            const x = (i / (history.length - 1)) * 100;
            const y = 100 - ((p.close - min) / range) * 80 - 10; // 80% height, 10% padding
            return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
        }).join(' ');
    };

    return (
        <motion.main 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="flex-1 overflow-y-auto p-8 bg-surface-container-low transition-all duration-300"
        >
            <div className="max-w-7xl mx-auto space-y-8">
                {/* Hero Section: Total Portfolio Value */}
                <section className="relative overflow-hidden rounded-xl bg-gradient-to-br from-primary to-primary-container p-10 text-white shadow-xl">
                    <div className="relative z-10 flex justify-between items-end">
                        <div className="space-y-4">
                            <div className="flex items-center gap-2">
                                <span className="text-secondary-container font-semibold tracking-widest uppercase text-xs">SentinAL Managed Assets</span>
                                <span className="material-symbols-outlined text-sm">trending_up</span>
                            </div>
                            <h1 className="text-5xl font-bold tracking-tight">₹1,28,45,592.42</h1>
                            <div className="flex items-center gap-3">
                                <span className="bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full text-xs font-bold">+12.4% vs last month</span>
                                <span className="text-on-primary-container text-xs font-mono opacity-60">SECURE NODE: 0x4f2...9b11</span>
                            </div>
                        </div>
                        <div className="flex gap-8">
                            <div className="text-right">
                                <p className="text-white/60 text-xs uppercase font-bold tracking-widest mb-1">Live Profit/Loss</p>
                                <p className="text-2xl font-bold text-emerald-400">+₹1,42,203</p>
                            </div>
                            <div className="h-12 w-[1px] bg-white/10"></div>
                            <div className="text-right">
                                <p className="text-white/60 text-xs uppercase font-bold tracking-widest mb-1">Verified Assets</p>
                                <p className="text-2xl font-bold">14 Entities</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Grid Layout */}
                <div className="grid grid-cols-12 gap-8">
                    {/* Asset Allocation Donut */}
                    <div className="col-span-12 lg:col-span-4 bg-white rounded-xl p-8 shadow-[0_20px_40px_rgba(0,26,69,0.06)] flex flex-col items-center justify-between premium-card">
                        <div className="w-full mb-6">
                            <h2 className="text-lg font-bold text-primary mb-1">Intelligence Sector Allocation</h2>
                            <p className="text-on-surface-variant text-sm font-medium italic">Agent identified distribution</p>
                        </div>
                        <div className="relative w-48 h-48 flex items-center justify-center">
                            <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" r="40" fill="transparent" stroke="#f1f5f9" strokeWidth="12" />
                                <circle cx="50" cy="50" r="40" fill="transparent" stroke="#00B9F1" strokeWidth="12" strokeDasharray="251.2" strokeDashoffset="100.48" strokeLinecap="round" />
                                <circle cx="50" cy="50" r="40" fill="transparent" stroke="#003D88" strokeWidth="12" strokeDasharray="251.2" strokeDashoffset="200.96" strokeLinecap="round" />
                            </svg>
                            <div className="flex flex-col items-center">
                                <span className="text-2xl font-bold text-primary tracking-tighter">FinTech</span>
                                <span className="text-xs font-semibold text-slate-400">62%</span>
                            </div>
                        </div>
                        <div className="w-full mt-8 space-y-3">
                            {[
                                { label: 'Banking & UPI', value: '42%', color: 'bg-primary' },
                                { label: 'Equity Markets', value: '38%', color: 'bg-primary-container' },
                                { label: 'Cash Reserves', value: '20%', color: 'bg-slate-200' },
                            ].map((item, i) => (
                                <div key={i} className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-3 h-3 rounded-full ${item.color}`}></div>
                                        <span className="text-sm font-medium text-on-surface">{item.label}</span>
                                    </div>
                                    <span className="text-sm font-mono font-bold">{item.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Performance Trend Chart */}
                    <div className="col-span-12 lg:col-span-8 bg-white rounded-xl p-8 shadow-[0_20px_40px_rgba(0,26,69,0.06)] premium-card">
                        <div className="flex justify-between items-start mb-12">
                            <div>
                                <h2 className="text-lg font-bold text-primary mb-1">Index Performance (NIFTY 50)</h2>
                                <p className="text-on-surface-variant text-sm font-medium">Real-time market volatility tracking</p>
                            </div>
                            <div className="flex gap-2">
                                <button className="px-4 py-1.5 rounded-full text-xs font-bold bg-primary text-white">1M</button>
                                <button className="px-4 py-1.5 rounded-full text-xs font-bold text-slate-400 hover:bg-slate-50">3M</button>
                                <button className="px-4 py-1.5 rounded-full text-xs font-bold text-slate-400 hover:bg-slate-50">1Y</button>
                            </div>
                        </div>
                        <div className="h-64 relative">
                            {loading ? (
                                <div className="absolute inset-0 flex items-center justify-center text-slate-400 font-medium italic">
                                    Analyzing market trends...
                                </div>
                            ) : (
                                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 100">
                                    <defs>
                                        <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                            <stop offset="0%" stopColor="#00B9F1" stopOpacity="0.2" />
                                            <stop offset="100%" stopColor="#00B9F1" stopOpacity="0" />
                                        </linearGradient>
                                    </defs>
                                    <path d={`${generatePath()} L 100 100 L 0 100 Z`} fill="url(#gradient)" />
                                    <path d={generatePath()} fill="none" stroke="#00B9F1" strokeWidth="2.5" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            )}
                            <div className="absolute bottom-[-24px] w-full flex justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest px-2">
                                {history.length > 0 && (
                                    <>
                                        <span>{history[0].date}</span>
                                        <span>{history[Math.floor(history.length / 2)].date}</span>
                                        <span>{history[history.length - 1].date}</span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Live Asset Feed */}
                <section className="space-y-6">
                    <div className="flex justify-between items-center">
                        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">Live Asset Intelligence</h3>
                        <span className="text-[10px] font-bold text-primary italic bg-primary/5 px-2 py-1 rounded">DATA SOURCE: YAHOO FINANCE</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        {assets.slice(0, 4).map((asset) => (
                            <motion.div 
                                key={asset.symbol}
                                whileHover={{ y: -4 }}
                                className="bg-white p-6 rounded-xl space-y-3 cursor-pointer shadow-sm premium-card border-b-4 border-primary/10"
                            >
                                <div className="flex justify-between items-start">
                                    <h4 className="text-lg font-bold text-primary">{asset.symbol}</h4>
                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${asset.change_percent >= 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                                        {asset.change_percent >= 0 ? '↑' : '↓'} {Math.abs(asset.change_percent)}%
                                    </span>
                                </div>
                                <div>
                                    <p className="text-2xl font-bold text-primary">₹{asset.price.toLocaleString('en-IN')}</p>
                                    <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-tight">Current Valuation</p>
                                </div>
                                <div className="pt-2 border-t border-slate-50 flex items-center gap-2">
                                    <span className="material-symbols-outlined text-xs text-slate-400">verified</span>
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">Authenticated by Agent</span>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </section>
            </div>
        </motion.main>
    );
};

export default InvestmentPortfolio;
