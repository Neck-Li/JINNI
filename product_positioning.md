# doc2md 产品定位文档

## 一句话定位

**把收到的文件变成干净的 Markdown，不需要折腾。**

---

## 解决的问题

用户每天收到各种格式的文件——PDF 课件、Word 文档、会议纪要、EPUB 电子书。他们想把内容整理到笔记里、喂给 AI 分析、或者存入知识库，但：

- 从 PDF 复制粘贴格式全乱
- 专有格式打不开（如 .rtf、.epub）
- AI 工具读不懂 PDF 里的表格
- 没有简单好用的工具

doc2md 把这一切简化为一步：**拖入文件 → 拿到干净的 Markdown**。

---

## 目标用户（详细）

### 第一类：学生与教育用户

**特征：**
- 在读大学生/研究生，理工科或文科都有
- 手头有大量 PDF 课件、论文、电子书
- 使用 Obsidian/Notion/语雀做笔记
- 有一定动手能力但不愿折腾环境配置
- 对命令行有抵触

**痛点：**
- PDF 里无法搜索
- 复习时几十个 PDF 翻来翻去
- 想导入 Obsidian 但格式太乱
- 想把课件喂给 AI 总结，但复制粘贴效果差

**使用场景：**
```
期末复习：把一学期 10 份 PDF 课件批量转成 Markdown
         → 导入 Obsidian → 全文搜索 + AI 问答
```

**规模估算：** 中国每年 1000 万+ 大学生，即使 1% 有转换需求也是 10 万级用户。

---

### 第二类：非技术职场人（运营/产品/写作者）

**特征：**
- 不需要编程，日常用飞书/语雀/Notion
- 经常收到 PDF/Word 格式的文档
- 需要摘取内容写入周报、公众号、知识库
- Mac/Windows 都会用，但不碰终端

**痛点：**
- 收到的 PDF 合同/报价单需要摘数据
- Word 文档里的表格复制到飞书就乱
- 想把会议纪要变成可搜索的知识库
- 公司内部文档整理需要统一格式

**使用场景：**
```
运营：收到一份 PDF 行业报告
    → 拖入 doc2md → 复制 Markdown
    → 粘贴到飞书文档/公众号 → 直接发布无需排版
```

---

### 第三类：AI 开发者（RAG 管道）

**特征：**
- 知道 Markdown 是什么，日常用命令行
- 搭建 RAG 系统，需要把文档转成 LLM 友好的格式
- 用过 MarkItDown / Docling / LlamaParse
- 对转换质量有要求，但不需要企业级精确度

**痛点：**
- MarkItDown 表格提取太差，PDF 表格全碎
- Docling 模型太大（2GB+），启动慢
- LlamaParse 付费，不适合批量
- 中文支持普遍不好

**使用场景：**
```
# RAG 管道预处理
pip install doc2md
doc2md 合同.pdf -o output.md     # 单文件
doc2md ./docs/ --recursive        # 批量
→ 把 output.md 喂给 embedding 模型
```

**与竞品的差异：**

| 对比维度 | doc2md | MarkItDown | Docling |
|---------|--------|------------|---------|
| 安装大小 | ~50MB | ~50MB | ~2GB+ |
| 表格质量 | 50/50 测试通过 | PDF 表格全碎 | 好 |
| 中文支持 | CJK 优化 | 一般 | 一般 |
| GUI | 有（Gradio） | 无 | 无 |
| 命令行 | 有 | 有 | 有 |
| 启动速度 | 秒级 | 秒级 | 分钟级 |

---

### 第四类：开源社区贡献者

**特征：**
- 对文档处理技术感兴趣
- 有 Python 基础
- 希望通过参与开源项目积累经验

**价值：**
- 代码库小（< 3000 行 Python），容易上手
- 模块化设计（converters / segmenter / writers）
- 覆盖真实 PDF/Word/EPUB 转换问题
- 有完整的测试集（50 份真实 PDF）

---

## 产品能力边界

### 支持的功能
- 10 种格式转 Markdown：docx、pdf、txt、md、csv、json、html、rtf、epub、pptx
- 图片提取和保存
- 基础表格提取（pdfplumber 方案，适合有边框表格）
- 段落自动合并（reflow，修复 PDF 逐词断行）
- CJK 中文字符合并
- 列表模式识别（编号/项目符号）
- 标题优化（误判降级）
- LLM 可选增强分段（对接 Groq/SiliconFlow 等免费 API）
- CLI + Gradio GUI 双模式
- 批量处理

### 不支持的（方案限制）
- 复杂表格（合并单元格、无边框表格、财务层次表）— 需要 ML/OCR 方案
- 图片中的文字（OCR）— 需要接入 PaddleOCR
- 扫描件 PDF — 无文字层，无法提取
- 文档结构恢复（列表语义、代码块识别）— 需要 LLM 后处理
- 公式识别 — LaTeX 公式在 PDF 中通常渲染为图片或特殊编码

---

## 产品形式

| 形式 | 地址 | 目标用户 |
|------|------|---------|
| Python 包 | `pip install doc2md` | 开发者 |
| GitHub 仓库 | https://github.com/Neck-Li/JINNI | 所有人 |
| 在线 Demo | https://huggingface.co/spaces/Neck-Li/JINNI | 非技术用户（不装软件即用） |
| Gradio 本地 | `python -m doc2md.app` | 有 Python 环境的用户 |

---

## 后续方向（待决策）

根据反馈，以下方向可择一深入：

1. **PyPI 发布** — 完善 README + 发布到 PyPI，降低开发者使用门槛
2. **飞书/钉钉机器人** — 对接 IM 平台，让非技术用户在聊天框里就能转文档
3. **Obsidian 插件** — 直接导入 PDF 到笔记
4. **Web API 服务** — 提供 HTTP API 供其他服务调用
5. **Chrome 扩展** — 在浏览器里转网页为 Markdown
