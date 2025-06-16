---
applyTo: "**.py"
---

# Cosmos DB FastAPI Inventory API - Development Guidelines

## Core Requirements
- Use Python 3.11+ with complete type annotations for all functions and methods
- Follow async/await patterns for all I/O operations without exception
- Import types from `typing` module when needed (List, Dict, Optional, etc.)

## Code Style & Documentation
- Include docstrings for all public functions with Args, Returns, and Raises sections
- Use descriptive variable names following snake_case convention
- Group imports: standard library, third-party, local imports (separated by blank lines)
- Maximum line length: 100 characters

## Azure Functions Integration
- Use Azure Functions v2 programming model with FastAPI integration pattern
- Mount FastAPI app to function_app as shown in function_app.py
- Configure logging through host.json settings
- Use environment variables from local.settings.json for configuration

## API Design Patterns
- Follow RESTful conventions for endpoint naming
- Separate routes for single vs batch operations (e.g., /products vs /products/batch)
- Use appropriate HTTP status codes:
  - 200: Successful GET/PUT
  - 201: Successful POST
  - 204: Successful DELETE
  - 404: Resource not found
  - 409: Conflict (e.g., ETag mismatch)
  - 422: Validation error

## Database Operations (Cosmos DB)
- Always use async ContainerProxy methods from azure.cosmos.aio
- Include partition key (category) in all database operations
- Implement optimistic concurrency control using ETags for updates
- Use handle_cosmos_error() helper from exceptions.py for error handling
- Follow existing query patterns in inventory_api/crud/product_queries.py

## Dependency Injection
- Use FastAPI's Depends() for database connections and other dependencies
- Follow the pattern: `async def get_container() -> ContainerProxy`
- Close connections properly using async context managers

## Error Handling
- Extend custom exceptions from inventory_api/exceptions.py base classes
- Always provide meaningful error messages in exceptions
- Log errors appropriately before raising exceptions
- Handle Cosmos DB specific errors (404, 409, 412) with appropriate HTTP responses

## Project File Organization
```
inventory_api/
├── models/      # Pydantic models with validation
├── routes/      # API endpoint handlers
├── crud/        # Database operations
├── db.py        # Database connection management
└── exceptions.py # Custom exception classes
```

## Model Validation
- Use Pydantic models for all request/response schemas
- Include field validators for business logic (e.g., positive quantities)
- Provide clear validation error messages
- Use Optional[] for nullable fields with appropriate defaults

## Testing & Development
- Run locally with: `func start` or VS Code task "func: host start"
- Access API documentation at: http://localhost:7071/docs
- Use debugpy for debugging (port 5678 configured)
- Test batch operations with appropriate payload sizes

## Performance Considerations
- Implement connection pooling for Cosmos DB client
- Use batch operations for bulk create/update/delete
- Configure appropriate timeouts in host.json
- Follow guidelines in .copilot-docs/azure-functions-python-performance-guide.md

## Security Requirements
- Validate API key in x-functions-key header for all endpoints
- Never log sensitive information (API keys, connection strings)
- Sanitize user inputs before database operations
- Use environment variables for all configuration values

## Before Adding Dependencies
- Check requirements.txt for existing packages
- Install new packages with: `uv pip install <package>`
- Update requirements.txt after adding dependencies
- Prefer built-in Python modules when possible

## Infrastructure Changes
- Review infra/main.bicep for resource naming conventions
- Update azure.yaml if adding new Azure resources
- Document new environment variables in README.md
- Follow existing Bicep module patterns in infra/core/

## Common Patterns to Follow
- Single item operation: `inventory_api/routes/product_route.py`
- Batch operations: `inventory_api/routes/product_route_batch.py`
- CRUD operations: `inventory_api/crud/product_crud.py`
- Query operations: `inventory_api/crud/product_queries.py`
- Exception handling: `inventory_api/exceptions.py`

## Response Examples
Always match existing response formats:
```python
# Single item response
{"id": "...", "name": "...", "category": "...", "_etag": "..."}

# List response
{"items": [...], "total_count": 10}

# Error response
{"detail": "Error message here"}
```