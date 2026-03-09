from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json

@dataclass
class SuspectState:
    health: int = 100
    pain: int = 0
    thirst: int = 0
    hunger: int = 0
    fainted: bool = False

class CourtSession:
    """
    管理单次庭审（审讯）的核心黑盒引擎。
    仅负责维护生理状态、动作逻辑与原始记录。
    没有任何硬编码的公文内容，所有的格式化输出建议由 Agent 在特定的 Environment 指令下生成。
    """
    
    def __init__(self, interrogator_name: str, suspect_name: str, location_info: Optional[Dict[str, str]] = None, prisoner_list: Optional[List[str]] = None):
        self.interrogator = interrogator_name
        self.suspect = suspect_name
        self.location_info = location_info or {"province": "浙江", "prefecture": "湖州府", "county": "德清县"}
        self.prisoner_list = prisoner_list or [suspect_name]
        self.state = SuspectState()
        self.log: List[Dict[str, str]] = []
        self.raw_data: List[Dict[str, Any]] = [] # 结构化原始数据
        self.full_history: List[Dict[str, str]] = []
        
    def _get_physiological_desc(self) -> str:
        """中性描述身体状态。"""
        s = self.state
        descs = []
        if s.pain > 70:
            descs.append("由于受到重创，你正处于强烈的生理痛苦中，神志恍惚。")
        elif s.pain > 30:
            descs.append("你感到身体多处带有持续的、显著的痛感。")
        elif s.pain > 0:
            descs.append("你的身体感到轻微的不适与疼痛。")
        
        if s.health < 30:
            descs.append("你感到极度虚弱，体力不支。")
        if s.thirst > 50:
            descs.append("你感到喉咙异常干涩。")
        
        return " ".join(descs)

    def apply_torture(self, tool: str, question: str) -> Dict[str, Any]:
        """执行一个审问动作。"""
        if self.state.fainted:
            return {"status": "error", "message": "被审问者已昏厥"}

        # 物理模拟逻辑
        pain_inc = 0
        health_dec = 0
        if tool == "夹棍":
            pain_inc, health_dec = 30, 15
        elif tool == "赞指":
            pain_inc, health_dec = 20, 5
        elif tool == "鞭打":
            pain_inc, health_dec = 15, 8
        elif tool == "掌嘴":
            pain_inc, health_dec = 10, 2
        elif tool == "压踝":
            pain_inc, health_dec = 40, 20
        elif tool == "不给水":
            self.state.thirst += 40
        else:
            pain_inc = 2
            
        self.state.pain += pain_inc
        self.state.health -= health_dec
        
        if self.state.pain >= 100:
            self.state.fainted = True
            event_type = "fainted"
        elif self.state.health <= 0:
            self.state.health = 0
            event_type = "death"
        else:
            event_type = "action"
            
        action_record = {
            "type": event_type,
            "tool": tool,
            "question": question,
            "state_snapshot": {
                "pain": self.state.pain,
                "health": self.state.health
            }
        }
        
        self.log.append({"role": "system", "content": f"动作：{tool}"})
        self.log.append({"role": "interrogator", "content": question})
        self.raw_data.append({"actor": self.interrogator, "action": "question", "detail": action_record})
        self.full_history.append({"role": "user", "content": f"（审问官：）{question}"})
        
        return action_record

    def add_suspect_response(self, content: str):
        self.log.append({"role": "suspect", "content": content})
        self.raw_data.append({"actor": self.suspect, "action": "answer", "content": content})
        self.full_history.append({"role": "assistant", "content": content})

    def _parse_commands(self, text: str) -> tuple[str, List[tuple[str, str, str]]]:
        """
        Parses commands in the format [[/command args]] or raw /command at start of lines.
        Returns (cleaned_text, list_of_commands) where list_of_commands is [(full_match, cmd_name, args)].
        """
        import re
        text = str(text)
        commands = []
        
        # 1. Parse [[/command args]]
        pattern_bracket = re.compile(r'\[\[(/[\w_]+)\s*([^\]]*)\]\]')
        for match in pattern_bracket.finditer(text):
            commands.append((match.group(0), match.group(1), match.group(2).strip()))
        
        cleaned_text = pattern_bracket.sub("", text).strip()
        
        # 2. Parse raw /command at the beginning of the text or new lines
        pattern_raw = re.compile(r'^(/[\w_]+)\s*(.*)', re.MULTILINE)
        for match in pattern_raw.finditer(cleaned_text):
            # Check if this command was already captured by bracket pattern (unlikely but safe)
            full_match = match.group(0)
            cmd_name = match.group(1)
            args = match.group(2).strip()
            
            # Avoid duplicating or capturing dialogue as commands if they don't look like commands
            # Usually /commands are followed by a space and then args
            commands.append((full_match, cmd_name, args))
        
        # Clean up the raw commands from text if they were processed
        cleaned_text = pattern_raw.sub("", cleaned_text).strip()
        
        return cleaned_text, commands

    def run_auto_step(self, official_agent: Any, suspect_agent: Any, llm: Any, model: str, returned_memorials: Optional[str] = None) -> bool:
        """运行一个回合。"""
        if self.state.fainted or self.state.health <= 0:
            return False

        # 1. 审问官
        loc_str = f"{self.location_info['province']}{self.location_info['prefecture']}{self.location_info['county']}公堂"
        prisoners_str = "、".join(self.prisoner_list)
        scene_ctx_off = (
            f"当前场景：{loc_str}。\n"
            f"【在押名册 (Prisoner Registry)】：{prisoners_str}。\n"
            f"重要提示：当前堂上仅有 {self.suspect} 在场受审。你无法当堂传唤名册之外或不在现场的人员。"
        )
        scene_inst_off = (
            "你正在履行司法审讯职责。请直接进行提问或使用刑讯工具。\n"
            "如果你认为审讯已经可以结束（例如已获得口供、嫌犯已招认、或认为无需再审），请使用 [[/finish]] 指令。\n"
            "如果你发现了嫌犯供词中的矛盾、新的线索或任何值得日后查阅的信息，请务必使用 [[/update_memory 内容]] 指令先进行记录。\n"
            "严禁进行任何神态、心理或情境描写，只输出你的动作指令或公堂话语。\n"
            "可选工具：夹棍, 赞指, 鞭打, 掌嘴, 压踝, 不给水, 言语, [[/finish]]。\n"
        )
        
        prompt_off = official_agent.generate_prompt(scene_ctx_off, scene_inst_off, ["/torture", "/read_memory"], returned_memorials=returned_memorials)
        user_off = f"当前堂上记录：\n{json.dumps(self.log[-4:], ensure_ascii=False)}"
        
        resp_off_raw = official_agent.get_response(llm, prompt_off, user_off, model=model)
        dialogue_off, cmds_off = self._parse_commands(resp_off_raw)

        # Handle Commands
        has_read_memory = False
        for full, cmd, args in cmds_off:
            if cmd == "/update_memory":
                if args:
                    official_agent.add_memory(args)
                    official_agent.save_memory()
            elif cmd == "/read_memory":
                has_read_memory = True
            elif cmd == "/finish":
                self.log.append({"role": "system", "content": "审讯结束：知县下令收审。"})
                self.raw_data.append({"actor": self.interrogator, "action": "finish", "detail": "知县下令结束审讯"})
                return False
            elif cmd == "/torture":
                parts = args.split(" ", 1)
                tool = parts[0] if parts[0] else "言语"
                question = parts[1] if len(parts) > 1 else dialogue_off # fallback to dialogue if no question in args
                self.apply_torture(tool, question)
                # If we did torture, the "action" part of the turn is done
        
        if has_read_memory:
            memory_data = official_agent.get_formatted_memory()
            user_off += f"\n\n你的记忆查询结果：\n{memory_data}\n请重新审视情况。"
            # Re-generate with memory context
            resp_off_raw = official_agent.get_response(llm, prompt_off, user_off, model=model)
            dialogue_off, cmds_off = self._parse_commands(resp_off_raw)
            # Re-parse for action (torture/finish) if any
            for full, cmd, args in cmds_off:
                if cmd == "/torture":
                    parts = args.split(" ", 1)
                    tool = parts[0]
                    question = parts[1] if len(parts) > 1 else dialogue_off
                    self.apply_torture(tool, question)
                elif cmd == "/finish":
                    return False

        # Fallback if no torture command but dialogue exists
        if not any(c[1] == "/torture" for c in cmds_off) and dialogue_off:
            self.apply_torture("言语", dialogue_off)

        if self.state.fainted or self.state.health <= 0:
            return False

        # 2. 嫌犯
        scene_ctx_sus = f"当前场景：{loc_str}。生理状态：{self._get_physiological_desc()}"
        scene_inst_sus = (
            "你正在接受讯问。请仅输出你的供述或反应。严禁进入任何文学性的心理或神态描述。\n"
            "基于你的身份背景和当前生理痛苦做出最直接的回应。\n"
            "如果你有意记录某些想法，请使用 [[/update_memory 内容]]。"
        )
        
        prompt_sus = suspect_agent.generate_prompt(scene_ctx_sus, scene_inst_sus, ["/read_memory"])
        user_sus = f"审问官施加了：{self.log[-1]['content']}"
        
        resp_sus_raw = suspect_agent.get_response(llm, prompt_sus, user_sus, model=model)
        dialogue_sus, cmds_sus = self._parse_commands(resp_sus_raw)

        for full, cmd, args in cmds_sus:
            if cmd == "/update_memory" and args:
                suspect_agent.add_memory(args)
                suspect_agent.save_memory()
            elif cmd == "/read_memory":
                memory_data = suspect_agent.get_formatted_memory()
                user_sus += f"\n\n你的记忆查询结果：\n{memory_data}\n请继续。"
                resp_sus_raw = suspect_agent.get_response(llm, prompt_sus, user_sus, model=model)
                dialogue_sus, _ = self._parse_commands(resp_sus_raw)

        # Record suspect response
        self.add_suspect_response(dialogue_sus or "（唯唯诺诺，不发一言）")
        
        return True

    def get_raw_log(self) -> str:
        """以可读字符串形式导出所有原始事实。"""
        lines = []
        for entry in self.raw_data:
            if entry['action'] == "question":
                d = entry['detail']
                lines.append(f"[动作] {entry['actor']} 使用了 {d['tool']}，提问：‘{d['question']}’")
            else:
                lines.append(f"[回答] {entry['actor']}：‘{entry['content']}’")
        return "\n".join(lines)
