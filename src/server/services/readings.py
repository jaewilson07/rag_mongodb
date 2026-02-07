"""Service for save-and-research readings (Wallabag/Instapaper style).

Pipeline:
1. Crawl the URL via Crawl4AI
2. Generate an LLM summary with key points
3. Search for related content via SearXNG
4. Store the reading in MongoDB
5. Queue the content for RAG ingestion
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
import openai

from mdrag.dependencies import AgentDependencies
from mdrag.settings import load_settings

logger = logging.getLogger(__name__)


class ReadingsService:
    """Save URLs, crawl content, summarize, and research."""

    def __init__(self) -> None:
        self.deps = AgentDependencies()

    async def initialize(self) -> None:
        await self.deps.initialize()

    async def close(self) -> None:
        await self.deps.cleanup()

    async def save_reading(
        self,
        url: str,
        tags: List[str] | None = None,
        source_group: str | None = None,
        user_id: str | None = None,
        org_id: str | None = None,
    ) -> Dict[str, Any]:
        """Save a URL: crawl, summarize, research, and store.

        Args:
            url: URL to save
            tags: Optional tags
            source_group: Source group for organization
            user_id: User ID for multi-tenancy
            org_id: Org ID for multi-tenancy

        Returns:
            Complete reading with summary and related links
        """
        await self.initialize()

        try:
            reading_id = hashlib.md5(
                f"{url}-{time.time()}".encode()
            ).hexdigest()[:16]
            domain = urlparse(url).netloc
            saved_at = datetime.utcnow().isoformat()

            # Step 1: Crawl the URL
            logger.info("Crawling URL: %s", url)
            crawl_result = await self._crawl_url(url)

            title = crawl_result.get("title", domain)
            content = crawl_result.get("content", "")
            word_count = len(content.split()) if content else 0

            # Step 2: Generate summary with key points
            logger.info("Generating summary for: %s", title)
            summary_data = await self._generate_summary(title, content, url)

            # Step 3: Search for related content
            logger.info("Researching related content for: %s", title)
            related_links = await self._research_topic(
                title, summary_data.get("summary", ""), url
            )

            # Step 4: Store in MongoDB
            reading_doc = {
                "_id": reading_id,
                "url": url,
                "title": title,
                "summary": summary_data.get("summary", "No summary available."),
                "key_points": summary_data.get("key_points", []),
                "related_links": [rl for rl in related_links],
                "tags": tags or [],
                "content_preview": content[:500] if content else "",
                "word_count": word_count,
                "saved_at": saved_at,
                "status": "complete",
                "source_group": source_group or domain,
                "domain": domain,
                "user_id": user_id,
                "org_id": org_id,
                "full_content": content,
            }

            collection = self.deps.db["readings"]
            await collection.replace_one(
                {"_id": reading_id}, reading_doc, upsert=True
            )

            # Step 5: Queue for RAG ingestion (non-blocking)
            job_id = await self._queue_ingestion(url, source_group or domain)

            reading_doc["ingestion_job_id"] = job_id
            # Don't return full_content in API response
            reading_doc.pop("full_content", None)
            reading_doc["id"] = reading_doc.pop("_id")

            return reading_doc

        except Exception as e:
            logger.exception("Error saving reading for %s: %s", url, str(e))
            # Return a partial result even on error
            return {
                "id": hashlib.md5(url.encode()).hexdigest()[:16],
                "url": url,
                "title": urlparse(url).netloc,
                "summary": f"Error processing this URL: {str(e)}",
                "key_points": [],
                "related_links": [],
                "tags": tags or [],
                "content_preview": "",
                "word_count": 0,
                "saved_at": datetime.utcnow().isoformat(),
                "status": "error",
                "source_group": source_group,
            }
        finally:
            await self.close()

    async def list_readings(
        self,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List saved readings."""
        await self.initialize()

        try:
            collection = self.deps.db["readings"]
            query: Dict[str, Any] = {}
            if user_id:
                query["user_id"] = user_id

            total = await collection.count_documents(query)
            cursor = (
                collection.find(query, {"full_content": 0})
                .sort("saved_at", -1)
                .skip(offset)
                .limit(limit)
            )

            readings = []
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                readings.append(doc)

            return {"readings": readings, "total": total}

        finally:
            await self.close()

    async def get_reading(self, reading_id: str) -> Optional[Dict[str, Any]]:
        """Get a single reading by ID."""
        await self.initialize()

        try:
            collection = self.deps.db["readings"]
            doc = await collection.find_one(
                {"_id": reading_id}, {"full_content": 0}
            )
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
            return None
        finally:
            await self.close()

    # --- Private helpers ---

    async def _crawl_url(self, url: str) -> Dict[str, Any]:
        """Crawl a URL and extract content."""
        try:
            from mdrag.integrations.crawl4ai.client import Crawl4AIClient

            client = Crawl4AIClient()
            source = await client.crawl_single_page(
                url=url,
                word_count_threshold=10,
                remove_overlay_elements=True,
                timeout=30,
            )

            if source:
                return {
                    "title": source.frontmatter.source_title or urlparse(url).netloc,
                    "content": source.content or "",
                    "html": source.html or "",
                    "links": source.links or [],
                    "metadata": source.metadata or {},
                }
        except Exception as e:
            logger.warning("Crawl4AI failed for %s, falling back to httpx: %s", url, str(e))

        # Fallback: simple httpx fetch
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; KnowledgeWiki/1.0)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                text = response.text

                title = urlparse(url).netloc
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, "html.parser")
                    title_tag = soup.find("title")
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                    # Extract text content
                    for script in soup(["script", "style", "nav", "footer"]):
                        script.decompose()
                    content = soup.get_text(separator="\n", strip=True)
                except Exception:
                    content = text[:5000]

                return {
                    "title": title,
                    "content": content[:10000],
                    "html": text[:10000],
                    "links": [],
                    "metadata": {},
                }
        except Exception as e:
            logger.error("httpx fallback failed for %s: %s", url, str(e))
            return {
                "title": urlparse(url).netloc,
                "content": "",
                "html": "",
                "links": [],
                "metadata": {},
            }

    async def _generate_summary(
        self, title: str, content: str, url: str
    ) -> Dict[str, Any]:
        """Generate a summary and key points using LLM."""
        settings = self.deps.settings
        client = openai.AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        # Truncate content for context window
        truncated = content[:6000] if content else "No content available."

        prompt = f"""Analyze the following web page and provide:
1. A concise summary (2-3 paragraphs)
2. A list of 3-7 key points or takeaways

URL: {url}
Title: {title}

Content:
{truncated}

Respond in this exact JSON format:
{{
  "summary": "Your summary here...",
  "key_points": ["Point 1", "Point 2", "Point 3"]
}}

If the content is empty or unclear, provide your best assessment based on the URL and title.
Return ONLY valid JSON."""

        try:
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a research assistant that summarizes web content. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            await client.close()

            result_text = response.choices[0].message.content.strip()

            # Clean markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text.rsplit("```", 1)[0]
            result_text = result_text.strip()

            import json
            return json.loads(result_text)

        except Exception as e:
            logger.error("Summary generation failed: %s", str(e))
            return {
                "summary": f"Saved from {urlparse(url).netloc}: {title}",
                "key_points": [title],
            }

    async def _research_topic(
        self, title: str, summary: str, original_url: str
    ) -> List[Dict[str, Any]]:
        """Search for related content using SearXNG."""
        settings = self.deps.settings
        base_url = (settings.searxng_url or "").rstrip("/")

        if not base_url:
            logger.info("SearXNG not configured, skipping research")
            return []

        # Build a search query from the title
        search_query = title[:100]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "q": search_query,
                    "format": "json",
                    "pageno": 1,
                }
                response = await client.get(f"{base_url}/search", params=params)
                response.raise_for_status()
                data = response.json()

            related = []
            original_domain = urlparse(original_url).netloc

            for item in data.get("results", [])[:10]:
                item_url = item.get("url", "")
                item_domain = urlparse(item_url).netloc

                # Skip the original URL
                if item_domain == original_domain and item_url == original_url:
                    continue

                related.append({
                    "title": item.get("title", ""),
                    "url": item_url,
                    "snippet": item.get("content", "")[:300],
                    "source": item.get("engine"),
                })

                if len(related) >= 5:
                    break

            return related

        except Exception as e:
            logger.warning("SearXNG research failed: %s", str(e))
            return []

    async def _queue_ingestion(
        self, url: str, source_group: str
    ) -> Optional[str]:
        """Queue the URL for RAG ingestion (non-blocking)."""
        try:
            from mdrag.server.services.ingest import IngestJobService
            service = IngestJobService()
            result = service.queue_web(
                url=url,
                deep=False,
                max_depth=None,
                namespace={"source_group": source_group},
            )
            return result.get("job_id")
        except Exception as e:
            logger.warning("Failed to queue ingestion for %s: %s", url, str(e))
            return None
