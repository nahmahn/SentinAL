import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot } from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs));
}

interface Message {
    id: string;
    type: 'info' | 'error' | 'success' | 'warning' | 'user' | 'agent';
    message: string;
    financeContext?: any;
}

// Simple Markdown-like formatter for a "premium" look
const FormattedMessage = ({ content }: { content: string }) => {
    // Process newlines first
    const lines = content.split('\n');
    
    return (
        <div className="space-y-2">
            {lines.map((line, i) => {
                const isBullet = line.trim().startsWith('- ');
                const cleanLine = isBullet ? line.trim().substring(2) : line;

                // Process bolding: **text**
                const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
                const renderedLine = parts.map((part, j) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                        return <strong key={j} className="font-extrabold text-primary">{part.slice(2, -2)}</strong>;
                    }
                    return part;
                });

                if (isBullet) {
                    return (
                        <div key={i} className="flex gap-2 items-start ml-2">
                            <span className="text-secondary mt-1.5 min-w-[6px] h-[6px] rounded-full bg-secondary" />
                            <p className="flex-1">{renderedLine}</p>
                        </div>
                    );
                }

                return renderedLine.length > 0 ? <p key={i}>{renderedLine}</p> : <div key={i} className="h-2" />;
            })}
        </div>
    );
};

const AgentSidebar = () => {
    const [input, setInput] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [activeTab, setActiveTab] = useState<'context' | 'agent' | 'payments' | 'history'>('agent');
    const [messages, setMessages] = useState<Message[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [socket, setSocket] = useState<WebSocket | null>(null);
    
    // HITL States
    const [hitlRequest, setHitlRequest] = useState<any>(null);
    const [hitlFeedback, setHitlFeedback] = useState('');

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const reconnectTimeoutRef = useRef<any>(null);

    useEffect(() => {
        const connect = () => {
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
            
            const ws = new WebSocket('ws://localhost:8000/ws/agent');

            ws.onopen = () => {
                addMessage('success', 'Connected to SentinAL Financial Core.');
                setSocket(ws);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'agent' || data.type === 'info' || data.type === 'error' || data.type === 'success') {
                        addMessage(data.type, data.message || JSON.stringify(data), data.data);
                    } else if (data.type === 'finance_context') {
                        addMessage('agent', data.message, data.data);
                    } else if (data.type === 'hitl_request') {
                        setHitlRequest({
                            reason: data.reason || data.message || 'Approval Required',
                            action_name: data.action_name
                        });
                        setIsProcessing(false); // Make it look paused
                    }
                    
                    if (data.type === 'done' || data.type === 'error') {
                        setIsProcessing(false);
                    }
                } catch (e) {
                    console.error('Failed to parse WS message:', e);
                }
            };

            ws.onerror = () => {
                // Silently attempt reconnect
            };

            ws.onclose = () => {
                setSocket(null);
                reconnectTimeoutRef.current = setTimeout(connect, 3000); // Reconnect in 3s
            };
        };

        connect();
        return () => {
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        };
    }, []);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        addMessage('user', input);
        setIsProcessing(true);

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ task: input }));
        } else {
            addMessage('error', 'Agent Core not connected.');
            setIsProcessing(false);
        }

        setInput('');
    };

    const addMessage = (type: Message['type'], message: string, financeContext?: any) => {
        setMessages(prev => [...prev, { id: Math.random().toString(36), type, message, financeContext }]);
    };

    const handleHitlResponse = (action: 'approve' | 'reject') => {
        if (!socket || socket.readyState !== WebSocket.OPEN) return;
        
        socket.send(JSON.stringify({ 
            type: 'hitl_response', 
            action, 
            feedback: hitlFeedback 
        }));
        
        addMessage('user', `Reviewed: ${action.toUpperCase()}${hitlFeedback ? `\nFeedback: ${hitlFeedback}` : ''}`);
        
        setHitlRequest(null);
        setHitlFeedback('');
        setIsProcessing(true);
    };

    return (
        <aside className="fixed right-0 top-20 h-[calc(100vh-80px)] w-[380px] bg-surface-container-lowest/70 backdrop-blur-2xl shadow-[-20px_0_40px_rgba(0,26,69,0.04)] flex flex-col z-40 border-l border-white/20">
            {/* Sidebar Header */}
            <div className="glass-header p-6 flex items-center gap-4 border-b border-surface-container/50">
                <div className="bg-gradient-to-br from-primary to-primary-container rounded-xl p-2 h-12 w-12 flex items-center justify-center shadow-lg shadow-primary/20">
                    <span className="material-symbols-outlined text-white text-2xl">smart_toy</span>
                </div>
                <div className="flex-1">
                    <h2 className="text-sm font-extrabold tracking-tight text-primary uppercase">SentinAL Agent</h2>
                    <div className="flex items-center gap-1.5">
                        <div className={cn("w-1.5 h-1.5 rounded-full", isProcessing ? "bg-secondary animate-pulse" : "bg-green-500")} />
                        <p className="text-[10px] font-bold text-secondary uppercase tracking-widest">
                            {isProcessing ? 'Processing Task' : 'Financial Curator Active'}
                        </p>
                    </div>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-surface/5">
                <AnimatePresence initial={false}>
                    {messages.length === 0 && (
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="h-full flex flex-col items-center justify-center text-on-surface-variant/40 space-y-4 text-center"
                        >
                            <Bot className="w-12 h-12 opacity-20" />
                            <div className="space-y-1">
                                <p className="text-sm font-bold uppercase tracking-widest">Awaiting Instruction</p>
                                <p className="text-[10px] font-medium max-w-[200px]">How can I assist your financial portfolio today?</p>
                            </div>
                        </motion.div>
                    )}

                    {messages.map((msg) => (
                        <motion.div 
                            key={msg.id}
                            initial={{ opacity: 0, y: 10, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            className={cn(
                                "flex flex-col gap-2",
                                msg.type === 'user' ? "items-end" : "items-start"
                            )}
                        >
                            {/* Finance Context Card (Special Rendering) */}
                            {msg.financeContext && (
                                <div className="bg-surface-container-low rounded-xl p-5 shadow-[0_4px_12px_rgba(0,26,69,0.04)] space-y-4 w-full mb-2 border border-outline-variant/10">
                                    <div className="flex justify-between items-center">
                                        <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Transaction Context</span>
                                        <div className="flex items-center gap-1 bg-secondary-container/20 text-secondary px-2 py-0.5 rounded-full border border-secondary/20">
                                            <span className="material-symbols-outlined text-xs" style={{ fontVariationSettings: "'FILL' 1" }}>verified</span>
                                            <span className="text-[9px] font-bold">Verified</span>
                                        </div>
                                    </div>
                                    <div className="flex justify-between items-baseline">
                                        <p className="text-xs text-on-surface-variant font-medium">Proposed Amount</p>
                                        <p className="text-2xl font-bold text-primary">₹ {msg.financeContext.estimated_amount?.toLocaleString() || '---'}</p>
                                    </div>
                                    <div className="pt-3 border-t border-surface-container flex justify-between items-center text-[10px] font-bold">
                                        <span className="text-on-surface-variant font-mono">Platform: {msg.financeContext.paytm_detected ? 'Paytm' : 'Universal'}</span>
                                        <span className={cn(
                                            "uppercase tracking-tighter",
                                            msg.financeContext.risk_level === 'high' ? 'text-error' : 'text-primary'
                                        )}>
                                            Risk: {msg.financeContext.risk_level}
                                        </span>
                                    </div>
                                </div>
                            )}

                            <div className={cn(
                                "p-4 rounded-2xl text-sm leading-relaxed shadow-sm max-w-[90%]",
                                msg.type === 'user' 
                                    ? "bg-white text-on-surface rounded-tr-none shadow-[0_4px_16px_rgba(0,26,69,0.08)] border border-surface-container" 
                                    : "bg-[#E3F8FF] border-l-4 border-secondary text-primary rounded-tl-none",
                                (msg.type === 'error' || msg.type === 'warning') && "bg-error-container/20 text-error border-error shadow-none"
                            )}>
                                <FormattedMessage content={msg.message} />
                            </div>
                        </motion.div>
                    ))}

                    {isProcessing && !hitlRequest && (
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex justify-start"
                        >
                            <div className="bg-[#E3F8FF] border-l-4 border-secondary px-4 py-3 rounded-full flex gap-1.5 items-center shadow-sm">
                                <div className="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce [animation-duration:0.8s]" />
                                <div className="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce [animation-duration:0.8s] [animation-delay:0.2s]" />
                                <div className="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce [animation-duration:0.8s] [animation-delay:0.4s]" />
                            </div>
                        </motion.div>
                    )}

                    {hitlRequest && (
                        <motion.div 
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-error-container/10 border border-error/30 rounded-2xl p-5 space-y-4 shadow-lg shadow-error/5 my-4 mx-2 backdrop-blur-sm"
                        >
                            <div className="flex items-center gap-2 text-error">
                                <span className="material-symbols-outlined text-xl">gpp_maybe</span>
                                <h3 className="font-extrabold text-sm tracking-tight uppercase">Security Review Required</h3>
                            </div>
                            
                            <div className="text-sm text-on-surface bg-white/50 p-3 rounded-lg border border-outline-variant/20 shadow-inner">
                                <p className="font-medium text-error">{hitlRequest.reason}</p>
                            </div>

                            <div className="space-y-3 pt-2">
                                <input
                                    type="text"
                                    value={hitlFeedback}
                                    onChange={(e) => setHitlFeedback(e.target.value)}
                                    placeholder="Add feedback or instructions before resuming..."
                                    className="w-full bg-white border border-outline-variant/30 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-error focus:ring-1 focus:ring-error transition-all shadow-sm font-medium"
                                />
                                
                                <div className="flex gap-2">
                                    <button 
                                        onClick={() => handleHitlResponse('reject')}
                                        className="flex-1 bg-error hover:bg-error/90 text-white py-2.5 rounded-lg font-bold text-xs uppercase tracking-wider transition-all shadow-md active:scale-95"
                                    >
                                        Reject Action
                                    </button>
                                    <button 
                                        onClick={() => handleHitlResponse('approve')}
                                        className="flex-1 bg-green-500 hover:bg-green-600 text-white py-2.5 rounded-lg font-bold text-xs uppercase tracking-wider transition-all shadow-md active:scale-95"
                                    >
                                        Approve Action
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-6 pt-2 bg-surface-container-lowest/80 border-t border-surface-container/50">
                <div className="bg-surface-container-lowest rounded-xl shadow-[0_12px_24px_rgba(0,26,69,0.08)] p-2 border border-outline-variant/10 group-focus-within:border-secondary/50 transition-all">
                    <textarea 
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSubmit(e))}
                        className="w-full bg-transparent border-none focus:ring-0 text-sm p-3 min-h-[80px] resize-none placeholder:text-on-surface-variant/50 font-medium" 
                        placeholder="Ask SentinAL anything..."
                    />
                    <div className="flex justify-between items-center px-3 pb-2">
                        <div className="flex gap-2">
                            <button className="p-2 text-on-surface-variant hover:text-secondary transition-colors rounded-lg hover:bg-surface-container">
                                <span className="material-symbols-outlined text-lg">attach_file</span>
                            </button>
                            <button 
                                onClick={() => isProcessing && socket?.send(JSON.stringify({ type: 'stop' }))}
                                className={cn("p-2 transition-colors rounded-lg", isProcessing ? "text-error hover:bg-error-container/20" : "text-on-surface-variant hover:text-secondary hover:bg-surface-container")}
                            >
                                <span className="material-symbols-outlined text-lg">{isProcessing ? 'stop_circle' : 'mic'}</span>
                            </button>
                        </div>
                        <button 
                            onClick={handleSubmit}
                            disabled={!input.trim() || isProcessing || hitlRequest !== null}
                            className="bg-primary hover:bg-primary-container text-white px-6 py-2 rounded-lg text-xs font-bold flex items-center gap-2 active:scale-95 transition-all disabled:opacity-50 disabled:grayscale shadow-md"
                        >
                            Execute Transaction
                            <span className="material-symbols-outlined text-sm">arrow_forward</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex justify-around items-center h-20 border-t border-surface-container bg-surface-container-low/50">
                {[
                    { id: 'context', icon: 'analytics', label: 'Context' },
                    { id: 'agent', icon: 'smart_toy', label: 'Agent' },
                    { id: 'payments', icon: 'account_balance_wallet', label: 'Payments' },
                    { id: 'history', icon: 'receipt_long', label: 'History' },
                ].map((tab) => (
                    <button 
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className={cn(
                            "flex flex-col items-center gap-1 transition-all duration-300 px-4 py-2 rounded-xl",
                            activeTab === tab.id 
                                ? "text-primary border-b-4 border-secondary opacity-100 bg-surface/10" 
                                : "text-on-surface-variant opacity-60 hover:opacity-100 hover:bg-surface-container"
                        )}
                    >
                        <span className="material-symbols-outlined">{tab.icon}</span>
                        <span className="text-[9px] font-bold uppercase tracking-widest">{tab.label}</span>
                    </button>
                ))}
            </div>
        </aside>
    );
};

export default AgentSidebar;
