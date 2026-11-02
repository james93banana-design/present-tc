# 使用 GitHub Desktop 发布

本目录是独立的 `present-tc` 仓库，使用 `main` 分支。完整版本包含技能说明、HTML交互代码、默认配置、虚构示例、检查脚本及整套 `assets/present-tc/` 素材（213页PPT、213张预览、索引、页码映射与W3/W7字体）。

## 已排除的本地文件

- `AI-progress.txt`：个人分享素材。
- `outputs/`、`private/`、缓存、环境配置与常见凭据文件。

这些文件可留在电脑上；不要在 GitHub Desktop 中强制加入忽略文件，也不要选择上一级目录作为仓库。

## 发布前运行

```bash
python3 scripts/validate_repo.py
python3 scripts/check_public.py
python3 -m unittest discover -s tests -v
```

公共文件检查会读取 Git 跟踪文件和未被忽略的新文件，在临时独立目录验证结构与链接，校验整套素材及其索引路径、PPT页数和文件哈希。它不会提交、上传或修改原文件，也不扫描其他目录。

目前未附加开源许可证；这不阻止将源码设为 Public，但不要宣称已授予开源使用许可。若以后选择开源许可证，添加完整 `LICENSE` 后再运行 `python3 scripts/check_public.py --require-license`。该选项只检查文件存在且非空。

## GitHub Desktop 操作

1. 选择 **File → Add Local Repository**，选中本 `present-tc` 目录。
2. 在 **Changes** 查看待提交文件，确认包含完整 `assets/present-tc/`，且没有 `AI-progress.txt`。若已存在首次提交，跳过提交步骤。
3. Summary 填写 `Prepare present-tc for public source release`，点击 **Commit to main**。
4. 点击 **Publish repository**，名称填写 `present-tc`，选择自己的账号，取消 **Keep this code private**，然后发布。
5. 在 GitHub 查看文件及 Actions 结果；本地检查通过不等于远程 CI 已运行。

本次发布包含整套指定模板及字体，保留素材自身的来源与许可说明；生成的真实业务汇报不纳入提交。默认字号、布局编辑、持续计时和 PPT 可编辑性规则仍保留。HTML 参考脚本需要按 DOM 契约接入，并不是完整的即开即用演示应用；浏览器交互与 PPT 渲染验收见 `tests/scenarios.md`。

## 仓库描述建议

Agent skill for offline HTML reports and editable PowerPoint presentations, with layout editing, presentation timers, and delivery checks.
