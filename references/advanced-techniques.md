# 高阶技巧与最佳实践

本文档收集 seed_browser_use / browser-use 生态的高阶技巧，帮助提升自动化效率、稳定性和安全性。

---

## 一、数据采集加速

### 1.1 网络请求捕获 — 不解析 DOM，直接抓 API 数据

**原理**：页面渲染前，数据已经通过 XHR/Fetch 请求返回。通过 CDP 监听网络响应，直接获取结构化 JSON，比解析 DOM 快 10 倍且更稳定。

**seed_browser_use API**：
```python
# 读取缓冲的网络请求（控制台和网络读取只消耗各自的缓冲事件）
requests = bu.network_requests()

# 浏览器内 HTTP 请求（自动带当前页面的 cookies，适合需要登录的 API）
data = bu.http_get("https://api.example.com/endpoint")
```

**适用场景**：
- 抓取列表页数据（文献列表、商品列表、订单列表）
- 获取分页数据（API 通常支持 page 参数）
- 验证操作是否成功（检查 API 响应状态码）

**实战示例**：Scopus 作者页加载时，文献列表数据通过 XHR 返回。捕获该请求可直接拿到结构化的 EID、引用数、标题，无需写复杂的 DOM 遍历 JS。

---

### 1.2 资源阻塞提速 — 阻塞图片/字体/分析脚本，页面加载快 2-3 倍

**原理**：自动化不需要渲染图片和字体，阻塞这些资源能显著减少页面加载时间和网络带宽。

**实现方式**（通过 `bu.js()` 或 CDP）：
```python
# 方式1：导航后移除图片 src（简单但图片可能已开始加载）
bu.js('''
    document.querySelectorAll('img').forEach(img => img.removeAttribute('src'));
    document.querySelectorAll('link[rel="stylesheet"]').forEach(link => link.remove());
''')

# 方式2：通过 CDP 设置 Network.setBlockedURLs（导航前设置，更彻底）
# seed_browser_use 可通过 bu.cdp() 调用底层 CDP 命令
bu.cdp("Network.setBlockedURLs", {"urls": ["*.png", "*.jpg", "*.gif", "*.woff*", "*google-analytics*"]})
```

**阻塞优先级**（从高到低）：
1. 分析/跟踪脚本（google-analytics、facebook pixel、doubleclick）— 既提速又减少干扰
2. 图片（png/jpg/gif/webp）— 自动化不需要看
3. 字体（woff/woff2/ttf）— 不影响 DOM 操作
4. 视频/音频（mp4/mp3）— 几乎用不到

**注意**：不要阻塞 CSS（可能影响元素可见性和布局）和 JavaScript（页面功能依赖）。

---

## 二、元素定位

### 2.1 高效选择器优先级

**优先级从高到低**：

| 优先级 | 选择器类型 | 示例 | 稳定性 |
|--------|-----------|------|--------|
| 1 | `bu.find("文本")` ref | `bu.click(bu.find("Export").first)` | 最高（AI 自动找最佳匹配） |
| 2 | data-testid / data-* | `[data-testid="export-button"]` | 高（专为测试设计） |
| 3 | ID | `#export-button` | 高（页面内唯一） |
| 4 | role + name | `[role="button"][aria-label="Export"]` | 高（无障碍属性稳定） |
| 5 | CSS class | `.export-btn.primary` | 中（可能随样式变更） |
| 6 | XPath | `//div[@class='container']/div[3]/button` | 低（结构变更即失效） |

**seed_browser_use 推荐方式**：永远优先用 `bu.find("文本")` + ref 点击，不要手写 CSS/XPath。只有当 `bu.find()` 无法定位时，才回退到 `bu.js()` + CSS 选择器。

```python
# 推荐
bu.click(bu.find("导出").first)

# 回退（bu.find 找不到时）
bu.js("document.querySelector('[data-testid=export]').click()")

# 避免
bu.js("document.querySelector('div.main > div.actions > button:nth-child(2)').click()")
```

---

### 2.2 DOM 可见性精确判断 — 用 getBoundingClientRect，不用 offsetParent

**问题**：`el.offsetParent !== null` 不是可靠的可见性判断。`position: fixed` 的元素 `offsetParent` 为 `null`，但它是可见的；被弹窗遮挡的元素 `offsetParent` 不为 `null`，但它实际上不可点击。

**正确判断**：
```javascript
function isInViewport(el) {
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 &&
           rect.top < window.innerHeight && rect.bottom > 0 &&
           rect.left < window.innerWidth && rect.right > 0;
}

function isClickable(el) {
    if (!isInViewport(el)) return false;
    // 检查是否被其他元素遮挡
    const rect = el.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const topEl = document.elementFromPoint(centerX, centerY);
    return el === topEl || el.contains(topEl);
}
```

**seed_browser_use 的优势**：`bu.find()` + ref 点击不受视觉遮挡影响（ref 是文档作用域标识，直接调用元素的 click() 方法），所以不需要判断可见性。**只有在用坐标点击（`bu.click_xy()`）时才需要判断可见性。**

**今天踩的坑**：用 `offsetParent !== null` 筛选翻页按钮，结果被 LeapSpace 弹窗遮挡的按钮被跳过了。正确做法是用 ref 点击（不筛选可见性）。

---

## 三、任务设计

### 3.1 任务描述必须带验证条件

**原理**：AI 决策存在概率性，可能点错按钮或走错路径。明确的验证条件让 AI 知道什么是"成功"，减少错误。

**反面示例**：
```
"点击导出按钮"  → AI 可能点错，也不知道是否成功
```

**正面示例**：
```
"找到文字为'Export'的按钮并点击，等待CSV下载对话框出现，
点击对话框底部的蓝色'Export'确认按钮，
等待下载完成后验证文件大小 > 0 字节"
```

**验证条件类型**：
- URL 变化（`等待URL包含'/home'`）
- 元素出现（`等待文字为'成功'的提示出现`）
- 文件下载（`等待下载完成，验证文件大小>0`）
- 网络请求（`等待API返回200状态码`）
- DOM 变化（`等待列表项数量从10变为20`）

---

### 3.2 关键步骤分拆为小任务

**原理**：单次任务越复杂，AI 决策错误概率越高。将复杂流程拆分为多个小任务，每个任务只做一件事，降低决策复杂度。

**反面**：
```
"打开Scopus作者页，设置按引用排序，每页100条，翻到第二页，
对每篇文章点击引用，导出CSV，下载，重命名"
```

**正面**（分阶段）：
```
阶段1：设置排序和分页（设置按引用降序、每页100条）
阶段2：单篇验证（对第1篇跑通完整导出流程）
阶段3：批量执行（每批6篇，失败项记录不重试）
阶段4：失败重试+核对交付（统一重试、集合交集核对、重命名、打包）
```

**每个小任务的完成标准**必须明确，未达标不进入下一阶段。

---

## 四、浏览器管理

### 4.1 Tab 管理三件套

**适用场景**：需要从列表页进入详情页操作，操作完返回列表继续下一项，且目标网站不支持 URL 模板直接导航。

```python
# 1. 标记初始标签页
initial_tab = bu.current_tab()

# 2. 在新标签页打开链接（不离开列表页）
bu.js("window.open('https://example.com/detail/123', '_blank')")
time.sleep(2)
# 切换到新标签
tabs = bu.list_tabs()
new_tab = next(t for t in tabs if "detail/123" in t["url"])
bu.switch_tab(new_tab)

# 3. 在新标签页执行操作...
# ...

# 4. 关闭新标签，返回初始页
bu.close_tab()
bu.switch_tab(initial_tab)
```

**注意**：`target="_blank"` 的链接会在新标签打开，`bu` 可能仍附着在旧标签。用 `bu.list_tabs()` 匹配 URL 找到新标签，再 `bu.switch_tab()` 切换。

---

### 4.2 登录态复用

**原理**：每次重新登录浪费时间，且可能触发风控。复用已有的浏览器登录态。

**seed_browser_use 现状**：豆包自动复用用户的 Chrome 浏览器登录态，无需手动处理。

**进阶**：如果需要在其他环境复用登录态：
```python
# 导出 cookies
cookies = bu.js("JSON.stringify(document.cookie)")

# 或通过 CDP 获取完整 cookies（包括 HttpOnly）
all_cookies = bu.cdp("Network.getAllCookies")
```

**browser-use 官方方式**：
```python
# 保存会话状态
await agent.browser.save_storage_state("session.json")

# 加载会话（保持登录状态）
from browser_use import BrowserConfig
browser_config = BrowserConfig(storage_state="session.json")
```

---

### 4.3 速率限制 — 防止被网站封禁

**原理**：短时间内大量请求会触发网站的反爬机制，导致 IP 被封禁或出现验证码。

```python
import time

class RateLimiter:
    def __init__(self, requests_per_minute=30):
        self.requests = []
        self.rpm = requests_per_minute

    def wait(self):
        cutoff = time.time() - 60
        self.requests = [t for t in self.requests if t > cutoff]
        if len(self.requests) >= self.rpm:
            sleep_time = 60 - (time.time() - self.requests[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self.requests.append(time.time())

# 使用
limiter = RateLimiter(requests_per_minute=30)
for item in items:
    limiter.wait()
    # 执行操作...
```

**经验值**：
- 学术数据库（Scopus/WoS）：30-60 次/分钟较安全
- 电商平台（淘宝/京东）：10-20 次/分钟较安全
- 反爬严格的网站：5-10 次/分钟

**今天的情况**：Scopus 100篇约20分钟，约5篇/分钟，非常温和，没有触发风控。

---

## 五、安全与合规

### 5.1 域名白名单/黑名单

**适用场景**：让 AI 自由浏览时，防止它导航到银行、支付、色情等敏感网站。

```python
from urllib.parse import urlparse

BLOCKED_DOMAINS = {
    'chase.com', 'bankofamerica.com', 'wellsfargo.com',  # 银行
    'paypal.com', 'stripe.com', 'venmo.com',              # 支付
    'accounts.google.com', 'login.microsoft.com',          # 账号登录
}

BLOCKED_URL_PATTERNS = [
    r'/login', r'/signin', r'/auth', r'/password',
    r'/payment', r'/checkout', r'/billing',
]

def validate_url(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix('www.')
    # 黑名单检查
    if any(domain == d or domain.endswith('.' + d) for d in BLOCKED_DOMAINS):
        return False
    # 敏感路径检查
    if any(re.search(p, url, re.I) for p in BLOCKED_URL_PATTERNS):
        return False
    return True
```

**今天的情况**：任务范围明确（只在 Scopus），不需要域名限制。但如果做通用爬虫 Skill，这是必须的安全措施。

---

### 5.2 敏感操作防护

**原则**：涉及资金、数据删除、账号变更的操作，必须人工确认。

| 操作类型 | 风险 | 处理方式 |
|----------|------|----------|
| 支付/下单 | 资金损失 | 必须人工确认，禁止自动执行 |
| 删除数据 | 不可逆 | 必须人工确认，禁止自动执行 |
| 提交表单 | 外部影响 | 关键表单需人工确认 |
| 发送消息 | 社交影响 | 需人工确认内容 |
| 密码填充 | 凭证泄露 | 禁止自动填充密码字段 |

**seed_browser_use 对应机制**：`interaction.request_action(type="browserControl")` — 在需要人工确认时，将浏览器控制权交给用户。

---

## 六、技巧速查表

| 技巧 | 一句话 | 适用场景 |
|------|--------|----------|
| 网络请求捕获 | 直接抓 API，不解析 DOM | 列表数据抓取、验证操作结果 |
| 资源阻塞 | 阻塞图片/字体/分析，提速2-3倍 | 大量页面导航、慢网站 |
| 验证条件 | 任务描述写明什么是成功 | 所有自动化任务 |
| 步骤分拆 | 复杂流程拆成小任务 | 多步骤批量操作 |
| ref-first | 用 bu.find() 不用 CSS/XPath | 所有元素交互 |
| getBoundingClientRect | 不用 offsetParent 判断可见性 | 坐标点击前的可见性检查 |
| Tab三件套 | 标记/新标签/关闭返回 | 列表→详情→返回的流程 |
| 速率限制 | 控制请求频率防封禁 | 反爬严格的网站 |
| 域名白名单 | 防止AI跑偏到敏感网站 | 通用自由浏览 |
| 人工确认 | 资金/删除/提交必须确认 | 高风险操作 |
