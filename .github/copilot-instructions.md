# Copilot Instructions

Use Python 3.11+ with type annotations for all functions.
Implement Azure Functions with FastAPI and ASGI patterns.
Connect to Azure Cosmos DB using async operations.
Install packages using `uv pip install` commands.
Write maintainable, well-documented, and testable code.

Run Azure Functions locally with `func start`.
Install all dependencies with `uv pip install -r requirements.txt`.
Add new packages with `uv pip install <package_name>`.

Check dependencies before suggesting packages in #requirements.txt.
Follow configuration patterns from #local.settings.json and #host.json.
Maintain consistency with application structure in #function_app.py.
Use existing data models from #inventory_api/models/.
Follow CRUD patterns from #inventory_api/crud/.
Match API route structure from #inventory_api/routes/.