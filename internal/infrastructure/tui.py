from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log, Input, TextArea, Button, ListItem, ListView, LoadingIndicator
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Center
from textual.screen import Screen
from textual import work, on
from omegaconf import DictConfig
from internal.domain.agent import Agent
from internal.domain.letters import LettersSystem, Rescript
from internal.domain.cases import CasesSystem
from internal.infrastructure.llm import LLMClient
from internal.infrastructure.persistence import PersistenceManager
from internal.rag.retriever import SoulstealerRetriever
from internal.application.setup_service import SetupService
from internal.application.game_session_service import GameSessionService
from internal.application.archive_service import ArchiveService
import os
import re
import asyncio
from datetime import datetime

class MemorialEditor(TextArea):
    """一个模拟文本编辑器的奏折阅览与朱批插入组件"""
    
    BINDINGS = [
        Binding("i", "insert_rescript", "插入朱批", show=True),
        Binding("ctrl+s", "save_rescript", "保存朱批", show=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = "markdown"

    def action_insert_rescript(self) -> None:
        """在当前光标位置插入朱批占位符并进入编辑区"""
        res_placeholder = "[[朱批:在此输入内容]]"
        self.insert(res_placeholder)
        cursor_pos = self.cursor_location
        self.move_cursor((cursor_pos[0], cursor_pos[1] - 2))
        
    def _is_cursor_in_rescript(self) -> bool:
        """判断当前光标是否在朱批块内部"""
        row, col = self.cursor_location
        line_obj = self.get_line(row)
        line = line_obj.plain if hasattr(line_obj, "plain") else str(line_obj)
        
        pattern = re.compile(r'\[\[朱批:.*?\]\]')
        for match in pattern.finditer(line):
            start, end = match.span()
            if start + 5 <= col <= end - 2:
                return True
        return False

    def _get_rescript_range(self) -> tuple[int, int] | None:
        """获取当前光标所在朱批块的起始和结束列"""
        row, col = self.cursor_location
        line_obj = self.get_line(row)
        line = line_obj.plain if hasattr(line_obj, "plain") else str(line_obj)
        pattern = re.compile(r'\[\[朱批:.*?\]\]')
        for match in pattern.finditer(line):
            start, end = match.span()
            if start <= col <= end:
                return start, end
        return None

    def on_key(self, event) -> None:
        """拦截按键实现局部只读控制"""
        if event.key in ("up", "down", "left", "right", "home", "end", "pageup", "pagedown", "escape", "tab"):
            return

        if event.key == "i":
            if not self._is_cursor_in_rescript():
                self.action_insert_rescript()
                event.prevent_default()
                event.stop()
                return
            else:
                return

        if event.key == "ctrl+s":
            return

        if not self._is_cursor_in_rescript():
             event.prevent_default()
             event.stop()
             return

        rrange = self._get_rescript_range()
        if rrange:
            start, end = rrange
            row, col = self.cursor_location
            if event.key == "backspace" and col <= start + 5:
                event.prevent_default()
                event.stop()
            elif event.key == "delete" and col >= end - 2:
                event.prevent_default()
                event.stop()
        
    def get_rescripts(self) -> list:
        """从文本中解析出所有朱批及其位置"""
        rescripts = []
        text = self.text
        lines = text.split('\n')
        pattern = re.compile(r'\[\[朱批:(.*?)\]\]')
        
        for row, _ in enumerate(lines):
            line_obj = self.get_line(row)
            line = line_obj.plain if hasattr(line_obj, "plain") else str(line_obj)
            for match in pattern.finditer(line):
                content = match.group(1)
                col = match.start()
                rescripts.append(Rescript(
                    content=content,
                    row=row,
                    col=col,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        return rescripts

class HomeScreen(Screen):
    """游戏主界面"""
    
    CSS = """
    HomeScreen {
        align: center middle;
        background: #1a1a1a;
    }
    #menu_container {
        width: 40;
        height: auto;
        border: double #8b4513;
        padding: 1 2;
        background: #2b2b2b;
    }
    #title {
        text-align: center;
        color: #ffd700;
        text-style: bold;
        margin-bottom: 1;
    }
    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="menu_container"):
            yield Static("🏮 乾隆模拟器：叫魂 🏮", id="title")
            yield Button("启新章 (新开始)", variant="primary", id="btn_new_game")
            yield Button("考旧档 (读档)", variant="default", id="btn_load_game")
            yield Button("摆驾 (退出)", variant="error", id="btn_exit")

    @on(Button.Pressed, "#btn_new_game")
    def start_new_game(self) -> None:
        self.app.push_screen(SetupScreen())

    @on(Button.Pressed, "#btn_load_game")
    def load_game_menu(self) -> None:
        self.app.push_screen(LoadScreen())

    @on(Button.Pressed, "#btn_exit")
    def exit_game(self) -> None:
        self.app.exit()

class LoadScreen(Screen):
    """读档界面"""
    
    CSS = """
    LoadScreen {
        align: center middle;
        background: #1a1a1a;
    }
    #load_container {
        width: 60;
        height: 70%;
        border: double #8b4513;
        padding: 1;
        background: #2b2b2b;
    }
    #load_title {
        text-align: center;
        color: #ffd700;
        text-style: bold;
        margin-bottom: 1;
    }
    ListView {
        height: 1fr;
        border: solid #444;
        margin-bottom: 1;
    }
    ListItem {
        padding: 1;
    }
    #load_actions {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="load_container"):
            yield Static("📜 内阁存档库", id="load_title")
            yield ListView(id="save_list")
            with Horizontal(id="load_actions"):
                yield Button("回驾 (返回)", id="btn_back")
                yield Button("启运 (读档)", variant="primary", id="btn_confirm_load")

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self):
        lv = self.query_one("#save_list", ListView)
        lv.clear()
        slots = self.app.persistence.list_slots()
        if not slots:
            lv.append(ListItem(Static("库中空空如也")))
        else:
            for slot in slots:
                desc = slot.get('metadata', {}).get('desc', '政务存档')
                label = f"【{desc}】 - {slot['timestamp']} (政务点: {slot['ap']})"
                li = ListItem(Static(label))
                li.slot_id = slot['id']
                lv.append(li)

    @on(Button.Pressed, "#btn_back")
    def go_back(self):
        self.app.pop_screen()

    @on(Button.Pressed, "#btn_confirm_load")
    def confirm_load(self):
        lv = self.query_one("#save_list", ListView)
        if lv.index is not None:
            li = lv.children[lv.index]
            if hasattr(li, "slot_id"):
                self.app.push_screen(GameScreen(slot_id=li.slot_id))

class SetupScreen(Screen):
    """角色初始设定界面，负责调用 AgentBuilder 生成 Agent"""
    
    CSS = """
    SetupScreen {
        align: center middle;
        background: #1a1a1a;
    }
    #setup_container {
        width: 80;
        height: auto;
        border: double #8b4513;
        padding: 1 2;
        background: #2b2b2b;
    }
    #setup_title {
        text-align: center;
        color: #ffd700;
        text-style: bold;
        margin-bottom: 1;
    }
    .setup_label {
        color: #ffd700;
        margin-top: 1;
    }
    #gen_status {
        margin-top: 1;
        color: #00ff00;
        text-align: center;
        height: 1;
    }
    #progress_area {
        height: 3;
        align: center middle;
        display: none;
    }
    #setup_actions {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    Input {
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup_container"):
            yield Static("📜 乾坤初定 - 塑造你的时代 📜", id="setup_title")
            yield Static("请输入或描述你想要扮演的【知县】背景：", classes="setup_label")
            yield Input(placeholder="例如：一名刚从会稽调任、清廉但固执的县令", id="magistrate_req", value="德清知县，乾隆三十三年在任，处理叫魂案初起之时")
            
            yield Static("请输入或描述案件中的【嫌犯】背景：", classes="setup_label")
            yield Input(placeholder="例如：一名德清本地乞丐，因在茶馆多言被抓", id="suspect_req", value="德清县的一名乞丐，本地人，卷入了剪辫案")
            
            with Center(id="progress_area"):
                 yield LoadingIndicator()
            
            yield Static("", id="gen_status")
            
            with Horizontal(id="setup_actions"):
                yield Button("开始造像 (生成角色)", variant="primary", id="btn_generate")
                yield Button("回驾 (返回)", id="btn_cancel")

    @on(Button.Pressed, "#btn_cancel")
    def cancel(self):
        self.app.pop_screen()

    @work(exclusive=True, thread=True)
    async def generate_agents(self, mag_req: str, sus_req: str):
        progress = self.query_one("#progress_area")
        progress.styles.display = "block"
        status = self.query_one("#gen_status")
        status.update("⏳ 正在调取大清档案 (RAG 检索中)...")
        
        try:
            # Wait for shared resources if they are still loading
            if not hasattr(self.app, "setup_service") or self.app.setup_service is None:
                for i in range(180): # Wait up to 180 seconds for heavy model loading
                    if i % 5 == 0:
                        status.update(f"⏳ 档案库正在初始化 (已耗时 {i}s)...")
                    
                    if hasattr(self.app, "setup_service") and self.app.setup_service is not None:
                        break
                    if hasattr(self.app, "init_error") and self.app.init_error:
                        status.update(f"❌ 初始化失败: {self.app.init_error}")
                        progress.styles.display = "none"
                        return
                    await asyncio.sleep(1)
                
            if not hasattr(self.app, "setup_service") or self.app.setup_service is None:
                status.update("❌ 档案库初始化超时，请检查网络或配置")
                progress.styles.display = "none"
                return

            status.update("⏳ 正在批量塑造历史角色灵魂...")
            
            mag_dir = "saves/temp_agents/magistrate"
            sus_dir = "saves/temp_agents/suspect"
            
            requests = [
                {"save_dir": mag_dir, "name": "县令", "desc": mag_req},
                {"save_dir": sus_dir, "name": "阿二", "desc": sus_req}
            ]
            
            def progress_cb(completed, total, msg):
                self.app.call_from_thread(status.update, f"⏳ {msg} ({completed}/{total})")

            results = await self.app.setup_service.batch_generate_agents(requests, progress_callback=progress_cb)
            
            if all(results):
                status.update("✨ 角感已成，即将启程...")
                await asyncio.sleep(1.5)
                self.app.call_from_thread(self.app.push_screen, GameScreen(is_new_game=True, mag_path=mag_dir, sus_path=sus_dir))
            else:
                status.update("❌ 角色生成部分或全部失败")
                progress.styles.display = "none"

        except Exception as e:
            status.update(f"❌ 发生错误: {str(e)}")
            progress.styles.display = "none"

    @on(Button.Pressed, "#btn_generate")
    def on_gen(self):
        mag_req = self.query_one("#magistrate_req").value
        sus_req = self.query_one("#suspect_req").value
        self.generate_agents(mag_req, sus_req)

class GameScreen(Screen):
    """核心玩法界面"""
    
    CSS = """
    #main_layout {
        height: 100%;
    }
    #left_panel {
        width: 30%;
        border-right: double #8b4513;
        padding: 1;
    }
    #right_panel {
        width: 70%;
        padding: 1;
    }
    #status_bar {
        height: 3;
        background: #2b2b2b;
        border-bottom: solid #8b4513;
        color: #ffd700;
        content-align: center middle;
        text-style: bold;
    }
    #editor {
        height: 1fr;
        border: tall #8b4513;
        background: #261a1a;
        color: #d4cfc1;
        display: none;
    }
    #editor .text_area--path {
        color: #ff4444;
        text-style: bold;
    }
    #editor_placeholder {
        height: 1fr;
        border: dashed #444;
        content-align: center middle;
        color: #666;
    }
    #dev_monitor {
        height: 8;
        border: solid #c00;
        background: #000;
        color: #0f0;
    }
    #input_area {
        height: auto;
        border-top: solid #8b4513;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit_game", "摆驾回宫"),
        ("v", "toggle_dev", "通天镜"),
        ("h", "show_help", "谕旨"),
        ("ctrl+s", "quick_save", "奏进")
    ]

    def __init__(self, is_new_game=False, slot_id=None, mag_path=None, sus_path=None):
        super().__init__()
        self.is_new_game = is_new_game
        self.slot_id = slot_id
        self.mag_path = mag_path or "agents/magistrate"
        self.sus_path = sus_path or "agents/aer"
        self.ap = 5
        self.current_report_id = None
        
        # Agents & Systems (initialized in on_mount or via load)
        self.magistrate_agent = None
        self.suspect_agent = None
        self.letters_system = LettersSystem()
        self.cases_system = CasesSystem()
        self.game_session = None
        self.llm = None
        self.llm_model = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, id="game_header")
        with Vertical(id="main_layout"):
            yield Static("御案亲裁 - 乾隆三十三年", id="status_bar")
            with Horizontal():
                with Vertical(id="left_panel"):
                    yield Static("📜 待批奏折 (奏章)", id="letters_header")
                    yield Static("[尚无奏章]", id="letters_list")
                with Vertical(id="right_panel"):
                    yield Static("请于左侧择一奏章，细加阅览并予朱批", id="editor_placeholder")
                    yield MemorialEditor(id="editor")
                    yield Log(id="dev_monitor")
            with Vertical(id="input_area"):
                yield Input(placeholder="谕令: /始 | /览 [编号] | /退 [编号] | /查 [编号] | /存 | /退", id="cmd_input")
        yield Footer()

    def on_mount(self) -> None:
        self._setup_game()

    def _setup_game(self):
        cfg = self.app.cfg
        self.magistrate_agent = Agent(self.mag_path)
        self.suspect_agent = Agent(self.sus_path)
        
        self.llm_model = cfg.llm.get("model", "deepseek/deepseek-chat") if cfg else "deepseek/deepseek-chat"
        # Use shared LLM client from app
        self.llm = self.app.llm
        if not self.llm:
            api_key = os.getenv("LLM_API_KEY") or (cfg.llm.get("api_key", "") if cfg else "")
            base_url = cfg.llm.get("base_url", "https://openrouter.ai/api/v1") if cfg else "https://openrouter.ai/api/v1"
            self.llm = LLMClient(api_key=api_key, base_url=base_url)
        
        if self.slot_id:
            self._load_from_persistence(self.slot_id)
        elif self.is_new_game:
            # New game: Reset to defaults
            self.ap = 5
            self.letters_system.reports = []
            # We could also reset agent memories if desired
            
        self.game_session = GameSessionService(
            llm=self.llm,
            llm_model=self.llm_model,
            letters_system=self.letters_system,
            cases_system=self.cases_system,
            magistrate=self.magistrate_agent,
            suspect=self.suspect_agent
        )
            
        self._update_status()
        self._update_letters_list()

    def _load_from_persistence(self, slot_id):
        success = self.app.archive_service.load_game(
            slot_id, 
            self.letters_system, 
            self.magistrate_agent, 
            self.suspect_agent
        )
        if success:
            # Retrieve AP directly from persistence payload
            data = self.app.persistence.load_game(slot_id)
            if data:
                self.ap = data.get("ap", 5)
            self.query_one("#dev_monitor", Log).write_line(f"✅ 已加载存档 {slot_id}")

    def _update_status(self):
        status = self.query_one("#status_bar", Static)
        status.update(f"🏮 乾坤御览 | 行动点 (政务): {self.ap} | 时维: 乾隆三十三年")

    def _update_letters_list(self):
        list_view = self.query_one("#letters_list", Static)
        if not self.letters_system.reports:
            list_view.update("[尚无奏折]")
            return
        
        text = ""
        for r in self.letters_system.reports:
            marker = "㊙️" if r.type == "密折" else "📜"
            return_marker = " ↩️" if getattr(r, 'is_returned', False) else ""
            text += f"{marker} ID:{r.id} | {r.author}的{r.type}{return_marker}\n"
        list_view.update(text)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        self.query_one("#cmd_input", Input).value = ""
        
        if cmd.startswith(("/start", "/始")):
            self._start_simulation()
        elif cmd.startswith(("/view", "/览")):
            parts = cmd.split(" ", 1)
            if len(parts) > 1 and parts[1].isdigit():
                self._view_report(int(parts[1]))
        elif cmd.startswith(("/audit", "/查")):
            parts = cmd.split(" ", 1)
            if len(parts) > 1 and parts[1].isdigit():
                self._audit_report(int(parts[1]))
        elif cmd.startswith(("/return", "/退")):
            parts = cmd.split(" ", 1)
            if len(parts) > 1 and parts[1].isdigit():
                self._return_memorial(int(parts[1]))
        elif cmd.startswith(("/save", "/存")):
            self.action_quick_save()
        elif cmd.startswith(("/quit", "/退")):
            self.action_quit_game()
        else:
            self.query_one("#dev_monitor", Log).write_line(f"⚠️ 旨意不明: {cmd}")

    @work(exclusive=True, thread=True)
    async def action_quick_save(self) -> None:
        if not hasattr(self.app, 'archive_service'):
            return
            
        success, slot_id = await self.app.archive_service.quick_save(
            self.ap,
            self.letters_system,
            [self.magistrate_agent, self.suspect_agent]
        )
        if success:
            self.query_one("#dev_monitor", Log).write_line(f"💾 游戏已保存至 slot_{slot_id}")

    def action_quit_game(self):
        self.app.pop_screen()

    def action_toggle_dev(self):
        monitor = self.query_one("#dev_monitor")
        monitor.visible = not monitor.visible

    def action_show_help(self):
        dev = self.query_one("#dev_monitor", Log)
        dev.write_line("📜 朕之谕旨：")
        dev.write_line("/始 - 下旨审讯，开启乾坤")
        dev.write_line("/览 [编号] - 调取并亲阅此奏")
        dev.write_line("/退 [编号] - 批阅毕，发回本处")
        dev.write_line("/查 [编号] - 耗二政务点，密查案卷底稿")
        dev.write_line("/存 - 记录圣踪，封档存案")
        dev.write_line("/退 - 罢手暂歇，摆驾回宫")
        dev.write_line("便捷法门：v (启闭通天镜), Ctrl+S (奏进), q (还朝)")

    def action_save_rescript(self) -> None:
        if self.current_report_id is None:
            return
        editor = self.query_one("#editor", MemorialEditor)
        report = self.letters_system.get_report(self.current_report_id)
        if report:
            report.content = editor.text
            report.rescripts = editor.get_rescripts()
            self.letters_system.save_to_file("data/letters.json")
            self.query_one("#dev_monitor", Log).write_line(f"✅ 奏折 ID: {self.current_report_id} 已保存。")

    @work(exclusive=True, thread=True)
    async def _start_simulation(self):
        dev = self.query_one("#dev_monitor", Log)
        dev.write_line("⏳ 旨意已下达，德清县令正在紧急审理中...")
        
        if not self.game_session:
            dev.write_line("❌ 尚未建立政务环境 (GameSession)")
            return
            
        try:
            async for event in self.game_session.run_simulation_sequence():
                if getattr(self, "_worker_cancelled", False):
                    # In textual you can check worker status but catching cancellations in generators handles it gracefully
                    break
                    
                if event["type"] == "log":
                    speaker = event.get("speaker", "system")
                    if speaker == "magistrate":
                        self.app.call_from_thread(dev.write_line, f"知县：{event['content']}")
                    elif speaker == "suspect":
                        self.app.call_from_thread(dev.write_line, f"嫌犯：{event['content']}")
                    else:
                        self.app.call_from_thread(dev.write_line, event["content"])
                elif event["type"] == "report":
                    self.app.call_from_thread(dev.write_line, f"✨ 收到来自 {event['author']} 的一份新奏折 (ID: {event['report_id']})")
                    self.app.call_from_thread(self._view_report, event["report_id"])
                    self.app.call_from_thread(self._update_letters_list)
        except asyncio.CancelledError:
            dev.write_line("⚠️ 审理被叫停。")
        except Exception as e:
            self.app.call_from_thread(dev.write_line, f"❌ 审理中断: {str(e)}")
            import traceback
            traceback.print_exc()

    def _view_report(self, rid: int):
        report = self.letters_system.get_report(rid)
        editor = self.query_one("#editor", MemorialEditor)
        if report:
            self.current_report_id = rid
            self.query_one("#editor_placeholder").styles.display = "none"
            editor.styles.display = "block"
            editor.text = report.content
            self.query_one("#dev_monitor", Log).write_line(f"📖 正在阅览奏折 ID: {rid}")

    def _return_memorial(self, rid: int):
        if self.current_report_id == rid: 
            self.action_save_rescript()
        report = self.letters_system.get_report(rid)
        if report and report.rescripts:
            report.is_returned = True
            self._start_simulation()
            self._update_letters_list()

    def _audit_report(self, rid: int):
        dev = self.query_one("#dev_monitor", Log)
        if self.ap < 2:
            dev.write_line("❌ 行动点不足")
            return
        report = self.letters_system.get_report(rid)
        if report and report.raw_case_data:
            self.ap -= 2
            self._update_status()
            dev.clear()
            dev.write_line(f"⚠️ [机密审计：{report.author} 案原案记录]\n" + "-"*40 + f"\n{report.raw_case_data}")

class SoulstealerTUI(App):
    """乾隆模拟器 - 真·叫魂 MVP"""
    
    def __init__(self, cfg: DictConfig = None):
        super().__init__()
        self.cfg = cfg
        self.persistence = PersistenceManager()
        self.retriever = None
        self.llm = None
        self.init_error = None

    def on_mount(self) -> None:
        self.title = "乾隆模拟器 - 《叫魂》MVP"
        self._init_resources()
        self.push_screen(HomeScreen())

    @work(exclusive=True, thread=True)
    async def _init_resources(self):
        """异步初始化重型资源（如 RAG 检索器）"""
        import sys
        cfg = self.cfg
        if not cfg:
            return
            
        try:
            api_key = os.getenv("LLM_API_KEY") or cfg.llm.get("api_key", "")
            base_url = cfg.llm.get("base_url", "https://openrouter.ai/api/v1")
            self.llm = LLMClient(api_key=api_key, base_url=base_url)
            
            # Initialize RAG retriever (heavy operation)
            # This might take some time on the first run as it loads models
            print("DEBUG: Initializing SoulstealerRetriever...", file=sys.stderr)
            self.retriever = SoulstealerRetriever(vector_store_dir="data/vectordb")
            # Setup the application level services
            model = cfg.llm.get("model", "deepseek/deepseek-chat")
            self.setup_service = SetupService(self.retriever, self.llm)
            self.archive_service = ArchiveService(self.persistence, self.llm, model)
            
        except Exception as e:
            self.init_error = str(e)
            print(f"DEBUG ERROR during initialization: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

def run_tui(cfg: DictConfig = None):
    app = SoulstealerTUI(cfg)
    app.run()
