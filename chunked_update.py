#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lark-doc-chunked-updater - 飞书云文档长文档分块更新工具

解决 overwrite 模式内容过长被截断的问题。
通过按章节分块，逐块追加到飞书文档。

Usage:
    python chunked_update.py --doc "<doc_id_or_url>" --file "document.md"
    python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --chunk-size 3000
    python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --dry-run
    python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --resume
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Retry config
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# State file for resume
STATE_FILE = ".lark_chunked_update_state.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="飞书云文档长文档分块更新工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python chunked_update.py --doc "DXwRdeid2oYoavxzAVqcnyy1neC" --file "document.md"
    python chunked_update.py --doc "DXwRdeid2oYoavxzAVqcnyy1neC" --file "document.md" --chunk-size 3000
    python chunked_update.py --doc "DXwRdeid2oYoavxzAVqcnyy1neC" --file "document.md" --dry-run
    python chunked_update.py --doc "DXwRdeid2oYoavxzAVqcnyy1neC" --file "document.md" --resume
        """,
    )
    parser.add_argument("--doc", required=True, help="飞书文档 ID 或 URL")
    parser.add_argument("--file", required=True, help="本地 Markdown 文件路径")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=4000,
        help="每块最大字符数（默认 4000）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干运行模式，只预览分块，不实际写入",
    )
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="从上次中断处继续（读取 .lark_chunked_update_state.json）",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="跳过写入后的字符数验证",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=MAX_RETRIES,
        help=f"每块失败重试次数（默认 {MAX_RETRIES}）",
    )
    return parser.parse_args()


def extract_doc_id(doc_input: str) -> str:
    """从 URL 或纯 ID 提取文档 ID。"""
    if doc_input.startswith("http"):
        match = re.search(r"(?:docx?|wiki|sheets)/([a-zA-Z0-9]+)", doc_input)
        if match:
            return match.group(1)
        raise ValueError(f"无法从 URL 提取文档 ID: {doc_input}")
    return doc_input


def split_by_sections(content: str, chunk_size: int = 4000) -> List[str]:
    """
    按 Markdown 章节分隔符分块。

    策略:
    1. 首先按 '---' 分隔符切分
    2. 如果单个块超过 chunk_size，进一步按段落切分
    3. 保持 Markdown 语法完整性
    """
    sections = re.split(r"\n---\n", content)

    chunks: List[str] = []
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(current_chunk) + len(section) + 4 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)

            if len(section) > chunk_size:
                sub_chunks = split_large_section(section, chunk_size)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1]
            else:
                current_chunk = section
        else:
            if current_chunk:
                current_chunk += "\n\n---\n\n" + section
            else:
                current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def split_large_section(section: str, chunk_size: int) -> List[str]:
    """切分超过限制的大章节。"""
    if len(section) <= chunk_size:
        return [section]

    paragraphs = re.split(r"\n\n+", section)

    sub_chunks: List[str] = []
    current_chunk = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            if current_chunk:
                sub_chunks.append(current_chunk)
                current_chunk = ""

            lines = para.split("\n")
            temp_chunk = ""
            for line in lines:
                if len(temp_chunk) + len(line) + 1 > chunk_size:
                    sub_chunks.append(temp_chunk)
                    temp_chunk = line
                else:
                    if temp_chunk:
                        temp_chunk += "\n" + line
                    else:
                        temp_chunk = line
            if temp_chunk:
                sub_chunks.append(temp_chunk)
        elif len(current_chunk) + len(para) + 2 > chunk_size:
            sub_chunks.append(current_chunk)
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    if current_chunk:
        sub_chunks.append(current_chunk)

    return sub_chunks


def run_with_retry(
    cmd: List[str],
    retries: int,
    verbose: bool = False,
) -> tuple[bool, str]:
    """带重试的命令执行。"""
    last_stderr = ""
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
            )
            if verbose:
                logger.info("响应：%s", result.stdout[:200])
            if '"success": true' in result.stdout or '"ok": true' in result.stdout:
                return True, ""
            else:
                logger.warning("API 响应异常：%.100s", result.stdout)
                return False, result.stdout
        except subprocess.CalledProcessError as e:
            last_stderr = e.stderr or ""
            logger.warning("第 %d/%d 次尝试失败: %s", attempt, retries, last_stderr[:200])
            if attempt < retries:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            last_stderr = str(e)
            logger.warning("第 %d/%d 次尝试异常: %s", attempt, retries, last_stderr)
            if attempt < retries:
                time.sleep(RETRY_DELAY)
    return False, last_stderr


def update_chunk(
    doc_id: str,
    markdown: str,
    is_first: bool = False,
    verbose: bool = False,
    retries: int = MAX_RETRIES,
) -> bool:
    """更新一个块到飞书文档。"""
    mode = "overwrite" if is_first else "append"

    cmd = [
        "lark-cli",
        "docs",
        "+update",
        "--doc",
        doc_id,
        "--mode",
        mode,
        "--markdown",
        markdown,
    ]

    if verbose:
        logger.info("命令: %s", " ".join(cmd[:8]))
        logger.info("内容长度: %d 字符", len(markdown))

    success, error = run_with_retry(cmd, retries, verbose)
    return success


def save_state(
    doc_id: str,
    file_path: str,
    total_chunks: int,
    completed: List[int],
) -> None:
    """保存状态以便 resume。"""
    state = {
        "doc_id": doc_id,
        "file_path": file_path,
        "total_chunks": total_chunks,
        "completed": completed,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_state() -> Optional[dict]:
    """读取上次保存的状态。"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def clear_state() -> None:
    """清除状态文件。"""
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def print_progress(current: int, total: int) -> None:
    """打印简单的进度条。"""
    width = 30
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(100 * current / total)
    sys.stdout.write(f"\r  [{bar}] {pct:3d}% ({current}/{total})")
    sys.stdout.flush()


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Extract doc ID
    try:
        doc_id = extract_doc_id(args.doc)
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Read file
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error("文件不存在: %s", args.file)
        return 1

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("无法读取文件: %s", e)
        return 1

    logger.info("文档 ID: %s", doc_id)
    logger.info("文件路径: %s", args.file)
    logger.info("总字符数: %d", len(content))
    logger.info("分块大小: %d", args.chunk_size)

    # Split into chunks
    chunks = split_by_sections(content, args.chunk_size)
    logger.info("分块数量: %d", len(chunks))

    # Dry-run mode
    if args.dry_run:
        logger.info("=== 干运行模式：预览分块 ===")
        for i, chunk in enumerate(chunks, 1):
            preview = chunk[:120]
            logger.info(
                "  块 %d/%d  (%d 字符): %s...",
                i,
                len(chunks),
                len(chunk),
                preview[:80],
            )
        logger.info("=== 干运行结束 ===")
        return 0

    # Resume mode
    completed: List[int] = []
    start_index = 0
    if args.resume:
        state = load_state()
        if state and state.get("doc_id") == doc_id and state.get("file_path") == args.file:
            completed = state.get("completed", [])
            start_index = max(completed) if completed else 0
            logger.info("恢复模式: 已跳过前 %d 块", start_index)
        else:
            logger.warning("未找到匹配的 resume 状态，从头开始")

    # Execute update
    logger.info("=== 开始更新飞书文档 ===")
    print_progress(0, len(chunks))

    success_count = 0
    for i, chunk in enumerate(chunks, 1):
        if i in completed:
            success_count += 1
            print_progress(i, len(chunks))
            continue

        is_first = (i == 1)
        mode_str = "overwrite" if is_first else "append"

        if update_chunk(doc_id, chunk, is_first, args.verbose, args.retries):
            success_count += 1
            completed.append(i)
            save_state(doc_id, args.file, len(chunks), completed)
        else:
            logger.error("块 %d 写入失败", i)
            choice = input("\n是否继续? (y/n): ").strip().lower()
            if choice != "y":
                logger.warning("更新中止。成功写入 %d/%d 块", success_count, len(chunks))
                return 1

        print_progress(i, len(chunks))

    # Verify
    if not args.no_verify and success_count == len(chunks):
        logger.info("")
        logger.info("=== 验证完整性 ===")
        logger.info(
            "提示: 建议用 lark-cli docs +fetch --doc %s 检查文档完整度",
            doc_id,
        )
        logger.info(
            "对比字符数: 本地 %d vs 飞书 (需 fetch 后确认)",
            len(content),
        )

    # Clean up state on full success
    clear_state()

    logger.info("")
    logger.info("=== 更新完成 ===")
    logger.info("成功: %d/%d 块", success_count, len(chunks))

    if success_count == len(chunks):
        logger.info("✓ 所有块写入成功！")
        return 0
    else:
        logger.warning("⚠ 部分块写入失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
