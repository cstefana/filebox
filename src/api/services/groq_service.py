import os
from functools import lru_cache

from dotenv import load_dotenv
from groq import Groq

load_dotenv("config.env")

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """Get or create a cached Groq client."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return Groq(api_key=api_key)


def query_files(user_query: str, file_contents: list[str]) -> str:
    """Query the Groq model with a question about user files.
    
    Args:
        user_query: The user's question about their files
        file_contents: List of file contents to provide context
        
    Returns:
        The model's response as a string
    """
    if not user_query or not user_query.strip():
        raise ValueError("Query must not be empty.")
    
    if not file_contents:
        raise ValueError("At least one file content is required.")
    
    # Prepare context from file contents
    context = "\n\n---\n\n".join(file_contents)
    
    # Build the prompt
    system_prompt = "You are a helpful assistant that answers questions about the user's files. Use the provided file contents to answer accurately."
    user_message = f"""Here are the contents of the user's files:

{context}

---

User's question: {user_query}

Please answer the question based on the file contents provided."""
    
    client = get_groq_client()
    
    message = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
    )
    
    return message.choices[0].message.content
