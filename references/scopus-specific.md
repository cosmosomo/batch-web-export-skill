# Scopus 学术数据库 - 特定操作指南

本文档记录 Scopus 网站批量导出的特定细节，包括选择器、URL模板、页面结构等。

## 作者页面结构

### 作者详情页 URL
```
https://www.scopus.com/authid/detail.uri?authorId={author_id}
```

### 排序设置
作者详情页的文献列表排序通过 `<select>` 元素控制，直接设置 value 并触发 change 事件：

```javascript
const selects = document.querySelectorAll('select');
for (let s of selects) {
    if (s.value === 'plf-f' || s.value === 'cp-f') {
        s.value = 'cp-f';  // 设施引文献最高
        s.dispatchEvent(new Event('change', {bubbles: true}));
        break;
    }
}
```

**排序 value 映射：**
| value | 含义 |
|-------|------|
| `plf-f` | 日期（降序）- 默认 |
| `plf-t` | 日期（升序） |
| `cp-f` | 施引文献（最高）- 引用数降序 |
| `cp-t` | 施引文献（最低）- 引用数升序 |

### 每页显示数量设置
```javascript
const selects = document.querySelectorAll('select');
for (let s of selects) {
    for (let opt of s.options) {
        if (opt.value === '100') {
            s.value = '100';
            s.dispatchEvent(new Event('change', {bubbles: true}));
            break;
        }
    }
}
```

可选值：10, 20, 50, 100, 200

**推荐设置为200条/页**：减少翻页次数，高引用文章（施引文献>100）也能在一页内显示大部分。施引文献页同样可以设置每页200条。

## 施引文献页 URL 模板

从作者页的引文链接提取 EID 后，直接构造施引文献页 URL：

```
https://www.scopus.com/results/results.uri?s=ref%28{EID}%29&sot=cite&sdt=a&origin=AuthorProfile
```

**EID 格式**：`2-s2.0-XXXXXXXXXX`（如 `2-s2.0-85219204737`）

**从引文链接提取 EID**：
```javascript
const href = a.href;  // https://www.scopus.com/results/results.uri?s=ref%282-s2.0-xxx%29&sot=cite...
const eid = href.split('ref%28')[1].split('%29')[0];
```

## 导出操作流程

### 步骤1：打开 Export 菜单
```python
btns = bu.find("Export")
bu.click(btns.first)  # 第一个是工具栏的Export按钮
```

### 步骤2：选择 CSV 格式
菜单展开后，用 JS 点击 `[role="menuitem"]` 中文字为 "CSV" 的项：
```javascript
const items = document.querySelectorAll('[role="menuitem"]');
for (let el of items) {
    if (el.textContent.trim() === 'CSV') { el.click(); break; }
}
```

**其他可选格式**：CSV、RIS、BibTeX、纯文本

### 步骤3：选择导出范围并确认（关键）

CSV 对话框出现后，**必须先选择导出范围为"Documents 1 - N"，再点击 Export 按钮**。不要选"All documents on this page"（只导出当前页，高引用文章会漏数据）。

```python
# 3a. 用JS选择"Documents 1 - N"单选按钮，并填入总数
bu.js('''
    // 找到"Documents 1 -"的单选按钮（第二个radio）
    const radios = document.querySelectorAll('input[type="radio"]');
    let docRangeRadio = null;
    for (let r of radios) {
        const label = r.closest('label') || r.parentElement;
        if (label && label.textContent.includes('Documents 1')) {
            docRangeRadio = r;
            break;
        }
    }
    if (docRangeRadio) {
        docRangeRadio.click();
        // 找到后面的数字输入框，填入总数（从对话框标题提取，如"Export 565 documents"）
        const title = document.querySelector('[role="dialog"] h2, .modal-title, h2');
        let total = 0;
        if (title) {
            const match = title.textContent.match(/(\\d+)/);
            if (match) total = parseInt(match[1]);
        }
        if (total > 0) {
            const input = docRangeRadio.closest('label')?.querySelector('input[type="number"]') ||
                          document.querySelector('input[type="number"]');
            if (input) {
                input.value = total;
                input.dispatchEvent(new Event('change', {bubbles: true}));
                input.dispatchEvent(new Event('input', {bubbles: true}));
            }
        }
    }
''')
time.sleep(1.0)  # 等待范围选择生效

# 3b. 点击对话框底部的蓝色"Export"按钮
# 用 bu.find("Export") 取最后一个ref（对话框底部的确认按钮）
btns2 = bu.find("Export")
bu.click(btns2[-1])
```

**为什么必须选"Documents 1 - N"**：
- "All documents on this page" 只导出当前页（每页最多200条）
- 高引用文章（如565次施引）需要3页，只导当前页会丢失365条数据
- "Documents 1 - N" 一次性导出全部，最多支持20,000条
- 对话框标题会显示总数（如"Export 565 documents to CSV"），直接提取填入即可

### 步骤4：等待下载
```python
record = bu.wait_for_download(timeout=25)
# record.state == "completed" 表示成功
# record.path 是下载文件路径
```

## 导出对话框结构（精确）

CSV 导出对话框的完整结构：

### 顶部
- **标题**：`Export N documents to CSV`（N为施引文献总数，如"Export 565 documents to CSV"）
- **提示**：`You can export up to 20,000 documents in CSV format.`

### 导出范围（两个单选按钮，必须选第二个）
| 选项 | 说明 | 是否推荐 |
|------|------|----------|
| `All documents on this page` | 只导出当前页（每页最多200条） | ❌ 高引用文章会漏数据 |
| `Documents 1 - [输入框]` | 导出指定范围，输入框填总数 | ✅ **必须选这个** |

### 导出信息（5个分类，默认勾选第一个）
| 分类 | 默认状态 | 包含字段 |
|------|----------|----------|
| `Citation information` | ✅ 默认勾选 | Author(s), Document title, Year, EID, Source title, Volume/issues/pages, Citation count, Source & document type, Publication stage, DOI, Open access |
| `Bibliographical information` | ❌ 未勾选 | Affiliations, Serial identifiers, Publisher, Editor(s), Language, Correspondence address, Abbreviated source title |
| `Abstract & keywords` | ❌ 未勾选 | Abstract, Author keywords, Indexed keywords |
| `Funding details` | ❌ 未勾选 | Funding text, Sponsor |
| `Other information` | ❌ 未勾选 | Number, Tradenames & manufacturers, Accession numbers & chemicals, Acronym, Conference information, Include references |

**默认勾选"Citation information"已足够**，不需要额外勾选其他分类（会增加文件大小和导出时间）。

### 底部选项
- `Select all information` — 链接，点击勾选所有分类（不推荐）
- `Truncate to optimize for Excel` — 开关，**默认开启**，保持开启即可
- `Save as preference` — 复选框，保存为首选项（不需要）
- `Export` — **蓝色按钮**，点击开始导出

### 操作要点
1. **必须选"Documents 1 - N"**，不要选"All documents on this page"
2. 输入框中填入总数（从对话框标题提取，如"Export 565 documents"→填565）
3. 保持默认的"Citation information"勾选
4. 保持"Truncate to optimize for Excel"开启
5. 点击蓝色"Export"按钮

### 高引用文章处理策略
- 施引文献 ≤ 200：选"Documents 1 - N"，一次性导出全部
- 施引文献 > 200：仍然选"Documents 1 - N"，Scopus支持最多20,000条一次性导出
- **不需要翻页导出**：只要选对范围，Scopus会自动处理多页数据
- 验证：导出后检查CSV行数（含表头）是否等于施引文献数+1

## 抓取文献列表

### 从作者页抓取当前页文献
```javascript
const citeLinks = document.querySelectorAll('a[href*="sot=cite"]');
const articles = [];
citeLinks.forEach(a => {
    const href = a.href;
    const citeText = a.textContent.trim();
    let eid = '';
    if (href.includes('ref%28')) eid = href.split('ref%28')[1].split('%29')[0];
    
    // 提取标题（向上遍历找到文献条目）
    let title = '';
    let parent = a.closest('tr, div, li') || a.parentElement;
    for (let i = 0; i < 15 && parent; i++) {
        const titleLink = parent.querySelector('a[href*="/pages/publications/"]');
        if (titleLink) { title = titleLink.textContent.trim(); break; }
        parent = parent.parentElement;
    }
    
    articles.push({eid, citations: parseInt(citeText) || 0, title});
});
```

**注意**：0引用的文章没有引文链接（`a[href*="sot=cite"]`），因此抓不到。如果需要完整列表（含0引用），需用其他选择器抓取文献标题行。

## 分页

作者详情页的分页控件在页面底部，包含页码按钮（1, 2, 3...）和"上一个/下一个"。

翻页方法（**不要用 offsetParent 可见性筛选**，弹窗遮挡会导致按钮被跳过）：
```javascript
// 方法1：用 bu.find() 定位页码按钮（推荐，不受遮挡影响）
// 在 Python 中：bu.click(bu.find("2").first)  —— 但注意"2"可能匹配其他元素
// 更精确的方式：用JS定位分页区域内的页码按钮

// 方法2：JS精确选择分页控件（推荐）
const pagination = document.querySelector('[role="navigation"], .pagination, nav');
if (pagination) {
    const links = pagination.querySelectorAll('a, button');
    for (let el of links) {
        if (el.textContent.trim() === '2') {
            el.click();
            break;
        }
    }
} else {
    // 兜底：全局搜索但不筛选可见性
    const all = document.querySelectorAll('a, button');
    for (let el of all) {
        if (el.textContent.trim() === '2' && el.closest('[role="navigation"], .pagination, nav')) {
            el.click();
            break;
        }
    }
}
```

翻页后等待 5-6 秒让页面加载完成。

## 批量执行

对于100篇以上的批量导出，使用 `scripts/batch_export_template.py` 执行引擎模板：
1. 复制模板到 computer_use_tool 的 code 参数中
2. 修改 CONFIG 中的 URL 模板和参数
3. 填入 ITEMS 列表（从作者页抓取的 EID 和引用数）
4. 3个自定义函数已预置 Scopus 的实现，通常不需要修改
5. 执行即可，引擎自动处理分批、失败收集、重试、重命名

## 已知问题

1. **LeapSpace 推荐弹窗**：右下角可能出现 "Scopus recommends LeapSpace" 弹窗，不影响 ref 点击，但会遮挡视觉。不要用可见性筛选按钮。
2. **低引用文章对话框打开慢**：只有1-2次引用的文章，CSV对话框打开可能需要3秒以上，重试时增加等待时间。
3. **第三页0引用文章**：按引用降序排列后，第三页后半部分是0引用文章，没有引文链接，无法导出施引文献（因为没有施引文献）。
4. **新界面导出需要先选范围**：Scopus 新界面的 CSV 导出对话框必须选择"Documents 1 - N"并填入总数，不能用默认的"All documents on this page"，否则高引用文章会漏数据。
5. **不要误勾选左侧筛选器**：左侧"Refine search"面板有各种筛选器（如"All open access"、年份范围、文献类型等），导出前确认没有误勾选，否则导出结果会被筛选不全。如果误勾选了，取消勾选后重新导出。
6. **导出按钮灰色不可点**：如果导出按钮显示"需要进行有效选择才能导出"，说明当前页没有选中任何文献。需要先全选当前页文献（点击列表顶部的全选复选框），或直接在导出对话框中选择"Documents 1 - N"范围。
