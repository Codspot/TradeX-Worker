# SmartAPI Worker PM2 Deployment Guide

## 🚀 Quick Setup for DigitalOcean Droplet

### Prerequisites
- Node.js and npm installed
- Python 3.8+ installed
- PM2 installed globally: `npm install -g pm2`

### 1. Deploy the Worker

```bash
# Navigate to the worker directory
cd /home/lenovo/Documents/PPersonal/MCD-project/backend/smartapi_candle_tracker

# Run the deployment script
./deploy-pm2.sh
```

### 2. Check Status

```bash
# Quick status check
./check-status.sh

# Or use PM2 commands directly
pm2 status
pm2 logs smartapi-worker
```

### 3. Configuration

The worker uses environment variables from `.env` file:

```env
# Your SmartAPI credentials
API_KEY=your_api_key
CLIENT_CODE=your_client_code
PASSWORD=your_password
TOTP_SECRET=your_totp_secret

# Environment
ENV=production

# Backend URLs (update these for your droplet)
BACKEND_BASE_URL=http://localhost:3000
BACKEND_WEBHOOK_URL=http://localhost:3000/api/in-memory-candles

# Worker configuration
WORKER_HOST=0.0.0.0
WORKER_PORT=5000
```

### 4. PM2 Commands

```bash
# View all processes
pm2 status

# View logs (live)
pm2 logs smartapi-worker

# Restart the worker
pm2 restart smartapi-worker

# Stop the worker
pm2 stop smartapi-worker

# Delete the worker process
pm2 delete smartapi-worker

# Save PM2 configuration
pm2 save

# Setup auto-restart on server reboot
pm2 startup
```

### 5. Endpoints

Once deployed, the worker will:

- **Run on**: `http://localhost:5000` (or your configured port)
- **Forward ticks to**: `http://localhost:3000/api/in-memory-candles/process-tick`
- **WebSocket available at**: `ws://localhost:5000`

### 6. Testing

Test the deployment:

```bash
# Test worker health
curl http://localhost:5000

# Test backend connection
curl http://localhost:3000/api/in-memory-candles/stats

# View live logs
pm2 logs smartapi-worker --lines 50
```

### 7. Production Considerations

For production deployment:

1. **Update URLs**: Change `localhost` to your actual domain/IP in `.env`
2. **SSL/HTTPS**: Configure reverse proxy (nginx) if needed
3. **Firewall**: Ensure ports 3000 and 5000 are accessible
4. **Monitoring**: Set up PM2 monitoring dashboard
5. **Backup**: Backup your `.env` configuration

### 8. Troubleshooting

**Worker not starting:**
- Check logs: `pm2 logs smartapi-worker`
- Verify Python dependencies: `pip3 install -r requirements.txt`
- Check configuration: `python3 -c "from app.config import config; print(config.display_config())"`

**Backend connection failed:**
- Verify NestJS backend is running on port 3000
- Check firewall settings
- Test endpoint: `curl http://localhost:3000/api/in-memory-candles/stats`

**SmartAPI authentication failed:**
- Verify credentials in `.env`
- Check TOTP secret is correct
- Ensure SmartAPI account has API access

### 9. Architecture

```
SmartAPI WebSocket → SmartAPI Worker (Port 5000) → NestJS Backend (Port 3000)
                                   ↓
                              In-Memory Candles
                                   ↓
                              Database (PostgreSQL)
```

The worker receives real-time ticks from SmartAPI and forwards them to your NestJS backend for candle processing.
