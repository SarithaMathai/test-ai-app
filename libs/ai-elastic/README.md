# ai-elastic

Elasticsearch client for the AI monorepo. Built on `elasticsearch-py`, configured via `ai-core` Settings.

## Usage

```python
from ai_elastic import ElasticsearchClient

es = ElasticsearchClient.from_settings(settings)
hits = es.search("my-index", {"match": {"field": "value"}})
es.index_document("my-index", {"key": "val"}, doc_id="abc123")
```

## Configuration

```yaml
# config/base.yaml
elasticsearch:
  url: "http://localhost:9200"
  username: "elastic"
  verify_certs: true
```

Set `ELASTICSEARCH__PASSWORD` as an env var — never in YAML.
