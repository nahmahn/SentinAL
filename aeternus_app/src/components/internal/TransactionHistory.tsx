import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface Transaction {
    id: number;
    title: string;
    category: string;
    description: string;
    amount: number | null;
    status: string;
    icon: string;
    timestamp: string;
    is_positive: boolean;
    source: string;
}

const TransactionHistory: React.FC = () => {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTransactions = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/transactions');
            if (response.ok) {
                const data = await response.json();
                setTransactions(data);
            }
        } catch (error) {
            console.error('Error fetching transactions:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTransactions();
        const interval = setInterval(fetchTransactions, 10000); // Polling every 10s
        return () => clearInterval(interval);
    }, []);

    return (
        <motion.main 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="flex-1 overflow-y-auto p-8 bg-surface-container-low transition-all duration-300"
        >
            <div className="max-w-7xl mx-auto">
                {/* Header Section */}
                <header className="mb-10 flex justify-between items-end">
                    <div className="space-y-1">
                        <h1 className="text-[3.5rem] font-bold leading-none tracking-tight text-primary">Intelligence Log</h1>
                        <p className="text-on-surface-variant text-lg font-medium opacity-80">Audit history of agent actions and financial events.</p>
                    </div>
                    <div className="flex gap-3">
                        <button className="flex items-center gap-2 px-6 py-3 rounded-xl bg-surface-container-lowest text-primary font-semibold shadow-sm hover:bg-white active:scale-95 transition-all">
                            <span className="material-symbols-outlined text-xl">filter_list</span>
                            Filter
                        </button>
                        <button className="flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-white font-semibold shadow-lg hover:shadow-primary/20 active:scale-95 transition-all">
                            <span className="material-symbols-outlined text-xl">download</span>
                            Export Audit
                        </button>
                    </div>
                </header>

                {/* Stats Overview Bento */}
                <div className="grid grid-cols-12 gap-6 mb-10">
                    <div className="col-span-12 lg:col-span-8 bg-primary-container rounded-[2rem] p-8 text-white relative overflow-hidden shadow-xl">
                        <div className="relative z-10">
                            <p className="text-secondary-container font-semibold uppercase tracking-widest text-xs mb-2">System Throughput (24H)</p>
                            <h2 className="text-5xl font-bold mb-6">{transactions.length} Actions</h2>
                            <div className="flex gap-8">
                                <div className="flex items-center gap-2">
                                    <span className="w-2 h-6 bg-secondary-container rounded-full animate-pulse"></span>
                                    <div>
                                        <p className="text-[10px] uppercase font-bold text-blue-100">Success Rate</p>
                                        <p className="text-lg font-bold">98.2%</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="w-2 h-6 bg-emerald-400 rounded-full"></span>
                                    <div>
                                        <p className="text-[10px] uppercase font-bold text-blue-100">Avg. Response</p>
                                        <p className="text-lg font-bold">1.2s</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        {/* Background mesh ornament */}
                        <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -mr-20 -mt-20 blur-3xl"></div>
                    </div>
                    <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest rounded-[2rem] p-8 flex flex-col justify-between shadow-sm premium-card border-l-4 border-secondary">
                        <div>
                            <div className="flex justify-between items-start mb-4">
                                <span className="bg-secondary/10 p-3 rounded-2xl">
                                    <span className="material-symbols-outlined text-secondary font-bold">shield_with_heart</span>
                                </span>
                                <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Active Guard</span>
                            </div>
                            <h3 className="text-xl font-bold text-primary">SentinAL Integrity</h3>
                            <p className="text-sm text-on-surface-variant mt-2 font-medium">All outgoing signals are verified against the local security policy.</p>
                        </div>
                        <div className="bg-surface-container-low h-2 w-full rounded-full mt-4 overflow-hidden">
                            <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: '100%' }}
                                transition={{ duration: 1.5, ease: 'easeOut' }}
                                className="bg-secondary h-full rounded-full" 
                            />
                        </div>
                    </div>
                </div>

                {/* Transaction List */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between px-6 mb-2">
                        <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Event Source & Description</span>
                        <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Status</span>
                    </div>

                    {loading ? (
                        <div className="text-center py-20 text-slate-400 font-medium italic">Loading intelligence logs...</div>
                    ) : transactions.length === 0 ? (
                        <div className="text-center py-20 text-slate-400 font-medium italic">No transactions recorded yet.</div>
                    ) : (
                        transactions.map((tx, i) => (
                            <motion.div 
                                key={tx.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.05 * Math.min(i, 10) }}
                                className="bg-surface-container-lowest rounded-[1.5rem] p-5 flex items-center justify-between shadow-sm hover:shadow-md transition-all duration-300 premium-card border-l-4 border-transparent hover:border-primary/20"
                            >
                                <div className="flex items-center gap-6">
                                    <div className="w-14 h-14 bg-surface-container-low rounded-2xl flex items-center justify-center p-3 text-primary shadow-inner">
                                        <span className="material-symbols-outlined text-2xl">{tx.icon}</span>
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-bold text-primary">{tx.title}</h4>
                                        <div className="flex items-center gap-3 text-sm text-on-surface-variant mt-1 font-medium">
                                            <span className="font-mono bg-surface-container-low px-2 py-0.5 rounded text-[10px] text-primary/70">{tx.category}</span>
                                            <span>•</span>
                                            <span className="text-xs">{tx.timestamp}</span>
                                        </div>
                                        <p className="text-xs text-on-surface-variant/70 mt-1 italic max-w-md truncate">{tx.description}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-12 text-right">
                                    <div>
                                        <p className={`text-xl font-bold ${tx.is_positive ? 'text-emerald-600' : 'text-primary'}`}>
                                            {tx.amount ? (tx.is_positive ? '+' : '-') + `₹${tx.amount.toLocaleString('en-IN')}` : '---'}
                                        </p>
                                        <p className="text-[10px] font-extrabold text-secondary uppercase tracking-widest">{tx.source}</p>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <span className={`px-4 py-1.5 text-[10px] font-bold rounded-full uppercase tracking-wider ${
                                            tx.status === 'Completed' || tx.status === 'Verified' 
                                            ? 'bg-emerald-50 text-emerald-700' 
                                            : tx.status === 'Failed' 
                                              ? 'bg-rose-50 text-rose-700'
                                              : 'bg-blue-50 text-blue-700 animate-pulse'
                                        }`}>
                                            {tx.status}
                                        </span>
                                        <button className="text-primary/40 hover:text-primary transition-colors">
                                            <span className="material-symbols-outlined">more_vert</span>
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        ))
                    )}
                </div>
            </div>
        </motion.main>
    );
};

export default TransactionHistory;
