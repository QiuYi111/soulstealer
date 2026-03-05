# 《叫魂》(Soulstealer)

> **"一场关于权力、谎言与生存的历史社会学模拟。"**

[![Built with Python](https://img.shields.io/badge/Made%20with-Python-blue.svg)](https://www.python.org/)
[![TUI powered by Textual](https://img.shields.io/badge/UI-Textual-orange.svg)](https://github.com/Textualize/textual)
[![Dependency Manager uv](https://img.shields.io/badge/Managed%20by-uv-green.svg)](https://github.com/astral-sh/uv)

本项目是一场硬核且沉浸的历史社会学模拟游戏，基于 1768 年大清帝国“叫魂”妖术大恐慌的历史背景。玩家将扮演居于权力之巅的乾隆皇帝，在政治高压与信息扭曲的迷雾中，通过审阅奏折、施加压力，揭开或制造一场影响国本的“阴谋”。

---

## 🏛️ 项目核心机制 (Core Mechanics)

### 1. 乾隆模拟器 (Qianlong Simulator)
玩家的视角完全收束于“案牍”之上。你不是直接的执法者，而是信息的裁决者。
- **公文桌面**：在黑底白字的 TUI 界面中，查阅来自全国各地的秘密奏折。
- **朱批权**：通过朱批（命令、训斥或安抚）将政治压力向下传导。

### 2. 信息过滤系统 (The Information Grinder)
- **奏折 (Letters)**：地方官员递交的经过“润色”和粉饰的公文。
- **案卷 (Cases)**：最基层的原始审讯记录。通过消耗特定资源（如派出密探），玩家可以强行调阅包含酷刑、哭喊与逻辑偏差的原始证据，在字里行间捕捉谎言。

### 3. LLM 驱动的 Agent 生态
- **官员 Agent**：在政治压力下，他们会为了保住乌纱帽而粉饰太平、推卸责任甚至伪造案情。
- **嫌犯 Agent**：具备真实的生理属性（疼痛、健康、饥荒）。在残酷的刑讯压力下，他们会涌现出“屈打成招”或“疯狂攀咬”等真实反馈。

---

## 🛠️ 技术栈 (Tech Stack)

本项目采用现代 Python 工具链，致力于构建高性能、可扩展的 Agent 对演系统。

- **语言**：Python 3.12+
- **环境管理**：[uv](https://github.com/astral-sh/uv) (极速依赖解析与构建)
- **终端 UI (TUI)**：[Textual](https://github.com/Textualize/textual) / [Rich](https://github.com/Textualize/rich)
- **Agent 引擎**：集成 OpenRouter / DeepSeek API 进行大规模语义推理
- **架构**：Pragmatic Domain-Driven Design (DDD)

---

## 🚀 快速开始 (Getting Started)

### 1. 环境配置
确保已安装 `uv`。

```bash
# 克隆项目
git clone https://github.com/your-repo/soulstealer.git
cd soulstealer

# 创建虚拟环境并同步依赖
uv sync
```

### 2. 配置 API Key
在根目录创建 `.env` 文件：
```env
OPENROUTER_API_KEY=your_key_here
```

### 3. 运行游戏
```bash
make run
```

---

## 🏗️ 项目架构 (Architecture)

项目遵循严谨的三层架构，确保业务逻辑与基础设施隔离：

```text
Project/
├── api/                  # 契约层 (Protobuf / API 定义)
├── app/                  # 应用集成层 (TUI 视图与交互)
├── internal/             # 私有核心代码
│   ├── domain/           # 领域核心 (纯业务逻辑，不依赖框架)
│   └── infrastructure/   # 基础设施 (数据库、API 客户端)
└── agents/               # Agent 行为逻辑与提示词工程
```

---

## 🤝 贡献指南 (Contributing)

我们非常欢迎开发者参与这个历史实验室的建设。在提交 PR 前，请务必阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)。

- **TDD 驱动**：本项目严格执行 TDD (Test-Driven Development) 流程。
- **代码规范**：使用 `make verify` 进行自动化 Lint 和测试检查。

---

## 📜 许可 (License)

本项目仅用于学术探讨与历史社会学模拟研究。

> *"大清帝国的官僚机制，在这一刻变成了一台精密且冷酷的谎言加工厂。"*
