# Inventory CosmosDB Fast Functions

## What This Does

This is an inventory management API that lets you:

- Create, read, update, and delete products
- Perform batch operations on multiple products at once
- Query products by category
- Access API documentation via Swagger UI

## Prerequisites

- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- [Python 3.11+](https://www.python.org/downloads/)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)

## Getting Started

### 1. Configure Azure CLI Authentication

Make sure you're logged into Azure CLI before deploying the project:

```bash
# Login to Azure CLI
az login

# Verify you're using the correct account
az account show
```

### 2. Deploy to Azure

After authenticating, deploy the application to Azure to generate the necessary environment configuration:

```bash
# Deploy to Azure (this will create the .azure folder with environment settings)
azd up
```

### 3. Configure Cosmos DB Access

You need to grant your user account access to the Cosmos DB instance. Update the script with your actual values:

```bash
# Update the values in cosmosdb_access.sh with your account name and resource group
# Then run:
chmod +x cosmosdb_access.sh
./cosmosdb_access.sh
```

The script assigns the Cosmos DB Data Contributor role to your user principal:

```bash
az cosmosdb sql role assignment create \
  --account-name YOUR_COSMOSDB_ACCOUNT_NAME \
  --resource-group YOUR_RESOURCE_GROUP_NAME \
  --scope "/" \
  --principal-id $(az ad signed-in-user show --query id -o tsv) \
  --role-definition-id "00000000-0000-0000-0000-000000000002"
```

### 4. Configure Local Settings

After deployment, copy the environment values from the Azure deployment:

1. Navigate to `.azure/[environment-name]/.env`
2. Copy the required values to your `local.settings.json`

Your `local.settings.json` should include:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOSDB_ENDPOINT": "https://yourcosmosdbaccount.documents.azure.com:443/",
    "COSMOSDB_DATABASE": "inventory",
    "COSMOSDB_CONTAINER_PRODUCTS": "products",
    "APPLICATIONINSIGHTS_CONNECTION_STRING": ""
  }
}
```

**Required Environment Variables:**

| Variable | Description |
|----------|-------------|
| `COSMOSDB_ENDPOINT` | Your Cosmos DB endpoint URL (copy from `.azure/[environment-name]/.env`) |
| `COSMOSDB_DATABASE` | The name of your Cosmos DB database |
| `COSMOSDB_CONTAINER_PRODUCTS` | The name of your Cosmos DB container for products |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Your Application Insights connection string (optional) |

### 5. Run Locally

Install required Python packages:

- Start a virtual environment (optional but recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use .venv\Scripts\activate
pip install -r requirements.txt
```

Start the function app:

```bash
func start
```

Access the API documentation:
Navigate to [http://localhost:7071/docs?code=apikey](http://localhost:7071/docs?code=apikey)

Click on the **Authorize** button and enter the `apikey` as the value. Locally an actual API key is not required, but it is needed for the deployed version.


## Accessing the Deployed API

Once the application is deployed to Azure, you can access the API endpoints directly from the Azure portal or using tools like Postman or curl.

You can also access the swagger UI for the deployed function app at:

```plaintext
https://<your-function-app-name>.azurewebsites.net/api/docs?code=apikey
```

> **Note**:  
> - Replace `<your-function-app-name>` with the name of your Azure Function App.
> - Replace `apikey` with the actual API key which is the function key for the deployed function that you can find in the Azure portal.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Cosmos DB Access Issues** | Ensure you're logged into Azure CLI with the correct account and have run the `cosmosdb_access.sh` script |
| **Missing Environment Variables** | Check that you've copied all required values from `.azure/[environment-name]/.env` to `local.settings.json` |

## API Endpoints

### Product Operations

#### List Products by Category

```bash
GET /products/?category=electronics&page=1&size=10
```

#### Get Single Product

```bash
GET /products/{product_id}
```

#### Create Product

```bash
POST /products/
{
  "name": "Laptop",
  "category": "electronics",
  "price": 999.99,
  "sku": "LAP-001",
  "quantity": 10,
  "description": "High-performance laptop",
  "status": "active"
}
```

#### Update Product

```bash
PATCH /products/{product_id}
Headers: If-Match: {etag}
{
  "price": 899.99,
  "quantity": 15
}
```

#### Delete Product

```bash
DELETE /products/{product_id}
```

#### List Categories

```bash
GET /products/categories
```

### Batch Operations

#### Create Multiple Products

```bash
POST /products/batch/
[
  {
    "name": "Product 1",
    "category": "electronics",
    "price": 100.00,
    "sku": "PROD-001",
    "quantity": 5
  },
  {
    "name": "Product 2",
    "category": "electronics",
    "price": 200.00,
    "sku": "PROD-002",
    "quantity": 3
  }
]
```

#### Update Multiple Products

```bash
PATCH /products/batch/
[
  {
    "id": "product-id-1",
    "_etag": "etag-value-1",
    "price": 150.00
  },
  {
    "id": "product-id-2",
    "_etag": "etag-value-2",
    "quantity": 10
  }
]
```

#### Delete Multiple Products

```bash
DELETE /products/batch/
["product-id-1", "product-id-2", "product-id-3"]
```

## Authentication

### Local Development

When running locally, use any value for the API key:

```bash
curl http://localhost:7071/products/?code=anyvalue
```

### Production

In production, you need the actual function key from Azure Portal:

1. Go to your Function App in Azure Portal
2. Navigate to "Functions" → "App keys"
3. Copy the default host key or create a function-specific key
4. Use it in your requests:

```bash
curl https://your-app.azurewebsites.net/api/products/?code=your-actual-key
```

Or in headers:

```bash
curl https://your-app.azurewebsites.net/api/products/ \
  -H "x-functions-key: your-actual-key"
```

### Cosmos DB Authentication

The application uses Azure AD authentication to connect to Cosmos DB. Your user account needs the "Cosmos DB Data Contributor" role, which is assigned using the provided script.
