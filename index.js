require('dotenv').config();
const express = require('express');
const cors = require('cors');

const MetaApi = require('metaapi.cloud-sdk').default;
const TradeService = require('./trade_service');

const app = express();
app.use(cors());
app.use(express.json());

// Initialize Trade Service
const tradeService = new TradeService(process.env.META_API_TOKEN);

// --- Middleware: API Key Security ---
const authMiddleware = (req, res, next) => {
    const clientApiKey = req.headers['x-botx-api-key'];
    const SERVER_API_KEY = process.env.APP_API_KEY || "BotX_Pro_Engine_Secure_Key_2026";
    
    if (clientApiKey !== SERVER_API_KEY) {
        return res.status(401).json({ error: 'Unauthorized Access. Invalid API Key.' });
    }
    next();
};

// Use security for all trading routes
app.use('/api/trade', authMiddleware);
// ------------------------------------

// 1. Connection Endpoint (Provisioning)
app.post('/api/broker/connect', authMiddleware, async (req, res) => {
  const { broker, login, password, server, platform } = req.body;
  
  if (!login || !password || !server) {
    return res.status(400).json({ error: 'Missing credentials' });
  }

  const META_TOKEN = process.env.META_API_TOKEN;

  try {
    console.log(`[Connecting] Broker: ${broker} | Account: ${login} | Server: ${server}`);

    const api = new MetaApi(META_TOKEN);
    const metaPlatform = (platform && platform.toLowerCase().includes('mt5')) ? 'mt5' : 'mt4';

    console.log(`Provisioning ${metaPlatform} account to the cloud...`);
    const account = await api.metatraderAccountApi.createAccount({
      name: `${broker} - ${login}`,
      type: 'cloud-g2',
      login: login,
      password: password,
      server: server,
      platform: metaPlatform,
      magic: 1000 
    });

    console.log(`Deploying account (${account.id}) ...`);
    await account.deploy();

    console.log('Waiting for connection to broker server...');
    await account.waitConnected();

    console.log('Successfully connected!');
    
    return res.status(200).json({
      success: true,
      message: 'Account verified and linked successfully.',
      accountId: account.id
    });
  } catch (err) {
    console.error('MetaApi Error:', err.message);
    res.status(500).json({ error: 'Failed to connect to broker.', details: err.message });
  }
});

/**
 * START TRADING ENDPOINTS
 */

// 2. Execute Order (Buy/Sell)
app.post('/api/trade/execute', async (req, res) => {
    const { accountId, symbol, action, volume } = req.body;
    
    try {
        const result = await tradeService.executeOrder(accountId, symbol, action, volume);
        res.status(200).json(result);
    } catch (err) {
        res.status(500).json({ error: 'Order execution failed', details: err.message });
    }
});

// 3. Get Open Positions
app.get('/api/trade/positions/:accountId', async (req, res) => {
    const { accountId } = req.params;
    
    try {
        const positions = await tradeService.getPositions(accountId);
        res.status(200).json({ success: true, positions });
    } catch (err) {
        res.status(500).json({ error: 'Failed to fetch positions', details: err.message });
    }
});

// 4. Close Position
app.post('/api/trade/close', async (req, res) => {
    const { accountId, positionId } = req.body;
    
    try {
        const result = await tradeService.closePosition(accountId, positionId);
        res.status(200).json({ success: true, result });
    } catch (err) {
        res.status(500).json({ error: 'Failed to close position', details: err.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`BotX Pro Trading Engine running on port ${PORT}`);
});

