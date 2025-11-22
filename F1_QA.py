from typing import Dict, List, Tuple
from utilities import (
    num_tokens_from_messages,
    get_embedding,
    get_n_nearest_neighbors,
    memoize_to_sqlite,
)
from f1_utilities import wikipedia_splitter, Section
from io import StringIO

import csv
import requests
import os
import itertools
import tiktoken
import openai
import pandas as pd

from dotenv import load_dotenv

load_dotenv(".env")

openai.api_key = os.environ["OPENAI_API_KEY"]


from typing import Optional
import logging

logger = logging.getLogger(__name__)


MAX_CONTEXT_WINDOW = 4097
MINIMUM_RESPONSE_SPACE = 1000
MAX_PROMPT_SIZE = MAX_CONTEXT_WINDOW - MINIMUM_RESPONSE_SPACE


# Model & token encoders
chat_model = "gpt-3.5-turbo"
embedding_enc = tiktoken.encoding_for_model("text-embedding-ada-002")
enc = tiktoken.encoding_for_model(chat_model)


def ask_embedding_store(
    question: str, embeddings: Dict[Section, List[float]], max_documents: int
) -> str:
    """
    Fetch necessary context from our embedding store, striving to fit the top max_documents
    into the context window (or fewer if the total token count exceeds the limit)

    :param question: The question to ask
    :param embeddings: A dictionary of Section objects to their corresponding embeddings
    :param max_documents: The maximum number of documents to use as context
    :return: GPT's response to the question given context provided in our embedding store
    """
    query_embedding = get_embedding(question)

    nearest_neighbors = get_n_nearest_neighbors(
        query_embedding, embeddings, max_documents
    )
    messages: Optional[List[Dict[str, str]]] = None

    base_token_count = num_tokens_from_messages(get_messages([], question), chat_model)
    token_counts = [
        len(enc.encode(document.text.replace("\n", " ")))
        for document, _ in nearest_neighbors
    ]
    cumulative_token_counts = list(itertools.accumulate(token_counts))
    indices_within_limit = [
        True
        for x in cumulative_token_counts
        if x <= (MAX_PROMPT_SIZE - base_token_count)
    ]
    most_messages_we_can_fit = len(indices_within_limit)

    context = [x[0] for x in nearest_neighbors[: most_messages_we_can_fit + 1]]

    debug_str = "\n".join(
        [
            f"{x[0].location}: {x[1]}"
            for x in nearest_neighbors[: most_messages_we_can_fit + 1]
        ]
    )
    #     print(f"Using {most_messages_we_can_fit} documents as context:\n" + debug_str)
    messages = get_messages(context, question)

    #     print(f"Prompt: {messages[-1]['content']}")
    result = openai.chat.completions.create(model=chat_model, messages=messages)
    return result.choices[0].message.content


@memoize_to_sqlite("cache.db")
def wikipedia_api_fetch(article_title: str, field: str) -> str:
    base_url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "titles": article_title,
        "explaintext": 1,
    }

    headers = {
        # Wikipedia expects a descriptive User-Agent
        "User-Agent": "F1-QA-Bot/1.0 (https://example.com; contact@example.com)"
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
    except Exception as e:
        logger.exception("HTTP request to Wikipedia failed")
        raise ValueError(f"Failed to fetch page {article_title}: {e}") from e

    if response.status_code != 200:
        # Give helpful diagnostics when non-200 is returned
        logger.error("Wikipedia API returned status %s for %s: %s", response.status_code, article_title, response.text[:200])
        raise ValueError(f"Wikipedia API returned status {response.status_code} for {article_title}")

    try:
        data = response.json()
    except Exception as e:
        logger.exception("Failed to decode JSON from Wikipedia response")
        body = response.text or ""
        # show a truncated response to help debugging
        snippet = body[:1000] + ("..." if len(body) > 1000 else "")
        raise ValueError(
            f"Invalid JSON from Wikipedia for {article_title}. HTTP {response.status_code}. Response body (truncated): {snippet}"
        ) from e

    if "query" in data and "pages" in data["query"]:
        page = list(data["query"]["pages"].values())[0]
        if field in page:
            return page[field]
        else:
            raise ValueError(f"Could not find {field} for page {page}")
    else:
        raise ValueError(f"Could not find page {article_title}")


def prepare_embeddings(csv_path: str = "FormulaOne_Data.Csv") -> Tuple[Dict[Section, List[float]], List[Section]]:
    """Load the CSV, fetch Wikipedia pages (memoized), split into sections and compute embeddings.

    Returns (embeddings, sections)
    """
    df = pd.read_csv(csv_path)

    # Fetch page content (memoized)
    df["Page_Content"] = df["Link"].apply(lambda x: wikipedia_api_fetch(x, "extract"))
    df["Display Title"] = df["Link"].apply(lambda x: wikipedia_api_fetch(x, "title"))

    sections: List[Section] = []
    split_point_regexes = [r"\n==\s", r"\n===\s", r"\n====\s", r"\n\n", r"\n"]

    for index, row in df.iterrows():
        for section in wikipedia_splitter(
            row["Page_Content"],
            row["Display Title"],
            token_limit=MAX_CONTEXT_WINDOW,
            split_point_regexes=split_point_regexes,
        ):
            sections.append(section)

    if sections:
        print(str(sections[0]))

    total_tokens = sum([len(embedding_enc.encode(str(section))) for section in sections])
    cost = total_tokens * (0.0004 / 1000)
    print(f"Estimated Cost ${cost:.2f}")

    embeddings: Dict[Section, List[float]] = {section: get_embedding(str(section)) for section in sections}
    return embeddings, sections


def answer_question(question: str, embeddings: Dict[Section, List[float]], max_documents: int = 10) -> str:
    return ask_embedding_store(question, embeddings, max_documents)


def main():
    embeddings, sections = prepare_embeddings()
    print("Ready. Ask a question (empty to quit).")
    try:
        while True:
            q = input("Question: ")
            if not q or not q.strip():
                break
            answer = answer_question(q, embeddings, 10)
            print("\n" + answer + "\n")
    except KeyboardInterrupt:
        print("\nExiting.")



def get_messages(context: List[Section], question: str) -> List[Dict[str, str]]:
    context_str = "\n\n".join([f"Path: {x.location}\nBody:\n{x.text}" for x in context])
    return [
        {
            "role": "system",
            "content": """
You will receive a question from the user and some context to help you answer the question.

Evaluate the context and provide an answer if you can confidently answer the question.

If you are unable to provide a confident response, kindly state that it is the case and explain the reason.

Prioritize offering an "I don't know" response over conveying potentially false information.

The user will only see your response and not the context you've been provided. Thus, respond in precise detail, directly repeating the information that you're referencing from the context.
""".strip(),
        },
        {
            "role": "user",
            "content": f"""
Using the following information as context, I'd like you to answer a question.

{context_str}

Please answer the following question: {question}
""".strip(),
        },
    ]