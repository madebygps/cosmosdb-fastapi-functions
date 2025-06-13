# Store Location Endpoint Specification

## Overview

Create a RESTful API endpoint for managing store locations with full CRUD operations, including models, database layer, and routing.

## Context

**Requirements**: Store location management system that tracks physical store information including address, coordinates, operating hours, and status

**Referenced files**:

- #inventory_api/models/product.py
- #inventory_api/crud/product_crud.py  
- #inventory_api/crud/product_queries.py
- #inventory_api/crud/product_crud_batch.py
- #inventory_api/routes/product_route.py
- #inventory_api/routes/product_route_batch.py
- #inventory_api/db.py
- #inventory_api/exceptions.py
- #function_app.py

**Constraints**:

- FOLLOW existing project patterns
- Cosmos DB as database with partition key strategy
- Maintain API consistency with existing endpoints
- Use region-based partitioning for scalability

## Success Criteria

- [ ] Store location model SUPPORTS all required fields (name, address, coordinates, hours)
- [ ] CRUD operations HANDLE CREATE, READ, UPDATE, DELETE with proper validation
- [ ] API routes FOLLOW RESTful conventions with appropriate status codes
- [ ] Geographic coordinates VALIDATED within valid ranges (-90 to 90 lat, -180 to 180 lon)
- [ ] Region-based partitioning IMPLEMENTED for scalability
- [ ] Error handling USES custom exceptions following ApplicationError patterns
- [ ] Batch operations SUPPORT bulk create, update, delete
- [ ] Proximity search IMPLEMENTED with geospatial calculations
- [ ] Models can be imported and validated without environment dependencies
- [ ] All routes registered in main application

## Data Model Requirements

### Core Fields

- **name**: Store location name (1-255 chars)
- **region**: Partition key for scalability (normalized)
- **store_number**: Unique identifier (alphanumeric with dashes)
- **address**: Full address with validation
- **coordinates**: Lat/lon with range validation
- **operating_hours**: Weekly schedule with time validation
- **status**: ACTIVE, INACTIVE, CLOSED enum
- **phone**: Optional phone number with format validation
- **email**: Optional email with validation
- **manager_name**: Optional manager name

### Validation Rules

- Coordinates must be within valid ranges
- Operating hours: open_time < close_time when not closed
- Store numbers must follow pattern: `^[A-Z0-9-]+$`
- Default operating hours should be "closed" to avoid validation errors

## Tasks

### Task 1: CREATE Store Location Models

CREATE `inventory_api/models/store_location.py`

**Requirements:**

- FOLLOW #inventory_api/models/product.py patterns
- INCLUDE: Address, Coordinates, OperatingHours, WeeklyHours models
- VALIDATE: coordinate ranges, operating hours consistency
- DEFAULT: WeeklyHours should default to closed (is_closed=True)
- SUPPORT: Batch operation models (Create, Update, Delete)
- ADD: NearbySearchRequest model for proximity search

**Key Models:**

- `StoreLocation` (base model)
- `StoreLocationCreate` (creation requests)
- `StoreLocationUpdate` (update requests with validation)
- `StoreLocationResponse` (API responses with system fields)
- `StoreLocationIdentifier` (for lookups)
- `VersionedStoreLocationIdentifier` (with ETag)
- Batch operation models
- `NearbySearchRequest` (for proximity search)

### Task 2: IMPLEMENT CRUD Layer

CREATE `inventory_api/crud/store_location_crud.py`

**Requirements:**

- FOLLOW #inventory_api/crud/product_crud.py patterns exactly
- PARTITION-KEY: region (normalized using normalize_category)
- USE: patch_item for updates (not replace_item)
- HANDLE: optimistic concurrency with ETag headers
- ERROR-HANDLING: Use handle_cosmos_error for consistency

**Functions:**

- `create_store_location`
- `get_store_location_by_id`
- `update_store_location`
- `delete_store_location`

CREATE `inventory_api/crud/store_location_queries.py`

**Requirements:**

- FOLLOW #inventory_api/crud/product_queries.py patterns
- IMPLEMENT: paginated listing by region
- ADD: proximity search with Haversine distance calculation
- HANDLE: async iteration patterns correctly
- ERROR-HANDLING: Use handle_cosmos_error

**Functions:**

- `list_store_locations`
- `list_regions`
- `search_nearby_store_locations`

CREATE `inventory_api/crud/store_location_crud_batch.py`

**Requirements:**

- FOLLOW #inventory_api/crud/product_crud_batch.py patterns exactly
- USE: execute_item_batch (not execute_batch)
- HANDLE: concurrent processing by region
- ERROR-HANDLING: Use handle_batch_operation_error with proper parameters

**Functions:**

- `batch_create_store_locations`
- `batch_update_store_locations`
- `batch_delete_store_locations`

### Task 3: CREATE API Routes

CREATE `inventory_api/routes/store_location_route.py`

**Requirements:**

- FOLLOW #inventory_api/routes/product_route.py patterns
- REQUIRE: region query parameter for all operations
- ADD: /search/nearby endpoint for proximity search
- USE: proper HTTP status codes and response models
- HANDLE: ETag headers for updates (_etag field mapping)

**Endpoints:**

- `GET /store-locations/regions` - List all regions
- `GET /store-locations/` - List by region (paginated)
- `POST /store-locations/` - Create new store location
- `GET /store-locations/{id}` - Get by ID and region
- `PUT /store-locations/{id}` - Update with ETag
- `DELETE /store-locations/{id}` - Delete by ID and region
- `POST /store-locations/search/nearby` - Proximity search

CREATE `inventory_api/routes/store_location_route_batch.py`

**Requirements:**

- FOLLOW #inventory_api/routes/product_route_batch.py patterns
- SUPPORT: bulk operations endpoints
- USE: proper HTTP status codes for batch operations

**Endpoints:**

- `POST /store-locations/batch/create`
- `PUT /store-locations/batch/update`
- `DELETE /store-locations/batch/delete`

### Task 4: UPDATE Configuration

MODIFY `inventory_api/db.py`

**Requirements:**

- ADD: `STORE_LOCATIONS = "store_locations"` to ContainerType enum
- ADD: container configuration with environment variable support
- USE: `os.environ.get("STORE_LOCATIONS_CONTAINER_NAME", "store_locations")`

**Note:** Environment variable should be documented but not required for basic functionality

### Task 5: ADD Exception Types

MODIFY `inventory_api/exceptions.py`

**Requirements:**

- ADD: Store location specific exceptions
- FOLLOW: existing ApplicationError patterns exactly
- USE: appropriate HTTP status codes

**Exceptions to Add:**

- `StoreLocationNotFoundError` (404)
- `InvalidStoreLocationError` (400)
- `DuplicateStoreLocationError` (409)
- `StoreLocationAlreadyExistsError` (409)

### Task 6: REGISTER Routes

MODIFY `function_app.py`

**Requirements:**

- IMPORT: both route modules
- REGISTER: store_location_route.router
- REGISTER: store_location_route_batch.router
- MAINTAIN: existing import and registration patterns

## Testing Requirements

### Model Testing

- [ ] Models can be imported without environment dependencies
- [ ] Basic store location creation and validation works
- [ ] Operating hours validation works correctly
- [ ] Coordinate validation enforces proper ranges
- [ ] Nearby search request validation works

### Integration Testing

- [ ] All components can be imported successfully
- [ ] No circular import issues
- [ ] No lint errors in implementation
- [ ] Routes are properly registered

## Common Implementation Pitfalls

1. **Model Defaults**: Don't create OperatingHours() defaults that fail validation
2. **Batch Operations**: Use execute_item_batch, not execute_batch
3. **Updates**: Use patch_item with proper ETag handling, not replace_item
4. **Pagination**: Follow async iteration patterns from product_queries.py
5. **Error Handling**: Use existing error handling functions with correct parameters
6. **Container Registration**: Remember to add to both enum and CONTAINERS dict
