import json

import transformers
import torch

from app.config import SECTION, SECTION, CORPUS_VOCAB_PATH


## LLM Pipeline

pipeline = transformers.pipeline(
    "text-generation",
    model="meta-llama/Meta-Llama-3.1-8B-Instruct",
    model_kwargs={"dtype": torch.bfloat16},
    device_map="auto",
)


prompt_template = """
You rewrite user questions into retrieval queries for an MLflow experiment database.

The database is organized into sections. Each section contains specific fields:
{section_queries}

Your task: rewrite the question as a single search query using ONLY terminology from the relevant sections above.

Rules:
1. Identify which section(s) the question is about.
2. Replace vague phrasing with the exact field terms from those sections (e.g. "how good is the model" → "metrics accuracy performance").
3. Do not introduce concepts absent from the sections.
4. Output ONLY the rewritten query — no explanation, no quotes, no preamble.
5. Only generate terminologies that are present in the sections above. If a term is not in the sections, do not use it.

Example:
Question: "what settings gave the best accuracy?"
Output:
performance: metrics accuracy
configuration: params hyperparameters

"""

def generate_section():
    """
    Extracts and returns the vocabulary for each section based on the corpus vocabulary defined in CORPUS_VOCAB_PATH.
    Returns: corpus_vocab (dict): A dictionary where keys are section names and values are sets of vocabulary terms for that section.
    """
    vocab  = json.load(open( CORPUS_VOCAB_PATH, "r"))
    if not vocab:
        raise ValueError(f"Corpus vocabulary is empty or not found at {CORPUS_VOCAB_PATH}. Please ensure the file exists and contains valid JSON data.")
    corpus_vocab = {}
    for section, fields in SECTION.items():
        vocab_set = set()
        for field in fields.split():
            print(f"Processing section '{section}', field '{field}'")
            if field in vocab:
                vocab_set.update(vocab[field])
        corpus_vocab[section] = vocab_set

    return corpus_vocab



def rewrite_query(query: str) -> dict[str, str]:
    """
    Rewrite a vague user query into a structured query using corpus vocabulary from the relevant sections.
    """

    section_vocab = "\n".join(f"{k}: {v}" for k, v in generate_section().items())

    prompt = prompt_template.format(section_queries=section_vocab)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": query},
    ]
    response = pipeline(
        messages,
        max_new_tokens=100,     
        do_sample=False,       
    )
    response_text = response[0]["generated_text"][-1]["content"]

    routed = {}
    for line in response_text.splitlines():
        if ":" not in line:
            continue
        section, _, keywords = line.partition(":")
        print(f"Detected section: '{section.strip()}', keywords: '{keywords.strip()}'")
        section = section.strip().lower()
        if section in SECTION:
            if "runs" in keywords.lower() and section != "info": # this is an issue with the LLM sometimes adding "runs" to the query, which is not a field in the sections
                keywords = keywords.replace("runs", "")
            routed[section] = keywords

    return routed

if __name__ == "__main__":
    test_query = "What are the hyperparameters and metrics for the latest runs?" ## change this to represent the examples of queries you want to test

    rewritten = rewrite_query(test_query)

    print("Original Query:", test_query)

    for section in rewritten:
        print("Rewritten Query Section:", rewritten[section])
    