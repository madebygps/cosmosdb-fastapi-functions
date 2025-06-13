# Azure Functions Python Performance Optimization Guide

FROM: https://learn.microsoft.com/en-us/azure/azure-functions/python-scale-performance-reference

## Overview

This guide covers optimizing Python applications in Azure Functions for better throughput and performance.

## Key Performance Factors

- **Horizontal scaling**: Automatic scaling based on workload
- **Throughput performance**: Configuration optimizations

## Workload Types

### I/O-Bound Applications

- Handle many concurrent invocations
- Process large numbers of I/O events (network calls, disk operations)
- **Examples**: Web APIs

### CPU-Bound Applications  

- Perform long-running computations (image resizing)
- Handle data transformation tasks
- **Examples**: Data processing, Machine learning inference

## Performance Optimization Strategies

### 1. Async Programming

**For I/O-bound apps**, use async functions:

```python
import aiohttp
import azure.functions as func

async def main(req: func.HttpRequest) -> func.HttpResponse:
    async with aiohttp.ClientSession() as client:
        async with client.get("YOUR_URL") as response:
            return func.HttpResponse(await response.text())
```

**Key Points:**

- Python is single-threaded by default
- Async functions run with asyncio
- Sync functions run in ThreadPoolExecutor
- Use async-compatible libraries (aiohttp, pyzmq, etc.)

### 2. Multiple Language Worker Processes

**Configuration**: `FUNCTIONS_WORKER_PROCESS_COUNT` (max 10)

**Guidelines:**

- **CPU-bound**: Set equal to or higher than CPU cores
- **I/O-bound**: Can exceed CPU cores
- **Warning**: Too many workers can hurt performance due to context switching

### 3. Thread Pool Configuration

**Configuration**: `PYTHON_THREADPOOL_THREAD_COUNT`

**Recommendations:**
- **CPU-bound**: Start with 1, increase gradually
- **I/O-bound**: Start with (CPU cores + 4)
- **Mixed workloads**: Balance both worker processes and thread count

### 4. Event Loop Management

For non-async libraries, wrap synchronous calls:

```python
import asyncio
from requests import get

async def invoke_get_request(eventloop: asyncio.AbstractEventLoop):
    result = await eventloop.run_in_executor(None, get, 'URL')
    return result

async def main(req: func.HttpRequest):
    eventloop = asyncio.get_event_loop()
    tasks = [asyncio.create_task(invoke_get_request(eventloop)) 
             for _ in range(10)]
    done_tasks, _ = await asyncio.wait(tasks)
    return func.HttpResponse("Complete")
```

### 5. Vertical Scaling

- Upgrade to premium plans for CPU-bound operations
- Higher processing units enable better parallelism
- Adjust worker processes based on available cores

## Configuration Summary

| Setting | Purpose | CPU-Bound | I/O-Bound |
|---------|---------|-----------|-----------|
| `FUNCTIONS_WORKER_PROCESS_COUNT` | Worker processes per host | = CPU cores | > CPU cores |
| `PYTHON_THREADPOOL_THREAD_COUNT` | Threads per worker | Start with 1 | CPU cores + 4 |
| Async functions | Concurrency model | Less beneficial | Highly beneficial |

## Best Practices

1. **Profile your application** under realistic production loads
2. **Use async libraries** when available (aiohttp, pyzmq)
3. **Avoid blocking operations** in async functions
4. **Monitor and adjust** configurations based on performance metrics
5. **Consider workload mixing** - most real-world apps are mixed I/O/CPU bound

## Important Notes

- Async functions without `await` will severely impact performance
- Default configurations work for most applications
- Always test configuration changes under load
- Consider trigger-specific optimizations for non-HTTP functions