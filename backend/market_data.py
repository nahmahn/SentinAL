import yfinance as yf
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import asyncio
import logging

router = APIRouter(prefix="/api/market", tags=["market"])
logger = logging.getLogger(__name__)

# Default watchlist for Aeternus
DEFAULT_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", 
    "ICICIBANK.NS", "BHARTIARTL.NS", "SBIN.NS", "LICI.NS",
    "ITC.NS", "HINDUNILVR.NS"
]

@router.get("/indices")
async def get_indices():
    """Get current values for NIFTY 50 and SENSEX."""
    try:
        # ^NSEI is NIFTY 50, ^BSESN is SENSEX
        indices = ["^NSEI", "^BSESN"]
        data = {}
        
        for index in indices:
            ticker = yf.Ticker(index)
            info = ticker.fast_info
            history = ticker.history(period="2d")
            
            if not history.empty and len(history) >= 2:
                prev_close = history['Close'].iloc[-2]
                current = info['last_price']
                change = current - prev_close
                change_percent = (change / prev_close) * 100
                
                name = "NIFTY 50" if index == "^NSEI" else "SENSEX"
                data[name] = {
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "symbol": index
                }
        return data
    except Exception as e:
        logger.error(f"Error fetching indices: {e}")
        # Fallback data if yfinance fails
        return {
            "NIFTY 50": {"price": 22462.00, "change": 135.10, "change_percent": 0.60, "symbol": "^NSEI", "is_fallback": True},
            "SENSEX": {"price": 74014.55, "change": 450.20, "change_percent": 0.61, "symbol": "^BSESN", "is_fallback": True}
        }

@router.get("/watchlist")
async def get_watchlist():
    """Get real-time quotes for the default watchlist."""
    try:
        quotes = []
        # Fetching multiple tickers at once is faster
        tickers = yf.Tickers(" ".join(DEFAULT_WATCHLIST))
        
        for symbol in DEFAULT_WATCHLIST:
            try:
                ticker = tickers.tickers[symbol]
                info = ticker.fast_info
                
                # Get 2 days of history for change calculation
                hist = ticker.history(period="2d")
                change = 0.0
                change_percent = 0.0
                
                if not hist.empty and len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    current = info['last_price']
                    change = current - prev_close
                    change_percent = (change / prev_close) * 100

                quotes.append({
                    "symbol": symbol.replace(".NS", ""),
                    "full_symbol": symbol,
                    "price": round(info['last_price'], 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "currency": "INR"
                })
            except Exception as inner_e:
                logger.warning(f"Error fetching {symbol}: {inner_e}")
                continue
                
        return quotes
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}")
        return []

@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get detailed quote for a specific symbol."""
    if not symbol.endswith(".NS") and not symbol.endswith(".BO") and "." not in symbol:
        symbol = f"{symbol}.NS"
        
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        
        # Determine name (yf.info is slow, so we use a simple map or skip)
        hist = ticker.history(period="2d")
        change = 0.0
        change_percent = 0.0
        
        if not hist.empty and len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            current = info['last_price']
            change = current - prev_close
            change_percent = (change / prev_close) * 100
            
        return {
            "symbol": symbol,
            "price": round(info['last_price'], 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "high": round(info['day_high'], 2),
            "low": round(info['day_low'], 2),
            "volume": int(info['last_volume'])
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found or error occurred: {str(e)}")

@router.get("/history/{symbol}")
async def get_history(symbol: str, period: str = "1mo"):
    """Get historical data for a stock. Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max."""
    if not symbol.endswith(".NS") and not symbol.endswith(".BO") and "." not in symbol:
        symbol = f"{symbol}.NS"
        
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return []
            
        history_data = []
        for index, row in hist.iterrows():
            history_data.append({
                "date": index.strftime("%Y-%m-%d"),
                "close": round(row['Close'], 2)
            })
        return history_data
    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {e}")
        return []
