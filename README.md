# lark-doc-chunked-updater

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen.svg)](tests/)

**飞书云文档长文档分块更新工具** — 解决 overwrite/replace_all 模式内容过长被静默截断的问题。

## 问题

### 症状

在使用 `lark-cli docs +update --mode overwrite` 更新长文档时，内容被**静默截断** — 不报错、不提示，超出部分直接丢失。

### 真实案例

更新 EP02 视频脚本策划时：

```bash
# 本地文件：脚本_断舍离_最终打磨版.md (231 行，约 6500 字符)
lark-cli docs +update --doc DXwRdeid2oYoavxzAVqcnyy1neC --mode overwrite --markdown "$(cat 脚本.md)"

# 结果：飞书文档只到"相识段"（第 4 镜），约 3500 字符
# 丢失：后续 5 个段落 + 发布文案 + 核心金句 + 素材清单
```

### 根因

飞书 API 对单次写入操作有 ~4000 字符限制：

| API 模式 | 限制类型 | 大约限制 |
|----------|----------|----------|
| `overwrite` | 单次写入总字符数 | ~4000-5000 |
| `append` | 单次追加字符数 | ~4000-5000 |
| `replace_range` | 单次替换字符数 | ~4000-5000 |

`overwrite` 模式 = `delete_all` + `append`，当内容超过限制时，`append` 操作在飞书服务端被截断，客户端不会收到任何错误信号。

### 为什么分块追加有效

每次 `append` 写入的内容都在限制范围内，通过多次小写入绕过单次大写入限制：

```bash
# 第 1 块：overwrite 写入前 3500 字符 → 成功
# 第 2 块：append 追加 3000 字符 → 成功
# 结果：6500 字符完整写入，无截断
```

## 特性

- **自动分块**：按章节分隔符（`---`）切分，逐块追加到飞书
- **多语言支持**：NFC 标准化（日语浊点、韩文组合）、可视化单元计数、阿拉伯语 RTL 完整性保护
- **智能合并**：小章节自动合并，大章节自动切分
- **断点续传**：中断后从上次位置继续，不重复写入
- **干运行预览**：执行前查看分块效果

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
文档
  │
  ├─→ 按 `---` 分隔符切分
  │      │
  │      ├─→ 小章节（< chunk_size）→ 合并到同一块
  │      │
  │      └─→ 超大章节（> chunk_size）
  │             │
  │             ├─→ 按段落切分（\n\n）
  │             │      │
  │             │      ├─→ 小段落 → 合并
  │             │      │
  │             │      └─→ 超长段落
  │             │            │
  │             │            ├─→ 按行切分（\n）
  │             │            │      │
  │             │            │      └─→ 超长单行
  │             │            │            │
  │             │            │            └─→ 按可视化单元（grapheme）切分
```

**Markdown 语法保护**：章节分隔符在块之间保留为 `\n\n---\n\n`，表格/列表/代码块等结构不被切断。

## 多语言支持

v2.1.0 引入的多语言适配模块 `_multilang.py`（零第三方依赖）：

| 语言 | 问题 | 解决方案 |
|------|------|----------|
| **阿拉伯语** | RTL 双向标记（RLE/RLO/RLI）跨块断裂导致渲染错乱 | 自动检测并补全未闭合标记 |
| **日语** | 濁点/半濁点组合字符分离（か + ゙ → が） | NFC 标准化自动组合 |
| **韩语** | NFD 韩文字母分解为 jamo（ㄱ + ㅏ → 가） | NFC 标准化自动组合 |
| **通用** | `len()` 按 code point 计数不准确 | 按可视化单元（grapheme）计数 |

## 最佳实践

### Markdown 文档结构

用 `---` 明确分隔章节，每章控制在 3000 字符以内：

```markdown
# 视频脚本策划

## 基础信息
| 项目 | 内容 |
|------|------|
| 集数 | EP01 |

---

## 完整脚本
### 开场段
...

---

## 发布文案
...
```

### chunk-size 选择

| 文档类型 | 推荐 chunk-size | 原因 |
|----------|----------------|------|
| 简单文本 | 4000 | 安全范围 |
| 含表格 | 3000 | 表格语法额外占用字符 |
| 含画板 | 2500 | 画板 token 很长 |
| 复杂混排 | 2000 | 最保守 |

## 依赖

- Python 3.10+
- [lark-cli](https://github.com/larkcloud/lark-cli)（飞书官方 CLI 工具）
- 无其他第三方依赖（纯标准库实现）

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

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.1.0 | 2026-04-30 | 多语言支持（RTL/NFC/grapheme）、grapheme 硬切分、`--encoding` 参数 |
| v2.0.0 | 2026-04-29 | 重试机制、断点续传、进度条、单元测试 |
| v1.0.0 | 2026-04-16 | 初始版本：按章节分块、干运行预览 |

## 许可证

MIT
