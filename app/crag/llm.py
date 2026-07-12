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
    Rewrite a vague user query into corpus-vocabulary section queries.
    Falls back to the full section vocabulary if the LLM output is unparseable.
    """
    vocab = generate_section()          # {section: keywords} — info already excluded
    section_vocab = "\n".join(f"{k}: {v}" for k, v in vocab.items())

    prompt = REWRITE_PROMPT_TEMPLATE.format(section_queries=section_vocab)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": query},
    ]
    response = pipeline(messages, max_new_tokens=100, do_sample=False)
    response_text = response[0]["generated_text"][-1]["content"]

    print(f"[rewrite_query] RAW OUTPUT:\n{response_text!r}\n")      # ① see the failure

    routed = {}
    for line in response_text.splitlines():
        if ":" not in line:
            continue
        section, _, keywords = line.partition(":")
        section = section.strip().strip("*-#• ").lower()             # ② tolerate md/bullets
        keywords = keywords.strip().strip("*` ")
        print(f"Detected section: '{section}', keywords: '{keywords}'")
        if section in SECTION and keywords:
            routed[section] = keywords

    if not routed:                                                    # ③ fail-safe fallback
        print("[rewrite_query] nothing parsed — falling back to full section vocabulary")
        routed = dict(vocab)

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
        do_sample=False,   
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
        do_sample=False,      
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
    