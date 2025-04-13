# WebCrawlerAPI LangChain Integration

[WebcrawlerAPI](https://webcrawlerapi.com/) - is a website to LLM data API. It allows to convert websites and webpages markdown or cleaned content. 

**No subscription required**.

This package provides LangChain integration for [WebCrawlerAPI](https://webcrawlerapi.com/), allowing you to easily use web crawling capabilities with [LangChain](https://www.langchain.com/) document processing pipeline.

## Installation

Get your [API key](https://webcrawlerapi.com/docs/access-key) first

```bash
pip install webcrawlerapi-langchain
```

## Usage

### Basic Loading
```python
from webcrawlerapi_langchain import WebCrawlerAPILoader

# Initialize the loader
loader = WebCrawlerAPILoader(
    url="https://example.com",
    api_key="your-api-key",
    scrape_type="markdown",
    items_limit=10
)

# Load documents
documents = loader.load()

# Use documents in your LangChain pipeline
for doc in documents:
    print(doc.page_content[:100])
    print(doc.metadata)
```

### Async Loading
```python
# Async loading
documents = await loader.aload()
```

### Lazy Loading
```python
# Lazy loading
for doc in loader.lazy_load():
    print(doc.page_content[:100])
```

### Async Lazy Loading
```python
# Async lazy loading
async for doc in loader.alazy_load():
    print(doc.page_content[:100])
```

## Configuration

The loader accepts the following parameters:

- `url`: The URL to crawl
- `api_key`: Your WebCrawlerAPI API key
- `scrape_type`: Type of scraping (html, cleaned, markdown)
- `items_limit`: Maximum number of pages to crawl
- `whitelist_regexp`: Regex pattern for URL whitelist
- `blacklist_regexp`: Regex pattern for URL blacklist

### Links
- [WebCrawlerAPI Python SDK](https://github.com/WebCrawlerAPI/webcrawlerapi-python-sdk)
- [WebCrawlerAPI Documentation](https://webcrawlerapi.com/docs/getting-started)
- [WebCrawlerAPI API Reference](https://webcrawlerapi.com/docs/api-reference)

If you need help with integration feel free to [contact us](support@webcrawlerapi.com).

## License

MIT License 