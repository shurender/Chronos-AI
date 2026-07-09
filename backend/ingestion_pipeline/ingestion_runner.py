import json
from pathlib import Path

from parsers.github_parser import parse_github_commits, parse_github_issues
from parsers.slack_parser import parse_slack_export
from parsers.notion_parser import parse_notion_markdown
from parsers.pdf_parser import parse_pdf_resume

BASE_DIR = Path(__file__).resolve().parent
RAW_SOURCES_DIR = BASE_DIR / "raw_sources"
OUTPUT_PATH = BASE_DIR / "ingestion_output.jsonl"

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
    github_file = RAW_SOURCES_DIR / "sample_github.json"
    if github_file.exists():
        print("Parsing GitHub data...")
        with github_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            all_chunks.extend(parse_github_commits(data.get("commits", []), "Chronos-AI"))
            all_chunks.extend(parse_github_issues(data.get("issues", []), "Chronos-AI"))

    # 2. Parse Slack Mock Data
    slack_file = RAW_SOURCES_DIR / "sample_slack.json"
    if slack_file.exists():
        print("Parsing Slack data...")
        with slack_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            all_chunks.extend(parse_slack_export(data, "dev-team"))

    # 3. Parse Notion Mock Data
    notion_file = RAW_SOURCES_DIR / "sample_notion.json"
    if notion_file.exists():
        print("Parsing Notion markdown data...")
        with notion_file.open("r", encoding="utf-8") as f:
            content = f.read()
            all_chunks.extend(parse_notion_markdown(content, str(notion_file), "Project Specs"))

    # 4. Parse PDF Resume
    pdf_file = RAW_SOURCES_DIR / "sample_resume.pdf"
    if pdf_file.exists():
        print("Parsing PDF Resume...")
        all_chunks.extend(parse_pdf_resume(str(pdf_file), author="Jane Doe"))

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(all_chunks)} chunks to {OUTPUT_PATH} successfully.")

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