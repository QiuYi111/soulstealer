import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from internal.domain.court import CourtSession
from internal.domain.letters import LettersSystem
from internal.domain.cases import CasesSystem
from internal.domain.agent import Agent

class GameSessionService:
    """Service to orchestrate the core gameplay loop: questioning, memory, cases, and letters."""
    
    def __init__(
        self, 
        llm: Any, 
        llm_model: str,
        letters_system: LettersSystem,
        cases_system: CasesSystem,
        magistrate: Agent,
        suspect: Agent
    ):
        self.llm = llm
        self.llm_model = llm_model
        self.letters_system = letters_system
        self.cases_system = cases_system
        self.magistrate = magistrate
        self.suspect = suspect
        self.current_session: Optional[CourtSession] = None

    async def run_simulation_sequence(self, max_steps: int = 10) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes an automated sequence of court session steps, case summarization, and memorial drafting.
        Yields progress events that the UI can render in real time.
        """
        prisoner_list = [self.suspect.name]
        self.current_session = CourtSession(self.magistrate.name, self.suspect.name, prisoner_list=prisoner_list)
        
        # Prepare returned memorials context
        returned_memorials = ""
        relevant_reports = [r for r in self.letters_system.reports if r.rescripts][-3:]
        for r in relevant_reports:
            res_contents = [res.content if hasattr(res, 'content') else res['content'] for res in r.rescripts]
            res_str = "; ".join(res_contents)
            returned_memorials += f"《{r.type} ID:{r.id}》\n内容：{r.content}\n皇帝朱批：{res_str}\n"

        # Step 1: Court Session Simulation
        for _ in range(max_steps):
            # run_auto_step makes LLM calls, so run it in a thread
            success = await asyncio.to_thread(
                self.current_session.run_auto_step,
                self.magistrate,
                self.suspect,
                self.llm,
                self.llm_model,
                returned_memorials=returned_memorials
            )
            
            # Yield new log entries
            if len(self.current_session.log) >= 2:
                last_entry = self.current_session.log[-1]
                if last_entry['role'] == 'system':
                    yield {"type": "log", "speaker": "magistrate", "content": last_entry['content']}
                else:
                    yield {"type": "log", "speaker": "magistrate", "content": self.current_session.log[-2]['content']}
                    yield {"type": "log", "speaker": "suspect", "content": last_entry['content']}
            
            if not success:
                break
                
        raw_log = self.current_session.get_raw_log()
        
        # Step 2: Memory Update
        summary_ctx = "审讯已结束。作为知县，请总结本次审讯的关键点、嫌犯的矛盾之处或你的新发现，以便日后查阅。请使用 [[/update_memory 内容]] 指令记录。"
        prompt = self.magistrate.generate_prompt(summary_ctx, "记录审讯摘要", available_tools=["/read_memory"])
        summary_resp_raw = await asyncio.to_thread(
            self.magistrate.get_response,
            self.llm,
            prompt,
            f"审讯实录：\n{raw_log}",
            model=self.llm_model
        )
        
        _, summary_cmds = self.current_session._parse_commands(summary_resp_raw)
        for full, cmd, args in summary_cmds:
            if cmd == "/update_memory" and args:
                self.magistrate.add_memory(args)
                self.magistrate.save_memory()
                yield {"type": "log", "speaker": "system", "content": "📓 知县已将审讯摘要存入记忆。"}
                break

        # Step 3: Case Generation
        loc = self.current_session.location_info
        polish_ctx = f"你正处于{loc['province']}{loc['prefecture']}{loc['county']}县衙。审讯已结束。请将原始审讯记录整理成一份言辞严谨、逻辑清晰的正式案卷。"
        polish_prompt = self.magistrate.generate_prompt(polish_ctx, "整理正式案卷")
        polished_case = await asyncio.to_thread(
            self.magistrate.get_response,
            self.llm,
            polish_prompt,
            f"原始事实记录：\n{raw_log}",
            model=self.llm_model
        )
        
        # Step 4: Memorial Drafting
        draft_ctx = (
            "你正在撰写上呈给乾隆皇帝的正式奏折。请基于以下案卷内容进行深加工，不仅要陈述事实，更要体现出官员的政治立场。请以第一人称（臣）称呼自己。\n"
            "【强制格式要求】\n"
            "1. 第一行必须仅包含奏折类型：‘密折’ 或 ‘明发奏折’。\n"
            "2. 从第二行开始为奏折正文，必须符合清代奏折文体规范。\n"
            "3. 严禁尝试调用任何 API 指令（如 /read_memory 或 /torture）。"
        )
        draft_prompt = self.magistrate.generate_prompt(draft_ctx, "撰写奏折")
        full_draft_resp = await asyncio.to_thread(
            self.magistrate.get_response,
            self.llm,
            draft_prompt,
            f"案卷内容副本：\n{polished_case}",
            model=self.llm_model
        )
        
        # Parse and save report
        if "\n" in full_draft_resp:
            r_type, r_content = full_draft_resp.split("\n", 1)
            report_type = "明发奏折" if "明" in r_type else "密折"
            report_content = r_content.strip()
        else:
            report_type, report_content = "密折", full_draft_resp

        report = self.letters_system.add_report(report_type, report_content, self.magistrate.name)
        report.raw_case_data = raw_log
        report.polished_case_data = polished_case
        
        # Save to disk
        self.letters_system.save_to_file("data/letters.json")
        self.cases_system.save_case(report.id, raw_log, polished_case)
        
        yield {
            "type": "report", 
            "report_id": report.id, 
            "report_type": report_type, 
            "author": self.magistrate.name
        }
