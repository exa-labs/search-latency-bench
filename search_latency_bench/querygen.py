import os

from openai import AsyncOpenAI
from pydantic import BaseModel


class QueriesResponse(BaseModel):
    queries: list[str]


async def generate_queries(count: int, api_key: str | None = None) -> list[str]:
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise ValueError("OPENAI_API_KEY is required")

    client = AsyncOpenAI(api_key=api_key)

    prompt = f"""Generate {count} diverse search queries that cover a wide variety of topics, styles, and use cases.

Include a mix of:
- Different topics (technology, science, history, entertainment, current events, etc.)
- Different query styles (questions, keywords, phrases)
- Different lengths (short and long queries)
- Different specificity levels (broad and specific)"""

    response = await client.chat.completions.parse(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="low",
        response_format=QueriesResponse,
    )

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Empty response from OpenAI")

    return parsed.queries[:count]
