import json
import os
import re
from dotenv import load_dotenv 
import anthropic
from jsonschema import ValidationError
from pydantic_core import ValidationError
import transformers
import torch

from app.config import SECTION, SECTION, CORPUS_VOCAB_PATH
from app.crag.prompt import REWRITE_PROMPT_TEMPLATE, GENERATE_PROMPT, JUDGE_PROMPT

from app.crag.response import GenerateResponse, JudgeResponse, RewriteQueryResponse

## LLM Pipeline
load_dotenv() 

api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)
model_name = "claude-haiku-4-5-20251001" 

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
        if section is "info":
            continue  # Skip the "info" section as it is not a valid section for query rewriting
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
    Falls back to the full section vocabulary if the LLM output is unusable.
    """
    vocab = generate_section()
    section_vocab = "\n".join(f"{k}: {v}" for k, v in vocab.items())
    prompt = REWRITE_PROMPT_TEMPLATE.format(section_queries=section_vocab)

    response = client.messages.create(
        model=model_name,
        max_tokens=150,
        system=prompt,
        messages=[{"role": "user", "content": query}],
    )
    response_text = response.content[0].text
    print(f"[rewrite_query] RAW OUTPUT:\n{response_text!r}\n")

    rewritten = RewriteQueryResponse({})
    m = re.search(r"\{.*\}", response_text, re.DOTALL)
    if m:
        try:
            rewritten = RewriteQueryResponse.model_validate_json(m.group(0))
        except (ValueError, ValidationError) as e:
            print(f"[rewrite_query] validation failed: {e}")

    if rewritten.is_empty():
        print("[rewrite_query] falling back to full section vocabulary")
        return dict(vocab)

    return rewritten.as_queries()

## This takes so much time, find a better llm

def generate_report(query: str, aggregates: str) -> GenerateResponse:
    """
    Generates a query based on the user input using the LLM pipeline.
    """
    user_message = f"QUERY: {query} \nMLflow experiment data: {aggregates}"

    messages = [
        {"role": "user", "content": user_message},
    ]
    response = client.messages.create(
        model=model_name,
        max_tokens=500,
        system=GENERATE_PROMPT,
        messages=messages,
    )
    response_text = response.content[0].text

    m = re.search(r"\{.*\}", response_text, re.DOTALL)   
    if not m:
        raise ValueError(f"No JSON object found in: {response_text[:120]!r}")
    
    response_text = m.group(0)

    try:
        generated_response = GenerateResponse.model_validate_json(response_text)
        return generated_response
    except Exception as e:
        print(f"[generate_query] Failed to parse response: {e}")
        return GenerateResponse(
            answer="",
            extracted={}
        )


def grade_report(query: str, answer: str, aggregates: str) -> JudgeResponse:
    """
    Grades the generated answer based on the user query and the provided facts (aggregates).
    Returns a dictionary containing the verdict and explanation.
    """

    user_message = f"QUERY: {query}\nANSWER: {answer} \n MLflow experiment evidence: {aggregates}"

    messages = [
        {"role": "user", "content": user_message},
    ]
    
    response = client.messages.create(
        model=model_name,
        max_tokens=500,
        system=JUDGE_PROMPT,
        messages=messages,
    )
    response_text = response.content[0].text
    print(f"[grade_response] RAW OUTPUT:\n{response_text!r}\n")  

    m = re.search(r"\{.*\}", response_text, re.DOTALL)   
    if not m:
        raise ValueError(f"No JSON object found in: {response_text[:120]!r}")
    
    response_text = m.group(0)

    try:
        graded_response = JudgeResponse.model_validate_json(response_text)
        return graded_response
    except Exception as e:
        print(f"[grade_response] Failed to parse response: {e}")
        return JudgeResponse(
            verdict="unsupported",
            reason="Failed to parse LLM output.",
            evidence_ids=[],
            related_run_ids=[],
            missing_evidence=[]
        )

if __name__ == "__main__":
    test_query = "What are the hyperparameters and metrics for the latest runs?" ## change this to represent the examples of queries you want to test

    rewritten = rewrite_query(test_query)

    print("Original Query:", test_query)

    for section in rewritten:
        print("Rewritten Query Section:", rewritten[section])
    