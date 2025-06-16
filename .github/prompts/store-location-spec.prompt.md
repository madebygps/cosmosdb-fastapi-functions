---
mode: 'agent'
tools: ['codebase']
description: 'Create store location API with CRUD operations, batch processing, and geospatial search'
---

# Store Location API Implementation

Create a complete store location management system for the inventory API, following existing patterns for products.

## Core Requirements

**Partition Strategy**: Use region-based partitioning (e.g., "north-america", "europe", "asia-pacific")
**Database**: Store locations in new Cosmos DB container with region as partition key
**API Pattern**: Match existing product endpoints structure with single and batch operations

## Data Model

### Store Location Fields
```python
{
    "id": "uuid",                    # Auto-generated
    "name": "Store Name",            # Required, 1-255 chars
    "store_number": "ST-001",        # Unique, pattern: ^[A-Z0-9-]+$
    "region": "north-america",       # Partition key (normalized)
    "address": {
        "street": "123 Main St",
        "city": "Seattle",
        "state": "WA",
        "postal_code": "98101",
        "country": "USA"
    },
    "coordinates": {
        "latitude": 47.6062,         # Range: -90 to 90
        "longitude": -122.3321       # Range: -180 to 180
    },
    "operating_hours": {
        "monday": {"open_time": "09:00", "close_time": "21:00", "is_closed": false},
        "tuesday": {"open_time": "09:00", "close_time": "21:00", "is_closed": false},
        # ... other days default to is_closed=true
    },
    "status": "ACTIVE",              # Enum: ACTIVE, INACTIVE, CLOSED
    "phone": "+1-206-555-0100",     # Optional
    "email": "store001@example.com", # Optional
    "manager_name": "John Doe"       # Optional
}
```

## Implementation Tasks

### 1. Create Models - `inventory_api/models/store_location.py`

Define Pydantic models following the pattern in inventory_api/models/product.py:
- `StoreLocation` - Base model with all fields
- `StoreLocationCreate` - For POST requests
- `StoreLocationUpdate` - For PUT requests (all fields optional)
- `StoreLocationResponse` - With _etag and timestamps
- `StoreLocationIdentifier` - For lookups (id + region)
- `VersionedStoreLocationIdentifier` - With _etag for updates
- Batch operation models (Create, Update, Delete)
- `NearbySearchRequest` - For proximity search

**Validation Requirements**:
- Coordinates must be within valid ranges
- Operating hours: open_time < close_time when not closed
- Default all days to is_closed=true to avoid validation errors
- Store numbers must match pattern

### 2. Create CRUD Operations - `inventory_api/crud/store_location_crud.py`

Follow patterns from inventory_api/crud/product_crud.py:
- Use async ContainerProxy operations
- Include region as partition key in all operations
- Use patch_item for updates (not replace_item)
- Handle ETags for optimistic concurrency
- Use handle_cosmos_error() for all exceptions

### 3. Create Query Operations - `inventory_api/crud/store_location_queries.py`

Follow patterns from inventory_api/crud/product_queries.py:
- `list_store_locations(region, limit, offset)` - Paginated listing
- `list_regions()` - Get all unique regions
- `search_nearby_store_locations(coordinates, max_distance_km)` - Geospatial search

For proximity search, implement Haversine distance calculation.

### 4. Create Batch Operations - `inventory_api/crud/store_location_crud_batch.py`

Follow patterns from inventory_api/crud/product_crud_batch.py:
- Use execute_item_batch (not execute_batch)
- Group operations by region for concurrent processing
- Use handle_batch_operation_error() with proper parameters

### 5. Create API Routes - `inventory_api/routes/store_location_route.py`

Single operation endpoints:
- `GET /store-locations/regions` - List all regions
- `GET /store-locations/?region={region}` - List by region (paginated)
- `POST /store-locations/` - Create new store
- `GET /store-locations/{id}?region={region}` - Get by ID
- `PUT /store-locations/{id}?region={region}` - Update with ETag
- `DELETE /store-locations/{id}?region={region}` - Delete
- `POST /store-locations/search/nearby` - Find stores within radius

### 6. Create Batch Routes - `inventory_api/routes/store_location_route_batch.py`

Batch endpoints following product patterns:
- `POST /store-locations/batch/create`
- `PUT /store-locations/batch/update`
- `DELETE /store-locations/batch/delete`

### 7. Update Database Configuration

In inventory_api/db.py:
- Add `STORE_LOCATIONS = "store_locations"` to ContainerType enum
- Add to CONTAINERS dict with environment variable support:
  ```python
  ContainerType.STORE_LOCATIONS: os.environ.get("STORE_LOCATIONS_CONTAINER_NAME", "store_locations")
  ```

### 8. Add Custom Exceptions

In inventory_api/exceptions.py, add:
- `StoreLocationNotFoundError(ApplicationError)` - 404
- `InvalidStoreLocationError(ApplicationError)` - 400
- `DuplicateStoreLocationError(ApplicationError)` - 409
- `StoreLocationAlreadyExistsError(ApplicationError)` - 409

### 9. Register Routes

In function_app.py:
- Import both route modules
- Add `app.include_router(store_location_route.router)`
- Add `app.include_router(store_location_route_batch.router)`

## Validation Checklist

Before completing:
- [ ] All models can be imported without environment dependencies
- [ ] Operating hours validation works with default closed days
- [ ] Coordinate validation enforces proper ranges
- [ ] Batch operations use execute_item_batch
- [ ] All CRUD operations include region parameter
- [ ] Proximity search returns distances in kilometers
- [ ] Routes are registered in function_app.py
- [ ] No circular imports or lint errors

## Common Pitfalls to Avoid

1. Don't create OperatingHours() with defaults that fail validation
2. Always use execute_item_batch for batch operations, not execute_batch
3. Use patch_item with ETags for updates, not replace_item
4. Include region in all database operations as partition key
5. Follow exact error handling patterns from existing CRUD files