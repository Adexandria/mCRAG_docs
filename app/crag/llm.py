import json

import transformers
import torch

from app.config import SECTION, SECTION, CORPUS_VOCAB_PATH
from app.crag.prompt import REWRITE_PROMPT_TEMPLATE, GENERATE_PROMPT, JUDGE_PROMPT


## LLM Pipeline

model_id = "meta-llama/Llama-3.2-3B-Instruct"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"dtype": torch.bfloat16},
    device_map="auto",
)


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

    prompt = REWRITE_PROMPT_TEMPLATE.format(section_queries=section_vocab)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": query},
    ]
    response = pipeline(
        messages,
        max_new_tokens=100,           
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

## This takes so much time, find a better llm

def generate_query(query: str, aggregates: str) -> str:
    """
    Generates a query based on the user input using the LLM pipeline.
    """
    prompt = GENERATE_PROMPT.format(aggregates=aggregates)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": query},
    ]
    response = pipeline(
        messages,
        max_new_tokens=500,      
    )
    response_text = response[0]["generated_text"][-1]["content"]

    return response_text

def grade_response(query: str, answer: str, aggregates: str) -> dict:
    """
    Grades the generated answer based on the user query and the provided facts (aggregates).
    Returns a dictionary containing the verdict and explanation.
    """
    prompt = JUDGE_PROMPT.format(aggregates=aggregates, answer=answer)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": query},
    ]
    response = pipeline(
        messages,
        max_new_tokens=100,          
    )
    response_text = response[0]["generated_text"][-1]["content"]

    try:
        verdict = json.loads(response_text)
    except json.JSONDecodeError:
        verdict = {"verdict": "fail", "explanation": "Failed to parse JSON from LLM response."}

    return verdict

if __name__ == "__main__":
    test_query = "What are the hyperparameters and metrics for the latest runs?" ## change this to represent the examples of queries you want to test

    rewritten = rewrite_query(test_query)

    print("Original Query:", test_query)

    for section in rewritten:
        print("Rewritten Query Section:", rewritten[section])
    