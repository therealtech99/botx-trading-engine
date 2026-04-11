const MetaApi = require('metaapi.cloud-sdk').default;

class TradeService {
    constructor(token) {
        this.api = new MetaApi(token);
        this.connections = {}; // Cache connections to avoid re-logging in
    }

    async getConnection(accountId) {
        if (this.connections[accountId]) {
            return this.connections[accountId];
        }

        console.log(`[TradeService] Establishing new RPC connection for ${accountId}...`);
        const account = await this.api.metatraderAccountApi.getAccount(accountId);
        const connection = account.getRPCConnection();
        
        await connection.connect();
        await connection.waitSynchronized();
        
        this.connections[accountId] = connection;
        return connection;
    }

    async executeOrder(accountId, symbol, action, volume) {
        try {
            const connection = await this.getConnection(accountId);
            console.log(`[Order] Placing ${action} on ${symbol} | Vol: ${volume}`);
            
            const result = await connection.createMarketOrder(
                symbol,
                action === 'BUY' ? 'ORDER_TYPE_BUY' : 'ORDER_TYPE_SELL',
                parseFloat(volume),
                0, // Stop Loss (0 for demo)
                0, // Take Profit (0 for demo)
                { comment: 'BotX Pro Execution' }
            );

            return { success: true, orderId: result.orderId, details: result };
        } catch (err) {
            console.error(`[Order Failed] ${err.message}`);
            throw err;
        }
    }

    async getPositions(accountId) {
        try {
            const connection = await this.getConnection(accountId);
            const positions = await connection.getPositions();
            return positions;
        } catch (err) {
            console.error(`[Positions Failed] ${err.message}`);
            throw err;
        }
    }

    async closePosition(accountId, positionId) {
        try {
            const connection = await this.getConnection(accountId);
            const result = await connection.closePosition(positionId);
            return result;
        } catch (err) {
            console.error(`[Close Failed] ${err.message}`);
            throw err;
        }
    }
}

module.exports = TradeService;
