from connectors.embeddings import HashedTokenEmbedding, cosine
from connectors.search import InMemoryVectorSearch
from entities.issue import KnowledgeChunk


def test_hashed_embeddings_rank_overlapping_tokens():
    embedder = HashedTokenEmbedding(32)
    query = embedder.embed(["ciclo de vida da engenharia de dados"])[0]
    close = embedder.embed(["o ciclo de vida cobre ingestao e transformacao"])[0]
    far = embedder.embed(["quantum qubits teleport recipes"])[0]
    assert cosine(query, close) > cosine(query, far)


def test_in_memory_vector_search_returns_nearest_chunk():
    index = InMemoryVectorSearch(embedder=HashedTokenEmbedding(32))
    index.upsert(
        [
            {
                "id": "a",
                "source_id": "fx",
                "source_path": "book.txt",
                "title": "ciclo",
                "page": 1,
                "text": "o ciclo de vida da engenharia de dados cobre geracao e ingestao",
            },
            {
                "id": "b",
                "source_id": "fx",
                "source_path": "book.txt",
                "title": "outro",
                "page": 2,
                "text": "receitas de cerveja artesanal e lupulo",
            },
        ]
    )
    hits = index.search("ciclo de vida engenharia de dados", top_k=2)
    assert hits
    assert hits[0].id == "a"
    assert isinstance(hits[0], KnowledgeChunk)
    assert hits[0].page == 1
