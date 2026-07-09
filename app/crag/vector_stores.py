
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Initialize the embedding model

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", 
                                         encode_kwargs={"normalize_embeddings": True})

# Initialize the Chroma vector store with the embedding model and specify the persist directory and collection name
vector_store = Chroma(
        embedding_function=embedding_model,
        persist_directory= "./chroma_db",
        collection_name="mlflow_runs"
    )
