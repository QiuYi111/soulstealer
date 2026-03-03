from textual.app import App, ComposeResult, RenderResult
from textual.widgets import Header, Footer, Static, Log, Input, LoadingIndicator
from textual.containers import Container, Horizontal, Vertical
from textual import work
from textual.worker import get_current_worker
from omegaconf import DictConfig
from internal.domain.court import CourtSession, SuspectState
from internal.domain.agent import Agent
from internal.domain.letters import LettersSystem
from internal.infrastructure.llm import LLMClient
import os

class SoulstealerTUI(App):
    """The main Terminal User Interface for Soulstealer (MVP 1.0)."""
    
    def __init__(self, cfg: DictConfig = None):
        super().__init__()
        self.cfg = cfg
        self.session = CourtSession("德清县令", "阿二")
        
        # Unified Agents initialized from their respective directories
        self.suspect_agent = Agent("agents/aer")
        self.official_agent = Agent("agents/magistrate")
        
        # Letters System
        self.letters = LettersSystem()
        
        # Load API key and model from config or env
        self.llm_model = self.cfg.llm.get("model", "deepseek/deepseek-chat") if self.cfg else "deepseek/deepseek-chat"
        api_key = os.getenv("LLM_API_KEY") or (self.cfg.llm.get("api_key", "") if self.cfg else "")
        base_url = self.cfg.llm.base_url if self.cfg else "https://openrouter.ai/api/v1"
        self.llm = LLMClient(api_key=api_key, base_url=base_url)

    CSS = """
    Screen {
        background: $surface;
    }
    #main_container {
        height: 100%;
    }
    #letters_panel {
        width: 30%;
        border: solid $accent;
        padding: 1;
    }
    #cases_panel {
        width: 70%;
        border: solid $warning;
        padding: 1;
    }
    #status_display {
        background: $surface-lighten-1;
        padding: 1;
        margin-bottom: 1;
        border: round $warning;
    }
    #court_log {
        height: 1fr;
    }
    #report_content {
        height: 1fr;
        display: none;
        border: solid $accent;
        padding: 1;
    }
    #input_panel {
        height: auto;
        border: solid $success;
        padding: 1;
    }
    #loading_overlay {
        height: 3;
        content-align: center middle;
        background: $accent-darken-2;
        display: none;
    }
    """
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"), 
        ("q", "quit", "Quit"),
        ("c", "show_cases", "Show Cases"),
        ("l", "show_letters", "Show Letters")
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        with Container(id="main_container"):
            with Horizontal():
                with Vertical(id="letters_panel"):
                    yield Static("📖 奏折系统 (Letters)\n\n[暂无新奏折]", id="letters_display")
                with Vertical(id="cases_panel"):
                    yield Static("", id="status_display")
                    yield Log(id="court_log")
                    yield Static("", id="report_content")
            with Vertical(id="input_panel"):
                yield Static("⏳ 正在思考中...", id="loading_overlay")
                yield Input(placeholder="指令: /torture [工具] [问题] | /draft [secret/direct] | 或直接输入...", id="command_input")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "乾隆模拟器 - 《叫魂》MVP"
        self._update_status()
        self.query_one("#court_log", Log).write_line(f"🏛️ 德清县衙审讯室。嫌犯{self.suspect_agent.name}已被带上。")

    def _update_status(self):
        status = self.query_one("#status_display", Static)
        s = self.session.state
        status_text = f"👤 嫌犯: {self.session.suspect}\n"
        status_text += f"❤️ 健康: {s.health} | 🔥 疼痛: {s.pain} | 💧 饥渴: {s.thirst}"
        
        if s.health <= 0:
            status_text += " [已死亡]"
        elif s.fainted:
            status_text += " [已昏厥]"
            
        status.update(status_text)

    def _update_letters_list(self):
        display = self.query_one("#letters_display", Static)
        if not self.letters.reports:
            display.update("📖 奏折系统 (Letters)\n\n[暂无新奏折]")
            return
        
        text = "📖 奏折系统 (Letters)\n\n"
        for r in self.letters.reports:
            marker = "㊙️" if r.type == "密折" else "📜"
            text += f"{marker} ID:{r.id} | {r.type}\n"
        
        text += "\n使用 /view [ID] 查看详情"
        display.update(text)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        
        input_widget = self.query_one("#command_input", Input)
        input_widget.value = ""
        
        log = self.query_one("#court_log", Log)
        
        if text.startswith("/torture"):
            parts = text.split(" ", 2)
            tool = parts[1] if len(parts) > 1 else "轻敲"
            question = parts[2] if len(parts) > 2 else "快说！"
            
            action_desc = self.session.apply_torture(tool, question)
            log.write_line(f"❌ {action_desc}")
            log.write_line(f"👤 审问官：{question}")
            self._fetch_suspect_response()
        elif text.startswith("/draft"):
            is_secret = "secret" in text.lower()
            self._fetch_official_report(is_secret)
        elif text.startswith("/view"):
            parts = text.split(" ")
            if len(parts) > 1 and parts[1].isdigit():
                idx = int(parts[1])
                report = self.letters.get_report(idx)
                if report:
                    self.action_show_letters()
                    display = self.query_one("#report_content", Static)
                    display.update(
                        f"【{report.type}】\n"
                        f"作者：{report.author}\n"
                        f"时间：{report.timestamp}\n\n"
                        f"{report.content}"
                    )
                else:
                    log.write_line(f"⚠️ 未找到 ID 为 {idx} 的奏折")
        else:
            # Normal questioning
            self.session.apply_torture("言语", text)
            log.write_line(f"👤 审问官：{text}")
            self._fetch_suspect_response()

        self._update_status()

    def _get_physiological_desc(self, state: SuspectState) -> str:
        """Helper to generate physiological context for the unified Agent."""
        pain_desc = ""
        if state.pain <= 30: pain_desc = "隐隐作痛"
        elif state.pain <= 70: pain_desc = "钻心剜骨"
        else: pain_desc = "意识模糊，剧痛让你随时想自杀"

        health_desc = ""
        if state.health >= 80: health_desc = "尚能支撑"
        elif state.health >= 30: health_desc = "气息奄奄，伤口开始发炎脓肿"
        else: health_desc = "命悬一线，随时可能断气"

        thirst_desc = ""
        if state.thirst > 80:
            thirst_desc = "喉咙如火烧，嘴唇干裂出血，你为了喝一口水愿意做任何事"

        if state.fainted:
            return "你已经痛得昏死过去，意识断断续续。"
        
        res = f"你当前的状态：\n- 疼痛：{pain_desc}\n- 健康：{health_desc}\n"
        if thirst_desc:
            res += f"- 饥渴：{thirst_desc}\n"
        return res

    @work(exclusive=True, thread=True)
    def _fetch_suspect_response(self):
        log = self.query_one("#court_log", Log)
        overlay = self.query_one("#loading_overlay", Static)
        overlay.styles.display = "block"
        
        try:
            # Prepare initial call
            phys_context = self._get_physiological_desc(self.session.state)
            current_task = "你正在接受审问。你可以通过指令获取资源，或直接回答。"
            # Suspect can only read their own data
            available_tools = [
                "/read_memory : 读取你的过往记忆。",
                "/read_relationships : 查看你与其他人的关系。"
            ]
            
            # Simulated Tool Loop (Max 3 iterations)
            last_response = ""
            for _ in range(3):
                system_prompt = self.suspect_agent.generate_prompt(current_task, phys_context, available_tools)
                user_prompt = self.session.full_history[-1]["content"] if self.session.full_history else "..."
                if last_response:
                    user_prompt = f"系统返回结果：{last_response}\n请继续。"

                response = self.suspect_agent.get_response(self.llm, system_prompt, user_prompt, model=self.llm_model)
                
                # Command detection
                if response.startswith("/read_memory"):
                    last_response = f"你的记忆内容如下：{json.dumps(self.suspect_agent.memory, ensure_ascii=False)}"
                    log.write_line("🔍 嫌犯正在回忆...")
                    continue
                elif response.startswith("/read_relationships"):
                    last_response = f"你的关系网如下：{json.dumps(self.suspect_agent.relationships, ensure_ascii=False)}"
                    log.write_line("🔍 嫌犯正在查看人际关系...")
                    continue
                else:
                    # Final reaction or normal response
                    worker = get_current_worker()
                    if not worker.is_cancelled:
                        self.session.add_suspect_response(response)
                        log.write_line(f"👤 {self.suspect_agent.name}：{response}")
                        self._update_status()
                    break
        except Exception as e:
            log.write_line(f"⚠️ 无法获得回应: {str(e)}")
        finally:
            overlay.styles.display = "none"

    @work(exclusive=True, thread=True)
    def _fetch_official_report(self, is_secret: bool):
        log = self.query_one("#court_log", Log)
        overlay = self.query_one("#loading_overlay", Static)
        report_type_name = "密折" if is_secret else "明发奏折"
        overlay.update(f"✍️ 正在起草{report_type_name}...")
        overlay.styles.display = "block"
        
        try:
            # Prepare context
            log_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in self.session.log])
            current_task = (
                f"请根据下方的基层审讯记录（原案），以【{self.official_agent.name}】的身份撰写一份呈递给皇上的【{report_type_name}】。\n"
                "语言风格应符合清代官话，带有你的人设特征（如邀功、推卸责任、政治敏感等）。"
            )
            # Official can read their own data and use torture in court (though here they are drafting)
            available_tools = [
                "/read_memory : 读取你的过往记忆。",
                "/read_relationships : 查看你与其他人的关系。"
            ]

            last_response = ""
            for _ in range(3):
                system_prompt = self.official_agent.generate_prompt(current_task, available_tools=available_tools)
                user_prompt = f"以下是审讯记录：\n{log_text}"
                if last_response:
                    user_prompt = f"系统返回结果：{last_response}\n请继续撰写汇报内容："
                else:
                    user_prompt += "\n\n请写出汇报内容："

                response = self.official_agent.get_response(self.llm, system_prompt, user_prompt, model=self.llm_model)

                if response.startswith("/read_memory"):
                    last_response = f"你的记忆内容如下：{json.dumps(self.official_agent.memory, ensure_ascii=False)}"
                    log.write_line("🔍 县令正在翻阅过往笔记...")
                    continue
                elif response.startswith("/read_relationships"):
                    last_response = f"你的私人关系网如下：{json.dumps(self.official_agent.relationships, ensure_ascii=False)}"
                    log.write_line("🔍 县令正在思考各方势力关系...")
                    continue
                else:
                    worker = get_current_worker()
                    if not worker.is_cancelled:
                        self.letters.add_report(report_type_name, response, self.official_agent.name)
                        self.letters.save_to_file("reports.json")
                        log.write_line(f"✅ {report_type_name}起草完成并存入系统（已同步至 reports.json）。")
                        self._update_letters_list()
                        overlay.update("⏳ 正在思考中...")
                    break
        except Exception as e:
            log.write_line(f"⚠️ 起草失败: {str(e)}")
        finally:
            overlay.styles.display = "none"

    def action_show_cases(self):
        self.query_one("#court_log").styles.display = "block"
        self.query_one("#report_content").styles.display = "none"

    def action_show_letters(self):
        self.query_one("#court_log").styles.display = "none"
        self.query_one("#report_content").styles.display = "block"


def run_tui(cfg: DictConfig = None):
    app = SoulstealerTUI(cfg)
    app.run()
