# RAG 系统开发约束与契约 (Phase 1 & Phase 2)

为了支持并行开发，必须在 Phase 1（数据预处理与获取）与 Phase 2（RAG框架搭建与集成）之间建立清晰的边界、目标、契约与验收标准。

本项目的基础设定为《叫魂》MVP（1768年，清乾隆三十三年）。所有检索和生成必须契合此时空背景。

---

## Phase 1: 语料获取与预处理 (Data Sourcing & Preprocessing)

### 总体目标描述
从开源渠道获取真实的清代历史文献文本（如《清史稿》、地方志等），清洗、切割（Chunking），并最终输出符合 Phase 2 读取标准的结构化数据。本阶段完全不关心如何存储进向量数据库。

### 具体任务要求
1. **数据源获取**：准备 `data/archives/raw/` 存放原始文本文件（TXT 或 Markdown格式）。测试阶段先提供少量的测试文本（例如《清史稿·本纪·高宗》节选，或浙江地方志节选）。
2. **文本清洗**：去除现代排版符号、网页爬虫可能带来的 HTML 标签、或无关的注释题跋，提纯为文言文或半白话实体文本。
3. **内容切片 (Chunking)**：实现一个切片脚本。考虑到文言文信息密度大，需使用固定字符长度加滑动窗口（Overlap）的机制切片（例如 200字/Chunk，50字/Overlap）。
4. **元数据提取 (Metadata Extraction)**：为每个 Chunk 打上元数据（例如来源书目、预计年份、所属地理位置或主体人物等），以便支持后期的结构化过滤查询。

### 接口契约 (Contract with Phase 2)
Phase 1 的最终产出必须是一个或多个易于迭代读取的文件（如 JSON Lines 或结构化 JSON），存放在 `data/archives/processed/`。

**数据实体契约示例**：
```json
// data/archives/processed/chunks_v1.jsonl
{"id": "doc_001", "content": "乾隆三十三年春，浙江德清县修桥，有石匠削人衣发，作法魇魅...", "metadata": {"source": "叫魂相关县志.txt", "year": "1768", "location": "浙江德清", "keywords": ["案卷", "迷信", "石匠"]}}
{"id": "doc_002", "content": "浙江巡抚觉罗防出巡，闻民间惊惧，下令各地严查妖党...", "metadata": {"source": "清实录.txt", "year": "1768", "location": "浙江", "keywords": ["巡抚", "妖党", "公文"]}}
```
*注：Phase 2 的 `DocumentLoader` 将直接从该 `jsonl` 格式读取数据录入 Vector DB。*

### 验收标准 (Acceptance Criteria)
- [ ] 提供了至少一份能够跑通全流程的真实清代文献测试数据 (Raw Text)。
- [ ] 执行 `python scripts/data_pipeline.py` 后，能够在 `data/archives/processed/` 生成合规的 JSONL 文件。
- [ ] Chunk 的文字内容 (`content`) 干净无乱码，且 `metadata` 中的字段（如 `source`）完整无误。
- [ ] 随机抽查 JSONL 中的文本片段，上下文语义没有被暴力截断导致完全不可读。

---

## Phase 2: RAG 核心框架搭建 (Framework Integration)

### 总体目标描述
选定基于 Python 的 LangChain 框架和 ChromaDB 本地向量数据库，封装标准的文档读取、向量索引构建、以及带 Metadata 过滤的检索接口层。本阶段不关心原始文本是如何被清洗和切片的，完全信任 Phase 1 提供的标准 JSONL 文件。

### 具体任务要求
1. **依赖准备**：引入 `langchain`、`langchain-community`、`chromadb` 及相关 Embedding 模型（如 `sentence-transformers` 或调用 OpenAI Embeddings）。
2. **文档加载层 (`document_loader.py`)**：编写读取 Phase 1 标准 JSONL 契约文件的逻辑，将其转化为 LangChain 识别的 `Document` 对象。
3. **向量存储层 (`vector_store.py`)**：初始化 ChromaDB，加载 `Document` 并计算 Embeddings 存入本地磁盘持久化目录（例如 `data/vectordb/`）。
4. **检索接口层 (`retriever.py`)**：对外暴露一个干净的 `query(text: str, top_k: int = 3, filter_kwargs: dict = None)` 方法，返回最相关的史料 Context 列表。

### 接口契约 (Contract from Phase 1 & to Phase 3)
1. **接受 Phase 1 的输入**：严格解析如 `{"content": "...", "metadata": {"source": "..."}}` 的 JSONL 结构。
2. **面向 Phase 3 (Agent Builder) 的输出**：
   - 暴露独立的检索 API 供核心领域层随时调用。
   - **返回值示例**：
     ```python
     # retriever.query("德清县 县令", top_k=2)
     # Returns:
     [
       {"content": "德清县地处...知县日常...", "metadata": {"source": "...", "location": "德清"}},
       {"content": "前任知县因...", "metadata": {"source": "..."}}
     ]
     ```

### 验收标准 (Acceptance Criteria)
- [ ] 依赖库已通过 `uv lock` 正确安装。
- [ ] 提供一个构建脚本 `python scripts/build_vector_db.py`，能够成功读取 Phase 1 的 JSONL 并将向量文件持久化写入本地磁盘 `data/vectordb/`，无报错。
- [ ] 提供单元测试 `tests/test_rag_pipeline.py`，能够初始化检索器并输入关键字（如“乾隆”），断言返回的列表中包含符合预期的 `content` 与 `metadata`。
- [ ] 支持按元数据查询（如限制检索时的 `location='浙江'`）。
