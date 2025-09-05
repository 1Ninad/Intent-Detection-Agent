# scripts/setup_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams

def setup_qdrant():
    # connect to your local Qdrant
    client = QdrantClient("http://localhost:6333")
    collection_name = "company_signals"

    # if already exists: delete first
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    # create new collection with vector config
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance="Cosine")
    )

    print(f"Qdrant collection '{collection_name}' created successfully")

if __name__ == "__main__":
    setup_qdrant()
