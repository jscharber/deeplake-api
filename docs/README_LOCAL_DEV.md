# Tributary AI services for DeepLake - Local Development Guide

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Run the automated setup script
./run_local.sh
```

### Option 2: Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-local.txt

# Run the service
python local_dev_config.py
```

### Option 3: Debug Mode (For 500 Error Investigation)
```bash
# Run with enhanced debugging
python debug_run.py
```

## 🐛 Debugging the 500 Error

### Current Issue
- Vectors are successfully inserted into the database
- HTTP endpoint returns 500 error during response serialization
- Backend logs show: `"inserted": 1, "skipped": 0, "failed": 0`

### Debug Steps

1. **Run in debug mode:**
   ```bash
   python debug_run.py
   ```

2. **Test vector insertion:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/datasets/test/vectors/ \
     -H "Authorization: ApiKey dev-12345-abcdef-67890-ghijkl" \
     -H "Content-Type: application/json" \
     -d '{"document_id": "test", "values": [1.0, 0.0, 0.0]}'
   ```

3. **Check debug output in console and `debug.log`**

### Suspected Issues

1. **Response Serialization:** `VectorBatchResponse` object not JSON serializable
2. **Field Types:** One of these fields might be problematic:
   - `result.error_messages` (could be non-serializable object)
   - `result.processing_time_ms` (could be NaN/infinity)
3. **Middleware Issues:** FastAPI middleware causing issues

### Debugging Tools Available

- **Enhanced Logging:** All function calls logged
- **Exception Tracing:** Full stack traces in console
- **Function Patching:** Vector endpoint wrapped with debug info
- **Debug Log File:** `debug.log` for persistent logging

## 📁 Local Development Structure

```
deeplake-api/
├── app/                    # Application code
├── local_data/            # Local vector storage
├── debug_data/            # Debug mode storage  
├── logs/                  # Application logs
├── debug.log              # Debug session log
├── venv/                  # Virtual environment
├── run_local.sh           # Automated setup
├── local_dev_config.py    # Manual setup
├── debug_run.py           # Debug mode
└── requirements-local.txt # Local dependencies
```

## 🔧 Configuration

### Environment Variables (Auto-set)
```bash
DEEPLAKE_STORAGE_LOCATION=./local_data/vectors
CACHE_ENABLED=false
LOG_LEVEL=DEBUG
DEBUG=true
WORKERS=1
METRICS_ENABLED=false
```

### API Endpoints
- Health: `http://localhost:8000/api/v1/health`
- Datasets: `http://localhost:8000/api/v1/datasets/`
- Vectors: `http://localhost:8000/api/v1/datasets/{id}/vectors/`
- Docs: `http://localhost:8000/docs`

### Test API Key
```
Authorization: ApiKey dev-12345-abcdef-67890-ghijkl
```

## 🎯 Next Steps for 500 Error

1. Run `python debug_run.py`
2. Test vector insertion with curl command above
3. Look for the exact line where serialization fails
4. Check if `result.error_messages` is a list of strings or some other object
5. Verify all response fields are JSON-serializable primitives

The debug output will show exactly where the 500 error occurs! 🔍