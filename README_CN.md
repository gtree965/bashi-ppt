# 巴适PPT

[English README](./README.md)

巴适PPT原名 SlideForge，是一个以本地运行为核心的 AI PPT 生成工具，面向教师、教会同工和家庭沟通场景。它可以根据主题或参考文章生成可编辑的大纲，在本地渲染 `.pptx` 文件，也支持单语或双语的赞美诗歌词投影。

## 核心亮点

- 通过 LM Studio 等 OpenAI 兼容接口进行本地 AI 大纲生成
- 面向教学、教会、家长说明和通用场景的演示文稿工作流
- 演示文稿模式下自动匹配主题模板
- 纯 Python 本地渲染 PPTX，支持中文字体和文字自适应
- 赞美诗歌词模式支持单语与双语投影
- 可选标题页和阿们页
- 前后端由 Flask 统一服务，本地启动简单直接

## 当前版本范围

首发版本聚焦两个核心工作流：

1. `演示文稿 PPT`
   根据主题生成大纲，编辑后导出 PowerPoint 文件。
2. `赞美诗歌词 PPT`
   粘贴歌词，预览分页，再导出深色背景的大字歌词投影，不依赖 LLM。

## 环境要求

- Python 3.10 及以上
- Node.js 18 及以上
- `npm`
- LM Studio 或其他 OpenAI 兼容接口，用于演示文稿模式下的大纲生成

说明：

- 赞美诗歌词模式不需要 LLM。
- 演示文稿模式需要可用的模型接口。

## 快速启动

### Windows

```bat
scripts\start.bat
```

### macOS / Linux

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

启动后打开：

```text
http://localhost:5000
```

启动脚本会在需要时自动创建虚拟环境、安装 Python 依赖、构建前端，并启动 Flask 服务。

## 手动安装

### 1. 配置后端

将 `.env.example` 复制为 `.env`，按需要修改。

默认本地配置如下：

```env
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=qwen3.5-4b
LLM_MAX_TOKENS=16384
LLM_TIMEOUT=360
FLASK_PORT=5000
```

### 2. 安装后端依赖

```bash
python -m venv venv
```

Windows：

```bat
venv\Scripts\activate
pip install -r backend/requirements.txt
```

macOS / Linux：

```bash
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
npm run build
```

### 4. 启动应用

```bash
cd backend
python app.py
```

## 开发方式

前端开发：

```bash
cd frontend
npm install
npm run dev
```

后端开发：

```bash
cd backend
python app.py
```

Vite 已配置把 `/api` 请求代理到 `5000` 端口的 Flask 后端。

## 主要功能

### 演示文稿工作流

- 输入主题并选择场景
- 可粘贴参考文章
- AI 自动生成结构化大纲
- 导出前可手动编辑
- 本地渲染并导出 PowerPoint

### 赞美诗歌词工作流

- 粘贴原始歌词
- 支持单语或双语模式
- 使用语言下拉菜单，而不是固定语言单选项
- 智能识别段落并分页
- 提供适合投影的深色主题
- 导出前可先预览

## 项目结构

```text
slideforge/
├─ backend/
│  ├─ app.py
│  ├─ llm/
│  ├─ lyrics/
│  ├─ renderer/
│  └─ templates/
├─ frontend/
│  ├─ src/
│  └─ dist/
├─ scripts/
├─ .env.example
├─ README.md
└─ README_CN.md
```

## 技术栈

- 前端：React、Vite、Tailwind CSS
- 后端：Flask、Pydantic
- PPTX 生成：`python-pptx`、Pillow
- 大模型接入：OpenAI 兼容 API 客户端

## 常见问题

### 演示文稿模式无法生成大纲

请优先检查：

- LM Studio 已启动
- 已加载模型
- `.env` 中的模型名与当前激活模型一致
- 本地服务端口配置正确

### 页面打不开或前端没有显示

请先构建前端：

```bash
cd frontend
npm install
npm run build
```

### 导出的 PPT 文字过多

渲染器已经做了自动缩放和适配，但如果标题或内容特别长，仍建议在导出前手动精简。

## 许可证

当前仓库还没有附带许可证文件。如果你准备公开开源发布，建议在正式发布前补充许可证。
