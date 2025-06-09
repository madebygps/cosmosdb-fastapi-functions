# Inventory CosmosDB Fast Functions

This is an inventory management API that lets you:

- Create, read, update, and delete products
- Perform batch operations on multiple products at once
- Query products by category
- Access API documentation via Swagger UI

## Tech stack

- **Azure Functions on Flex Consumption**: Serverless compute service for running the API
- **Cosmos DB**: NoSQL database for storing product data. Serverless offering.
- **FastAPI**: Web framework for building APIs with Python

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

### 3. Access and Populate the Deployed API

You can also access the swagger UI for the deployed function app at:

```plaintext
https://<your-function-app-name>.azurewebsites.net/api/docs?code=apikey
```

- Replace `<your-function-app-name>` with the name of your Azure Function App.
- Replace `apikey` with the actual API key which is the function key for the deployed function that you can find in the Azure portal.
- Once the API is deployed, copy the items from `sample.json` and use the add products batch endpoint to populate your database.

## Running Locally

### 1. Configure Cosmos DB Access

You must deploy the application to Azure first to set up the Cosmos DB instance. After deployment, you can run the application locally.

You need to grant your user account access to the Cosmos DB instance. The `cosmosdb_access.sh` script assigns the Cosmos DB Data Contributor role to your user principal. Update the script with your actual values and run it:

```bash
chmod +x cosmosdb_access.sh
./cosmosdb_access.sh
```

### 2. Configure Local Settings

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
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Your Application Insights connection string |

### 3. Install Dependencies

Start a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use .venv\Scripts\activate
pip install -r requirements.txt
```

Start the function app:

```bash
func start
```

### 4. Access the Local API

Navigate to [http://localhost:7071/docs?code=apikey](http://localhost:7071/docs?code=apikey)

Click on the **Authorize** button and enter the `apikey` as the value. Locally an actual API key is not required, but it is needed for the deployed version.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Cosmos DB Access Issues** | Ensure you're logged into Azure CLI with the correct account and have run the `cosmosdb_access.sh` script |
| **Missing Environment Variables** | Check that you've copied all required values from `.azure/[environment-name]/.env` to `local.settings.json` |
