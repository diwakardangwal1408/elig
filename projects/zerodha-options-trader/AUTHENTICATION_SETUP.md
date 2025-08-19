# Zerodha Authentication Setup Guide

This guide will help you set up Zerodha authentication for the Options Trading System.

## Prerequisites

1. **Zerodha Kite Connect App**: You need to have a Kite Connect app created on the Zerodha Developer Portal.
2. **API Key and Secret**: You should have your API Key and API Secret from Zerodha.

## Step 1: Configure Redirect URL in Zerodha

1. Go to [Zerodha Kite Connect Console](https://developers.kite.trade/apps/)
2. Click on your app name
3. In the **Redirect URL** field, enter: `http://127.0.0.1:8080/`
4. Click **Update** to save the changes

> **Important**: The redirect URL must be exactly `http://127.0.0.1:8080/` (with the trailing slash)

## Step 2: Setup Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your credentials:
   ```bash
   # Zerodha API Configuration
   KITE_API_KEY=your_api_key_here
   KITE_API_SECRET=your_api_secret_here
   # Note: Access token will be generated automatically after authentication
   
   # Trading Configuration
   TRADING_MODE=paper  # paper or live
   MAX_DAILY_LOSS=5000  # Maximum daily loss in INR
   MAX_POSITION_SIZE=50000  # Maximum position size per trade in INR
   RISK_PER_TRADE=2  # Risk per trade as % of capital
   ```

## Step 3: Authenticate with Zerodha

1. Start the authentication server:
   ```bash
   python main.py auth
   ```

2. Open your browser and go to: `http://localhost:8502`

3. Click on the Zerodha Login URL provided

4. Login with your Zerodha credentials

5. After successful login, you'll be redirected to a URL like:
   ```
   http://127.0.0.1:8080/?request_token=XXXXXXXXXXXXXXXXXXXXXX&action=login&status=success
   ```

6. Copy the `request_token` value (the X's in the example above)

7. Paste the request token in the authentication page and click "Authenticate"

8. If successful, your access token will be saved automatically

## Step 4: Verify Authentication

Once authenticated, you can:

1. Launch the trading dashboard:
   ```bash
   python main.py dashboard
   ```

2. Start the trading engine:
   ```bash
   python main.py engine
   ```

## Token Management

- **Access tokens are automatically saved** to `zerodha_tokens.json`
- **Tokens are automatically loaded** on subsequent runs
- **Tokens expire daily** at 7:30 AM - you'll need to re-authenticate
- Use the `python main.py auth` command whenever you need to refresh your authentication

## Troubleshooting

### Error: "No valid access token found"
- Run `python main.py auth` to authenticate
- Make sure your `.env` file has the correct API key and secret

### Error: "Authentication failed"
- Verify your API key and secret in the `.env` file
- Make sure the redirect URL is configured correctly in Zerodha console
- Check that you're using the correct request token

### Error: "Token validation failed"
- Your token may have expired (tokens expire at 7:30 AM daily)
- Re-authenticate using `python main.py auth`

### Redirect URL Issues
- Ensure the redirect URL in Zerodha console is exactly: `http://127.0.0.1:8080/`
- Make sure there are no extra spaces or characters
- The URL is case-sensitive and must include the trailing slash

## Security Notes

- Never share your API key, API secret, or access tokens
- The `zerodha_tokens.json` file contains sensitive information - keep it secure
- Access tokens expire daily for security reasons
- Always use paper trading mode first to test your strategies

## Next Steps

After successful authentication:

1. Review and modify `strategies.json` for your trading strategies
2. Test with paper trading mode first
3. Switch to live trading only after thorough testing
4. Monitor your trades using the dashboard

For more help, refer to the main README or contact support.