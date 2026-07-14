import json
import os

from langchain_text_splitters import RecursiveJsonSplitter
from langchain_core.documents import Document
from app.config import CORPUS_VOCAB_PATH
from app.crag.vector_stores import vector_store
from collections import defaultdict

from app.retriever.extract_data import unwrap_run_data, flatten,get_all_runs_by_experiment_name, extract_keywords


def split_chunks(runs_data):
    """
    Split the run data into chunks and extract keywords for each section.
    """
    corpus_vocab = defaultdict(set)

    if os.path.exists(CORPUS_VOCAB_PATH):
        try:
            with open(CORPUS_VOCAB_PATH, "r") as f:
                data = json.load(f)
                for k, v in data.items():
                    corpus_vocab[k] = set(v)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read {CORPUS_VOCAB_PATH}: {e}. Starting fresh.")
    else:
        print(f"Vocabulary file not found at {CORPUS_VOCAB_PATH}. Initializing empty.")
    
    splitter = RecursiveJsonSplitter(max_chunk_size=300)

    print(f"Number of runs fetched: {len(runs_data)}")
    

    chunks = []
    for run in runs_data:
        unwrapped_run_data = unwrap_run_data(run)

        kw = extract_keywords(list(flatten(unwrapped_run_data)))
        for group, keywords in kw.items():
            corpus_vocab[group] |= keywords

        
        chunks.extend(split_run_chunks(unwrapped_run_data, splitter))


    print(f"Number of chunks created: {len(chunks)}")
    with open(CORPUS_VOCAB_PATH, "w") as f:
        json.dump({g: sorted(w) for g, w in corpus_vocab.items()}, f, indent=2)

    return chunks

def save_to_chroma(documents):
    """
    Save the documents to the Chroma vector store.
    """
    vector_store.add_documents(documents)


def split_run_chunks(run_data, splitter):
    """
    Split the run data into chunks and return a list of Document objects with metadata.
    """
    metadata = {
        "run_id": run_data["info"]["run_uuid"],
        "experiment_id": run_data["info"]["experiment_id"],
        "status": run_data["info"]["status"],
        "run_name": run_data["info"]["run_name"],
    }
    chunks = splitter.split_json(run_data)

    flattened_chunks = [list(flatten(chunk)) for chunk in chunks]
    print(f"Number of flattened chunks created for run {metadata['run_id']}: {len(flattened_chunks)}")

    return [
        Document(page_content=str(chunk), metadata={**metadata, "chunk_index": i}) 
        for i, chunk in enumerate(flattened_chunks)
    ]

    
if __name__ == "__main__":
    experiment_name = "Iris_Classification"
    runs_data = get_all_runs_by_experiment_name(experiment_name)
    flattened_chunks = split_chunks(runs_data)
    save_to_chroma(flattened_chunks)
