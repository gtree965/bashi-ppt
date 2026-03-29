# 巴适PPT

[English README](./README.md)

**版本：** 0.1.0

**许可证：** [MIT License](./LICENSE)

**更新日志：** [CHANGELOG.md](./CHANGELOG.md)

巴适PPT原名 SlideForge，是一个以本地运行为核心的 AI PPT 生成工具，面向教师、教会同工和家庭沟通场景。它可以根据主题或参考文章生成可编辑的大纲，在本地渲染 `.pptx` 文件，也支持单语或双语的赞美诗歌词投影。

## 核心亮点

- 通过 LM Studio 等 OpenAI 兼容接口进行本地 AI 大纲生成
- 面向教学、教会、家长说明和通用场景的演示文稿工作流
- 演示文稿模式下自动匹配主题模板
- 纯 Python 本地渲染 PPTX，支持中文字体和文字自适应
- 赞美诗歌词模式支持单语与双语投影
- 单语中文歌词支持繁简转换
- 单语歌词支持扩展到每页最多 6 行
- 可选标题页和阿们页
- 提供带嵌入式 Python 的 Windows 便携启动器
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

### Windows 便携版

```bat
run_portable.bat
```

启动后打开：

```text
http://localhost:5100
```

便携启动器会：

- 使用随包附带的嵌入式 Python
- 自动安装后端依赖
- 自动确保 OpenCC 可用，以支持繁简转换
- 直接服务已构建好的 `frontend/dist`
- 在 `5100` 端口启动应用

说明：

- `演示文稿 PPT` 仍然需要 LM Studio 或其他 OpenAI 兼容接口。
- `赞美诗歌词 PPT` 不依赖 LLM。

## 手动安装

如果你在 macOS / Linux 上使用，或需要开发调试，建议使用手动安装方式。

### 1. 配置后端

将 `.env.example` 复制为 `.env`，按需要修改。

默认本地配置如下：

```env
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=qwen3.5-4b
LLM_MAX_TOKENS=16384
LLM_TIMEOUT=360
FLASK_PORT=5100
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

然后打开：

```text
http://localhost:5100
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

Vite 已配置把 `/api` 请求代理到 `5100` 端口的 Flask 后端。

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
- 单语中文模式支持繁简转换
- 单语模式可选扩展到每页最多 6 行
- 智能识别段落并分页
- 提供适合投影的深色主题
- 导出前可先预览

## 使用方法

### 演示文稿 PPT

1. 打开 `演示文稿 PPT` 标签页。
2. 输入主题并选择场景。
3. 如有需要，可粘贴参考文章。
4. 等待本地模型生成大纲。
5. 检查并编辑大纲内容。
6. 导出为 PowerPoint 文件。

### 赞美诗歌词 PPT

1. 打开 `赞美诗歌词 PPT` 标签页。
2. 输入歌曲标题并粘贴歌词。
3. 选择单语或双语模式。
4. 如有需要，可开启繁简转换或单语扩展行数。
5. 调整每页行数和主题样式。
6. 按需勾选标题页或阿们页。
7. 先预览分页结果。
8. 导出为歌词投影 PowerPoint 文件。

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

## 故障排查

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

## 常见问题

### 赞美诗歌词模式需要 LM Studio 吗？

不需要。歌词模式只做本地解析与渲染，不依赖大模型。

### 繁简转换需要联网吗？

不需要。繁简转换通过本地 OpenCC 组件完成。

### 为什么大纲生成比较慢？

演示文稿模式依赖本地模型。若模型较小但带推理链，或者机器性能有限，生成可能需要几分钟。

### 可以换成自己的 OpenAI 兼容接口吗？

可以。直接修改 `.env` 中的 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL` 即可。

## 致谢

- Flask 后端框架
- React 和 Vite 前端生态
- `python-pptx` 与 Pillow 用于 PowerPoint 生成
- LM Studio 用于本地 OpenAI 兼容模型服务
- 开源社区

## 作者

**Alex Li**  
Email: ncorecpu@gmail.com

## 许可证

本项目采用 **[MIT License](./LICENSE)** 发布。
