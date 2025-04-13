from typing import Dict, Iterator, List, Optional, AsyncIterator, Any, Literal
import os
import json
import logging
from langchain_core.documents import Document
from langchain_core.utils import get_from_env
from langchain_core.document_loaders import BaseLoader
from webcrawlerapi import WebCrawlerAPI

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class WebCrawlerAPILoaderError(Exception):
    """Custom exception class for WebCrawlerAPILoader errors."""
    pass

class WebCrawlerAPILoader(BaseLoader):
    """WebCrawlerAPI document loader integration.

    This loader uses WebCrawlerAPI to crawl websites and convert them into LangChain Documents.
    Each crawled page becomes a Document with its content and metadata.

    Raises:
        WebCrawlerAPILoaderError: If there are issues with initialization or crawling
        ValueError: If required parameters are invalid
    """

    def __init__(
        self,
        url: str,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        version: str = "v1",
        scrape_type: Literal["html", "cleaned", "markdown"] = "markdown",
        items_limit: int = 10,
        allow_subdomains: bool = False,
        whitelist_regexp: Optional[str] = None,
        blacklist_regexp: Optional[str] = None,
        max_polls: int = 100
    ):
        """Initialize the WebCrawlerAPI document loader.

        Args:
            url: The URL to crawl
            api_key: Your WebCrawlerAPI API key. If not provided, will try to get from WEBCRAWLERAPI_API_KEY env var
            base_url: The base URL of the API. If not provided, will try to get from WEBCRAWLERAPI_BASE_URL env var
            version: API version to use (optional)
            scrape_type: Type of scraping (html, cleaned, markdown)
            items_limit: Maximum number of pages to crawl
            allow_subdomains: Whether to crawl subdomains
            whitelist_regexp: Regex pattern for URL whitelist
            blacklist_regexp: Regex pattern for URL blacklist
            max_polls: Maximum number of status checks before returning
        """
        if not url:
            raise ValueError("URL must be provided")

        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        if items_limit < 1:
            raise ValueError("items_limit must be greater than 0")

        if max_polls < 1:
            raise ValueError("max_polls must be greater than 0")

        if scrape_type not in ("html", "cleaned", "markdown"):
            raise ValueError(
                f"Invalid scrape_type '{scrape_type}'. "
                "Allowed: 'html', 'cleaned', 'markdown'."
            )

        # Get API key and base URL from env vars if not provided
        self.api_key = api_key or get_from_env("api_key", "WEBCRAWLERAPI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either through api_key parameter or WEBCRAWLERAPI_API_KEY environment variable")

        self.base_url = base_url or get_from_env(
            "base_url", 
            "WEBCRAWLERAPI_BASE_URL", 
            default="https://api.webcrawlerapi.com"
        )

        self.url = url
        self.version = version
        self.scrape_type = scrape_type
        self.items_limit = items_limit
        self.allow_subdomains = allow_subdomains
        self.whitelist_regexp = whitelist_regexp
        self.blacklist_regexp = blacklist_regexp
        self.max_polls = max_polls

        logger.debug(f"Initializing WebCrawlerAPILoader with URL: {url}, base_url: {self.base_url}")
        self.client = WebCrawlerAPI(
            api_key=self.api_key,
            base_url=self.base_url,
            version=version
        )

    def _create_document(self, item: Any) -> Optional[Document]:
        """Create a Document from a job item if it's valid.

        Args:
            item: Job item from the API response

        Returns:
            Document if item is valid and has content, None otherwise
        """
        try:
            logger.debug(f"Processing job item: {item}")
            if not (item.status == "done" and item.content):
                logger.debug(f"Skipping item - status: {item.status}, has_content: {bool(item.content)}")
                return None

            doc = Document(
                page_content=item.content,
                metadata={
                    "url": item.original_url,
                    "title": item.title,
                    "status_code": item.page_status_code,
                    "created_at": item.created_at,
                    "referred_url": item.referred_url,
                    "cost": item.cost
                }
            )
            logger.debug(f"Created document from item: {item.original_url}")
            return doc
        except AttributeError as e:
            logger.error(f"Failed to create document from item: {e}")
            raise WebCrawlerAPILoaderError(f"Invalid job item format: {str(e)}") from e

    def load(self) -> List[Document]:
        """Load data into Document objects.

        Returns:
            List of Document objects, one for each crawled page.

        Raises:
            WebCrawlerAPILoaderError: If there are issues with the crawling job or API response
            ValueError: If the response format is invalid
            json.JSONDecodeError: If the API response contains invalid JSON
        """
        logger.info(f"Starting crawl for URL: {self.url}")
        try:
            logger.debug("Making crawl request with params: "
                        f"scrape_type={self.scrape_type}, "
                        f"items_limit={self.items_limit}, "
                        f"allow_subdomains={self.allow_subdomains}")
            
            job = self.client.crawl(
                url=self.url,
                scrape_type=self.scrape_type,
                items_limit=self.items_limit,
                allow_subdomains=self.allow_subdomains,
                whitelist_regexp=self.whitelist_regexp,
                blacklist_regexp=self.blacklist_regexp,
                max_polls=self.max_polls
            )
            logger.debug(f"Received crawl response: {job}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in crawl response: {e}")
            raise WebCrawlerAPILoaderError(
                f"Failed to parse API response (invalid JSON at position {e.pos}): {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise WebCrawlerAPILoaderError(f"API request failed: {str(e)}") from e

        if job.status == "error":
            error_msg = getattr(job, 'error', 'Unknown error')
            logger.error(f"Crawl job failed with error: {error_msg}")
            raise WebCrawlerAPILoaderError(f"Crawling job failed: {error_msg}")

        documents = []
        logger.info(f"Processing {len(job.job_items)} job items")
        for item in job.job_items:
            try:
                doc = self._create_document(item)
                if doc:
                    documents.append(doc)
            except AttributeError as e:
                logger.error(f"Failed to process job item: {e}")
                raise WebCrawlerAPILoaderError(
                    f"Invalid job item format - missing required field: {str(e)}"
                ) from e

        logger.info(f"Successfully created {len(documents)} documents")
        return documents

    def lazy_load(self) -> Iterator[Document]:
        """A lazy loader for Documents.

        Yields:
            Document objects one at a time as they are crawled.

        Raises:
            WebCrawlerAPILoaderError: If there are issues with the crawling job or API response
            ValueError: If the response format is invalid
            json.JSONDecodeError: If the API response contains invalid JSON
        """
        logger.info(f"Starting async crawl for URL: {self.url}")
        try:
            logger.debug("Making async crawl request")
            response = self.client.crawl_async(
                url=self.url,
                scrape_type=self.scrape_type,
                items_limit=self.items_limit,
                allow_subdomains=self.allow_subdomains,
                whitelist_regexp=self.whitelist_regexp,
                blacklist_regexp=self.blacklist_regexp
            )
            logger.debug(f"Received async crawl response: {response}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in async crawl response: {e}")
            raise WebCrawlerAPILoaderError(
                f"Failed to parse API response (invalid JSON at position {e.pos}): {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Async API request failed: {e}")
            raise WebCrawlerAPILoaderError(f"API request failed: {str(e)}") from e

        job_id = response.id
        polls = 0
        processed_items = set()
        logger.info(f"Starting to poll job {job_id}")

        while polls < self.max_polls:
            try:
                logger.debug(f"Polling job {job_id} (attempt {polls + 1}/{self.max_polls})")
                job = self.client.get_job(job_id)
                logger.debug(f"Received job status: {job.status}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in job status response: {e}")
                raise WebCrawlerAPILoaderError(
                    f"Failed to parse job status response (invalid JSON at position {e.pos}): {str(e)}"
                ) from e
            except Exception as e:
                logger.error(f"Failed to fetch job status: {e}")
                raise WebCrawlerAPILoaderError(f"Failed to fetch job status: {str(e)}") from e

            if job.status == "error":
                error_msg = getattr(job, 'error', 'Unknown error')
                logger.error(f"Job failed with error: {error_msg}")
                raise WebCrawlerAPILoaderError(f"Crawling job failed: {error_msg}")

            for item in job.job_items:
                if item.id not in processed_items:
                    try:
                        doc = self._create_document(item)
                        if doc:
                            processed_items.add(item.id)
                            logger.debug(f"Yielding document for URL: {item.original_url}")
                            yield doc
                    except AttributeError as e:
                        logger.error(f"Failed to process job item: {e}")
                        raise WebCrawlerAPILoaderError(
                            f"Invalid job item format - missing required field: {str(e)}"
                        ) from e

            if job.is_terminal:
                logger.info("Job completed successfully")
                break

            delay_seconds = (
                job.recommended_pull_delay_ms / 1000
                if job.recommended_pull_delay_ms
                else self.client.DEFAULT_POLL_DELAY_SECONDS
            )

            import time
            logger.debug(f"Waiting {delay_seconds} seconds before next poll")
            time.sleep(delay_seconds)
            polls += 1

        if not job.is_terminal and polls >= self.max_polls:
            logger.error(f"Job timed out after {self.max_polls} polls")
            raise WebCrawlerAPILoaderError(
                f"Maximum number of polls ({self.max_polls}) reached without job completion"
            )

    async def aload(self) -> List[Document]:
        """Asynchronously load data into Document objects.

        Returns:
            List of Document objects, one for each crawled page.

        Raises:
            RuntimeError: If the crawling job fails
        """
        import asyncio
        return await asyncio.to_thread(self.load)

    async def alazy_load(self) -> AsyncIterator[Document]:
        """An async lazy loader for Documents.

        Yields:
            Document objects one at a time as they are crawled.

        Raises:
            RuntimeError: If the crawling job fails
        """
        import asyncio
        for doc in self.lazy_load():
            yield doc
            await asyncio.sleep(0) 