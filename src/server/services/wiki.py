"""Service layer for wiki generation from ingested RAG data.

Generates structured wiki content by:
1. Querying MongoDB for ingested documents/chunks
2. Clustering topics using LLM
3. Generating page content with RAG context
4. Streaming responses
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import openai

from mdrag.dependencies import AgentDependencies
from mdrag.tools import hybrid_search, SearchResult

logger = logging.getLogger(__name__)


class WikiService:
    """Generate wiki structures and content from ingested data."""

    def __init__(self) -> None:
        self.deps = AgentDependencies()

    async def initialize(self) -> None:
        await self.deps.initialize()

    async def close(self) -> None:
        await self.deps.cleanup()

    async def generate_structure(
        self,
        title: str = "Knowledge Base Wiki",
        filters: Optional[Dict[str, Any]] = None,
        match_count: int = 20,
    ) -> Dict[str, Any]:
        """Generate a wiki structure by analyzing ingested documents.

        Args:
            title: Wiki title
            filters: Optional filters for document selection
            match_count: Number of document groups to consider

        Returns:
            Wiki structure with pages and sections
        """
        await self.initialize()

        try:
            # Step 1: Discover documents in the collection
            documents = await self._discover_documents(filters)

            if not documents:
                return self._empty_structure(title)

            # Step 2: Use LLM to organize documents into wiki structure
            structure = await self._generate_structure_with_llm(
                title, documents
            )

            return structure

        finally:
            await self.close()

    async def generate_page_content(
        self,
        page_id: str,
        page_title: str,
        source_documents: List[str],
        wiki_title: str,
    ) -> str:
        """Generate content for a single wiki page using RAG.

        Args:
            page_id: Page identifier
            page_title: Page title
            source_documents: Source document references
            wiki_title: Parent wiki title

        Returns:
            Generated markdown content
        """
        await self.initialize()

        try:
            # Search for relevant chunks using the page title as query
            class DepsWrapper:
                def __init__(self, deps: AgentDependencies):
                    self.deps = deps

            ctx = DepsWrapper(self.deps)
            results = await hybrid_search(ctx, page_title, match_count=10)

            # Build context from search results
            context = self._build_page_context(results, source_documents)

            # Generate content using LLM
            content = await self._generate_page_with_llm(
                page_title, wiki_title, context, results
            )

            return content

        finally:
            await self.close()

    async def chat_with_context(
        self,
        messages: List[Dict[str, str]],
        wiki_context: str = "",
        search_type: str = "hybrid",
        match_count: int = 5,
    ) -> str:
        """Chat query within wiki context using RAG.

        Args:
            messages: Chat history
            wiki_context: Wiki context for scoping
            search_type: Search type (semantic, text, hybrid)
            match_count: Number of results

        Returns:
            Generated response
        """
        await self.initialize()

        try:
            # Get the latest user message
            last_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_message = msg.get("content", "")
                    break

            if not last_message:
                return "Please ask a question."

            # Search for relevant context
            class DepsWrapper:
                def __init__(self, deps: AgentDependencies):
                    self.deps = deps

            ctx = DepsWrapper(self.deps)
            query = f"{wiki_context}: {last_message}" if wiki_context else last_message
            results = await hybrid_search(ctx, query, match_count=match_count)

            # Build context from search results
            context_parts = []
            for i, result in enumerate(results, 1):
                context_parts.append(
                    f"[{i}] Source: {result.document_title}\n{result.content}\n"
                )
            context_text = "\n".join(context_parts)

            # Generate response
            settings = self.deps.settings
            client = openai.AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )

            system_prompt = (
                f"You are a knowledgeable assistant for a wiki about '{wiki_context}'. "
                "Answer questions using ONLY the provided context from the knowledge base. "
                "Cite sources using [N] notation. Be concise, accurate, and helpful. "
                "Use markdown formatting for readability."
            )

            llm_messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history
            for msg in messages[:-1]:
                llm_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

            # Add context with the last message
            user_prompt = (
                f"Context from knowledge base:\n{context_text}\n\n"
                f"Question: {last_message}"
            )
            llm_messages.append({"role": "user", "content": user_prompt})

            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=llm_messages,
                temperature=0.3,
                stream=False,
            )
            await client.close()

            return response.choices[0].message.content.strip()

        finally:
            await self.close()

    async def stream_page_content(
        self,
        page_id: str,
        page_title: str,
        source_documents: List[str],
        wiki_title: str,
    ):
        """Stream page content generation.

        Yields:
            Text chunks as they are generated
        """
        await self.initialize()

        try:
            class DepsWrapper:
                def __init__(self, deps: AgentDependencies):
                    self.deps = deps

            ctx = DepsWrapper(self.deps)
            results = await hybrid_search(ctx, page_title, match_count=10)

            context = self._build_page_context(results, source_documents)

            settings = self.deps.settings
            client = openai.AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )

            prompt = self._build_page_prompt(
                page_title, wiki_title, context, results
            )

            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert technical writer generating wiki documentation. "
                            "Generate comprehensive, well-structured markdown content. "
                            "Include Mermaid diagrams where appropriate. "
                            "Cite sources using the provided context."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            await client.close()

        except Exception as e:
            logger.exception("Error streaming page content: %s", str(e))
            yield f"\n\nError generating content: {str(e)}"
        finally:
            await self.close()

    async def stream_chat_response(
        self,
        messages: List[Dict[str, str]],
        wiki_context: str = "",
        match_count: int = 5,
    ):
        """Stream a chat response.

        Yields:
            Text chunks as they are generated
        """
        await self.initialize()

        try:
            last_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_message = msg.get("content", "")
                    break

            if not last_message:
                yield "Please ask a question."
                return

            class DepsWrapper:
                def __init__(self, deps: AgentDependencies):
                    self.deps = deps

            ctx = DepsWrapper(self.deps)
            query = (
                f"{wiki_context}: {last_message}"
                if wiki_context
                else last_message
            )
            results = await hybrid_search(ctx, query, match_count=match_count)

            context_parts = []
            for i, result in enumerate(results, 1):
                context_parts.append(
                    f"[{i}] Source: {result.document_title}\n{result.content}\n"
                )
            context_text = "\n".join(context_parts)

            settings = self.deps.settings
            client = openai.AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )

            system_prompt = (
                f"You are a knowledgeable assistant for a wiki about '{wiki_context}'. "
                "Answer questions using ONLY the provided context. "
                "Cite sources using [N] notation. Use markdown for readability."
            )

            llm_messages = [{"role": "system", "content": system_prompt}]
            for msg in messages[:-1]:
                llm_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

            user_prompt = (
                f"Context from knowledge base:\n{context_text}\n\n"
                f"Question: {last_message}"
            )
            llm_messages.append({"role": "user", "content": user_prompt})

            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=llm_messages,
                temperature=0.3,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            await client.close()

        except Exception as e:
            logger.exception("Error streaming chat: %s", str(e))
            yield f"\n\nError: {str(e)}"
        finally:
            await self.close()

    async def list_projects(self) -> List[Dict[str, Any]]:
        """List wiki projects based on ingested document groups.

        Returns:
            List of project summaries
        """
        await self.initialize()

        try:
            docs_collection = self.deps.db[
                self.deps.settings.mongodb_collection_documents
            ]
            chunks_collection = self.deps.db[
                self.deps.settings.mongodb_collection_chunks
            ]

            # Count documents and chunks
            doc_count = await docs_collection.count_documents({})
            chunk_count = await chunks_collection.count_documents({})

            if doc_count == 0:
                return []

            # Group by source_type for project-like grouping
            pipeline = [
                {
                    "$group": {
                        "_id": "$source_type",
                        "count": {"$sum": 1},
                        "latest": {"$max": "$created_at"},
                        "titles": {"$push": "$title"},
                    }
                },
                {"$sort": {"latest": -1}},
                {"$limit": 20},
            ]

            projects = []
            async for group in docs_collection.aggregate(pipeline):
                source_type = group["_id"] or "documents"
                titles = group.get("titles", [])[:5]
                description = f"Documents from {source_type}: {', '.join(str(t) for t in titles[:3])}"

                project_id = hashlib.md5(
                    source_type.encode()
                ).hexdigest()[:12]

                projects.append(
                    {
                        "id": project_id,
                        "title": f"{source_type.replace('_', ' ').title()} Knowledge Base",
                        "description": description,
                        "createdAt": str(group.get("latest", "")),
                        "updatedAt": str(group.get("latest", "")),
                        "pageCount": group["count"],
                        "sourceCount": group["count"],
                    }
                )

            # If no grouping, show a single project
            if not projects and doc_count > 0:
                projects.append(
                    {
                        "id": "default",
                        "title": "Knowledge Base Wiki",
                        "description": f"Wiki generated from {doc_count} documents and {chunk_count} chunks",
                        "createdAt": str(time.time()),
                        "updatedAt": str(time.time()),
                        "pageCount": doc_count,
                        "sourceCount": doc_count,
                    }
                )

            return projects

        finally:
            await self.close()

    # --- Private helpers ---

    async def _discover_documents(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Discover ingested documents from MongoDB."""
        docs_collection = self.deps.db[
            self.deps.settings.mongodb_collection_documents
        ]

        query: Dict[str, Any] = {}
        if filters:
            if "source_type" in filters:
                query["source_type"] = filters["source_type"]
            if "source_group" in filters:
                query["source_group"] = filters["source_group"]

        documents = []
        cursor = docs_collection.find(query).sort("created_at", -1).limit(100)
        async for doc in cursor:
            documents.append(
                {
                    "id": str(doc["_id"]),
                    "title": doc.get("title", "Untitled"),
                    "source_url": doc.get("source_url", ""),
                    "source_type": doc.get("source_type", "document"),
                    "created_at": str(doc.get("created_at", "")),
                    "chunk_count": doc.get("chunk_count", 0),
                }
            )

        return documents

    async def _generate_structure_with_llm(
        self, title: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use LLM to organize documents into a wiki structure."""
        settings = self.deps.settings
        client = openai.AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        doc_summaries = []
        for doc in documents[:50]:
            doc_summaries.append(
                f"- {doc['title']} (type: {doc['source_type']}, chunks: {doc.get('chunk_count', 'unknown')})"
            )
        doc_list = "\n".join(doc_summaries)

        prompt = f"""Analyze these ingested documents and create a wiki structure.
The wiki title is: "{title}"

Documents available:
{doc_list}

Generate a JSON structure with the following format:
{{
  "id": "<unique-id>",
  "title": "{title}",
  "description": "<brief description of the wiki>",
  "pages": [
    {{
      "id": "<page-id>",
      "title": "<page title>",
      "content": "",
      "importance": "high|medium|low",
      "relatedPages": ["<related-page-ids>"],
      "sourceDocuments": ["<source doc titles>"],
      "parentId": null,
      "isSection": false,
      "children": []
    }}
  ],
  "sections": [
    {{
      "id": "<section-id>",
      "title": "<section title>",
      "pages": ["<page-ids>"],
      "subsections": []
    }}
  ],
  "rootSections": ["<section-ids>"]
}}

Rules:
1. Create 5-15 wiki pages organized into 2-5 logical sections
2. Each page should focus on a specific topic discovered from the documents
3. Set importance: "high" for overview/architecture, "medium" for features, "low" for details
4. Include relatedPages connections between related topics
5. sourceDocuments should reference the actual document titles
6. Return ONLY valid JSON, no markdown code blocks

Respond with ONLY the JSON structure."""

        try:
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a wiki structure generator. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            await client.close()

            content = response.choices[0].message.content.strip()

            # Clean markdown code blocks if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()

            structure = json.loads(content)

            # Ensure required fields
            wiki_id = hashlib.md5(
                f"{title}-{time.time()}".encode()
            ).hexdigest()[:12]

            structure.setdefault("id", wiki_id)
            structure.setdefault("title", title)
            structure.setdefault("description", f"Wiki generated from {len(documents)} documents")
            structure.setdefault("pages", [])
            structure.setdefault("sections", [])
            structure.setdefault("rootSections", [s["id"] for s in structure.get("sections", [])])

            return structure

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM wiki structure: %s", str(e))
            # Fallback: create a simple structure
            return self._fallback_structure(title, documents)
        except Exception as e:
            logger.exception("Error generating wiki structure: %s", str(e))
            return self._fallback_structure(title, documents)

    def _fallback_structure(
        self, title: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a fallback wiki structure when LLM fails."""
        wiki_id = hashlib.md5(
            f"{title}-{time.time()}".encode()
        ).hexdigest()[:12]

        pages = []
        for i, doc in enumerate(documents[:10]):
            page_id = f"page-{i}"
            pages.append(
                {
                    "id": page_id,
                    "title": doc["title"],
                    "content": "",
                    "importance": "high" if i == 0 else "medium",
                    "relatedPages": [],
                    "sourceDocuments": [doc["title"]],
                    "parentId": None,
                    "isSection": False,
                    "children": [],
                }
            )

        section = {
            "id": "section-main",
            "title": "Documents",
            "pages": [p["id"] for p in pages],
            "subsections": [],
        }

        return {
            "id": wiki_id,
            "title": title,
            "description": f"Wiki generated from {len(documents)} documents",
            "pages": pages,
            "sections": [section],
            "rootSections": ["section-main"],
        }

    def _empty_structure(self, title: str) -> Dict[str, Any]:
        """Return an empty wiki structure."""
        wiki_id = hashlib.md5(title.encode()).hexdigest()[:12]
        return {
            "id": wiki_id,
            "title": title,
            "description": "No documents found. Please ingest some data first.",
            "pages": [
                {
                    "id": "getting-started",
                    "title": "Getting Started",
                    "content": (
                        "# Getting Started\n\n"
                        "No documents have been ingested yet. "
                        "Use the ingestion API to add documents, then generate a wiki.\n\n"
                        "## How to Ingest Data\n\n"
                        "1. Upload documents via the `/api/v1/ingest` endpoint\n"
                        "2. Crawl websites using the Crawl4AI integration\n"
                        "3. Import from Google Drive\n\n"
                        "Once data is ingested, return here to generate your wiki."
                    ),
                    "importance": "high",
                    "relatedPages": [],
                    "sourceDocuments": [],
                    "parentId": None,
                    "isSection": False,
                    "children": [],
                }
            ],
            "sections": [
                {
                    "id": "section-start",
                    "title": "Getting Started",
                    "pages": ["getting-started"],
                    "subsections": [],
                }
            ],
            "rootSections": ["section-start"],
        }

    def _build_page_context(
        self,
        results: List[SearchResult],
        source_documents: List[str],
    ) -> str:
        """Build context text from search results."""
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"## Source [{i}]: {result.document_title}\n"
                f"Source: {result.document_source}\n\n"
                f"{result.content}\n"
            )
        return "\n---\n".join(context_parts)

    def _build_page_prompt(
        self,
        page_title: str,
        wiki_title: str,
        context: str,
        results: List[SearchResult],
    ) -> str:
        """Build the prompt for page content generation."""
        source_refs = []
        for i, result in enumerate(results, 1):
            source_refs.append(f"[{i}] {result.document_title}")
        sources_list = "\n".join(source_refs)

        return f"""Generate a comprehensive wiki page for the following topic.

Wiki: {wiki_title}
Page Topic: {page_title}

Available Sources:
{sources_list}

Context from Knowledge Base:
{context}

Requirements:
1. Start with a brief introduction explaining the topic
2. Break content into logical sections using ## and ### headings
3. Include Mermaid diagrams where they help explain architecture or flows
4. Use tables for structured data (parameters, configurations, etc.)
5. Cite sources using [N] notation
6. Be comprehensive but concise
7. Ground all content in the provided context - do not invent information
8. Use markdown formatting for readability

Generate the wiki page content now:"""

    async def _generate_page_with_llm(
        self,
        page_title: str,
        wiki_title: str,
        context: str,
        results: List[SearchResult],
    ) -> str:
        """Generate page content using LLM."""
        settings = self.deps.settings
        client = openai.AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        prompt = self._build_page_prompt(
            page_title, wiki_title, context, results
        )

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert technical writer generating wiki documentation. "
                        "Generate comprehensive, well-structured markdown content. "
                        "Include Mermaid diagrams where appropriate. "
                        "Cite sources using the provided context."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        await client.close()

        return response.choices[0].message.content.strip()
