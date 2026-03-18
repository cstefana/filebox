import os
from functools import lru_cache

from dotenv import load_dotenv
from voyageai import Client

load_dotenv("config.env")

VOYAGE_MODEL = "voyage-4"
VOYAGE_OUTPUT_DIMENSION = 2048


@lru_cache(maxsize=1)
def get_voyage_client() -> Client:
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY environment variable is not set.")
    return Client(api_key=api_key)


def embed_text(text: str) -> list[float]:
    """Embed a single text string with Voyage AI and return its vector."""
    if not text or not text.strip():
        raise ValueError("Text must not be empty.")

    result = get_voyage_client().embed(
        texts=text,
        model=VOYAGE_MODEL,
        output_dimension=VOYAGE_OUTPUT_DIMENSION,
    )

    if not result.embeddings:
        raise RuntimeError("Voyage AI returned no embeddings.")

    return result.embeddings[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of text strings with Voyage AI and return their vectors."""
    if not texts:
        return []

    result = get_voyage_client().embed(
        texts=texts,
        model=VOYAGE_MODEL,
        output_dimension=VOYAGE_OUTPUT_DIMENSION,
    )

    if not result.embeddings:
        raise RuntimeError("Voyage AI returned no embeddings.")

    return result.embeddings