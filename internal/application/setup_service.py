import asyncio
from typing import List, Dict, Callable, Optional, Any
from internal.domain.agent_builder import AgentBuilder
from internal.rag.retriever import SoulstealerRetriever

class SetupService:
    """Service to handle heavy initializations and scalable agent generation."""

    def __init__(self, retriever: SoulstealerRetriever, llm: Any, model: str = "deepseek-chat", max_concurrency: int = 10):
        self.retriever = retriever
        self.llm = llm
        self.model = model
        self.max_concurrency = max_concurrency

    async def batch_generate_agents(self, requests: List[Dict[str, str]], progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[bool]:
        """
        Batch generate agents concurrently with rate limiting (semaphore).
        Because AgentBuilder uses synchronous operations, we run it in thread pool.
        
        Args:
            requests: List of dictionaries containing "save_dir", "name", "desc".
            progress_callback: Optional callback fn(completed: int, total: int, status_msg: str)
            
        Returns:
            List of boolean results indicating success for each request.
        """
        semaphore = asyncio.Semaphore(self.max_concurrency)
        builder = AgentBuilder(self.retriever, self.llm, model=self.model)
        
        total = len(requests)
        completed = 0
        
        async def _build(req: Dict[str, str]) -> bool:
            nonlocal completed
            save_dir = req["save_dir"]
            name = req["name"]
            desc = req["desc"]
            
            async with semaphore:
                # AgentBuilder.build_agent is synchronous (I/O heavy), so run in thread
                success = await asyncio.to_thread(builder.build_agent, save_dir, name, desc)
                
            completed += 1
            if progress_callback:
                status = f"Generated {name} ({'Success' if success else 'Failed'})"
                progress_callback(completed, total, status)
                
            return success

        tasks = [_build(req) for req in requests]
        results = await asyncio.gather(*tasks)
        return list(results)
