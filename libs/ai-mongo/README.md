# ai-mongo

MongoDB client for the AI monorepo. Built on `pymongo`, configured via `ai-core` Settings.

## Usage

```python
from ai_mongo import MongoClient

mongo = MongoClient.from_settings(settings)
col = mongo.collection("records")
doc = col.find_one({"_id": "abc"})
```

## Configuration

Set `MONGO__URL` to your MongoDB connection string. Embed credentials directly:

```
# Local dev (no auth)
MONGO__URL=mongodb://localhost:27017

# Authenticated
MONGO__URL=mongodb://user:pass@host:27017/mydb

# Atlas / SRV
MONGO__URL=mongodb+srv://user:pass@cluster.mongodb.net/mydb
```
