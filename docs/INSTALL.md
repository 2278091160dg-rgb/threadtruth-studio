# Install ThreadTruth Studio / 安装 ThreadTruth Studio

[English](#english) | [简体中文](#简体中文)

## English

### Before you begin

Use the Plugin ZIP from the [GitHub Releases landing page](https://github.com/2278091160dg-rgb/threadtruth-studio/releases), plus its separately downloaded `.sha256` sidecar. The optional original-media ZIP is evidence media, not the Plugin, and has a different checksum. Beta.2 is still a candidate until its artifact is published and release verification closes.

The release ZIP extracts to a versioned root such as `threadtruth-studio-1.0.0-beta.2/`. That whole root, containing `.codex-plugin/plugin.json` and `install-local.py`, is the install source. Do not use the inner `skills/threadtruth-studio/` folder.

### 1. Verify and extract

Put the Plugin ZIP and its matching sidecar in the same directory, then run:

```bash
shasum -a 256 -c threadtruth-studio-1.0.0-beta.2.zip.sha256
unzip threadtruth-studio-1.0.0-beta.2.zip
cd threadtruth-studio-1.0.0-beta.2
```

Use the actual published filenames if they differ. Stop if verification fails or extraction does not produce exactly one expected release root.

### 2. Preview, register, then enable

The helper is dry-run by default and prints JSON, including the source path, personal marketplace path, version, and returned `selector`:

```bash
python3 install-local.py
python3 install-local.py --apply
```

`--apply` copies the verified release to **home directory → `plugins` → `threadtruth-studio`** and registers that source in the implicitly discovered personal marketplace. It preserves unrelated marketplace entries. It does **not** enable the Plugin or edit Codex enabled-plugin state.

Run the exact `Next:` command printed by the helper. With the default marketplace it is:

```bash
codex plugin add threadtruth-studio@personal --json
codex plugin list --marketplace personal --available --json
```

The returned `selector` is already the full `plugin@marketplace` value. If the helper reports a marketplace name other than `personal`, use its printed command and substitute that marketplace name in the list command. Do not manually edit JSON/TOML. Do not run `codex plugin marketplace add` for the default personal marketplace.

### 3. First use

Start a **new Codex task** so the Skill is loaded. Upload a garment image first, then enter exactly:

```text
请用 $threadtruth-studio 识别并推荐风格，不要生图
```

Expected: a garment recognition card, a primary recommendation plus alternatives, and the full 24-style catalogue. No image should be generated and no generation cost is authorized.

### Upgrade and rollback

From a separately extracted and checksum-verified newer release, include `--replace` in the dry-run because an active source already exists. Inspect the reported paths, then apply and run the exact `Next:` command printed by the helper:

```bash
python3 install-local.py --replace
python3 install-local.py --apply --replace
codex plugin add threadtruth-studio@personal --json
```

`--replace` creates UTC-stamped backups of the active source and, when present, marketplace config. It adds a UTC `+codex.*` cachebuster to the installed manifest, so installed bytes intentionally differ from the pristine archive. Keep both archive checksum and installed version in any audit record. Start a new task after upgrade.

If runtime verification fails, use the `source_backup` path printed by the applied upgrade; do not overwrite the marketplace file from its backup because it may contain legitimate later changes:

```bash
python3 install-local.py --source <reported-source_backup-path> --replace
python3 install-local.py --source <reported-source_backup-path> --apply --replace
codex plugin add threadtruth-studio@personal --json
```

Again, use the helper's exact printed `Next:` command if the marketplace name is not `personal`, then start a new task and verify the restored release. To remove enabled state, use `codex plugin remove threadtruth-studio@personal --json` (or the returned non-default selector). Source directory, marketplace entry, and backups are separate layers and are retained unless deliberately handled.

### Distribution channels

- **Personal Plugin source:** the tested installer path described above.
- **GitHub:** source code and Release downloads; cloning a repository is not Codex registration or enablement.
- **Official marketplace:** no listing or acceptance is claimed.

See [compatibility](COMPATIBILITY.md). Submit sanitized installation results through the [installation feedback form](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/new?template=installation-feedback.yml); use [Discussions](https://github.com/2278091160dg-rgb/threadtruth-studio/discussions) for broader questions.

## 简体中文

### 开始前

请从 [GitHub Releases 落地页](https://github.com/2278091160dg-rgb/threadtruth-studio/releases)下载 Plugin ZIP，并单独下载与它匹配的 `.sha256` 校验文件。可选的原始媒体 ZIP 是证据素材，不是 Plugin，校验文件也不同。beta.2 在制品发布且验证闭环前仍是候选。

发行 ZIP 会解压为带版本号的根目录，例如 `threadtruth-studio-1.0.0-beta.2/`。安装源是包含 `.codex-plugin/plugin.json` 与 `install-local.py` 的整个根目录，不是内层 `skills/threadtruth-studio/`。

### 1. 校验并解压

把 Plugin ZIP 与匹配的 sidecar 放在同一目录：

```bash
shasum -a 256 -c threadtruth-studio-1.0.0-beta.2.zip.sha256
unzip threadtruth-studio-1.0.0-beta.2.zip
cd threadtruth-studio-1.0.0-beta.2
```

若正式发布文件名不同，以实际文件名为准。校验失败或未得到唯一、预期的发行根目录时立即停止。

### 2. 预检、注册、启用

安装器默认 dry-run，并输出 JSON，其中包含源路径、personal marketplace 路径、版本与返回的 `selector`：

```bash
python3 install-local.py
python3 install-local.py --apply
```

`--apply` 把已校验发行包复制到**用户主目录 → `plugins` → `threadtruth-studio`**，并注册到系统隐式发现的 personal marketplace，同时保留无关条目。它**不会**启用 Plugin，也不会修改 Codex 的启用状态。

执行安装器打印的完整 `Next:` 命令。默认 marketplace 的示例是：

```bash
codex plugin add threadtruth-studio@personal --json
codex plugin list --marketplace personal --available --json
```

返回的 `selector` 已经是完整的 `plugin@marketplace`。若安装器返回的 marketplace 名称不是 `personal`，以其打印命令为准，并在 list 命令中替换名称。不要手改 JSON/TOML；默认 personal marketplace 不需要执行 `codex plugin marketplace add`。

### 3. 首次使用

新建一个 **Codex 任务**以加载 Skill。先上传服饰图，再原样输入：

```text
请用 $threadtruth-studio 识别并推荐风格，不要生图
```

预期返回服饰识别卡、主推与备选风格、完整 24 风格目录；不应生成图片，也没有授权任何生图费用。

### 升级与回滚

在单独解压且校验通过的新版本根目录做 dry-run 时也必须带 `--replace`，因为活动源已经存在。核对路径后应用，并执行安装器打印的完整 `Next:` 命令：

```bash
python3 install-local.py --replace
python3 install-local.py --apply --replace
codex plugin add threadtruth-studio@personal --json
```

`--replace` 会为活动源目录和已有 marketplace 配置创建 UTC 时间戳备份，并给安装后的 manifest 增加 UTC `+codex.*` cachebuster，因此安装后字节与原始 ZIP 有意不同。审计时同时记录归档 checksum 与安装版本。升级后新建任务。

若运行验证失败，使用应用升级时输出的 `source_backup` 路径恢复；不要用 marketplace 备份直接覆盖现有文件，因为它可能已有合法的新变更：

```bash
python3 install-local.py --source <输出的-source_backup-路径> --replace
python3 install-local.py --source <输出的-source_backup-路径> --apply --replace
codex plugin add threadtruth-studio@personal --json
```

如果 marketplace 不是 `personal`，仍以安装器打印的完整 `Next:` 命令为准；随后新建任务验证旧版本。移除启用状态使用 `codex plugin remove threadtruth-studio@personal --json`（或返回的非默认 selector）。启用状态、源目录、marketplace 条目和备份是不同层，默认不会一并删除。

### 三种渠道不是一回事

- **Personal Plugin source：**本页说明的已测试安装路径。
- **GitHub：**源码与 Release 下载渠道；仅 clone 不等于完成 Codex 注册和启用。
- **官方 marketplace：**本项目未宣称上架或获批。

另见[兼容性说明](COMPATIBILITY.md)。脱敏安装结果请提交到[安装反馈表](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/new?template=installation-feedback.yml)；一般讨论请使用 [Discussions](https://github.com/2278091160dg-rgb/threadtruth-studio/discussions)。
