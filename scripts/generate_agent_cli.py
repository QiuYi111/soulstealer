import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from internal.infrastructure.llm import LLMClient
from internal.rag.retriever import SoulstealerRetriever
from internal.domain.agent_builder import AgentBuilder

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Generate a Soulstealer Agent using RAG and LLM.")
    parser.add_argument("--name", type=str, required=True, help="Name of the agent (e.g., '阿二')")
    parser.add_argument("--request", type=str, required=True, help="Who is this person? (e.g., '德清县的一名乞丐')")
    parser.add_argument("--model", type=str, default="qwen/qwen-2.5-72b-instruct", help="OpenRouter model string")
    parser.add_argument("--outdir", type=str, default="saves/generated_agents", help="Base directory for saves")
    
    args = parser.parse_args()
    
    # Try to load from config if .env fails
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    
    config_path = Path("conf/config.yaml")
    if not api_key and config_path.exists():
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                api_key = config.get('llm', {}).get('api_key')
                base_url = config.get('llm', {}).get('base_url', base_url)
        except Exception as e:
            print(f"Warning: Could not read config.yaml: {e}")

    if not api_key:
        print("Error: LLM_API_KEY not set in environment or conf/config.yaml.")
        return

    vector_db_dir = "data/vectordb"
    if not os.path.exists(vector_db_dir):
        print(f"Error: Vector DB directory {vector_db_dir} not found. Please run build_vector_db.py first.")
        return

    # 1. Initialize Components
    print("--- Initializing RAG Retriever ---")
    retriever = SoulstealerRetriever(vector_store_dir=vector_db_dir)
    
    print("--- Initializing LLM Client ---")
    llm = LLMClient(api_key=api_key, base_url=base_url)
    
    builder = AgentBuilder(retriever=retriever, llm_client=llm, model=args.model)
    
    # 2. Build Agent
    agent_dir = os.path.join(args.outdir, args.name)
    print(f"--- Generating Agent: {args.name} ---")
    success = builder.build_agent(agent_dir, args.name, args.request)
    
    if success:
        print(f"\nSuccess! Agent files generated at: {agent_dir}")
        print(f"Check {os.path.join(agent_dir, 'Soul.md')} for biography.")
        print(f"Check {os.path.join(agent_dir, 'trait.json')} for granular traits.")
    else:
        print("\nFailed to generate agent.")

if __name__ == "__main__":
    main()
