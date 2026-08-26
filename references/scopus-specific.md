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

如果施引文献超过10条，需要注意：默认只导出当前页。如需导出全部，需在对话框中选择"文献 1 - N"范围。

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

翻页方法：
```javascript
// 点击指定页码
const links = document.querySelectorAll('a, button');
for (let el of links) {
    if (el.textContent.trim() === '2' && el.offsetParent !== null) {
        el.click();
        break;
    }
}
```

翻页后等待 5-6 秒让页面加载完成。

## 已知问题

1. **LeapSpace 推荐弹窗**：右下角可能出现 "Scopus recommends LeapSpace" 弹窗，不影响 ref 点击，但会遮挡视觉。不要用可见性筛选按钮。
2. **低引用文章对话框打开慢**：只有1-2次引用的文章，CSV对话框打开可能需要3秒以上，重试时增加等待时间。
3. **第三页0引用文章**：按引用降序排列后，第三页后半部分是0引用文章，没有引文链接，无法导出施引文献（因为没有施引文献）。
