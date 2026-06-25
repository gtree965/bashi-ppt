# Bashi PPT v0.1.1

Release date: **June 25, 2026**

Major feature update introducing local project persistence and project library.

## 中文发布说明

巴适PPT本版迎来了重要的项目管理功能，解决了刷新或重启应用后“数据丢失”的问题。

主要功能：

- **本地项目持久化**：每次生成大纲或编辑内容时，系统都会在后台自动保存（1.5秒防抖），将所有主题、参考材料、大纲、讲稿及配置保存至本机 `projects/` 文件夹下的 JSON 文件中。
- **最近编辑项目**：在首页直接列出最近编辑的最多 5 个项目，点击即可一键继续编辑，重开项目会自动置顶。
- **项目图书馆**：点击“浏览全部过往项目”可打开弹窗搜索历史项目，方便快速导入和再次修改。
- **安全防穿越**：限制项目 ID 字符集，仅允许 `[A-Za-z0-9_-]`，防止路径遍历漏洞；同时设置单个文件 2MB 上限。
- **纯本地存储**：数据全保存在本地，绝对不上传云端，保障教师教案和敏感资料的绝对隐私。

### Windows 便携包

下载 `Bashi-PPT-v0.1.1-Windows-Portable.zip`，完整解压后双击 `run_portable.bat`。

便携包包含 Python 3.12、依赖、预构建前端、后端和用户文档；不包含 API Key、AI 模型、测试结果或个人项目数据。

---

## English release notes

This release introduces critical project management and auto-saving features to prevent data loss.

### New Features

- **Local Project Persistence**: The application now automatically saves your progress (including topic, source material, outlines, and speaker notes) in the background (1.5s debounced) to a local JSON file inside the `projects/` directory.
- **Recent Projects**: Displays up to 5 recently edited presentations on the home screen for easy one-click resuming. Re-opening a project dynamically moves it back to the top of the list.
- **Project Library**: A new modal library allows searching and loading any previously saved projects directly within the UI.
- **Path-Traversal Security & Limits**: Restricts project IDs to `[A-Za-z0-9_-]` characters to prevent file-system traversal exploits, with a 2MB maximum file size safeguard.
- **100% Offline & Private**: All project files are stored locally on your machine and never uploaded to any remote server.

### Windows portable download

Download `Bashi-PPT-v0.1.1-Windows-Portable.zip`, extract it completely, and run `run_portable.bat`.
