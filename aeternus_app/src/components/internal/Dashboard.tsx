import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface IndexData {
    price: number;
    change: number;
    change_percent: number;
    symbol: string;
}

interface StockQuote {
    symbol: string;
    full_symbol: string;
    price: number;
    change: number;
    change_percent: number;
    currency: string;
}

const Dashboard: React.FC = () => {
    const [indices, setIndices] = useState<Record<string, IndexData>>({});
    const [watchlist, setWatchlist] = useState<StockQuote[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const [indicesRes, watchlistRes] = await Promise.all([
                fetch('http://localhost:8000/api/market/indices'),
                fetch('http://localhost:8000/api/market/watchlist')
            ]);

            if (indicesRes.ok) {
                const indicesData = await indicesRes.json();
                setIndices(indicesData);
            }

            if (watchlistRes.ok) {
                const watchlistData = await watchlistRes.json();
                setWatchlist(watchlistData);
            }
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000); // Update every 30s
        return () => clearInterval(interval);
    }, []);

    return (
        <motion.main 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex-1 overflow-y-auto p-8 bg-surface-container-low transition-all duration-300"
        >
            <div className="max-w-5xl mx-auto space-y-8">
                {/* Dashboard Header */}
                <header className="flex justify-between items-end">
                    <div>
                        <h1 className="text-4xl font-bold tracking-tight text-primary">Portfolio Overview</h1>
                        <p className="text-on-surface-variant mt-2 font-medium italic">
                            Live Markets Analysis • {loading ? 'Updating...' : 'Real-time via yfinance'}
                        </p>
                    </div>
                    <div className="flex gap-4 items-center">
                        {Object.entries(indices).map(([name, data]) => (
                            <div key={name} className="text-right">
                                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{name}</p>
                                <div className="flex items-center gap-2">
                                    <span className="font-bold text-primary">{data.price.toLocaleString('en-IN')}</span>
                                    <span className={`text-xs font-bold ${data.change >= 0 ? 'text-emerald-500' : 'text-error'}`}>
                                        {data.change >= 0 ? '+' : ''}{data.change_percent}%
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </header>

                {/* Bento Grid Layout */}
                <div className="grid grid-cols-12 gap-6">
                    {/* Live Watchlist (Replacing the Asset Distribution bars) */}
                    <div className="col-span-8 bg-surface-container-lowest rounded-xl p-8 shadow-[0_20px_40px_rgba(0,26,69,0.04)] premium-card">
                        <div className="flex justify-between items-start mb-6">
                            <h2 className="text-xs uppercase tracking-widest font-bold text-on-surface-variant">Real-Time Watchlist (NSE)</h2>
                            <span className="text-secondary font-bold">Top Movers</span>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                            {watchlist.slice(0, 6).map((stock) => (
                                <div key={stock.symbol} className="p-4 rounded-lg bg-surface-container-low flex justify-between items-center group hover:bg-primary/5 transition-colors cursor-pointer">
                                    <div>
                                        <p className="font-bold text-primary group-hover:text-primary-600">{stock.symbol}</p>
                                        <p className="text-[10px] text-on-surface-variant font-medium">₹{stock.price.toLocaleString('en-IN')}</p>
                                    </div>
                                    <div className={`text-right px-3 py-1 rounded-md text-xs font-bold ${stock.change >= 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                                        {stock.change >= 0 ? '+' : ''}{stock.change_percent}%
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Mini Metric Card */}
                    <div className="col-span-4 bg-primary-container rounded-xl p-8 text-white relative overflow-hidden flex flex-col justify-between shadow-lg">
                        <div className="relative z-10">
                            <h2 className="text-xs uppercase tracking-widest font-bold opacity-70 mb-1">Estimated Net Worth</h2>
                            <p className="text-3xl font-bold">₹2,84,10,092</p>
                            <p className="text-[10px] opacity-60 mt-1 font-medium italic">Calculated across 12 verified accounts</p>
                        </div>
                        <div className="mt-4 relative z-10">
                            <button className="bg-secondary-container text-on-secondary-container px-4 py-3 rounded-lg text-xs font-bold w-full active:scale-95 transition-all shadow-md hover:shadow-lg">
                                Generate Financial Audit
                            </button>
                        </div>
                        {/* Background Decoration */}
                        <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
                    </div>

                    {/* Recent Agent Activity (Replacing fake manual transactions) */}
                    <div className="col-span-12 space-y-4">
                        <h3 className="text-lg font-bold text-primary">Recent Intelligence Activity</h3>
                        <div className="bg-surface-container-lowest rounded-xl divide-y divide-surface-container shadow-sm overflow-hidden">
                            {[
                                { title: 'Market Sentiment Analysis', date: 'Just now', detail: 'Analyzed 12 news sources for Reliance Industries', status: 'Completed', icon: 'psychology', color: 'text-primary' },
                                { title: 'Beneficiary Verification', date: '15m ago', detail: 'Verified UPI ID: rahul@paytm (Rahul Sharma)', status: 'Verified', icon: 'verified_user', color: 'text-secondary' },
                                { title: 'Portfolio Optimization', date: '2h ago', detail: 'Rebalanced weightage for IT sector allocation', status: 'Executed', icon: 'query_stats', color: 'text-emerald-500' },
                            ].map((tx, i) => (
                                <div key={i} className="flex items-center justify-between p-6 hover:bg-surface transition-colors cursor-pointer group">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center transition-transform group-hover:scale-105">
                                            <span className={`material-symbols-outlined ${tx.color}`}>{tx.icon}</span>
                                        </div>
                                        <div>
                                            <p className="font-bold text-primary">{tx.title}</p>
                                            <p className="text-xs text-on-surface-variant font-medium">{tx.detail}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs font-bold text-on-surface-variant mb-1">{tx.date}</p>
                                        <span className="text-[10px] px-3 py-1 bg-surface-container-high rounded-full font-bold uppercase tracking-wider text-primary">
                                            {tx.status}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </motion.main>
    );
};

export default Dashboard;
