from fastapi import FastAPI, Body, HTTPException, BackgroundTasks
import uvicorn
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from core.broker_manager import BrokerManager
from services.indicator_engine import IndicatorEngine
from services.risk_manager import RiskManager
from services.market_data_service import MarketDataService
from services.backtest_engine import BacktestEngine
from typing import Dict, Any

from strategies.grid_bot import GridBot
from strategies.dca_bot import DCABot
from strategies.smart_bot import SmartBot

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize services
broker_manager = BrokerManager()
risk_manager = RiskManager()
market_data = MarketDataService()
backtest_engine = BacktestEngine()

# --- Multi-User Native Memory State (Play Store Ready) ---
active_bots: Dict[str, Dict[str, Dict[str, Any]]] = {} # user_id -> bot_id -> stats
bot_tasks: Dict[str, Dict[str, asyncio.Task]] = {}     # user_id -> bot_id -> task
stop_signals = set() # global stop signals for specific bot_ids

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Market Data Streamer
    logger.info("Initializing Market Data Streamer...")
    asyncio.create_task(market_data.start())
    yield
    # Shutdown: Stop all workers
    await market_data.stop()
    await broker_manager.close_all()
    # Cancel all running bot tasks for ALL users
    for user_task_map in bot_tasks.values():
        for task in user_task_map.values():
            task.cancel()

app = FastAPI(title="BotX Pro Trading Engine (Native)", lifespan=lifespan)

# --- BOT STRATEGY EXECUTION LOOPS ---

async def run_strategy_loop(bot_data: dict):
    # Ensure bot_id is extracted as a string to avoid NoneType dictionary keys
    bot_id = str(bot_data.get('bot_id', 'unknown_bot'))
    user_id = bot_data.get('user_id', 'default_user')
    bot_type = bot_data.get('type')
    symbol = bot_data.get('symbol', 'BTC/USDT')
    params = bot_data.get('params', {})
    is_paper = bot_data.get('paper', True)
    credentials = bot_data.get('credentials', {})

    logger.info(f"Starting bot {bot_id} ({bot_type}) on {symbol}...")
    
    if user_id not in active_bots:
        active_bots[user_id] = {}
        
    active_bots[user_id][bot_id] = {
        "status": "starting", 
        "bot_id": bot_id, 
        "realized_pnl": 0.0, 
        "symbol": symbol, 
        "type": bot_type
    }

    try:
        # 1. Initialize Market Data
        if not market_data.running:
            await market_data.start()

        # 2. Initialize Broker
        type_name = "paper" if is_paper else bot_data.get('broker_type', 'binance')
        broker = await broker_manager.add_broker(user_id, type_name, credentials)
        if hasattr(broker, 'market_data'):
            setattr(broker, 'market_data', market_data)

        # 3. Strategy Setup
        active_bots[user_id][bot_id]["status"] = "running"
        if bot_type == 'grid':
            await run_grid_logic(user_id, bot_id, broker, symbol, params)
        elif bot_type == 'dca':
            await run_dca_logic(user_id, bot_id, broker, symbol, params)
        else:
            await run_ai_logic(user_id, bot_id, broker, symbol, params)

    except asyncio.CancelledError:
        logger.info(f"Bot {bot_id} (User: {user_id}) was cancelled.")
        if user_id in active_bots:
            active_bots[user_id][bot_id] = {"status": "stopped", "bot_id": bot_id, "error": "Cancelled"}
    except Exception as e:
        logger.error(f"ERROR in bot {bot_id} (User: {user_id}): {e}")
        if user_id in active_bots:
            active_bots[user_id][bot_id] = {"status": "error", "bot_id": bot_id, "message": str(e)}

async def run_grid_logic(user_id, bot_id, broker, symbol, params):
    lower = params.get('lower_price', 0.0)
    upper = params.get('upper_price', 0.0)
    count = params.get('grid_count', 10)
    investment = params.get('investment', 100.0)
    
    bot = GridBot(bot_id, symbol, lower, upper, count, investment)
    
    current_price = market_data.get_price("binance", symbol) or await broker.get_price(symbol)
    bot.initialize_grid(current_price)
    
    logger.info(f"Grid initialized with {count} levels between {lower} and {upper}")
    
    try:
        while True:
            if bot_id in stop_signals:
                logger.info(f"GRID: Stop signal received for {bot_id}. Exiting loop.")
                stop_signals.remove(bot_id)
                break

            current_price = market_data.get_price("binance", symbol) or await broker.get_price(symbol)
            updates = bot.process_tick(current_price)
            
            for update in updates:
                logger.info(f"GRID EVENT [{bot_id}]: {update['type']} {update['side']} @ {update['price']}")
                
            status = bot.get_status()
            
            # Update native memory state
            if user_id in active_bots:
                active_bots[user_id][bot_id] = {
                    "bot_id": bot_id,
                    "status": "running",
                    "realized_pnl": round(status.get('realized_pnl', 0.0) or 0.0, 2),
                    "active_grids": status.get('active_grids', 0),
                    "inventory": round(status.get('inventory', 0.0) or 0.0, 4),
                }
            
            await asyncio.sleep(2) # Fast polling for grid
    finally:
        logger.info(f"GRID: Performing cleanup for {bot_id} on {symbol}")
        await broker.cleanup(symbol)
        if user_id in active_bots and bot_id in active_bots[user_id]:
            active_bots[user_id][bot_id]["status"] = "stopped"

async def run_dca_logic(user_id, bot_id, broker, symbol, params):
    step_pct = params.get('step_percent', 1.0)
    multiplier = params.get('multiplier', 1.5)
    max_orders = params.get('max_orders', 10)
    tp_pct = params.get('take_profit', 2.0)
    initial_amount = params.get('initial_amount', 10.0)
    
    bot = DCABot(step_pct, multiplier, max_orders, tp_pct)
    logger.info(f"DCA: Initialized for {symbol} (Step={step_pct}%, x{multiplier})")
    
    try:
        while True:
            if bot_id in stop_signals:
                logger.info(f"DCA: Stop signal for {bot_id}")
                stop_signals.remove(bot_id)
                break

            current_price = market_data.get_price("binance", symbol) or await broker.get_price(symbol)
            positions = await broker.get_positions(symbol)
            
            decision = bot.calculate_next_order(positions, current_price)
            
            if decision['action'] == 'INITIAL_ORDER':
                await broker.place_order(symbol, 'buy', 'market', initial_amount)
            elif decision['action'] == 'ADD_ORDER':
                logger.info(f"DCA EVENT: Adding layer {len(positions)} size {decision['size']}")
                await broker.place_order(symbol, 'buy', 'market', decision['size'])
            
            vwap = 0.0
            if positions:
                total_size = sum(float(p['contracts']) for p in positions)
                vwap = sum(float(p['entryPrice']) * float(p['contracts']) for p in positions) / total_size
                is_tp, reason = bot.check_take_profit(vwap, current_price, positions[0]['side'])
                if is_tp:
                    logger.info(f"DCA EXIT: {reason}")
                    await broker.close_all_positions(symbol)
                    bot.realized_pnl += (current_price - vwap) * total_size
                    
            active_bots[user_id][bot_id] = {
                "bot_id": bot_id,
                "status": "running",
                "realized_pnl": round(bot.realized_pnl or 0.0, 2),
                "layers": len(positions),
                "avg_price": round(vwap or 0.0, 5) if positions else 0
            }
            
            await asyncio.sleep(5)
    finally:
        await broker.cleanup(symbol)
        active_bots[user_id][bot_id]["status"] = "stopped"

async def run_ai_logic(user_id, bot_id, broker, symbol, params):
    bot = SmartBot(threshold=params.get('threshold', 75))
    logger.info(f"AI: Initialized for {symbol} (Threshold={bot.threshold})")
    
    try:
        while True:
            if bot_id in stop_signals:
                stop_signals.remove(bot_id)
                break
                
            df = await broker.get_historical_data(symbol, '15m', limit=100)
            signal, score = bot.generate_signal(df)
            current_price = df.iloc[-1]['close'] if not df.empty else 0.0
            
            if signal == "BUY":
                logger.info(f"AI SIGNAL: BUY (Score: {score})")
                await broker.place_order(symbol, 'buy', 'market', 100.0)
            elif signal == "SELL":
                logger.info(f"AI SIGNAL: SELL (Score: {score})")
                await broker.place_order(symbol, 'sell', 'market', 100.0)
                
            active_bots[user_id][bot_id] = {
                "bot_id": bot_id,
                "status": "running",
                "signal": signal,
                "conviction": score,
                "last_price": current_price
            }
            
            await asyncio.sleep(60) # AI runs on slower timeframe
    finally:
        await broker.cleanup(symbol)
        active_bots[user_id][bot_id]["status"] = "stopped"

# --- API ENDPOINTS ---

@app.post("/bot/start")
async def start_bot(data: Dict[str, Any] = Body(...)):
    """
    Launch a bot seamlessly using a native asyncio Task.
    """
    bot_id = str(data.get('bot_id'))
    user_id = str(data.get('user_id', 'default_user'))
    print("\n" + "="*50)
    print(f">>> RECEIVED BOT START REQUEST: {bot_id} for User: {user_id}")
    print("="*50 + "\n")
    
    if not bot_id:
        raise HTTPException(status_code=400, detail="bot_id is required")

    if user_id not in bot_tasks:
        bot_tasks[user_id] = {}

    if bot_id in bot_tasks[user_id] and not bot_tasks[user_id][bot_id].done():
        raise HTTPException(status_code=400, detail="Bot is already running")

    # Create the background task attached to the event loop
    task = asyncio.create_task(run_strategy_loop(data))
    bot_tasks[user_id][bot_id] = task
    
    return {
        "status": "success", 
        "bot_id": bot_id, 
        "message": "Bot engine engaged",
        "_ver": "1.0.0"
    }

@app.get("/bot/status/{user_id}/{bot_id}")
async def get_bot_status(user_id: str, bot_id: str):
    """
    Retrieve real-time status from the in-memory engine.
    """
    if user_id not in active_bots or bot_id not in active_bots[user_id]:
        return {"status": "inactive", "bot_id": bot_id, "realized_pnl": 0.0}
    return active_bots[user_id][bot_id]

@app.post("/bot/stop/{user_id}/{bot_id}")
async def stop_bot(user_id: str, bot_id: str):
    """
    Stop a bot running in the native engine.
    """
    if user_id in bot_tasks and bot_id in bot_tasks[user_id] and not bot_tasks[user_id][bot_id].done():
        stop_signals.add(bot_id)
        return {"status": "stopping", "bot_id": bot_id}
    elif user_id in active_bots and bot_id in active_bots[user_id]:
        active_bots[user_id][bot_id]["status"] = "stopped"
        return {"status": "stopped", "bot_id": bot_id}
    else:
        raise HTTPException(status_code=404, detail="Bot not found")

@app.post("/trade")
async def execute_trade(data: Dict[str, Any] = Body(...)):
    user_id = data.get('user_id')
    broker_type = data.get('broker_type')
    is_paper = data.get('paper', False)
    symbol = data.get('symbol')
    side = data.get('side')
    amount = data.get('amount')
    credentials = data.get('credentials', {}) if not is_paper else {"balance": data.get('balance', 10000.0)}

    if not all([user_id, broker_type, symbol, side, amount]):
        raise HTTPException(status_code=400, detail="Missing required parameters")

    type_name = "paper" if is_paper else broker_type
    broker = await broker_manager.add_broker(user_id, type_name, credentials)
    
    res = await broker.execute_trade(symbol, side, amount)
    return {"status": "executed", "result": res}

@app.get("/price/{broker_type}/{symbol}")
async def get_price(broker_type: str, symbol: str):
    price = market_data.get_price(broker_type, symbol)
    if price:
        return {"symbol": symbol, "price": price, "source": "cache"}
    
    broker = broker_manager.get_broker("default", broker_type)
    if broker:
        price = await broker.get_price(symbol)
        return {"symbol": symbol, "price": price, "source": "direct"}
    return {"symbol": symbol, "price": 65000.0, "source": "mock"}

@app.get("/health")
async def health():
    return {"status": "healthy", "active_bots": len(active_bots)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
