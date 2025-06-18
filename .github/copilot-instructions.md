---
applyTo: "**.py"
---

# CONTEXT: This is an Azure Functions Consumption Plan + FastAPI + Python project
**Always assume Azure Functions Consumption Plan constraints unless explicitly told otherwise.**

## Azure Functions Requirements
- **Process Reuse**: Module-level initialization for required shared resources (clients, credentials, config)
- **Stateless Design**: No persistent state between invocations
- **Resource Optimization**: Simple caching patterns, avoid complex lazy initialization
- **Memory/Timeout Limits**: Efficient resource usage, operations complete within 5 minutes

## Code Standards
- **Type Safety**: Complete type annotations, all functions `async def` with `await`
- **FastAPI**: `APIRouter`, `Depends()` injection, explicit `status_code`/`response_model`
- **Error Handling**: Custom exceptions, structured logging with `extra=context`
- **Data Models**: Pydantic with `Field()` validation, separate Create/Update/Response models

## Client Initialization Pattern
- **EAGER (module-level)**: Required clients (CosmosClient, auth, config validation)
- **SIMPLE CACHING**: Lightweight resources using module-level dicts
- **Rule**: If required for app → module-level, if optional → simple on-demand caching
- **Avoid**: `global` keyword patterns, complex lazy initialization functions

## Azure Tools (MANDATORY)
- When ANY Azure question/code: ALWAYS use `microsoft_docs_search` tool first