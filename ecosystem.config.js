module.exports = {
  apps: [
    {
      name: "smartapi-worker",
      script: "run.py",
      interpreter: "python3",
      cwd: "/home/lenovo/Documents/PPersonal/MCD-project/backend/smartapi_candle_tracker",
      instances: 1,
      exec_mode: "fork",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      max_memory_restart: "512M",
      env: {
        ENV: "production",
        BACKEND_BASE_URL: "http://localhost:3000",
        BACKEND_WEBHOOK_URL: "http://localhost:3000/api/in-memory-candles",
        WORKER_HOST: "0.0.0.0",
        WORKER_PORT: "5000",
        LOG_LEVEL: "INFO"
      },
      env_development: {
        ENV: "development",
        BACKEND_BASE_URL: "http://localhost:3000",
        BACKEND_WEBHOOK_URL: "http://localhost:3000/api/in-memory-candles",
        WORKER_HOST: "0.0.0.0",
        WORKER_PORT: "5000",
        LOG_LEVEL: "DEBUG"
      },
      error_file: "./logs/smartapi-worker-error.log",
      out_file: "./logs/smartapi-worker-out.log",
      log_file: "./logs/smartapi-worker-combined.log",
      time: true,
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    }
  ]
};
