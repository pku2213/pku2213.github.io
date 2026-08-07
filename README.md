# Zebin Zhang Academic Website

这是 Zebin Zhang 个人学术网站的唯一维护目录。网页公开地址为：

- Website: <https://pku2213.github.io/>
- GitHub repository: <https://github.com/pku2213/pku2213.github.io>

以后修改网页时，请直接编辑本目录中的 `site/`，不要继续修改旧的 Codex 任务目录，也不要直接修改 GitHub 的 `gh-pages` 分支。

## 目录结构

```text
pku2213.github.io/
├─ site/                         # GitHub Pages 实际发布的网站（唯一网页源文件）
│  ├─ index.html                 # 简介、Research Interests、News、Publications、Honors
│  └─ assets/
│     ├─ site.css                # 字体、字号、颜色、间距、图片尺寸、响应式排版
│     ├─ site.js                 # 导航栏等少量交互
│     └─ img/                    # 肖像照和两项工作的展示图片
├─ publish.ps1                   # 检查、提交、推送并等待上线的一键发布脚本
├─ tools/qa_site.py              # 桌面端和手机端浏览器自动检查
├─ _local_docs/                  # 本地总结、研究摘要、QA 截图；不会上传到 GitHub
├─ .github/workflows/deploy.yml  # GitHub Actions 自动部署配置
└─ README.md                     # 本说明
```

仓库里还保留了早期 al-folio 项目文件，主要是为了保持 Git 历史。当前部署流程只发布 `site/`，日常维护不需要改动那些旧文件。

## 最常见的修改

### 1. 修改文字、日期或链接

打开 `site/index.html`，搜索对应英文内容后直接修改。例如：

- 个人简介和院系链接：`About` 部分
- 研究方向：`Research Interests` 部分
- 时间线：`News` 部分
- 论文题目、作者和会议链接：`Publications` 部分
- 荣誉：`Honors` 部分

外部链接应保留完整的 `https://...` 地址。EDTM 论文当前链接为：

<https://ieeexplore.ieee.org/abstract/document/11497247>

### 2. 修改字体、字号、颜色或页面宽度

打开 `site/assets/site.css`。文件开头的 `:root` 集中了最常用的设置：

```css
:root {
  --accent: #0869a6;             /* 链接和强调色 */
  --ink: #24292f;                /* 正文颜色 */
  --sans: Calibri, "Segoe UI", sans-serif;
  --serif: Georgia, "Times New Roman", serif;
  --width: 1060px;               /* 正文最大宽度 */

  --font-body: 24px;             /* 桌面端正文 */
  --font-body-mobile: 17px;      /* 手机端正文 */
  --font-page-title: 42px;       /* 页面主标题 */
  --font-section-title: 26px;    /* News 等栏目标题 */
  --font-publication-title: 23px;
}
```

通常只需要改这些变量。比如把桌面正文从 24 px 改成 22 px，只需修改：

```css
--font-body: 22px;
```

### 3. 替换肖像照或论文图片

把新图片放入 `site/assets/img/`，然后在 `site/index.html` 中修改相应 `<img>` 的 `src` 路径。建议：

- 肖像照使用 JPG 或 WebP，并提前裁剪好比例。
- 工作展示图优先使用 PNG 或 WebP，确保文字在网页宽度下仍能看清。
- 不要在文件名中使用空格；例如 `snw2026-slide11.png`。
- 发布脚本会检查 HTML 引用的本地图片是否真实存在。

原始 EDTM/SNW 演示文稿继续保存在各自的研究目录中，无需复制进公开仓库。为网站整理的研究摘要位于本机 `_local_docs/research-summaries/`，该目录不会上传到 GitHub。

### 4. 替换浏览器标签页图标

准备一张正方形或接近正方形的 PNG/JPG 图片，在项目根目录运行：

```powershell
python .\tools\build_favicon.py "图片的完整路径"
```

脚本会自动生成浏览器需要的 32 px、192 px、Apple touch icon 和 `favicon.ico`。如果原图不是正方形，会从中心裁剪。生成后运行 `publish.ps1` 即可发布；浏览器可能缓存旧图标，可用 `Ctrl+F5` 刷新，或关闭原标签页后重新打开。

## 本地预览

在 PowerShell 中运行：

```powershell
Set-Location .\site
python -m http.server 8080
```

然后打开 <http://127.0.0.1:8080/>。预览结束后，在 PowerShell 中按 `Ctrl+C` 停止服务器。

不要直接双击 `index.html` 作为最终验证方式；本地 HTTP 服务器更接近 GitHub Pages 的真实环境。

## 一键重新发布

先在文件资源管理器中打开项目根目录，并从该目录启动 PowerShell。

推荐命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\publish.ps1 -Message "Update News"
```

如果当前 PowerShell 已允许执行本地脚本，也可以运行：

```powershell
.\publish.ps1 -Message "Update News"
```

脚本会依次：

1. 确认当前位于 `main` 分支，并检查未解决的 Git 冲突。
2. 检查 `index.html` 引用的本地资源是否缺失。
3. 用 Playwright 在桌面端和手机端执行页面 QA，并把截图保存在 `_local_docs/qa/`。
4. 只暂存 `site/` 中的网页改动，避免误上传个人研究资料。
5. 创建 Git commit 并推送到 `origin/main`。
6. 等待 GitHub Actions 完成部署，直到公网 `index.html` 与本地文件的 SHA-256 完全一致。
7. 输出最终网址 <https://pku2213.github.io/>。

如果只改了很小的内容、临时不想运行浏览器 QA，可以使用：

```powershell
.\publish.ps1 -Message "Fix a typo" -SkipTests
```

如部署耗时较长，可把等待上限从默认 240 秒调大：

```powershell
.\publish.ps1 -Message "Update Publications" -PublishTimeoutSeconds 600
```

## 首次运行 QA 的依赖

若脚本提示缺少 Playwright，请运行：

```powershell
pip install playwright
python -m playwright install chromium
```

安装完成后重新运行 `publish.ps1`。若只是需要紧急发布，可临时加 `-SkipTests`，但建议随后补做完整检查。

## GitHub Pages 的工作方式

`.github/workflows/deploy.yml` 会在 `main` 分支中的 `site/**` 发生变化后自动运行，并将 `site/` 发布到 `gh-pages` 分支。

```text
编辑 site/ → publish.ps1 推送 main → GitHub Actions → gh-pages → 公网网站
```

因此：

- 日常只编辑 `main` 分支的 `site/`。
- 不要手工编辑或强制推送 `gh-pages`。
- 如果发布失败，到 GitHub 仓库的 **Actions** 页面查看日志。

## 手工 Git 命令（脚本不可用时）

```powershell
git status
git add -- site
git commit -m "Update website"
git push origin main
```

推送后等待 GitHub Actions，再访问 <https://pku2213.github.io/> 并用 `Ctrl+F5` 强制刷新。

## 常见问题

### 脚本提示 `No website changes to commit`

说明 `site/` 与上一次 commit 相同。脚本仍会核对公网首页是否与本地一致，不会创建空 commit。

### GitHub 要求登录

按照 Git Credential Manager 的弹窗完成登录，或先运行 `gh auth login`。不要把访问令牌写进脚本或 README。

### 修改后网页没有立即变化

先查看 GitHub Actions 是否完成；完成后等待几十秒，再按 `Ctrl+F5`。发布脚本正常结束时已经完成了首页哈希核对。

### QA 截图在哪里

位于 `_local_docs/qa/`。该目录已写入本仓库的本地 `.git/info/exclude`，资料保留在电脑上但不会公开上传。

## 发布前自检

- 所有内容均为英文，姓名、年份、月份和作者身份准确。
- EDTM 链接可以打开；SNW 未正式上线前不要添加虚构链接。
- 桌面端和手机端都没有文字溢出或异常换行。
- 肖像照不过大，论文图片中文字清晰可读。
- `git status` 中没有意外加入 PPT、证件照原图或其他私人文件。
