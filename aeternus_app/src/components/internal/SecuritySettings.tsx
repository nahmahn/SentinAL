import React from 'react';
import { motion } from 'framer-motion';

const SecuritySettings: React.FC = () => {
    return (
        <motion.main 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex-1 overflow-y-auto p-8 bg-surface-container-low transition-all duration-300"
        >
            <div className="max-w-7xl mx-auto space-y-12">
                {/* Header */}
                <header className="mb-12">
                    <h1 className="text-[3.5rem] font-bold text-primary leading-tight tracking-tight">Security & Controls</h1>
                    <p className="text-on-surface-variant text-lg max-w-2xl mt-4 font-medium opacity-80">
                        Fine-tune your digital fortress. SentinAL uses institutional-grade encryption to safeguard your assets and privacy.
                    </p>
                </header>

                <div className="grid grid-cols-12 gap-6">
                    {/* Account Security Section */}
                    <section className="col-span-12 lg:col-span-8 space-y-6">
                        <div className="premium-card p-8 bg-surface-container-lowest shadow-sm border border-transparent hover:border-secondary/5 transition-all">
                            <div className="flex items-center justify-between mb-8">
                                <h2 className="text-2xl font-bold text-primary">Account Security</h2>
                                <span className="bg-secondary-container/10 text-secondary font-bold text-xs px-3 py-1 rounded-full uppercase tracking-widest">Enterprise Level</span>
                            </div>

                            {/* 2FA Control */}
                            <div className="flex items-center justify-between p-6 rounded-2xl bg-surface-container-low mb-6 transition-all hover:bg-surface-container-high cursor-pointer">
                                <div className="flex items-center gap-6">
                                    <div className="w-14 h-14 bg-white rounded-2xl flex items-center justify-center text-secondary shadow-sm">
                                        <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>fingerprint</span>
                                    </div>
                                    <div>
                                        <h4 className="font-bold text-primary text-lg">Two-Factor Authentication</h4>
                                        <p className="text-on-surface-variant text-sm font-medium">Biometric and app-based validation enabled.</p>
                                    </div>
                                </div>
                                <button className="bg-primary text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-primary-container transition-all active:scale-95 shadow-lg shadow-primary/10">
                                    Configure
                                </button>
                            </div>

                            {/* Login History */}
                            <div className="space-y-4">
                                <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-400 px-2">Recent Login History</h3>
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between p-4 bg-white rounded-xl shadow-sm border-l-4 border-secondary premium-card">
                                        <div className="flex flex-col">
                                            <span className="text-sm font-bold text-primary">Chrome on macOS</span>
                                            <span className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-widest mt-0.5">IP: 192.168.1.12 • Session: _ae_4920</span>
                                        </div>
                                        <div className="text-right">
                                            <span className="block text-sm font-bold text-primary">Today, 10:42 AM</span>
                                            <span className="text-[10px] text-green-600 font-bold uppercase tracking-widest">Active Now</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Privacy Controls */}
                        <div className="premium-card p-8 bg-surface-container-lowest shadow-sm">
                            <h2 className="text-2xl font-bold text-primary mb-8">Privacy Controls</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {[
                                    { title: 'Stealth Mode', icon: 'visibility_off', desc: 'Hides your portfolio balance from the main dashboard when enabled.', active: false },
                                    { title: 'AI Learning Exclusion', icon: 'data_exploration', desc: 'Prevent your transaction patterns from being used for global AI optimization.', active: true },
                                ].map((control, i) => (
                                    <div key={i} className={`p-6 rounded-2xl transition-all group ${control.active ? 'bg-surface-container-low border-2 border-secondary/20' : 'bg-surface-container-low'}`}>
                                        <div className="flex items-center gap-3 mb-4">
                                            <span className="material-symbols-outlined text-secondary group-hover:scale-110 transition-transform">
                                                {control.icon}
                                            </span>
                                            <h4 className="font-bold text-primary">{control.title}</h4>
                                        </div>
                                        <p className="text-sm text-on-surface-variant leading-relaxed mb-4 font-medium opacity-80">{control.desc}</p>
                                        <div className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors ${control.active ? 'bg-secondary' : 'bg-slate-300'}`}>
                                            <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${control.active ? 'right-1' : 'left-1'}`} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </section>

                    {/* Institutions Section */}
                    <section className="col-span-12 lg:col-span-4">
                        <div className="premium-card p-8 bg-primary-container text-white relative overflow-hidden h-full shadow-xl">
                            <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-secondary opacity-10 blur-3xl rounded-full" />
                            <h2 className="text-2xl font-bold mb-6 relative z-10">Connected Institutions</h2>
                            <p className="text-on-primary-container text-sm mb-8 relative z-10 font-medium">Manage secure API bridges to your external financial accounts.</p>
                            
                            <div className="space-y-4 relative z-10">
                                {[
                                    { name: 'Goldman Sachs', type: 'Trading Account', icon: 'account_balance' },
                                    { name: 'Binance Pro', type: 'Yield Wallet', icon: 'currency_bitcoin' },
                                    { name: 'JP Morgan Chase', type: 'Savings', icon: 'account_balance' },
                                ].map((inst, i) => (
                                    <div key={i} className="bg-white/10 backdrop-blur-md rounded-2xl p-5 flex items-center justify-between group cursor-pointer hover:bg-white/20 transition-all">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center p-2">
                                                <span className="material-symbols-outlined text-white text-xl">{inst.icon}</span>
                                            </div>
                                            <div>
                                                <span className="block text-sm font-bold">{inst.name}</span>
                                                <span className="block text-[10px] text-on-primary-container uppercase tracking-widest font-bold">{inst.type}</span>
                                            </div>
                                        </div>
                                        <span className="material-symbols-outlined text-on-primary-container group-hover:translate-x-1 transition-transform">chevron_right</span>
                                    </div>
                                ))}
                            </div>
                            
                            <button className="w-full mt-12 bg-secondary-container text-on-secondary-container py-4 rounded-2xl font-bold hover:shadow-lg active:scale-95 transition-all text-sm uppercase tracking-widest">
                                + Connect Institution
                            </button>
                        </div>
                    </section>
                </div>

                {/* Privacy Footer */}
                <div className="premium-card p-12 bg-surface-container-low flex flex-col md:flex-row items-center gap-8 border border-white/50 shadow-sm">
                    <div className="w-24 h-24 rounded-full bg-secondary-container/20 flex items-center justify-center text-secondary">
                        <span className="material-symbols-outlined text-5xl">verified_user</span>
                    </div>
                    <div className="flex-grow text-center md:text-left">
                        <h2 className="text-3xl font-bold text-primary mb-2">Your data is yours. Period.</h2>
                        <p className="text-on-surface-variant max-w-2xl leading-relaxed font-medium opacity-80 text-base">
                            SentinAL employs Zero-Knowledge Proofs for all sensitive computations. We never store your raw credentials, and our AI models only interact with obfuscated data signatures.
                        </p>
                    </div>
                    <button className="bg-white text-primary border border-slate-200 px-8 py-3 rounded-xl font-bold hover:shadow-md transition-all whitespace-nowrap active:scale-95">
                        Download Audit Report
                    </button>
                </div>
            </div>
        </motion.main>
    );
};

export default SecuritySettings;
