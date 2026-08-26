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

### 步骤3：确认导出（关键）
CSV 对话框出现后，**再次调用 `bu.find("Export")`，点击最后一个 ref**：
```python
btns2 = bu.find("Export")
bu.click(btns2[-1])  # 最后一个是对话框底部的蓝色确认按钮
```

**为什么是最后一个**：`bu.find("Export")` 在对话框打开时返回约10个匹配项，包括：
- 工具栏的 Export 按钮（前几个）
- 对话框内的各种 Export 文字（中间）
- 对话框底部的蓝色确认 Export 按钮（最后一个）

### 步骤4：等待下载
```python
record = bu.wait_for_download(timeout=25)
# record.state == "completed" 表示成功
# record.path 是下载文件路径
```

## 导出对话框说明

CSV 导出对话框默认设置：
- 导出范围：本页中的所有文献（施引文献通常≤10条，一页足够）
- 导出字段：引文信息（作者、标题、年份、EID、来源、卷期页、引用计数等）

如果施引文献超过10条，需要注意：默认只导出当前页。如需导出全部，需在对话框中选择导出范围：

```javascript
// CSV对话框打开后，找到范围选择的select或radio
// Scopus的导出对话框通常有"文献 1 - N"的下拉选择
const selects = document.querySelectorAll('select');
for (let s of selects) {
    for (let opt of s.options) {
        // 选择包含"全部"或最大数字的选项
        if (opt.textContent.includes('全部') || /\d+\s*-\s*\d+/.test(opt.textContent)) {
            // 优先选数字最大的范围
            s.value = opt.value;
            s.dispatchEvent(new Event('change', {bubbles: true}));
            break;
        }
    }
}
```

**注意**：施引文献通常较少（大部分文章<10条），默认导出当前页即可。只有高引用文章（>10条施引文献）才需要调整范围。如果不确定，可以在单篇验证阶段检查导出的CSV行数是否与页面显示的施引文献数一致。

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
