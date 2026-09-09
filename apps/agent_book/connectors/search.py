"""Search backends — local keyword lake, in-memory vectors (tests), Azure AI Search."""

from __future__ import annotations

import os
from typing import Any, Protocol

from connectors.embeddings import EmbeddingClient, HashedTokenEmbedding, build_embeddings, cosine
from dataplatform.utils import get_logger
from entities.issue import KnowledgeChunk
from knowledge.retrieve import KnowledgeRetriever, format_hits

logger = get_logger(__name__)

VECTOR_FIELD = "text_vector"
VECTOR_PROFILE = "agent_book-vector-profile"
VECTOR_ALGORITHM = "agent_book-hnsw"


class SearchClient(Protocol):
    def search(self, query: str, top_k: int = 4) -> list[KnowledgeChunk]: ...

    def ensure_index(self) -> None: ...

    def upsert(self, rows: list[dict[str, Any]]) -> int: ...


class LocalSearch:
    """Keyword retrieve over bronze JSON. No vector index."""

    def __init__(self, retriever: KnowledgeRetriever) -> None:
        self.retriever = retriever

    def search(self, query: str, top_k: int = 4) -> list[KnowledgeChunk]:
        return self.retriever.search(query, top_k=top_k)

    def ensure_index(self) -> None:
        return None

    def upsert(self, rows: list[dict[str, Any]]) -> int:
        del rows
        return 0


class InMemoryVectorSearch:
    """Cosine over hashed embeddings — same contract as Azure, no cloud."""

    def __init__(self, embedder: EmbeddingClient | None = None) -> None:
        self.embedder = embedder or HashedTokenEmbedding(32)
        self._rows: list[dict[str, Any]] = []
        self._vectors: list[list[float]] = []

    def ensure_index(self) -> None:
        return None

    def upsert(self, rows: list[dict[str, Any]]) -> int:
        texts = [str(row.get("text", "")) for row in rows]
        self._vectors = self.embedder.embed(texts)
        self._rows = list(rows)
        return len(rows)

    def search(self, query: str, top_k: int = 4) -> list[KnowledgeChunk]:
        if not self._rows:
            return []
        query_vec = self.embedder.embed([query])[0]
        ranked = sorted(
            (
                (cosine(query_vec, vector), row)
                for vector, row in zip(self._vectors, self._rows, strict=True)
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        hits: list[KnowledgeChunk] = []
        for score, row in ranked[:top_k]:
            if score <= 0:
                continue
            hits.append(_row_to_chunk(row))
        return hits


class AzureAiSearch:
    """Azure AI Search vector index (Databricks Vector Search stand-in)."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        index_name: str,
        embedder: EmbeddingClient,
        dimensions: int,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.index_name = index_name
        self.embedder = embedder
        self.dimensions = dimensions
        self._docs: Any = None

    def ensure_index(self) -> None:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        client = SearchIndexClient(self.endpoint, AzureKeyCredential(self.api_key))
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="text", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="source_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="source_path", type=SearchFieldDataType.String),
            SearchField(
                name=VECTOR_FIELD,
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.dimensions,
                vector_search_profile_name=VECTOR_PROFILE,
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name=VECTOR_ALGORITHM)],
            profiles=[
                VectorSearchProfile(
                    name=VECTOR_PROFILE,
                    algorithm_configuration_name=VECTOR_ALGORITHM,
                )
            ],
        )
        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
        client.create_or_update_index(index)
        logger.info("azure search index ready: %s", self.index_name)

    def _documents(self):
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient as AzureSearchClient

        if self._docs is None:
            self._docs = AzureSearchClient(
                self.endpoint, self.index_name, AzureKeyCredential(self.api_key)
            )
        return self._docs

    def upsert(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        vectors = self.embedder.embed([str(row.get("text", "")) for row in rows])
        documents = []
        for row, vector in zip(rows, vectors, strict=True):
            documents.append(
                {
                    "id": str(row["id"]),
                    "text": str(row.get("text", "")),
                    "title": str(row.get("title", "")),
                    "page": int(row.get("page") or 0),
                    "source_id": str(row.get("source_id", "")),
                    "source_path": str(row.get("source_path", "")),
                    VECTOR_FIELD: vector,
                }
            )
        client = self._documents()
        uploaded = 0
        for start in range(0, len(documents), 100):
            batch = documents[start : start + 100]
            result = client.upload_documents(batch)
            uploaded += sum(1 for item in result if getattr(item, "succeeded", True))
        logger.info("azure search upserted %s docs into %s", uploaded, self.index_name)
        return uploaded

    def search(self, query: str, top_k: int = 4) -> list[KnowledgeChunk]:
        from azure.search.documents.models import VectorizedQuery

        query_vector = self.embedder.embed([query])[0]
        client = self._documents()
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields=VECTOR_FIELD,
        )
        results = client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=top_k,
            select=["id", "text", "title", "page", "source_id", "source_path"],
        )
        return [_row_to_chunk(dict(doc)) for doc in results]


def resolve_search_provider(cfg: dict[str, Any]) -> str:
    return os.getenv("AGENT_BOOK_SEARCH_PROVIDER") or str(cfg.get("search_provider", "local"))


def build_search(
    provider: str, *, retriever: KnowledgeRetriever, cfg: dict[str, Any]
) -> SearchClient:
    name = (provider or "local").lower()
    if name == "local":
        return LocalSearch(retriever)
    if name == "memory":
        return InMemoryVectorSearch(embedder=HashedTokenEmbedding(32))
    if name in {"azure_search", "azure"}:
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        api_key = os.getenv("AZURE_SEARCH_API_KEY", "")
        if not endpoint or not api_key:
            logger.warning("Azure AI Search env missing — falling back to local search")
            return LocalSearch(retriever)
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if not openai_endpoint or not openai_key:
            logger.warning("Azure OpenAI env missing — falling back to local search")
            return LocalSearch(retriever)
        embedder = build_embeddings("azure_openai", cfg)
        return AzureAiSearch(
            endpoint=endpoint,
            api_key=api_key,
            index_name=str(cfg.get("search_index", "agent_book-knowledge")),
            embedder=embedder,
            dimensions=int(cfg.get("embedding_dimensions", 1536)),
        )
    raise ValueError(f"Unknown search provider: {provider}")


def hits_as_text(chunks: list[KnowledgeChunk]) -> str:
    return format_hits(chunks)


def _row_to_chunk(row: dict[str, Any]) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=str(row.get("id", "")),
        source_id=str(row.get("source_id", "")),
        source_path=str(row.get("source_path", "")),
        title=str(row.get("title", "")),
        text=str(row.get("text", "")),
        page=int(row.get("page") or 0),
    )
