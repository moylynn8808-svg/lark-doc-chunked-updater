---
name: lark-doc-chunked-updater
version: 2.1.0
description: "飞书云文档长文档分块更新工具。解决 overwrite/replace_all 模式内容过长被截断的问题。当文档内容超过 4000 字符时，自动按章节分块，逐块追加到飞书文档。支持多语言（阿拉伯语 RTL、日语、韩语）、重试、断点续传、进度条和干运行预览。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
  cliHelp: "python chunked_update.py --help"
---

# lark-doc-chunked-updater (v2)

飞书云文档长文档分块更新工具。

## 使用场景

当需要更新长文档（超过 4000 字符）到飞书云文档时，使用本工具避免内容被截断。

**典型场景**：
- 更新完整的视频脚本策划文档（8000+ 字符）
- 更新长篇文章、报告、提案
- 批量追加多个章节内容

## 触发条件

当以下任一条件成立时，**必须**使用本工具而非 `lark-cli docs +update`：
- 本地 Markdown 文件超过 3500 字符
- 文档包含多个用 `---` 分隔的章节
- 用户明确要求"完整更新"长文档到飞书

## 命令

```bash
# 基本用法
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md"

# 指定分块大小
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --chunk-size 3000

# 干运行模式（预览分块效果）
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --dry-run

# 详细输出 + 重试 5 次
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --verbose --retries 5

# 断点续传（上次中断后继续）
python chunked_update.py --doc "<doc_id_or_url>" --file "document.md" --resume
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--doc` | 是 | 飞书文档 ID 或 URL |
| `--file` | 是 | 本地 Markdown 文件路径 |
| `--chunk-size` | 否 | 每块最大字符数（默认 4000） |
| `--dry-run` | 否 | 只预览分块，不实际写入 |
| `--verbose` | 否 | 显示详细输出 |
| `--resume` | 否 | 从上次中断处继续 |
| `--no-verify` | 否 | 跳过写入后验证 |
| `--retries` | 否 | 每块失败重试次数（默认 3） |
| `--encoding` | 否 | 文件编码（默认 utf-8；支持 utf-8-sig、gbk、cp949 等） |

## 多语言支持

### NFC Unicode 标准化
- 所有文档在分块前自动进行 NFC 标准化
- **日语**：か +  combining ゙ → が（浊点组合字符自动合并）
- **韩语**：NFD 韩文字母（jamo）自动组合为预编码音节（가）

### 可视化单元计数
- 分块使用**可视化单元（grapheme）**计数，而非 code point
- 每个可见字符 = 1 个单元，无论底层编码多少 code point
- 日语浊音字符（が）、韩语音节（한글）均计为 1

### 阿拉伯语 RTL 保护
- 每个分块自动检测双向控制字符（RLE/RLO/RLI）
- 块结束时自动补全未闭合的 RTL 标记（PDF/PDI）
- 避免 RTL 标记跨块断裂导致的渲染问题

### 1. 按章节分隔符分块
- 识别 Markdown 中的 `---` 分隔符
- 每个章节作为一个独立的块
- 自动合并小章节，避免块过多

### 2. 大块进一步切分
- 当单个章节超过 `chunk_size` 时
- 优先在段落边界（双换行）处切分
- 其次在行边界（单换行）处切分
- 保持 Markdown 语法完整性

## 执行流程

1. **读取本地文件** → 计算总字符数
2. **按章节分块** → 输出分块数量
3. **逐块写入** → 第 1 块用 `overwrite`，后续用 `append`
4. **自动重试** → 失败自动重试（最多 3 次）
5. **断点保存** → 每块成功后记录状态，支持 resume
6. **完整性验证** → 完成后提示用户 fetch 对比

## 返回值

### 成功
```
=== 更新完成 ===
成功：5/5 块
✓ 所有块写入成功！
```

### 部分失败
```
[3/5] 写入块 3 (append 模式)... 失败
是否继续? (y/n):
```

## 最佳实践

### 1. 先用 dry-run 预览
```bash
python chunked_update.py --doc "<doc_id>" --file "document.md" --dry-run
```

### 2. 选择合适的 chunk-size

| 文档类型 | 推荐 chunk-size | 原因 |
|----------|----------------|------|
| 简单文本 | 4000 | 安全范围 |
| 含表格 | 3000 | 表格语法占用字符 |
| 含画板 | 2500 | 画板 token 很长 |
| 复杂混排 | 2000 | 最保守 |

### 3. 断点续传
```bash
# 如果网络中断或手动中止
python chunked_update.py --doc "<doc_id>" --file "document.md" --resume
```

### 4. verbose 模式调试
```bash
python chunked_update.py --doc "<doc_id>" --file "document.md" --verbose
```

## 与 lark-doc 的关系

本工具是 `lark-doc` skill 的补充。

| 场景 | 推荐工具 |
|------|----------|
| 短文档（< 4000 字符） | `lark-cli docs +update` |
| 长文档（> 4000 字符） | `chunked_update.py` |
| 精确局部修改 | `lark-cli docs +update --mode replace_range` |
| 追加大段内容 | `lark-cli docs +update --mode append` 或 `chunked_update.py` |

## 示例

### 示例 1：更新视频脚本策划

```bash
# 本地文件：脚本_断舍离_最终打磨版.md (约 6000 字符)
# 飞书文档：DXwRdeid2oYoavxzAVqcnyy1neC

# 干运行预览
python chunked_update.py --doc "DXwRdeid2oYoavxzAVqcnyy1neC" --file "脚本_断舍离_最终打磨版.md" --dry-run

# 执行更新
python chunked_update.py --doc "DXwRdeid2oYoavxzAVqcnyy1neC" --file "脚本_断舍离_最终打磨版.md"
```

### 示例 2：复杂文档 + 更保守的分块

```bash
python chunked_update.py --doc "<doc_id>" --file "document.md" --chunk-size 2500 --verbose --retries 5
```

## 故障排除

### 问题 1：某块写入失败
**原因**：该块内容仍超过 API 限制

**解决**：
1. 减小 `--chunk-size` 参数
2. 使用 `--resume` 跳过已成功的块

### 问题 2：文档内容重复
**原因**：部分块写入成功后又重复执行

**解决**：
1. 检查飞书文档当前内容
2. 使用 `lark-cli docs +fetch` 查看已写入部分
3. 删除 `.lark_chunked_update_state.json` 后重试

### 问题 3：Markdown 格式错乱
**原因**：分块位置切断了 Markdown 语法

**解决**：
1. 检查本地文件的章节分隔符
2. 确保 `---` 前后有换行
3. 手动调整分块位置

## 相关文件

- `SKILL.md` - 本文件（skill 定义）
- `chunked_update.py` - 核心脚本
- `ANALYSIS.md` - 技术分析报告
- `tests/test_chunked_update.py` - 单元测试

## 更新日志

### v2.1.0 (2026-04-30)
- 多语言支持：NFC Unicode 标准化（日语、韩语、阿拉伯语）
- 可视化单元计数替代 code point 计数
- 阿拉伯语 RTL 双向标记完整性保护
- 新增 `--encoding` 参数，支持 gbk、cp949 等非 UTF-8 编码
- 新增 `_multilang.py` 模块

### v2.0.0 (2026-04-29)
- 添加重试机制（指数退避）
- 添加断点续传（resume 模式）
- 添加进度条显示
- 添加完整的 type annotations
- 添加单元测试（test_chunked_update.py）
- 改进 logging（替代 print）
- 完善飞书 URL 解析

### v1.0.0 (2026-04-16)
- 初始版本
- 支持按章节分块
- 支持干运行模式
- 集成到 Claude Code skill 系统
