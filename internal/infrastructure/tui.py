from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log, Input, TextArea, Button, ListItem, ListView, LoadingIndicator
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Center
from textual.screen import Screen
from textual import work, on
from textual.worker import get_current_worker
from omegaconf import DictConfig
from internal.domain.court import CourtSession
from internal.domain.agent import Agent
from internal.domain.letters import LettersSystem, Rescript
from internal.domain.cases import CasesSystem
from internal.infrastructure.llm import LLMClient
from internal.infrastructure.persistence import PersistenceManager
from internal.domain.agent_builder import AgentBuilder
from internal.rag.retriever import SoulstealerRetriever
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
        
        cfg = self.app.cfg
        model = cfg.llm.get("model", "deepseek/deepseek-chat")
        
        try:
            # Wait for shared resources if they are still loading
            if self.app.retriever is None or self.app.llm is None:
                status.update("⏳ 档案库正在初始化，请稍候...")
                for _ in range(30): # Wait up to 30 seconds
                    if self.app.retriever is not None and self.app.llm is not None:
                        break
                    await asyncio.sleep(1)
                
            if self.app.retriever is None or self.app.llm is None:
                status.update("❌ 档案库初始化超时或失败")
                progress.styles.display = "none"
                return

            # Use shared resources from App
            builder = AgentBuilder(self.app.retriever, self.app.llm, model=model)
            
            # Paths for temporary generation
            mag_dir = "saves/temp_agents/magistrate"
            sus_dir = "saves/temp_agents/suspect"
            
            status.update("⏳ 正在塑造知县灵魂...")
            if not builder.build_agent(mag_dir, "县令", mag_req):
                status.update("❌ 知县生成失败")
                progress.styles.display = "none"
                return
                
            status.update("⏳ 正在塑造嫌犯因果...")
            if not builder.build_agent(sus_dir, "阿二", sus_req):
                status.update("❌ 嫌犯生成失败")
                progress.styles.display = "none"
                return
                
            status.update("✨ 角感已成，即将启程...")
            await asyncio.sleep(1.5)
            self.app.call_from_thread(self.app.push_screen, GameScreen(is_new_game=True, mag_path=mag_dir, sus_path=sus_dir))
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
        self.current_session = None
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
            
        self._update_status()
        self._update_letters_list()

    def _load_from_persistence(self, slot_id):
        data = self.app.persistence.load_game(slot_id)
        if data:
            self.ap = data["ap"]
            self.letters_system.reports = [] # Clear current
            # Proper way to load reports needs LettersSystem to handle data dicts
            for r_data in data["letters"]:
                report = self.letters_system.add_report(r_data["type"], r_data["content"], r_data["author"])
                report.id = r_data["id"]
                report.timestamp = r_data["timestamp"]
                report.is_returned = r_data.get("is_returned", False)
                report.rescripts = r_data.get("rescripts", [])
                report.raw_case_data = r_data.get("raw_case_data")
                report.polished_case_data = r_data.get("polished_case_data")
            
            # Load agent memories
            if "magistrate" in data["agents_memories"]:
                self.magistrate_agent.memory = data["agents_memories"]["magistrate"]
            if "aer" in data["agents_memories"]:
                self.suspect_agent.memory = data["agents_memories"]["aer"]
                
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

    async def _generate_save_name(self) -> str:
        """调用 LLM 生成具有文学色彩的存档名"""
        prompt = (
            "你是一个清代史官。请根据目前的政务进度，起一个4到8个字的、具有清代文书风格或文学色彩的存档名称。\n"
            f"当前政务：行动点剩{self.ap}，已有奏折{len(self.letters_system.reports)}份。\n"
            "名称示例：‘德清妖道初露端倪’、‘内阁秘议叫魂案’、‘江浙奏折纷至沓来’。\n"
            "仅输出名称，不要有任何修饰词或标点。"
        )
        try:
            name = await self.llm.get_response_async(
                "你是一个擅长起名的历史模拟助手。",
                prompt,
                model=self.llm_model
            )
            return name.strip().strip("'").strip("‘").strip("’").strip('"')
        except Exception:
            return "圣踪微巡"

    @work(exclusive=True, thread=True)
    async def action_quick_save(self) -> None:
        # Save to a timestamped slot
        slot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = await self._generate_save_name()
        metadata = {"desc": save_name}
        
        # Prepare letters data
        letters_data = []
        for r in self.letters_system.reports:
            letters_data.append({
                "id": r.id, "type": r.type, "content": r.content, "author": r.author,
                "timestamp": r.timestamp, "is_returned": getattr(r, 'is_returned', False),
                "rescripts": [vars(res) if not isinstance(res, dict) else res for res in r.rescripts],
                "raw_case_data": getattr(r, 'raw_case_data', None),
                "polished_case_data": getattr(r, 'polished_case_data', None)
            })
            
        success = self.app.persistence.save_game(
            slot_id, metadata, letters_data, "data/cases", 
            [self.magistrate_agent, self.suspect_agent], self.ap
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
    def _start_simulation(self):
        dev = self.query_one("#dev_monitor", Log)
        dev.write_line("⏳ 旨意已下达，德清县令正在紧急审理中...")
        prisoner_list = [self.suspect_agent.name]
        self.current_session = CourtSession(self.magistrate_agent.name, self.suspect_agent.name, prisoner_list=prisoner_list)
        
        returned_memorials = ""
        relevant_reports = [r for r in self.letters_system.reports if r.rescripts][-3:]
        for r in relevant_reports:
            res_contents = [res.content if hasattr(res, 'content') else res['content'] for res in r.rescripts]
            res_str = "; ".join(res_contents)
            returned_memorials += f"《{r.type} ID:{r.id}》\n内容：{r.content}\n皇帝朱批：{res_str}\n"

        for i in range(10):
            worker = get_current_worker()
            if worker.is_cancelled:
                return
            success = self.current_session.run_auto_step(self.magistrate_agent, self.suspect_agent, self.llm, self.llm_model, returned_memorials=returned_memorials)
            if len(self.current_session.log) >= 2:
                last_entry = self.current_session.log[-1]
                if last_entry['role'] == 'system':
                    dev.write_line(f"知县：{last_entry['content']}")
                else:
                    dev.write_line(f"知县：{self.current_session.log[-2]['content']}")
                    dev.write_line(f"嫌犯：{last_entry['content']}")
            if not success:
                break
        
        raw_log = self.current_session.get_raw_log()

        # Step: Let the agent autonomously update memory with a summary of this session
        summary_ctx = "审讯已结束。作为知县，请总结本次审讯的关键点、嫌犯的矛盾之处或你的新发现，以便日后查阅。请使用 [[/update_memory 内容]] 指令记录。"
        summary_resp_raw = self.magistrate_agent.get_response(self.llm, self.magistrate_agent.generate_prompt(summary_ctx, "记录审讯摘要", available_tools=["/read_memory"]), f"审讯实录：\n{raw_log}", model=self.llm_model)
        
        # Use the parser from current_session (or a temporary one)
        _, summary_cmds = self.current_session._parse_commands(summary_resp_raw)
        for full, cmd, args in summary_cmds:
            if cmd == "/update_memory" and args:
                self.magistrate_agent.add_memory(args)
                self.magistrate_agent.save_memory()
                dev.write_line("📓 知县已将审讯摘要存入记忆。")
                break # Only take the first summary for the log

        loc = self.current_session.location_info
        polish_ctx = f"你正处于{loc['province']}{loc['prefecture']}{loc['county']}县衙。审讯已结束。请将原始审讯记录整理成一份言辞严谨、逻辑清晰的正式案卷。"
        polished_case = self.magistrate_agent.get_response(self.llm, self.magistrate_agent.generate_prompt(polish_ctx, "整理正式案卷"), f"原始事实记录：\n{raw_log}", model=self.llm_model)
        
        draft_ctx = (
            "你正在撰写上呈给乾隆皇帝的正式奏折。请基于以下案卷内容进行深加工，不仅要陈述事实，更要体现出官员的政治立场。请以第一人称（臣）称呼自己。\n"
            "【强制格式要求】\n"
            "1. 第一行必须仅包含奏折类型：‘密折’ 或 ‘明发奏折’。\n"
            "2. 从第二行开始为奏折正文，必须符合清代奏折文体规范。\n"
            "3. 严禁尝试调用任何 API 指令（如 /read_memory 或 /torture）。"
        )
        full_draft_resp = self.magistrate_agent.get_response(self.llm, self.magistrate_agent.generate_prompt(draft_ctx, "撰写奏折"), f"案卷内容副本：\n{polished_case}", model=self.llm_model)
        
        if "\n" in full_draft_resp:
            r_type, r_content = full_draft_resp.split("\n", 1)
            report_type = "明发奏折" if "明" in r_type else "密折"
            report_content = r_content.strip()
        else:
            report_type, report_content = "密折", full_draft_resp

        report = self.letters_system.add_report(report_type, report_content, self.magistrate_agent.name)
        # 本地持久化 (即使不手动存档也保留最新记录)
        self.letters_system.save_to_file("data/letters.json")
        self.cases_system.save_case(report.id, raw_log, polished_case)

        report.raw_case_data = raw_log
        report.polished_case_data = polished_case
        
        dev.write_line(f"✨ 收到来自 {self.magistrate_agent.name} 的一份新奏折 (ID: {report.id})")
        self.app.call_from_thread(self._view_report, report.id)
        self.app.call_from_thread(self._update_letters_list)

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

    def on_mount(self) -> None:
        self.title = "乾隆模拟器 - 《叫魂》MVP"
        self._init_resources()
        self.push_screen(HomeScreen())

    @work(exclusive=True, thread=True)
    async def _init_resources(self):
        """异步初始化重型资源（如 RAG 检索器）"""
        cfg = self.cfg
        if not cfg:
            return
            
        api_key = os.getenv("LLM_API_KEY") or cfg.llm.get("api_key", "")
        base_url = cfg.llm.get("base_url", "https://openrouter.ai/api/v1")
        self.llm = LLMClient(api_key=api_key, base_url=base_url)
        
        # Initialize RAG retriever (heavy operation)
        try:
            self.retriever = SoulstealerRetriever(vector_store_dir="data/vectordb")
        except Exception:
            # We can log this to dev monitor later if it's visible, 
            # for now just ensure it doesn't crash the app start
            pass

def run_tui(cfg: DictConfig = None):
    app = SoulstealerTUI(cfg)
    app.run()
