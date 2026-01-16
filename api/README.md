# API Module - NYC Data Client

## Overview

This module provides a production-grade client for accessing NYC Open Data APIs with comprehensive resilience features.

## Files

- `nyc_data_client.py` - Main client implementation with all resilience features
- `__init__.py` - Module initialization, exports public API

## Quick Start

```python
import asyncio
from api import NYCDataClient

async def main():
    async with NYCDataClient(app_token="your_token") as client:
        violations = await client.get_dob_violations("1012650001")
        print(f"Found {len(violations)} violations")

asyncio.run(main())
```

## Documentation

See [NYC_DATA_CLIENT.md](../docs/NYC_DATA_CLIENT.md) for comprehensive documentation including:
- Feature overview
- API reference
- Configuration options
- Error handling
- Monitoring and metrics
- Best practices
- Troubleshooting

## Examples

See `../example_nyc_data_client.py` for detailed usage examples.

## Testing

```bash
pytest ../test_nyc_data_client.py -v
```

## Key Features

✅ Async HTTP with connection pooling (max 50 connections)  
✅ Circuit breaker for fault tolerance  
✅ Rate limiting (token bucket algorithm)  
✅ Multi-layer caching (LRU + Redis)  
✅ Exponential backoff retry with jitter  
✅ Request timeout handling (30s)  
✅ Automatic failover to cached data  
✅ Structured logging  
✅ Prometheus metrics  
✅ Health check endpoint  
✅ Type hints and docstrings  

## Dependencies

- `aiohttp>=3.9.0` - Async HTTP client
- `tenacity>=8.2.0` - Retry logic
- `redis>=5.0.0` - Optional distributed caching
- `prometheus-client>=0.19.0` - Metrics
- `circuitbreaker>=1.4.0` - Circuit breaker
- `cachetools>=5.3.0` - LRU cache
