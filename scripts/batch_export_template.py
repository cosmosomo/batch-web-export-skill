#!/usr/bin/env python3
"""
批量网页导出 - 执行引擎模板

这是一个可复用的批量导出执行框架。使用时只需修改【配置区】和实现【自定义函数区】
的3个函数，然后将整个代码放入 computer_use_tool(plane="bu") 中执行。

框架自动处理：
- 批量大小控制（避免单调用超时）
- 失败项收集（不当场重试，继续下一篇）
- 下载后立即重命名（避免系统默认名丢失）
- 失败项统一重试（针对性调参）
- 进度输出和最终统计

使用步骤：
1. 修改 CONFIG 字典中的参数
2. 填入 ITEMS 列表（从列表页抓取的预期项）
3. 实现 navigate_to_item / open_export_and_select_format / confirm_export_and_wait
4. 将本文件全部代码复制到 computer_use_tool(plane="bu") 的 code 参数中执行
"""

import time
import os
import re
import shutil
from pathlib import Path

# ============================================================
# 【配置区】根据任务修改以下内容
# ============================================================

CONFIG = {
    # URL模板：用 item 中的字段填充，直接导航到操作页（避免返回列表点击）
    "url_template": "https://www.scopus.com/results/results.uri?s=ref%28{EID}%29&sot=cite&sdt=a&origin=AuthorProfile",
    # 每批处理数量：单篇耗时 × batch_size ≤ 单调用超时 × 60%
    # 经验值：网页导出单篇约10-15秒，120秒超时 → batch_size=6
    "batch_size": 6,
    # 导航后等待秒数（页面加载）
    "wait_after_navigate": 3.0,
    # 选择导出格式后等待秒数（对话框出现）
    "wait_after_format": 2.2,
    # 下载等待超时秒数
    "download_timeout": 25,
    # 输出目录（下载文件重命名后保存到这里）
    "output_dir": "./scopus_citations",
    # 重命名模板：用 item 中的字段填充，序号建议零填充如 {rank:03d}
    "name_template": "{rank:03d}_{EID}_citations.csv",
    # 从下载文件名中提取ID的正则（捕获组1），用于验证和去重
    "id_regex": r"(2-s2\.0-\d+)",
}

# 预期项列表：从列表页抓取，每项是一个dict，至少包含URL模板用到的字段
# 示例格式：
# ITEMS = [
#     {"EID": "2-s2.0-85219204737", "rank": 101, "title": "...", "citations": 9},
#     {"EID": "2-s2.0-85219204738", "rank": 102, "title": "...", "citations": 8},
# ]
ITEMS = []

# 重试时的参数覆盖：失败项统一重试时使用，针对性调参
# 不要首轮就用大参数，会显著增加总耗时
RETRY_OVERRIDES = {
    "wait_after_format": 3.5,   # 低引用文章对话框打开慢，增加等待
    "download_timeout": 35,      # 增加下载超时
}

# ============================================================
# 【配置区结束】
# ============================================================


# ============================================================
# 【自定义函数区】根据目标网站实现以下3个函数
# ============================================================

def navigate_to_item(bu, item, config):
    """
    导航到单个项的操作页。

    参数：
        bu: seed_browser_use 库对象
        item: 当前项的dict（来自ITEMS列表）
        config: 配置字典

    返回：None
    """
    # 默认实现：用URL模板直接导航
    url = config["url_template"].format(**item)
    bu.navigate(url)
    bu.wait_for_load()
    time.sleep(config["wait_after_navigate"])


def open_export_and_select_format(bu, item, config):
    """
    打开导出菜单并选择导出格式。

    参数：
        bu: seed_browser_use 库对象
        item: 当前项的dict
        config: 配置字典

    返回：None

    实现要点：
    - 用 bu.find("导出/Export").first 打开菜单（第一个匹配是工具栏按钮）
    - 格式选择用 JS 点击 [role="menuitem"] 中匹配的项
    - 选择后等待 config["wait_after_format"] 秒让对话框出现
    """
    # === Scopus 示例实现 ===
    btns = bu.find("Export")
    bu.click(btns.first)
    time.sleep(1.0)
    # 用JS选择CSV格式（菜单是动态渲染的，ref可能不稳定）
    bu.js('''
        const items = document.querySelectorAll('[role="menuitem"]');
        for (let el of items) {
            if (el.textContent.trim() === 'CSV') { el.click(); break; }
        }
    ''')
    time.sleep(config["wait_after_format"])


def confirm_export_and_wait(bu, item, config):
    """
    确认导出并等待下载完成。

    参数：
        bu: seed_browser_use 库对象
        item: 当前项的dict
        config: 配置字典

    返回：
        成功：下载记录dict（包含 path, filename, state, bytes 等）
        失败：None

    实现要点：
    - 对话框确认按钮通常是 bu.find("确认/Export") 返回的最后一个ref
    - 不要用可见性筛选（offsetParent），弹窗可能遮挡按钮
    - 用 bu.wait_for_download(timeout=...) 等待下载
    - 验证 record.state == "completed" 且文件大小 > 0
    """
    # === Scopus 示例实现 ===
    btns = bu.find("Export")
    # 最后一个ref是对话框底部的蓝色确认按钮
    bu.click(btns[-1])
    try:
        record = bu.wait_for_download(timeout=config["download_timeout"])
        if record and record.get("state") == "completed":
            # 验证文件大小 > 0
            path = record.get("path", "")
            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                return record
            else:
                print(f"  ⚠️ 下载文件为空或不存在: {path}")
    except Exception as e:
        print(f"  ⚠️ 下载超时或失败: {e}")
    return None


# ============================================================
# 【自定义函数区结束】
# ============================================================


# ============================================================
# 【执行引擎】以下内容不需要修改
# ============================================================

def process_single_item(bu, item, config, item_index, total):
    """
    处理单个项：导航 → 打开导出 → 确认下载 → 验证 → 重命名。

    返回：(success: bool, renamed_path: str or None)
    """
    item_id = config["url_template"].split("{")[1].split("}")[0] if "{" in config["url_template"] else "id"
    item_value = item.get(item_id, str(item_index))

    print(f"  [{item_index}/{total}] 处理: {item_value}")

    try:
        # 1. 导航
        navigate_to_item(bu, item, config)

        # 2. 打开导出菜单并选择格式
        open_export_and_select_format(bu, item, config)

        # 3. 确认导出并等待下载
        record = confirm_export_and_wait(bu, item, config)
        if not record:
            print(f"    ❌ 导出失败")
            return False, None

        # 4. 重命名到输出目录
        output_dir = Path(config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        src_path = Path(record["path"])
        try:
            new_name = config["name_template"].format(**item)
        except KeyError as e:
            # 命名模板中缺少字段，用ID兜底
            print(f"    ⚠️ 命名模板缺少字段 {e}，用ID兜底命名")
            new_name = f"{item_value}_citations.csv"

        dst_path = output_dir / new_name
        shutil.copy2(src_path, dst_path)

        file_size = os.path.getsize(dst_path)
        print(f"    ✅ 成功: {new_name} ({file_size} bytes)")
        return True, str(dst_path)

    except Exception as e:
        print(f"    ❌ 异常: {type(e).__name__}: {e}")
        return False, None


def run_batch(bu, items, config, overrides=None, start_index=0):
    """
    执行一批导出。

    参数：
        bu: seed_browser_use 对象
        items: 要处理的项列表
        config: 配置字典
        overrides: 参数字典覆盖（用于重试时调参）
        start_index: 起始序号（用于进度显示）

    返回：(success_ids: list, failed_items: list)
    """
    if overrides:
        config = {**config, **overrides}

    success_ids = []
    failed_items = []
    total = len(items)

    for i, item in enumerate(items):
        idx = start_index + i + 1
        success, _ = process_single_item(bu, item, config, idx, total + start_index)
        if success:
            # 提取item的ID字段
            id_field = config["url_template"].split("{")[1].split("}")[0] if "{" in config["url_template"] else "id"
            success_ids.append(item.get(id_field))
        else:
            failed_items.append(item)

    return success_ids, failed_items


def execute_all(bu, items, config, retry_overrides=None):
    """
    完整执行：分批处理 → 收集失败 → 统一重试 → 输出统计。

    返回：(all_success_ids, all_failed_items)
    """
    if not items:
        print("❌ ITEMS 列表为空，请先填入预期项")
        return [], []

    batch_size = config["batch_size"]
    total = len(items)
    all_success = []
    all_failed = []

    print("=" * 60)
    print(f"批量导出开始：共 {total} 项，每批 {batch_size} 项")
    print(f"输出目录: {config['output_dir']}")
    print("=" * 60)

    # 分批处理
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_items = items[batch_start:batch_end]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"\n--- 第 {batch_num}/{total_batches} 批 (项 {batch_start+1}-{batch_end}) ---")
        success, failed = run_batch(bu, batch_items, config, start_index=batch_start)
        all_success.extend(success)
        all_failed.extend(failed)

        print(f"  本批结果: 成功 {len(success)} / 失败 {len(failed)}")
        print(f"  累计: 成功 {len(all_success)} / 失败 {len(all_failed)} / 剩余 {total - batch_end}")

    # 统一重试失败项
    if all_failed and retry_overrides:
        print(f"\n{'=' * 60}")
        print(f"统一重试 {len(all_failed)} 个失败项（调参后）")
        print(f"重试参数覆盖: {retry_overrides}")
        print("=" * 60)

        retry_success, retry_failed = run_batch(
            bu, all_failed, config, overrides=retry_overrides, start_index=0
        )
        all_success.extend(retry_success)
        all_failed = retry_failed

        print(f"  重试结果: 成功 {len(retry_success)} / 仍失败 {len(retry_failed)}")

    # 最终统计
    print(f"\n{'=' * 60}")
    print("最终统计")
    print("=" * 60)
    print(f"  总项数: {total}")
    print(f"  成功: {len(all_success)}")
    print(f"  失败: {len(all_failed)}")
    print(f"  成功率: {len(all_success)/total*100:.1f}%")

    if all_failed:
        print(f"\n  仍失败的项:")
        for item in all_failed:
            id_field = config["url_template"].split("{")[1].split("}")[0] if "{" in config["url_template"] else "id"
            print(f"    - {item.get(id_field)}: {item.get('title', '')[:40]}")

    # 验证输出目录
    output_dir = Path(config["output_dir"])
    if output_dir.exists():
        files = list(output_dir.glob("*.csv"))
        print(f"\n  输出目录文件数: {len(files)}")

    print("=" * 60)
    return all_success, all_failed


# ============================================================
# 【执行入口】
# ============================================================

# 当在 computer_use_tool 中执行时，bu 对象已由框架注入
# 直接调用 execute_all 即可
if __name__ == "__main__" or "bu" in dir():
    try:
        execute_all(bu, ITEMS, CONFIG, RETRY_OVERRIDES)
    except NameError:
        print("提示：本脚本需要在 computer_use_tool(plane='bu') 中执行，bu 对象由框架注入")
        print("请将本文件全部代码复制到 computer_use_tool 的 code 参数中")
