# SQCS-Skills

面向 Codex 的实用技能集合，覆盖远程服务器运维、模型推理服务、Obsidian 知识库检索、项目会议纪要归档，以及从 HTML 演示文稿到高保真可编辑 PPTX 的多种制作流程。

> 每个一级技能目录均可独立使用。将其放入 Codex Skills 目录后，Codex 会根据任务描述自动匹配相应工作流。

## 功能一览

| 分类 | 技能 | 适用场景 |
| --- | --- | --- |
| 服务器 | `ssh-content` | 从 Windows 通过 SSH 连接、巡检和诊断远程 Linux 服务器，支持凭据注册表与安全的临时密码传递。 |
| 服务器 | `model-interface` | 发现本地模型、启动并验证 OpenAI 兼容的 vLLM 推理服务。 |
| 知识库 | `obsidian` | 检索、读取、汇总本地 Obsidian Vault 中的 Markdown 笔记、标签和 Frontmatter。 |
| 项目管理 | `project-meeting-minutes` | 将会议转写整理为结构化 Excel 纪要，匹配或创建标准项目目录并完成归档。 |
| PPT | `ppt-gen` | 根据单页参考图生成高质量、可编辑的企业风格 PPTX。 |
| PPT | `image-to-editable-ppt` | 将截图、海报、图表或 UI 重建为可编辑的单页 PowerPoint。 |
| PPT | `image-svg-pptx-pro` | 通过“图片 -> SVG -> PPTX”流程，高保真重建复杂页面、报告图和幻灯片。 |
| PPT | `ai-visual-ppt-composer` | 用 AI 无文字背景、HTML/CSS/SVG 版式和 PPTXGenJS 制作高品质可编辑演示文稿。 |
| PPT | `html-ppt` | 基于主题、版式模板、动画与演讲者模式制作可键盘操作的静态 HTML 演示文稿。 |

## 目录结构

```text
SQCS-Skills/
├── 服务器技能/
│   ├── ssh-content/
│   └── model-interface/
├── obsidian笔记技能/
├── 项目管理技能/
│   └── project-meeting-minutes/
├── PPT技能/
│   ├── ai-visual-ppt-composer/
│   ├── html-ppt-skill-main/
│   ├── image-svg-pptx-pro-skill/
│   ├── image-to-editable-ppt/
│   └── ppt-gen/
└── README.md
```

各技能目录以 `SKILL.md` 作为入口。部分技能还包含：

- `agents/openai.yaml`：Codex Agent 元数据。
- `scripts/`：可复用的命令行工具或构建脚本。
- `references/`：详细工作流、数据结构和质量规范。
- `assets/`、`templates/`：演示文稿主题、布局、动画和示例资源。

## 安装

### 方式一：克隆后按需安装

```powershell
git clone https://github.com/Liangmu1234/SQCS-Skills.git
cd SQCS-Skills
```

将需要的技能文件夹复制到 Codex 的 Skills 根目录。Windows 上通常为：

```powershell
$skillsDir = "$env:USERPROFILE\.codex\skills"

Copy-Item ".\服务器技能\ssh-content" $skillsDir -Recurse
Copy-Item ".\服务器技能\model-interface" $skillsDir -Recurse
Copy-Item ".\obsidian笔记技能" "$skillsDir\obsidian" -Recurse
Copy-Item ".\项目管理技能\project-meeting-minutes" $skillsDir -Recurse
```

PPT 技能可按需复制并使用清晰的目录名：

```powershell
Copy-Item ".\PPT技能\ai-visual-ppt-composer" $skillsDir -Recurse
Copy-Item ".\PPT技能\html-ppt-skill-main" "$skillsDir\html-ppt" -Recurse
Copy-Item ".\PPT技能\image-svg-pptx-pro-skill" "$skillsDir\image-svg-pptx-pro" -Recurse
Copy-Item ".\PPT技能\image-to-editable-ppt" $skillsDir -Recurse
Copy-Item ".\PPT技能\ppt-gen" $skillsDir -Recurse
```

安装完成后重新打开 Codex 会话，或重启 Codex，使其重新发现本地技能。

### 方式二：作为团队技能库使用

保留本仓库目录结构，并将需要的技能目录同步至团队约定的 Codex Skills 目录。建议仅分发实际需要的技能，避免将包含特定机器路径、模型路径或工具依赖的技能直接用于不兼容的环境。

## 技能说明

### 服务器技能

#### `ssh-content`

用于在 Windows 环境中安全地访问和操作远程 Linux 服务器。

- 通过 `scripts/connect-ssh.cmd` 建立 SSH 连接，绕开本地 PowerShell 执行策略限制。
- 支持从 Markdown 注册表解析服务器别名和凭据。
- 可检查主机、内核、负载、内存、磁盘、进程、端口、服务和 Docker 容器。
- 使用临时环境变量传递未注册服务器的密码，避免将密码写入命令行、日志或技能文件。
- 对安装软件、修改服务、防火墙、存储、账号和重启等高风险操作，要求先明确授权并在变更后验证。

示例：

```powershell
& ".\scripts\connect-ssh.cmd" -Target "<主机或别名>" -Command "hostname && uptime"
```

#### `model-interface`

用于将服务器上的本地模型目录部署为 OpenAI 兼容的推理接口，默认工作流以 vLLM 为中心。

- 连接服务器后先检查 GPU、CUDA、运行中的容器、已占用端口及已有启动脚本。
- 验证模型目录、模型配置、`vllm` 版本和 Python/PyTorch CUDA 可用性。
- 以保守参数启动服务，并按 GPU 数量、显存、模型结构和既有脚本调整并行度。
- 通过 `/v1/models` 和 `/v1/chat/completions` 进行服务就绪验证。
- 最终返回 Base URL、模型名和 API Key，并说明上下文长度策略。

## Obsidian 笔记技能

### `obsidian`

用于读取和检索本地 Obsidian Vault，不修改笔记内容。

- 支持按关键词搜索笔记正文和文件名。
- 支持读取指定 Markdown、列出笔记、提取标签和读取 Frontmatter。
- 默认通过 `scripts/obsidian_cli.py` 完成受限范围内的本地文件读取。
- 对模糊查询先搜索，再读取最相关的笔记内容。

示例：

```powershell
python ".\scripts\obsidian_cli.py" search "项目复盘"
python ".\scripts\obsidian_cli.py" read "01-笔记/example.md"
```

> 使用前请检查 `SKILL.md` 中配置的 Vault 路径是否与本机一致；如不一致，请按团队规范调整后再分发。

## 项目管理技能

### `project-meeting-minutes`

用于将会议转写或语音识别记录整理为结构化项目会议纪要，并将最终 Excel 副本归档到对应项目的 `8.其他` 目录。

- 从转写中提取项目、客户、日期、参会人、测试范围、结论、责任人、风险和遗留事项；无法确认的信息标记为“待确认”或按模板约束留空。
- 优先使用用户提供的 Excel 模板；未提供时，从 `Meeting-Minutes-Template` 仓库同步受控缓存并按会议主题选择模板。
- 在项目信息目录中进行高置信项目匹配；项目不存在时，从完整标准项目模板复制并创建对应年度、季度和序号目录。
- 始终先复制模板再填写，保留字段标题、公式、数据验证、预置选项和原有样式，不修改模板原件。
- 对最终 XLSX 执行路径、关键字段、数据验证、公式、版式和源模板哈希检查。

项目目录定位、模板同步和副本创建优先使用附带脚本：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\prepare_project_minutes.ps1" -MinutesTemplateName "异构服务器.xlsx" ...
```

> 该技能包含本机项目根目录和受控缓存约定。分发到其他环境前，请先检查 `SKILL.md` 中的固定路径、模板仓库与目录规范。

## PPT 技能

### `ppt-gen`

将单页参考图重建为高质量、可编辑的 `.pptx`。

- 默认面向深色企业科技风格，强调背景氛围、可编辑文字、面板、图表和图标的分层。
- 优先使用本地素材缓存；缺少素材时可生成无文字背景或图标。
- 优先通过 `@oai/artifact-tool` 导出，并对 PPTX 包结构、字体、媒体文件和预览进行校验。

### `image-to-editable-ppt`

适合“参考图必须尽量还原，同时保留编辑能力”的单页重建任务。

- 按图层盘点文字、数字、形状和图像区域。
- 将文本、色块、圆角框、页脚和分隔线重建为原生 PowerPoint 对象。
- 将照片、Logo 和复杂图标裁剪为独立图片对象，而不是把整张参考图作为背景。
- 提供基于 JSON Manifest 的辅助构建脚本。

```bash
python scripts/build_editable_pptx.py path/to/manifest.json
```

### `image-svg-pptx-pro`

适合复杂的 PPT 截图、学术图片、UI 页面和报告页。

核心流程：

```text
源图片 -> 标准化图片 -> 语义布局计划 -> SVG 中间稿 -> 可编辑 PPTX -> 视觉 QA
```

- 在可编辑性与视觉一致性间提供 `balanced`、`max_editable` 和 `visual_locked` 三种策略。
- 将标题、卡片、线条、箭头、图表和表格优先重建为可编辑元素。
- 将照片、复杂插画、Logo、渐变和密集截图保留为裁剪资源或 SVG 回退，以避免低质量重绘。

### `ai-visual-ppt-composer`

适合路演、汇报、课程、竞赛、学术演讲等对视觉质感和编辑能力都有要求的场景。

- AI 只负责无文字的背景、光影、纹理和插画氛围。
- HTML/CSS/SVG 负责精确的版式、层级、图表和视觉节奏。
- PPTXGenJS 将主要文字、形状、表格、图表和图像重建为原生 PowerPoint 内容。
- 包含项目初始化、Deck JSON 校验和构建脚本。

```bash
python scripts/avpc_init_project.py --target ./my-ppt-project --title "AI Visual PPT"
node scripts/avpc_build.mjs deck.json output
```

### `html-ppt`

用于快速制作专业、静态、可演示的 HTML 幻灯片。

- 提供 36 套主题、31 种单页布局、15 套完整演示文稿模板。
- 包含 CSS 入场动画、Canvas 特效、键盘导航、全屏、概览和主题切换。
- 支持演讲者模式：当前页、下一页、演讲稿和计时器可在独立窗口中协同展示。
- 内置 Headless Chrome 渲染脚本，可将页面导出为 PNG。

```bash
./scripts/new-deck.sh my-talk
./scripts/render.sh examples/my-talk/index.html 12
```

## 依赖与环境

不同技能的运行依赖不同，请按使用范围准备环境：

| 场景 | 主要依赖 |
| --- | --- |
| SSH 运维 | Windows、OpenSSH 客户端、可访问的远程主机，以及可选的服务器注册表。 |
| 模型服务 | Linux 服务器、NVIDIA GPU、CUDA、Python、PyTorch，以及通常为 vLLM 的推理后端。 |
| Obsidian 检索 | Python 3 和可读取的本地 Obsidian Vault。 |
| 项目会议纪要 | Windows PowerShell、Git、Excel `.xlsx` 模板，以及 Codex 的 Spreadsheets 技能和工作区依赖。 |
| PPTX 重建 | Python 3；部分流程还需要 PowerPoint、Node.js、PPTXGenJS 或 Codex bundled runtime。 |
| HTML PPT | 现代浏览器；导出 PNG 时需要可被渲染脚本调用的 Chrome/Chromium。 |

请先阅读目标技能目录中的 `SKILL.md`。其中包含任务触发条件、前置检查、准确的命令格式和质量验收标准。

## 安全说明

- 不要将服务器密码、API Key、内网地址或用户数据写入 `SKILL.md`、示例命令、Git 历史或公开 Issue。
- 使用 `ssh-content` 时，优先执行只读检查；涉及服务、软件包、网络、账号或重启的修改，应在得到明确授权后执行。
- 使用 `model-interface` 启动服务前，确认端口占用、GPU 资源和现有进程，避免中断其他模型服务。
- 使用 Obsidian 技能前确认 Vault 根目录，避免在不受控目录中搜索和读取文件。
- 生成项目会议纪要时，不修改模板原件、模板缓存或现有项目目录；项目名称或匹配结果不明确时必须先确认，并妥善保护转写中的客户与项目信息。
- 生成或重建 PPT 时，注意源图片、演讲稿、数据和 Logo 的授权与保密要求。

## 贡献

欢迎通过 Issue 或 Pull Request 补充新技能、修复脚本和完善文档。提交前建议：

1. 为新技能提供清晰的 `name`、`description` 和 `SKILL.md` 工作流。
2. 将可复用脚本放入 `scripts/`，将较长说明放入 `references/`。
3. 不提交凭据、服务器地址、私有模型路径、真实业务数据或生成的临时缓存。
4. 为新工具补充最小可运行示例和验证方式。

## 许可证

仓库根目录当前未提供统一许可证文件。使用、复制或再分发前，请先与仓库维护者确认授权范围；其中部分第三方或子项目资源可能包含其自身的许可证声明。
