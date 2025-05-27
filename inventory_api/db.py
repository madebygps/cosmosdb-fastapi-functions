from typing import Optional, Dict
from azure.cosmos.aio import CosmosClient, ContainerProxy
from azure.identity.aio import DefaultAzureCredential
import os
import logging
from enum import Enum


logger = logging.getLogger(__name__)


class ContainerType(str, Enum):
    PRODUCTS = "products"


_client: Optional[CosmosClient] = None
_credential: Optional[DefaultAzureCredential] = None
_containers: Dict[str, ContainerProxy] = {}

try:
    COSMOSDB_ENDPOINT = os.environ["COSMOSDB_ENDPOINT"]
    DATABASE_NAME = os.environ["COSMOSDB_DATABASE"]
    CONTAINERS = {
        "products": os.environ["COSMOSDB_CONTAINER_PRODUCTS"],
    }

    logger.info(
        "Cosmos DB configuration loaded successfully",
        extra={
            "cosmosdb_endpoint": COSMOSDB_ENDPOINT,
            "database_name": DATABASE_NAME,
            "containers": list(CONTAINERS.keys()),
        },
    )
except KeyError as e:
    logger.error(
        f"Missing required environment variable: {e}",
        extra={
            "missing_variable": str(e),
            "available_vars": [
                k for k in os.environ.keys() if k.startswith("COSMOSDB")
            ],
        },
    )
    raise RuntimeError(f"Missing required environment variable: {e}") from e


async def _ensure_client() -> CosmosClient:
    """
    Ensures a single CosmosClient instance exists for the lifetime of the application.
    Implements best practices from Azure documentation.
    """
    global _client, _credential
    if _client is None:
        try:
            logger.info("Initializing Cosmos DB client with DefaultAzureCredential")
            _credential = DefaultAzureCredential()

            client_options = {
                "connection_timeout": 60, 
            }

            _client = CosmosClient(COSMOSDB_ENDPOINT, _credential, **client_options)

            logger.info(
                "Cosmos DB client initialized successfully",
                extra={
                    "endpoint": COSMOSDB_ENDPOINT,
                    "auth_method": "DefaultAzureCredential",
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Cosmos DB client: {e}",
                extra={"error_type": type(e).__name__, "endpoint": COSMOSDB_ENDPOINT},
                exc_info=True,
            )
            raise
    return _client


async def get_container(container_type: ContainerType) -> ContainerProxy:
    """
    Gets a container proxy, creating it if necessary.
    Maintains a cache of container proxies for performance.
    """
    container_name = CONTAINERS.get(container_type)
    if not container_name:
        logger.error(
            f"Container type '{container_type}' not configured",
            extra={
                "requested_container": container_type,
                "available_containers": list(CONTAINERS.keys()),
            },
        )
        raise ValueError(
            f"Container '{container_type}' not configured. "
            f"Valid options: {list(CONTAINERS.keys())}"
        )

    if container_name not in _containers:
        logger.info(
            f"Creating container client for: {container_name}",
            extra={"container_name": container_name, "database_name": DATABASE_NAME},
        )
        client = await _ensure_client()
        database = client.get_database_client(DATABASE_NAME)
        _containers[container_name] = database.get_container_client(container_name)
        logger.info(
            f"Container client created successfully for: {container_name}",
            extra={
                "container_name": container_name,
                "database_name": DATABASE_NAME,
                "cached_containers": list(_containers.keys()),
            },
        )

    return _containers[container_name]
