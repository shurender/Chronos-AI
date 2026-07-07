import json
import os
from parsers.github_parser import parse_github_commits, parse_github_issues
from parsers.slack_parser import parse_slack_export
from parsers.notion_parser import parse_notion_markdown
from parsers.pdf_parser import parse_pdf_resume

# Optional Vector DB setup
try:
    import chromadb
    import ollama
    from chromadb import EmbeddingFunction, Documents, Embeddings

    class NomicOllamaEmbedder(EmbeddingFunction):
        def __call__(self, input: Documents) -> Embeddings:
            embeddings = []
            for text in input:
                # Queries Ollama instance running nomic-embed-text locally
                response = ollama.embeddings(model="nomic-embed-text", prompt=text)
                embeddings.append(response["embedding"])
            return embeddings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

def main():
    all_chunks = []
    
    # 1. Parse GitHub Mock Data
    github_file = "test_data/sample_github.json"
    if os.path.exists(github_file):
        print("Parsing GitHub data...")
        with open(github_file, "r") as f:
            data = json.load(f)
            all_chunks.extend(parse_github_commits(data.get("commits", []), "Chronos-AI"))
            all_chunks.extend(parse_github_issues(data.get("issues", []), "Chronos-AI"))
            
    # 2. Parse Slack Mock Data
    slack_file = "test_data/sample_slack.json"
    if os.path.exists(slack_file):
        print("Parsing Slack data...")
        with open(slack_file, "r") as f:
            data = json.load(f)
            all_chunks.extend(parse_slack_export(data, "dev-team"))

    # 3. Parse Notion Mock Data
    notion_file = "test_data/sample_notion.md"
    if os.path.exists(notion_file):
        print("Parsing Notion markdown data...")
        with open(notion_file, "r") as f:
            content = f.read()
            all_chunks.extend(parse_notion_markdown(content, notion_file, "Project Specs"))

    # 4. Parse PDF Resume
    pdf_file = "test_data/sample_resume.pdf"
    if os.path.exists(pdf_file):
        print("Parsing PDF Resume...")
        all_chunks.extend(parse_pdf_resume(pdf_file, author="Jane Doe"))

    # Export structured output conforming to the required contract format
    output_path = "ingestion_output.jsonl"
    with open(output_path, "w") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + "\n")
            
    print(f"\nSaved {len(all_chunks)} chunks to {output_path} successfully.")

    # 5. Store inside the local vector database
    if CHROMA_AVAILABLE:
        print("\nChromaDB and Ollama libraries found. Proceeding with database ingestion...")
        try:
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = client.get_or_create_collection(
                name="chronos_memory", 
                embedding_function=NomicOllamaEmbedder()
            )
            
            ids = [c["chunk_id"] for c in all_chunks]
            documents = [c["raw_text"] for c in all_chunks]
            
            # Convert JSON structure dicts into standard flat string pairs for metadata fields
            metadata = []
            for c in all_chunks:
                flat_meta = {k: str(v) for k, v in c["metadata"].items()}
                flat_meta["source_type"] = c["source_type"]
                flat_meta["source_id"] = c["source_id"] or ""
                flat_meta["author"] = c["author"] or "unknown"
                flat_meta["timestamp"] = c["timestamp"] or "null"
                metadata.append(flat_meta)

            collection.add(ids=ids, documents=documents, metadatas=metadata)
            print(f"Stored {len(ids)} document embeddings in Chroma DB successfully.")
        except Exception as e:
            print(f"Chroma storage initialization bypassed: {e}.\nMake sure Ollama is running ('ollama run nomic-embed-text')")
    else:
        print("\nNote: chroma/ollama library not found in Python path. Skipping vector store step.")

if __name__ == "__main__":
    main()