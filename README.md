# Present-TC

An agent skill for evidence-led HTML reports and editable PowerPoint presentations.

从内容组织、版式选择到视觉与交付检查，制作单文件 HTML 汇报或可编辑 PPTX。保留已有材料风格，不依赖个人技能、公司内网、私有母版或 API key。

**项目身份：** 这是个人制作和维护的汇报材料技能项目。基础色盘采用蓝色 #0052D9、深灰 #53585F 及灰黑白；高饱和青绿橙不固定纳入，允许按内容少量自主选用协调辅助色。仓库包含模板素材与 W3/W7 字体。

**发布状态：** 本目录可用于 GitHub Desktop 的公开源码发布，包含技能说明、交互参考代码和验证流程。随附213页原生PPT、213张预览、模板索引与W3/W7字体；个人笔记仍被排除。目前没有附加开源许可证；公开可见不等于授予开源使用或再分发许可。

## 能做什么

- 创建、编辑和重排 HTML 汇报，默认单文件、离线可读、电脑与窄屏适配。
- 创建、编辑和重排 PPTX，优先现有母版，保留可编辑文字、表格和图表。
- 根据内容选对比、流程、时序、矩阵、数字、层级或表格，而非固定套三卡片。
- 使用克制的蓝黑灰默认样式；用户要求和现有视觉系统优先。
- 区分事实、判断、建议和待确认事项，检查显示问题与外发敏感信息。

不包含会议纪要整理、访谈提纲计时、普通网站开发，也不是无需智能体即可自动完成所有汇报的渲染引擎。

## 安装

在支持 Agent Skills 的客户端中，将技能目录以 `present-tc` 命名放入该客户端的技能目录。必须保留 `SKILL.md`、`references/`、`scripts/`、完整 `assets/`；`agents/` 是可选客户端元数据，不影响其他客户端阅读主定义。

例如，对支持该目录的 Claude Code，从本仓库根目录执行以下命令。若目标已有同名技能，先备份并比较，不要直接覆盖：

```bash
test ! -e "$HOME/.claude/skills/present-tc" && mkdir -p "$HOME/.claude/skills/present-tc" && cp -R SKILL.md references scripts agents assets "$HOME/.claude/skills/present-tc/"
```

重新加载技能或开启新会话；按客户端能力显式选择 `present-tc`，或直接提出汇报任务。下载或安装时保留完整 `assets/present-tc/` 目录及内部相对路径。W3/W7为WOFF2格式，可用于HTML；PPT端仍需检查实际可用的桌面字体。

## 使用示例

```text
使用 present-tc，把以下材料做成离线单文件 HTML 汇报。
受众是项目负责人，重点是进展、证据与下一步。保留待确认项，不编造数字。
```

```text
使用 present-tc，基于我提供的母版生成可编辑 PPTX。
沿用已有颜色和字体，先判断每页的信息关系，不要连续三页使用相同卡片布局。
```

```text
使用 present-tc，只修改这份汇报第 3 页的措辞和对齐。
不要改变其余页面、母版或已有交互，完成后检查受影响区域。
```

英文请求也可触发，例如 `Use present-tc to create an offline HTML report from these notes.` 主体指导采用中文，输出语言服从用户。虚构练习材料见 [示例输入](examples/brief.md)；人工验收情形见 [行为测试](tests/scenarios.md)。

## 环境与验证

技能指令本身不依赖运行时；随附只读检查脚本需要 Python 3.9+，仅使用标准库，无需 pip 安装。制作 PPTX 由客户端实际可用的演示应用、格式工具或公开编辑库完成，不把这些工具捆绑进本包。

```bash
python3 scripts/validate_repo.py
python3 scripts/check_public.py
python3 -m unittest discover -s tests -v
python3 scripts/check_delivery.py path/to/report.html
python3 scripts/check_delivery.py path/to/report.pptx --json
```

最后两个路径应替换为实际交付文件。检查器不上传、不执行输入中的脚本/宏、不解压到磁盘；限制输入及 ZIP 解压总量为 100 MiB、包内成员不超过 10000 个。

退出码：0 表示未发现基础检查错误，1 表示发现错误；警告需要人工复核。HTML 检查为启发式，无法覆盖所有 CSS/动态 JS。PPTX 检查不等于完整 OOXML 校验。两者都不验证视觉质量、数据真实性、跨设备字体或实际可编辑性。

`check_public.py` 检查 Git 当前跟踪文件及未忽略的新文件，验证独立副本中的代码、213页模板、预览、索引和字体是否完整；不会提交或上传。`--require-license` 可用于另行检查开源许可文件是否存在。

GitHub Actions 只运行仓库检查、公共文件检查与单元测试，不发布文件，不请求机密、不安装第三方包。它的存在不代表已在 GitHub 上执行。

## 文件组织

```text
present-tc/
├── SKILL.md
├── references/             # HTML、PPT、视觉、版式、QA、公开边界
├── assets/                 # 完整模板、213张预览、字体、HTML代码与配置
├── agents/openai.yaml      # 可选客户端展示配置
├── scripts/                # 只读基础检查与仓库检查
├── tests/                  # 自动测试与人工行为验收清单
├── examples/brief.md       # 明确标记为虚构的输入
├── docs/RELEASING.md       # GitHub Desktop发布步骤
├── .github/workflows/validate.yml
└── README.md
```

## 许可与公开发布

仓库当前不包含 `LICENSE`，可作为公开可见的源码仓库，不应称为 MIT、Apache 等开源授权项目。若后续决定授予开源许可，再添加对应完整许可证和准确权利人信息。随附素材自身的来源与许可说明仍适用，不因公开仓库而改变。

详细检查项见 [发布说明](docs/RELEASING.md)。不要把真实业务材料、无关素材、历史仓库或鉴权配置放进此仓库；生成输出建议放在已忽略的 `outputs/` 中。


## 默认汇报配置

固定16:9页面、独立侧栏、逐页PRESENT、模块移动/缩放与文字编辑、保存重开、页码、持续倒计时。HTML中文44/32/28/20px；PPT28/20/16/14pt；中文腾讯体W3/W7。详细行为以SKILL.md及references为准。完整模板、预览、索引和字体与技能一起分发。
