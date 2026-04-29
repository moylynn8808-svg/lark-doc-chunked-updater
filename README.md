# lark-doc-chunked-updater

飞书云文档长文档分块更新工具 | Chunked updater for Lark/Feishu documents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)

## 问题背景

飞书云文档 API 对单次写入操作有约 4000-5000 字符的限制。当使用 `lark-cli docs +update --mode overwrite` 更新长文档时，超出部分会被**静默截断**（不报错，直接丢失内容）。

本工具通过按章节分块、逐块追加的方式，绕过单次写入限制。

## 快速开始

```bash
# 安装依赖（仅需 lark-cli 已配置好）
# Python 3.6+

# 干运行预览
python chunked_update.py --doc "<doc_id>" --file "document.md" --dry-run

# 执行更新
python chunked_update.py --doc "<doc_id>" --file "document.md"

# 断点续传（网络中断后继续）
python chunked_update.py --doc "<doc_id>" --file "document.md" --resume
```

## 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--doc` | 是 | - | 飞书文档 ID 或完整 URL |
| `--file` | 是 | - | 本地 Markdown 文件路径 |
| `--chunk-size` | 否 | 4000 | 每块最大字符数 |
| `--dry-run` | 否 | false | 只预览分块，不实际写入 |
| `--verbose` | 否 | false | 显示详细日志 |
| `--resume` | 否 | false | 从上次中断处继续 |
| `--no-verify` | 否 | false | 跳过写入后验证提示 |
| `--retries` | 否 | 3 | 每块失败重试次数 |

## 使用示例

### 基础用法

```bash
python chunked_update.py \
  --doc "https://my.feishu.cn/docx/DXwRdeid2oYoavxzAVqcnyy1neC" \
  --file "video_script.md"
```

### 处理复杂文档（含表格/画板）

```bash
python chunked_update.py \
  --doc "<doc_id>" \
  --file "complex_doc.md" \
  --chunk-size 2500 \
  --verbose \
  --retries 5
```

### 断点续传

```bash
# 上次中断后，自动跳过已成功的块
python chunked_update.py \
  --doc "<doc_id>" \
  --file "document.md" \
  --resume
```

## 分块策略

1. 按 `---` 分隔符识别章节边界
2. 小章节自动合并，减少 API 调用次数
3. 超大章节在段落/行边界处进一步切分
4. 第 1 块用 `overwrite` 清空文档，后续块用 `append` 追加

## 项目结构

```
lark-doc-chunked-updater/
├── README.md                    # 本文件
├── LICENSE                      # MIT License
├── chunked_update.py            # 核心脚本
├── SKILL.md                     # Claude Code skill 定义
├── ANALYSIS.md                  # 技术分析报告（问题根因、方案对比）
├── examples/
│   └── USAGE.md                 # 详细使用示例
└── tests/
    └── test_chunked_update.py   # 单元测试（19 个用例）
```

## 运行测试

```bash
pip install pytest
python -m pytest tests/test_chunked_update.py -v
```

## 与 lark-doc 的关系

| 场景 | 推荐工具 |
|------|----------|
| 短文档（< 4000 字符） | `lark-cli docs +update` |
| 长文档（> 4000 字符） | `chunked_update.py`（本工具） |
| 精确局部修改 | `lark-cli docs +update --mode replace_range` |

## 系统要求

- Python 3.6+
- `lark-cli` 已安装并配置好认证

## License

MIT License — 详见 [LICENSE](LICENSE)
