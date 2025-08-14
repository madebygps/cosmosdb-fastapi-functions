---
mode: agent
---
I need to refactor the CRUD layer. Look at all the files in the #crud directory, understand how they work, understand how they work with the files in the #routes directory, and in the #models directory, and with the #exceptions.py. 

In the #crud directory we have #product_crud.py and #product_batch_crud.py. In these files you will find a mix of code that implements functionality that should remain in this crud layer and functionality/code that should be moved to a new service directory and respective service files product_service.py and product_batch_service.py.

In our #product_crud.py and #product_batch_crud.py files, we want only the code that directly interacts with the database to remain. Any other type of helper functionality and/or business logic should be moved to the service layer. 

Keep in mind any issues that you can see in the #problems area and address them before you consider that refactoring done.
