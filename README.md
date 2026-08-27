# batch-web-export-skill

**版本**: v1.3.0
**最后更新**: 2026-08-26
**测试平台**: 豆包（Doubao）桌面端

豆包批量网页导出 Skill — 在需要登录的网站上重复执行"进入列表项→点击导出→选择格式→确认下载"的批量操作。

---

## 🚀 豆包浏览器能力展示

本 Skill 深度利用 **豆包桌面端内置浏览器自动化能力**（`seed_browser_use`），在真实学术数据库场景下验证通过。

### 真实战例

> **Scopus 作者 266 篇文献，按引用量取第 101-200 名，逐篇导出施引文献 CSV**
>
> - 100/100 全部导出成功，集合交集核对 100% 匹配
> - 单篇平均耗时 ~12 秒，含导航+导出+下载+重命名
> - 失败项统一重试，首轮失败率 5%，重试后 100% 成功
> - 全程无人值守，自动处理弹窗遮挡、低引用慢加载、对话框确认等边界情况

### 豆包浏览器核心能力

| 能力 | 说明 | 本 Skill 中的应用 |
|------|------|-------------------|
| **`bu.find()` ref-first 定位** | 基于文本语义查找元素，返回文档作用域 ref，**不受视觉遮挡影响** | 对话框确认按钮取最后一个 ref，解决弹窗遮挡+快照截断双重问题 |
| **`bu.wait_for_download()`** | 原生等待浏览器触发的下载，返回文件路径和状态 | 每篇导出后立即验证 `state==completed` 且文件大小>0 |
| **`bu.js()` 执行任意 JS** | 在页面上下文执行 JavaScript，操作 DOM、读取数据、触发事件 | 选择导出格式、设置排序/分页、提取文献列表 EID |
| **`bu.navigate()` 直接导航** | 构造 URL 模板直接跳转，无需"返回列表→点击下一项" | 施引文献页 URL 模板直接导航，比逐一点击快 3-5 倍 |
| **`bu.network_requests()`** | 读取缓冲的网络请求，捕获 API 响应数据 | 高阶技巧：直接抓 XHR 响应，不解析 DOM |
| **`bu.http_get()`** | 浏览器内 HTTP 请求，自动携带 cookies | 高阶技巧：调用需要登录的内部 API |
| **登录态自动复用** | 豆包直接操作用户已登录的浏览器，无需处理 cookie/token | Scopus、淘宝、后台系统等需登录网站开箱即用 |
| **`computer_use_tool` 沙箱执行** | 浏览器操作在隔离环境执行，超时自动终止，不影响主会话 | 每批6篇在120秒超时内安全执行 |

### 与传统自动化的对比

| 维度 | 传统 Selenium/Playwright 脚本 | 豆包浏览器 + 本 Skill |
|------|-------------------------------|----------------------|
| 登录处理 | 需手动管理 cookie/token，处理验证码 | 自动复用用户登录态，零配置 |
| 元素定位 | 写脆弱的 CSS/XPath，页面改版即失效 | `bu.find()` 语义定位，AI 自动适配页面变化 |
| 弹窗/遮挡 | 需写复杂的等待和可见性判断 | ref 点击不受视觉遮挡，快照截断也不影响 |
| 下载处理 | 需配置下载目录、轮询文件、处理重名 | `wait_for_download()` 原生支持，返回文件路径 |
| 失败恢复 | 需自己写重试逻辑、状态保存 | 内置失败收集+统一重试+集合交集核对闭环 |
| 开发成本 | 写几百行代码，调试元素定位和等待 | 改3个函数+填参数，单篇验证后直接批量跑 |

### 适用平台（豆包浏览器可直接操作）

学术数据库：Scopus · Web of Science · CNKI · PubMed · IEEE Xplore
电商平台：淘宝 · 京东 · 拼多多
后台系统：CRM · OA · 财务系统 · 数据看板
社交媒体：微博 · 小红书 · 知乎 · B站

### 💰 成本优势：Turbo 模型跑批量任务，会员额度根本用不完

豆包智能体支持 **Turbo 模型**，在批量网页导出这类**结构化、重复性高**的任务上表现完全够用，而成本极低：

| 维度 | 说明 |
|------|------|
| **Turbo 模型定价** | 豆包会员额度内 Turbo 模型消耗极低，100篇批量导出仅消耗少量额度 |
| **会员额度** | 豆包专业版/会员自带大量智能体额度，用 Turbo 跑批量任务**根本用不完** |
| **对比外部 API** | 调用 GPT-4/Claude 等外部 API 跑100篇浏览器自动化，API 成本可能几十元；豆包 Turbo 在会员额度内几乎零边际成本 |
| **任务适配性** | 批量导出是"按固定流程重复执行"的任务，Turbo 模型完全胜任，不需要高价模型 |
| **单篇 token 消耗** | 每篇操作仅需页面快照+少量决策 token，Turbo 上下文窗口绰绰有余 |

**结论**：批量网页导出这类任务，用豆包 Turbo 模型跑是**性价比最高的选择**——会员额度覆盖，速度快，结果可靠，不需要为批量任务额外付费。

### 🛡️ 防反爬能力：字节维护的真实浏览器，反爬检测通过率高

豆包浏览器由**字节跳动**持续维护，基于真实 Chromium 内核，在反爬检测方面具有天然优势：

| 维度 | 说明 |
|------|------|
| **真实浏览器指纹** | 基于真实 Chromium 内核，非 headless 模式，浏览器指纹与正常用户一致 |
| **字节级维护** | 字节跳动持续跟进各大平台反爬策略更新，浏览器特征及时适配 |
| **登录态复用** | 操作用户已登录的浏览器，cookie/token/session 全部合法，避免未登录触发风控 |
| **人类级操作节奏** | AI 决策+页面加载自然形成操作间隔，不是脚本级毫秒请求，不易触发频率风控 |
| **无 webdriver 特征** | 不通过 Selenium/webdriver 协议操作，`navigator.webdriver` 等检测特征不存在 |
| **实战验证** | 在 Scopus（学术数据库）、淘宝（电商平台）等有反爬机制的网站上稳定运行，未触发验证码或封禁 |

**对比传统自动化工具**：Selenium/Playwright headless 模式容易被 Cloudflare、Akamai 等反爬系统检测到 webdriver 特征；豆包浏览器操作用户真实登录的浏览器，从指纹到登录态全部合法，**反爬检测通过率显著更高**。

---

## 生态边界（重要）

本 Skill 的不同组件有不同的生态依赖：

| 组件 | 依赖 | 通用性 |
|------|------|--------|
| 四阶段方法论、核对闭环、批量控制 | 纯流程知识 | ✅ 任何 Agent / 人类都能用 |
| `scripts/verify_and_rename.py` | 纯 Python 标准库 | ✅ 任何环境都能运行 |
| `references/scopus-specific.md` 中的 JS | 通用浏览器 JS | ✅ 任何能执行 JS 的浏览器工具 |
| `scripts/batch_export_template.py` | 豆包 `seed_browser_use` API | ⚠️ 豆包专有，其他 Agent 需改写 |
| SKILL.md 中的 `bu.find()` / `bu.click()` 等 | 豆包 `seed_browser_use` API | ⚠️ 豆包专有 |

**结论**：方法论和后处理工具通用，浏览器自动化执行层依赖豆包的 `seed_browser_use` 生态。其他 Agent 可以参考方法论和 JS 代码，但 `bu.xxx()` 调用需要改写为对应平台的浏览器 API。

---

## 适用场景

- **学术数据库**：Scopus、Web of Science、CNKI、PubMed、IEEE Xplore 批量导出文献/引用/施引文献
- **电商平台**：淘宝、京东批量导出订单/商品数据
- **后台系统**：CRM、OA、财务系统批量导出报表/数据
- **社交媒体**：批量导出内容/评论/数据
- 任何需要在网页上重复 N 次相同导出操作的任务

---

## 核心能力

- **四阶段闭环工作流**：前置准备 → 单篇验证 → 批量执行 → 失败重试+核对交付
- **批量执行引擎模板**：`batch_export_template.py` 提供完整框架，只需改3个网站特定函数
- **元素定位优先级**：`bu.find()` ref-first > JS DOM > 快照解析 > 坐标
- **批量大小控制**：每批 ≤ 超时上限 × 60%，失败项不重试继续下一篇
- **集合交集核对**：用唯一标识做确定性核对，消灭沉默失败
- **按业务键重命名**：下载后立即重命名，序号零填充，文件可追溯
- **三层交付结构**：原始文件 + 核对清单 + 全局索引

---

## 目录结构

```
batch-web-export/
├── SKILL.md                          # 主工作流指南（四阶段闭环）
├── README.md                         # 本文件
├── scripts/
│   ├── batch_export_template.py      # 批量执行引擎模板（改3个函数即用）
│   └── verify_and_rename.py          # 核对与重命名命令行工具
├── references/
│   ├── scopus-specific.md            # Scopus 学术数据库特定操作细节
│   ├── advanced-techniques.md        # 高阶技巧与最佳实践（网络捕获/资源阻塞/选择器/Tab管理等）
│   └── common-pitfalls.md            # 9大常见陷阱与排查指南
└── examples/
    └── expected_items_sample.json    # 预期项列表示例
```

---

## 安装方法

### 豆包（Doubao）桌面端

1. 下载或 clone 本仓库：
   ```bash
   git clone https://github.com/cosmosomo/batch-web-export-skill.git
   ```
2. 将仓库中的 `batch-web-export` 文件夹复制到豆包用户技能目录：
   - **Windows**: `%LOCALAPPDATA%\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\`
   - 完整路径示例：`C:\Users\<你的用户名>\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\batch-web-export\`
3. 重启豆包或刷新技能列表，Skill 自动生效

### 其他 AI Agent

1. 参考 `SKILL.md` 中的四阶段方法论
2. 将 `bu.find()` / `bu.click()` 等调用改写为你平台的浏览器 API
3. `verify_and_rename.py` 和 `scopus-specific.md` 中的 JS 可直接使用

---

## 使用方法

### 触发方式

对豆包说以下内容时，Skill 自动触发：
- "批量导出这些文献的引用数据"
- "把这个列表里的每一项都点开然后导出 CSV"
- "帮我批量下载这些报表"
- "逐一点开然后导出"

### 快速开始（Scopus 示例）

1. **单篇验证**：先用1篇跑通流程，确认导出按钮定位、格式选择、下载等待都可靠
2. **抓取列表**：从作者页抓取所有目标文献的 EID、引用数、标题，保存为 JSON
3. **批量执行**：复制 `batch_export_template.py`，填入 ITEMS 列表和 CONFIG 参数，3个自定义函数已预置 Scopus 实现，直接执行
4. **核对交付**：用 `verify_and_rename.py` 做集合交集核对，生成核对清单，按排名重命名，打包交付

### verify_and_rename.py 用法

```bash
python verify_and_rename.py \
  --expected expected_items.json \
  --download_dir ./downloads \
  --output_dir ./renamed \
  --name_template "{rank:03d}_{id}_citations.csv" \
  --checklist checklist.csv
```

功能：
- 读取预期 ID 列表（JSON/CSV，支持 id/eid/ID/EID 等字段别名）
- 扫描下载目录，自动提取文件名中的 ID
- 集合交集核对（缺失/多余/完全匹配）
- 按业务键模板重命名（模板缺字段时自动用 ID 兜底）
- 生成核对清单 CSV

---

## 测试与验证

本 Skill 在 **豆包（Doubao）桌面端** 上经过完整测试：

- **测试场景**：Scopus 作者 Huang, Zhingming（ID: 35268852900）的 266 篇文献，按引用量降序取第 101-200 名，逐篇导出施引文献 CSV
- **测试结果**：100/100 全部导出成功，集合交集核对 100% 匹配，按排名重命名，压缩包交付
- **验证工具**：`verify_and_rename.py` 已用真实数据测试通过
- **批量引擎**：`batch_export_template.py` 基于实际执行流程提炼，Scopus 的3个自定义函数已预置

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.3.0 | 2026-08-26 | Scopus导出流程精确化：CSV对话框必须选"Documents 1 - N"（非"All documents on this page"），推荐每页200条，新增高引用文章处理策略；common-pitfalls新增3个陷阱（只导出第一页、误勾选筛选器、导出按钮灰色）；SKILL.md单篇验证新增导出范围完整性检查 |
| v1.2.0 | 2026-08-26 | 新增高阶技巧参考文档（网络请求捕获、资源阻塞提速、高效选择器、可见性精确判断、Tab管理、速率限制、安全防护）；common-pitfalls 新增陷阱9（offsetParent可见性判断不可靠） |
| v1.1.0 | 2026-08-26 | 新增批量执行引擎模板；修复 scopus-specific.md 翻页代码 offsetParent 矛盾；改进 verify_and_rename.py 命名模板缺字段 fallback；明确生态边界 |
| v1.0.0 | 2026-08-26 | 初始版本：四阶段工作流、核对重命名工具、Scopus 特定指南、常见陷阱文档 |

---

## License

MIT
