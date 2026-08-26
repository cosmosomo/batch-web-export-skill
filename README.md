# batch-web-export-skill

豆包（Doubao）批量网页导出 Skill — 适用于需要登录的网站上重复执行"进入列表项→点击导出→选择格式→确认下载"的批量操作。

## 适用场景

- **学术数据库**：Scopus、Web of Science、CNKI、PubMed、IEEE Xplore 批量导出文献/引用/施引文献
- **电商平台**：淘宝、京东批量导出订单/商品数据
- **后台系统**：CRM、OA、财务系统批量导出报表/数据
- **社交媒体**：批量导出内容/评论/数据
- 任何需要在网页上重复 N 次相同导出操作的任务

## 核心能力

- **四阶段闭环工作流**：前置准备 → 单篇验证 → 批量执行 → 失败重试+核对交付
- **元素定位优先级**：`bu.find()` ref-first > JS DOM > 快照解析 > 坐标
- **批量大小控制**：每批 ≤ 超时上限 × 60%，失败项不重试继续下一篇
- **集合交集核对**：用唯一标识做确定性核对，消灭沉默失败
- **按业务键重命名**：下载后立即重命名，序号零填充，文件可追溯
- **三层交付结构**：原始文件 + 核对清单 + 全局索引

## 目录结构

```
batch-web-export/
├── SKILL.md                          # 主工作流指南（四阶段闭环）
├── scripts/
│   └── verify_and_rename.py          # 可复用的核对与重命名命令行工具
└── references/
    ├── scopus-specific.md            # Scopus 学术数据库特定操作细节
    └── common-pitfalls.md            # 8大常见陷阱与排查指南
```

## 安装方法

### 豆包（Doubao）桌面端

1. 下载或 clone 本仓库
2. 将 `batch-web-export` 文件夹复制到豆包的用户技能目录：
   - Windows: `%APPDATA%\..\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\`
   - 或在豆包中通过技能管理界面导入
3. 重启豆包或刷新技能列表，Skill 即可自动触发

### 其他支持 Skill 格式的 AI Agent

将 `batch-web-export` 文件夹放入对应 Agent 的技能目录即可。

## 使用方法

当你对豆包说以下内容时，该 Skill 会自动触发：

- "批量导出这些文献的引用数据"
- "把这个列表里的每一项都点开然后导出 CSV"
- "帮我批量下载这些报表"
- "逐一点开然后导出"

Skill 会引导你完成四阶段工作流，确保批量导出的可靠性和可核对性。

## 验证与测试

本 Skill 在 **豆包（Doubao）桌面端** 上经过完整测试验证：

- **测试场景**：Scopus 作者 Huang, Zhingming（ID: 35268852900）的 266 篇文献，按引用量降序取第 101-200 名，逐篇导出施引文献 CSV
- **测试结果**：100/100 全部导出成功，集合交集核对 100% 匹配，按排名重命名，压缩包交付
- **验证工具**：`scripts/verify_and_rename.py` 已用真实数据测试通过

## 可复用脚本

### verify_and_rename.py

命令行核对与重命名工具：

```bash
python verify_and_rename.py \
  --expected expected_ids.json \
  --download_dir ./downloads \
  --output_dir ./renamed \
  --name_template "{rank:03d}_{id}_citations.csv" \
  --checklist checklist.csv
```

功能：
- 读取预期 ID 列表（JSON/CSV，支持 id/eid/ID/EID 等字段别名）
- 扫描下载目录，自动提取文件名中的 ID
- 集合交集核对（缺失/多余/完全匹配）
- 按业务键模板重命名文件
- 生成核对清单 CSV

## License

MIT
