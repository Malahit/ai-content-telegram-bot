# Multi-Instance Conflict Resolution

## Overview

This document explains the multi-instance conflict prevention system implemented to resolve the TelegramConflictError: "terminated by other getUpdates request" issue.

## Problem

The Telegram Bot API only allows one active `getUpdates` connection per bot token. When multiple instances of the bot run simultaneously, they compete for updates, causing conflicts and the error:

```
TelegramConflictError: Telegram server says - Conflict: terminated by other getUpdates request
```

## Solution Components

### 1. Instance Lock (PID File-Based)

**Location**: `utils/instance_lock.py`

**Purpose**: Prevent multiple bot instances from running simultaneously using a PID (Process ID) file.

**How It Works**:
1. On startup, creates a lock file with the current process ID
2. Checks if another instance is running by verifying the PID in the lock file
3. Removes stale lock files (when PID is no longer running)
4. Releases lock file on shutdown or termination

**Features**:
- Cross-platform (uses `tempfile.gettempdir()` for lock file location)
- Automatic cleanup via `atexit` and signal handlers
- Detects and removes stale locks from crashed processes

**Usage**:
```python
from utils import InstanceLock

instance_lock = InstanceLock()
if not instance_lock.acquire():
    logger.error("Another instance is running")
    return

try:
    # Run your bot
    pass
finally:
    instance_lock.release()
```

### 2. Graceful Shutdown Manager

**Location**: `utils/shutdown_manager.py`

**Purpose**: Ensure all resources are properly cleaned up on shutdown.

**How It Works**:
1. Registers callbacks to execute on shutdown
2. Handles SIGTERM and SIGINT signals
3. Executes callbacks in LIFO order (last registered, first executed)
4. Continues cleanup even if individual callbacks fail

**Resources Cleaned Up**:
- APScheduler (autoposter)
- API client connections
- RAG observer (if enabled)
- Bot session

**Usage**:
```python
from utils import shutdown_manager

# Register cleanup functions
shutdown_manager.register_callback(on_shutdown)
shutdown_manager.register_signals()

# In cleanup function
async def on_shutdown():
    if scheduler:
        scheduler.shutdown(wait=False)
    await api_client.close()
```

### 3. Polling Manager with Retry Logic

**Location**: `utils/polling_manager.py`

**Purpose**: Handle transient conflicts with automatic retry and exponential backoff.

**How It Works**:
1. Wraps `dispatcher.start_polling()` with retry logic
2. Catches `TelegramConflictError` exceptions
3. Retries with exponential backoff delays
4. Executes optional callback on each conflict
5. Gives up after maximum retry attempts

**Retry Strategy**:
- **Max Retries**: 5 attempts (configurable)
- **Initial Delay**: 5 seconds
- **Max Delay**: 300 seconds (5 minutes)
- **Backoff Factor**: 2.0 (exponential)

**Delay Sequence**: 5s → 10s → 20s → 40s → 80s → 160s (capped at 300s)

**Usage**:
```python
from utils import PollingManager

polling_manager = PollingManager(
    max_retries=5,
    initial_delay=5.0,
    max_delay=300.0,
    backoff_factor=2.0
)

async def on_conflict():
    logger.warning("Conflict detected")

await polling_manager.start_polling_with_retry(
    dispatcher,
    bot,
    on_conflict_callback=on_conflict
)
```

## Integration in main.py and bot.py

### Startup Flow

1. **Acquire Instance Lock**
   ```python
   instance_lock = InstanceLock()
   if not instance_lock.acquire():
       logger.error("Failed to acquire lock")
       return
   ```

2. **Initialize Resources**
   ```python
   await on_startup()  # Init DB, scheduler, etc.
   ```

3. **Register Shutdown Callbacks**
   ```python
   shutdown_manager.register_callback(on_shutdown)
   shutdown_manager.register_signals()
   ```

4. **Start Polling with Retry**
   ```python
   polling_manager = PollingManager(...)
   await polling_manager.start_polling_with_retry(dp, bot)
   ```

5. **Cleanup on Exit**
   ```python
   finally:
       await shutdown_manager.shutdown()
       instance_lock.release()
   ```

### Complete Flow Diagram

```
┌─────────────────────────────────────┐
│  Bot Startup                        │
├─────────────────────────────────────┤
│                                     │
│  1. Try to acquire instance lock   │
│     ├─ Lock exists & PID running?  │
│     │  └─ EXIT (another running)   │
│     └─ Lock stale or doesn't exist?│
│        └─ Create lock file          │
│                                     │
│  2. Initialize resources            │
│     ├─ Database                     │
│     ├─ Scheduler (autoposter)      │
│     └─ Image fetcher, RAG, etc.    │
│                                     │
│  3. Register shutdown callbacks     │
│     └─ Signal handlers (SIGTERM)   │
│                                     │
│  4. Start polling with retry       │
│     ├─ Attempt 1                   │
│     ├─ TelegramConflictError?      │
│     │  ├─ Wait 5s, retry          │
│     │  ├─ Wait 10s, retry         │
│     │  └─ ... (up to 5 retries)   │
│     └─ Success → Running           │
│                                     │
│  5. On shutdown/error/SIGTERM      │
│     ├─ Stop scheduler              │
│     ├─ Close API client            │
│     ├─ Stop RAG observer           │
│     ├─ Close bot session           │
│     └─ Release instance lock       │
│                                     │
└─────────────────────────────────────┘
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
python3 -m unittest tests.test_instance_lock -v
python3 -m unittest tests.test_shutdown_manager -v
python3 -m unittest tests.test_polling_manager -v
```

**Test Coverage**:
- `test_instance_lock.py`: 7 tests covering lock acquisition, stale detection, cleanup
- `test_shutdown_manager.py`: 9 tests covering callbacks, LIFO execution, error handling
- `test_polling_manager.py`: 7 tests covering retry logic, exponential backoff, callbacks

### Manual Testing

Test instance locking manually:

```bash
# Terminal 1
python3 tests/test_instance_lock_manual.py

# Terminal 2 (while first is running)
python3 tests/test_instance_lock_manual.py
# Should fail with "Another instance is running"
```

## Operational Guidelines

### Checking for Running Instances

```bash
# Linux/Mac
ps aux | grep "python.*main.py\|python.*bot.py"

# Check lock file
ls -la /tmp/telegram_bot.lock
cat /tmp/telegram_bot.lock  # Shows PID
```

### Forcing a Restart

If the bot won't start due to a stale lock:

```bash
# 1. Check if process is actually running
ps -p $(cat /tmp/telegram_bot.lock)

# 2. If not running, remove stale lock
rm /tmp/telegram_bot.lock

# 3. Start bot
python3 main.py
```

### Monitoring Logs

Look for these key log messages:

**Successful Startup**:
```
✅ Instance lock acquired (PID: 12345, Lock: /tmp/telegram_bot.lock)
✅ Database initialized
🚀 Автопостинг запущен
✅ Signal handlers registered for graceful shutdown
🚀 Starting bot polling (attempt 1/6)...
```

**Conflict Detected**:
```
⚠️ Another bot instance is already running (PID: 12345)
Lock file: /tmp/telegram_bot.lock
To force start, stop the other instance or remove the lock file.
```

**Retry After Conflict**:
```
❌ TelegramConflictError: Telegram server says - Conflict
Another bot instance may be running.
Retry attempt 1/5
⏳ Waiting 5.0 seconds before retry...
💡 Tip: Check for other running instances or stale lock files.
```

**Graceful Shutdown**:
```
⚠️ Received SIGTERM, initiating graceful shutdown...
🛑 Shutting down bot resources...
✅ Scheduler stopped
✅ API client closed
✅ RAG observer stopped
✅ Bot session closed
🔓 Instance lock released (PID: 12345)
✅ Shutdown complete
```

## Deployment Considerations

### Systemd Service

When running as a systemd service, the instance lock provides additional safety:

```ini
[Unit]
Description=AI Content Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=10

# Ensure clean shutdown
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

### Docker

For Docker deployments, mount a volume for the lock file to persist across container restarts:

```yaml
version: '3'
services:
  telegram-bot:
    image: ai-content-bot
    volumes:
      - /tmp:/tmp  # Share lock file location
    restart: unless-stopped
```

### Multiple Servers

If deploying across multiple servers, consider using:
- Shared network lock (Redis, Consul)
- Database-based locking
- Load balancer with single instance constraint

**Note**: Current PID file implementation is single-server only.

## Troubleshooting

### Issue: "Failed to acquire instance lock"

**Causes**:
1. Another instance is actually running
2. Stale lock file from crashed process
3. Permission issues on lock file location

**Solutions**:
```bash
# Check for running instances
ps aux | grep python.*main.py

# Check lock file
cat /tmp/telegram_bot.lock

# Verify process is running
ps -p $(cat /tmp/telegram_bot.lock)

# If stale, remove it
rm /tmp/telegram_bot.lock
```

### Issue: "Max retries exceeded" on startup

**Causes**:
1. Another bot instance polling same token
2. Webhook still active on Telegram
3. Network connectivity issues

**Solutions**:
```bash
# 1. Check for other instances
ps aux | grep python

# 2. Delete webhook (if any)
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# 3. Check network
ping api.telegram.org

# 4. Wait a few minutes and retry
```

### Issue: Resources not cleaned up

**Causes**:
1. Bot killed with SIGKILL (kill -9)
2. System crash
3. Shutdown callbacks failed

**Solutions**:
```bash
# Check for orphaned processes
ps aux | grep scheduler

# Check lock file
rm /tmp/telegram_bot.lock

# Check logs for shutdown errors
tail -f bot.log | grep -i error
```

## Security Considerations

1. **Lock File Permissions**: Lock file is created with default user permissions
2. **PID Spoofing**: Attacker with write access to /tmp could create fake lock
3. **Denial of Service**: Attacker could hold lock file indefinitely

**Mitigations**:
- Run bot with dedicated user account
- Use restrictive file permissions
- Monitor lock file age and alert on staleness

## Future Enhancements

Potential improvements for multi-server deployments:

1. **Redis-based Locking**
   ```python
   from redis import Redis
   redis = Redis(host='localhost')
   lock = redis.lock('telegram_bot_lock', timeout=300)
   ```

2. **Database-based Locking**
   ```python
   # Use database advisory locks
   SELECT pg_try_advisory_lock(123456);
   ```

3. **Consul/etcd Integration**
   ```python
   from python_consul import Consul
   consul = Consul()
   session = consul.session.create()
   consul.kv.put('telegram_bot/lock', session=session)
   ```

4. **Health Check Endpoint**
   ```python
   # Expose HTTP endpoint for monitoring
   @app.get("/health")
   def health():
       return {"status": "running", "pid": os.getpid()}
   ```

## Summary

The multi-instance conflict resolution system provides:

✅ **Prevention**: PID file prevents multiple instances  
✅ **Detection**: Stale lock detection for crashed processes  
✅ **Recovery**: Exponential backoff retry on transient conflicts  
✅ **Cleanup**: Graceful shutdown with resource cleanup  
✅ **Monitoring**: Detailed logging at each stage  
✅ **Testing**: Comprehensive unit and manual tests  

This ensures the bot runs reliably without Telegram API conflicts.
