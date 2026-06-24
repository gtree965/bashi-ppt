# Bashi PPT v0.1.0

Release date: **June 23, 2026**

巴适PPT的第一个公开共创版本。

## 中文发布说明

巴适PPT不追求“一句话生成整套幻灯片”，而是帮助教师完成材料与课堂之间的工作：

- 审阅和修改备课文章、大纲；
- 生成原生可编辑的 PPTX；
- 将逐页讲稿写入 PowerPoint 备注区；
- 在严格依据材料模式中由用户确认事实；
- 事实遗漏或页面没有依据时给出透明提示。

主要功能：

- 根据主题、参考材料或两者结合进行备课；
- 教学创作 / 严格依据材料双模式；
- 自动推荐页数，并允许手动覆盖；
- 备课文章、大纲、逐页讲稿和 PPTX 导出；
- 图示和可选 Pixabay 图片；
- 单语/双语赞美诗歌词投影；
- 设置界面直接支持阿里云百炼、硅基流动、OpenRouter 和自定义兼容接口。

### Windows 便携包

下载 `Bashi-PPT-v0.1.0-Windows-Portable.zip`，完整解压后双击 `run_portable.bat`。

便携包包含 Python 3.12、依赖、预构建前端、后端和用户文档；不包含 API Key、AI 模型、测试结果或内部规划资料。

本版启动脚本保持 ASCII-only，以降低不同 Windows 终端代码页导致的乱码启动风险。

云端模型会接收用户提交的材料。本地模型速度和质量取决于电脑硬件。请在使用敏感资料前阅读 [隐私与数据去向](PRIVACY_CN.md)。

## English release notes

This is the first public co-creation release of Bashi PPT.

### What makes this release different

Bashi PPT focuses on the work between source material and classroom delivery:

- reviewable preparation instead of a black-box one-click deck;
- editable outlines and native PPTX elements;
- per-slide speaker notes in the PowerPoint Notes pane;
- a strict-material path with user-confirmed facts;
- transparent structural warnings when confirmed facts are missing or unassigned.

### Included workflows

- Teaching creation from a topic, source material, or both
- Preparation-article review and export
- Strictly grounded source-material workflow
- Slide-count recommendation with manual override
- Per-slide speaker-note generation
- Editable PPTX rendering
- Diagrams and optional Pixabay images
- Single-language and bilingual hymn-lyrics decks
- Settings-panel support for Alibaba Cloud Bailian / DashScope, SiliconFlow,
  OpenRouter, and custom compatible endpoints

### Windows portable download

Download `Bashi-PPT-v0.1.0-Windows-Portable.zip`, extract it completely, and run `run_portable.bat`.

The package includes Python 3.12, required libraries, the prebuilt frontend, backend, renderer, and user documentation. It excludes API keys, AI models, generated presentations, tests, experiment results, and internal planning material.

The Windows launcher is kept ASCII-only to avoid code-page related startup glitches on different terminals.

Read [Privacy and Data Flow](PRIVACY.md) before using sensitive material with a cloud model.

### Known limitations

- Windows PowerPoint and WPS Office are the primary tested office applications.
- macOS and Linux require manual Python installation in this release.
- Grounding audit checks fact-reference structure, not full semantic truth.
- Local model performance varies widely by hardware.
- Cloud availability, policy, retention, and fees vary by provider.
