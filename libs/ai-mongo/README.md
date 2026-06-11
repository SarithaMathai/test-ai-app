# ai-mongo

Shared MongoDB client for PLM AI apps. Provides Motor (async) and PyMongo (sync) clients wrapped in a `MongoClientManager`.

Install only in apps that need MongoDB — other apps do not pay the dependency cost.

## Usage

```python
from ai_core.config import get_settings
from ai_mongo import MongoClientManager

settings = get_settings()
mongo = MongoClientManager(settings.mongo)

# Async
db = mongo.get_db()
docs = await db["my_collection"].find({}).to_list(100)

# Sync (CLI scripts, ingestion)
sync_db = mongo.get_sync_db()
docs = list(sync_db["my_collection"].find({}))
```
