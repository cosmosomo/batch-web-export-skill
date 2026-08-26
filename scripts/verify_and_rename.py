#!/usr/bin/env python3
"""
批量网页导出 - 核对与重命名工具

功能：
1. 读取预期的ID列表（JSON或CSV）
2. 扫描下载目录，提取已下载文件的ID
3. 用集合交集核对：缺失、多余、完全匹配
4. 按业务键重命名文件（支持排名、ID等模板）
5. 生成核对清单CSV

用法：
  python verify_and_rename.py \
    --expected expected_ids.json \
    --download_dir ./downloads \
    --output_dir ./renamed \
    --name_template "{rank:03d}_{id}_citations.csv" \
    --checklist checklist.csv

预期ID列表格式（JSON）：
  [
    {"id": "2-s2.0-xxx", "rank": 101, "title": "...", "citations": 9},
    ...
  ]

或CSV格式（必须包含id列）：
  id,rank,title,citations
  2-s2.0-xxx,101,...,9
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path


def load_expected(filepath):
    """加载预期ID列表，支持JSON和CSV"""
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"错误：预期文件不存在: {filepath}")
        sys.exit(1)

    if filepath.suffix.lower() == '.json':
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    elif filepath.suffix.lower() == '.csv':
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = list(reader)
    else:
        print(f"错误：不支持的文件格式: {filepath.suffix}")
        sys.exit(1)

    # 统一ID字段名（支持 id/eid/ID/EID/record_id/item_id 等常见命名）
    id_aliases = ['id', 'eid', 'ID', 'EID', 'record_id', 'item_id', 'document_id', 'pub_id']
    for item in data:
        if 'id' not in item:
            for alias in id_aliases:
                if alias in item:
                    item['id'] = item[alias]
                    break
        if 'id' not in item:
            print(f"错误：预期列表中缺少id字段（支持的别名: {id_aliases}）: {item}")
            sys.exit(1)

    return data


def extract_id_from_filename(filename, id_pattern=None):
    """从文件名中提取ID"""
    if id_pattern:
        match = re.search(id_pattern, filename)
        if match:
            return match.group(1)
    # 默认：提取文件名中类似 2-s2.0-xxx 或纯数字ID的模式
    patterns = [
        r'(2-s2\.0-\d+)',  # Scopus EID
        r'(\d{6,})',        # 长数字ID
    ]
    for p in patterns:
        match = re.search(p, filename)
        if match:
            return match.group(1)
    return None


def scan_download_dir(download_dir, id_pattern=None):
    """扫描下载目录，返回 {id: filepath} 映射"""
    download_dir = Path(download_dir)
    if not download_dir.exists():
        print(f"错误：下载目录不存在: {download_dir}")
        sys.exit(1)

    result = {}
    for f in download_dir.iterdir():
        if f.is_file():
            fid = extract_id_from_filename(f.name, id_pattern)
            if fid:
                result[fid] = f
            else:
                print(f"警告：无法从文件名提取ID: {f.name}")
    return result


def verify(expected, downloaded_ids):
    """核对预期与实际，返回匹配、缺失、多余"""
    expected_ids = set(item['id'] for item in expected)
    downloaded_set = set(downloaded_ids.keys())

    matched = expected_ids & downloaded_set
    missing = expected_ids - downloaded_set
    extra = downloaded_set - expected_ids

    return matched, missing, extra


def rename_files(expected, downloaded_files, output_dir, name_template):
    """按业务键重命名文件到输出目录"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    renamed_count = 0
    failed_rename = []

    for item in expected:
        fid = item['id']
        if fid in downloaded_files:
            src = downloaded_files[fid]
            # 生成文件名：模板缺字段时用ID兜底，避免全部失败
            try:
                new_name = name_template.format(**item)
            except KeyError as e:
                print(f"    ⚠️ 命名模板缺少字段 {e}，用ID兜底命名: {fid}")
                ext = Path(name_template).suffix or '.csv'
                new_name = f"{fid}{ext}"
            except Exception as e:
                failed_rename.append((fid, f"命名模板错误: {e}"))
                item['renamed_file'] = ''
                item['downloaded'] = True
                continue

            try:
                dst = output_dir / new_name
                shutil.copy2(src, dst)
                renamed_count += 1
                item['renamed_file'] = new_name
                item['downloaded'] = True
            except Exception as e:
                failed_rename.append((fid, str(e)))
                item['renamed_file'] = ''
                item['downloaded'] = True
        else:
            item['renamed_file'] = ''
            item['downloaded'] = False

    return renamed_count, failed_rename


def generate_checklist(expected, output_path):
    """生成核对清单CSV"""
    if not expected:
        return

    # 确定所有字段
    fieldnames = list(expected[0].keys())
    # 确保 downloaded 和 renamed_file 在最后
    for f in ['downloaded', 'renamed_file']:
        if f in fieldnames:
            fieldnames.remove(f)
            fieldnames.append(f)

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(expected)

    print(f"核对清单已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='批量导出核对与重命名工具')
    parser.add_argument('--expected', required=True, help='预期ID列表文件（JSON或CSV）')
    parser.add_argument('--download_dir', required=True, help='下载文件目录')
    parser.add_argument('--output_dir', default='./renamed', help='重命名后输出目录')
    parser.add_argument('--name_template', default='{id}.csv',
                        help='命名模板，支持 {id} {rank} {title} 等字段，如 "{rank:03d}_{id}.csv"')
    parser.add_argument('--checklist', default='checklist.csv', help='核对清单输出路径')
    parser.add_argument('--id_pattern', default=None, help='从文件名提取ID的正则表达式（捕获组1）')
    parser.add_argument('--no_rename', action='store_true', help='只核对不重命名')

    args = parser.parse_args()

    # 1. 加载预期列表
    print("=" * 60)
    print("阶段1：加载预期列表")
    expected = load_expected(args.expected)
    print(f"  预期项数: {len(expected)}")

    # 2. 扫描下载目录
    print("\n阶段2：扫描下载目录")
    downloaded_files = scan_download_dir(args.download_dir, args.id_pattern)
    print(f"  已下载文件数: {len(downloaded_files)}")

    # 3. 核对
    print("\n阶段3：核对")
    matched, missing, extra = verify(expected, downloaded_files)
    print(f"  完全匹配: {len(matched)}")
    print(f"  缺失（预期有但未下载）: {len(missing)}")
    print(f"  多余（下载有但预期没有）: {len(extra)}")

    if missing:
        print(f"\n  缺失的ID:")
        for mid in sorted(missing):
            # 找到对应的预期项信息
            for item in expected:
                if item['id'] == mid:
                    extra_info = f" (rank={item.get('rank','?')}, {item.get('title','')[:30]})"
                    break
            else:
                extra_info = ''
            print(f"    - {mid}{extra_info}")

    if extra:
        print(f"\n  多余的ID:")
        for eid in sorted(extra):
            print(f"    - {eid} -> {downloaded_files[eid].name}")

    # 4. 重命名
    if not args.no_rename:
        print("\n阶段4：重命名文件")
        renamed_count, failed_rename = rename_files(
            expected, downloaded_files, args.output_dir, args.name_template
        )
        print(f"  成功重命名: {renamed_count}")
        if failed_rename:
            print(f"  重命名失败: {len(failed_rename)}")
            for fid, err in failed_rename:
                print(f"    - {fid}: {err}")
    else:
        # 即使不重命名，也要标记downloaded状态
        for item in expected:
            item['downloaded'] = item['id'] in downloaded_files
            item['renamed_file'] = ''

    # 5. 生成核对清单
    print("\n阶段5：生成核对清单")
    generate_checklist(expected, args.checklist)

    # 6. 总结
    print("\n" + "=" * 60)
    print("总结")
    print(f"  预期: {len(expected)}")
    print(f"  已下载: {len(downloaded_files)}")
    print(f"  匹配: {len(matched)}")
    print(f"  缺失: {len(missing)}")
    print(f"  多余: {len(extra)}")
    if not args.no_rename:
        print(f"  重命名输出: {args.output_dir}")
    print(f"  核对清单: {args.checklist}")

    if missing or extra:
        print("\n⚠️  存在不匹配项，请检查上方详情")
        sys.exit(1)
    else:
        print("\n✅ 全部匹配，核对通过")
        sys.exit(0)


if __name__ == '__main__':
    main()
