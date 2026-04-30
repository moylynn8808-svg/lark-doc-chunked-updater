# lark-doc-chunked-updater

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen.svg)](tests/)

**飞书云文档长文档分块更新工具** — 解决 overwrite/replace_all 模式内容过长被静默截断的问题。

## 问题

飞书 API 对单次写入有 ~4000 字符限制，`overwrite` 模式超出时**静默截断**（不报错、不提示）。

## 特性

- 自动按章节分隔符（`---`）分块，逐块追加到飞书
- **多语言支持**：NFC 标准化（日语浊点、韩文组合）、可视化单元计数、阿拉伯语 RTL 完整性保护
- 自动合并小章节、切分大章节
- 断点续传、进度条、失败重试、干运行预览

## 快速开始

```bash
# 基本用法
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md"

# 干运行预览分块效果
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --dry-run

# 指定分块大小 + 详细输出
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --chunk-size 3000 --verbose

# 断点续传
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --resume

# 非 UTF-8 编码文件
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --encoding gbk
```

## 参数

| 参数 | 说明 |
|------|------|
| `--doc` | 飞书文档 ID 或 URL |
| `--file` | 本地 Markdown 文件路径 |
| `--chunk-size` | 每块最大字符数（默认 4000） |
| `--dry-run` | 只预览分块，不实际写入 |
| `--verbose` | 显示详细输出 |
| `--resume` | 从上次中断处继续 |
| `--encoding` | 文件编码（默认 utf-8；支持 utf-8-sig、gbk、cp949） |
| `--retries` | 每块失败重试次数（默认 3） |
| `--no-verify` | 跳过写入后验证 |

## 分块策略

```
文档 ──→ 按 `---` 分隔符切分 ──→ 合并小章节（< chunk_size）
                                          │
                                   超大章节 ──→ 按段落切分（\n\n）
                                                 │
                                          超长段落 ──→ 按行切分（\n）
                                                           │
                                                    超长单行 ──→ 按可视化单元切分
```

**Markdown 语法保护**：章节分隔符在块之间保留为 `\n\n---\n\n`，表格/列表等结构不被切断。

## 多语言支持

v2.1.0 引入的多语言适配模块 `_multilang.py`：

| 语言 | 问题 | 解决方案 |
|------|------|----------|
| **阿拉伯语** | RTL 双向标记跨块断裂导致渲染错乱 | 自动检测并补全未闭合的 RLE/RLO/RLI 标记 |
| **日语** | 濁点/半濁点组合字符分离（か + ゙ → が） | NFC 标准化自动组合 |
| **韩语** | NFD 韩文字母分解为 jamo（ㄱ + ㅏ → 가） | NFC 标准化自动组合 |
| **通用** | `len()` 按 code point 计数不准确 | 按可视化单元（grapheme）计数 |

## 依赖

- Python 3.10+
- [lark-cli](https://github.com/larkcloud/lark-cli)（飞书官方 CLI 工具）
- 无其他第三方依赖（标准库实现）

## 与 lark-doc 的关系

| 场景 | 推荐工具 |
|------|----------|
| 短文档（< 4000 字符） | `lark-cli docs +update` |
| 长文档（> 4000 字符） | `chunked_update.py` |
| 精确局部修改 | `lark-cli docs +update --mode replace_range` |

## 测试

```bash
cd tests
python -m pytest -v
# 64 passed
```

## 许可证

MIT
