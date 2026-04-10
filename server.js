require('dotenv').config();
const express = require('express');
const cors = require('cors');

const MetaApi = require('metaapi.cloud-sdk').default;

const app = express();
app.use(cors());
app.use(express.json());

// Main Connection Endpoint for BotX Pro
app.post('/api/broker/connect', async (req, res) => {
  // --- Security Middleware: Block Unauthorized Requests ---
  const clientApiKey = req.headers['x-botx-api-key'];
  const SERVER_API_KEY = process.env.APP_API_KEY || "BotX_Pro_Engine_Secure_Key_2026";
  
  if (clientApiKey !== SERVER_API_KEY) {
    console.warn("BLOCKED: Unauthorized connection attempt detected.");
    return res.status(401).json({ error: 'Unauthorized Access. Invalid API Key.' });
  }
  // --------------------------------------------------------

  const { broker, login, password, server, platform } = req.body;
  
  if (!login || !password || !server) {
    return res.status(400).json({ error: 'Missing credentials' });
  }

  // Security check: Never hardcode your API key in standard environments!
  // It is recommended you add your token to the .env file as META_API_TOKEN
  const META_TOKEN = process.env.META_API_TOKEN;

  try {
    console.log(`[Connecting] Broker: ${broker} | Account: ${login} | Server: ${server}`);

    // 1. Initialize MetaApi
    const api = new MetaApi(META_TOKEN);
    
    // 2. Map payload platform to MetaApi's standard format
    const metaPlatform = (platform && platform.toLowerCase().includes('mt5')) ? 'mt5' : 'mt4';

    // 3. Provision the account to your MetaApi Cloud
    console.log(`Provisioning ${metaPlatform} account to the cloud...`);
    const account = await api.metatraderAccountApi.createAccount({
      name: `${broker} - ${login}`,
      type: 'cloud-g2', // Standard Cloud Server
      login: login,
      password: password,
      server: server,
      platform: metaPlatform,
      magic: 1000 // A unique ID to identify trades opened by your specific AI Bot
    });

    console.log(`Deploying account (${account.id}) ...`);
    await account.deploy();

    console.log('Waiting for connection to broker server...');
    await account.waitConnected();

    console.log('Successfully connected!');
    
    return res.status(200).json({
      success: true,
      message: 'Account verified and linked successfully via MetaApi.',
      accountId: account.id,
      state: account.state
    });
  } catch (err) {
    console.error('MetaApi Error Details:', err.message);
    res.status(500).json({ error: 'Failed to connect to broker.', details: err.message });
  }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`BotX Pro Trading Engine running on port ${PORT}`);
    console.log(`Waiting for BotX Pro users to connect their accounts...`);
});
