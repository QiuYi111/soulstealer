from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log, Input
from textual.containers import Container, Horizontal, Vertical
from omegaconf import DictConfig
from internal.domain.court import CourtSession
from internal.domain.agent import SuspectAgent
from internal.infrastructure.llm import LLMClient
import os

class SoulstealerTUI(App):
    """The main Terminal User Interface for Soulstealer (MVP 1.0)."""
    
    def __init__(self, cfg: DictConfig = None):
        super().__init__()
        self.cfg = cfg
        self.session = CourtSession("德清县令", "阿二")
        soul = "你是一个胆小的乞丐，名叫阿二。你因为形迹可疑被抓，现在正面临严审。你非常害怕疼痛，但在极端恐惧下也可能胡言乱语攀咬他人。"
        self.agent = SuspectAgent("阿二", soul)
        
        # Load API key from config or env
        api_key = os.getenv("LLM_API_KEY") or self.cfg.llm.get("api_key", "")
        self.llm = LLMClient(api_key=api_key, base_url=self.cfg.llm.base_url)

    CSS = """
    Screen {
        background: $surface;
    }
    #main_container {
        height: 100%;
        display: flex;
        flex-direction: column;
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
    #input_panel {
        height: auto;
        border: solid $success;
        padding: 1;
    }
    """
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]

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
            with Vertical(id="input_panel"):
                yield Input(placeholder="输入指令 (例如: /torture 夹棍 谁指使你的？) 或直接输入问题", id="command_input")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "乾隆模拟器 - 《叫魂》MVP"
        self._update_status()
        self.query_one("#court_log", Log).write_line("🏛️ 德清县衙审讯室。嫌犯阿二已被带上。")

    def _update_status(self):
        status = self.query_one("#status_display", Static)
        s = self.session.state
        status.update(
            f"👤 嫌犯: {self.session.suspect}\n"
            f"❤️ 健康: {s.health} | 🔥 疼痛: {s.pain} | 💧 饥渴: {s.thirst}"
        )

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
        else:
            # Normal questioning
            self.session.apply_torture("言语", text)
            log.write_line(f"👤 审问官：{text}")

        self._update_status()
        
        # Get agent response
        log.write_line("⏳ 嫌犯正在思考...")
        response = self.agent.get_response(self.session.state, self.session.full_history, self.llm)
        self.session.add_suspect_response(response)
        
        log.write_line(f"🧟 {self.session.suspect}：{response}")
        self._update_status()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

def run_tui(cfg: DictConfig = None):
    app = SoulstealerTUI(cfg)
    app.run()

