az cosmosdb sql role assignment create \
  --account-name gpscosinv-v6ia2h3rwllw2-cosmos \
  --resource-group gpscosinv-v6ia2h3rwllw2-rg \
  --scope "/" \
  --principal-id $(az ad signed-in-user show --query id -o tsv) \
  --role-definition-id "00000000-0000-0000-0000-000000000002"