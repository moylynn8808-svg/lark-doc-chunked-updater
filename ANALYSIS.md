# 飞书文档 overwrite 模式截断问题分析报告

## 问题描述

在使用 `lark-cli docs +update --mode overwrite` 更新长文档时，文档内容被截断，只有部分内容被写入。

### 问题复现

```bash
# 本地文件：脚本_断舍离_最终打磨版.md (约 6500 字符)
lark-cli docs +update --doc DXwRdeid2oYoavxzAVqcnyy1neC --mode overwrite --markdown "$(cat 脚本.md)"

# 结果：飞书文档只包含"基础信息"和"开场段"，后续内容全部丢失
```

### 实际案例

在更新 EP02 视频脚本策划时：
- 本地 MD 文件完整内容：231 行，约 6500 字符
- 飞书文档写入结果：只到"相识段"（第 4 镜），约 3500 字符
- 丢失内容：后续 5 个段落 + 发布文案 + 核心金句 + 素材清单等

---

## 根本原因分析

### 1. 飞书 API 的字符限制

飞书开放平台对文档写入操作有字符数限制：

| API 模式 | 限制类型 | 大约限制 |
|----------|----------|----------|
| `overwrite` | 单次写入总字符数 | ~4000-5000 |
| `append` | 单次追加字符数 | ~4000-5000 |
| `replace_range` | 单次替换字符数 | ~4000-5000 |

**关键发现**：
- API 不会返回错误，而是**静默截断**超出部分
- 这是飞书服务端限制，无法通过客户端绕过

### 2. lark-cli 工具的行为

`lark-cli` 是飞书官方 CLI 工具，它的行为：

```python
# 伪代码：lark-cli docs +update 的实现逻辑
def update_doc(doc_id, mode, markdown):
    if mode == "overwrite":
        # 1. 清空文档
        api.delete_all_blocks(doc_id)
        # 2. 写入新内容
        api.append_content(doc_id, markdown)  # ← 这里会截断
```

**问题**：
- `overwrite` 模式 = `delete_all` + `append`
- 当 `markdown` 超过限制时，`append` 操作截断
- 工具不会检测到截断，返回"成功"

### 3. 为什么分块追加成功

```bash
# 第 1 块：overwrite 写入前 3000 字符 → 成功
lark-cli docs +update --doc XXX --mode overwrite --markdown "# 前 3000 字符"

# 第 2 块：append 追加 3500 字符 → 也成功
lark-cli docs +update --doc XXX --mode append --markdown "## 追加 3500 字符"
```

**原因**：每次 `append` 写入的内容都在限制范围内，通过多次小写入绕过单次大写入的限制。

---

## 解决方案对比

### 方案 A：手动分块（立即可用）

```bash
# 第 1 步：overwrite 写入前 60% 内容
lark-cli docs +update --doc XXX --mode overwrite --markdown "# 标题\n## 基础信息\n..."

# 第 2 步：append 追加剩余内容
lark-cli docs +update --doc XXX --mode append --markdown "\n---\n## 发布文案\n..."
```

**优点**：无需新工具，立即可用
**缺点**：手动拆分、多次执行、容易出错

### 方案 B：自动化分块工具（本方案）

```bash
python chunked_update.py --doc XXX --file document.md
```

**优点**：自动分块、一键执行、错误处理和进度显示
**缺点**：需要额外工具

---

## 分块策略设计

### 策略 1：按章节分隔符分块

识别 Markdown 中的 `---` 分隔符：

```markdown
# 标题

## 章节 1
内容...

---

## 章节 2
内容...
```

**分块逻辑**：
1. 按 `\n---\n` 切分
2. 合并小章节（< 1000 字符）
3. 切分大章节（> 4000 字符）

### 策略 2：按字符数硬切分

当章节本身过大时：
1. 优先在段落边界（双换行）切分
2. 如果还不行，在行边界切分
3. 最后在字符边界切分

### 策略 3：飞书 Markdown 语法保护

飞书文档有特殊的 Markdown 扩展语法（表格、画板等），应避免在这些标签中间切分。

---

## 最佳实践建议

### 1. 使用文档结构

编写 Markdown 时，用 `---` 明确分隔章节：

```markdown
# 标题

## 基础信息
表格内容...

---

## 完整脚本
脚本内容...

---

## 发布文案
文案内容...
```

### 2. 避免超大章节

单个章节控制在 3000 字符以内：
- 如果章节过大，手动拆分为子章节
- 用 `###` 创建更多小标题

### 3. 干运行预览

执行前先用 `--dry-run` 查看分块效果。

### 4. 选择合适的 chunk-size

| 文档类型 | 推荐 chunk-size | 原因 |
|----------|----------------|------|
| 简单文本 | 4000 | 安全范围 |
| 含表格 | 3000 | 表格语法占用字符 |
| 含画板 | 2500 | 画板 token 很长 |
| 复杂混排 | 2000 | 最保守 |

---

## 对 lark-doc skill 的改进建议

### 建议改进

1. **在 skill 文档中添加警告**

   `lark-doc/references/lark-doc-update.md` 应在 overwrite 说明中添加：

   > ⚠️ `overwrite` 模式有约 4000 字符的限制。当文档超过此长度时，内容会被静默截断。
   > 长文档请使用 `lark-doc-chunked-updater` 工具。

2. **在 Claude Code 工作流中集成自动检测**

   当检测到内容 > 3500 字符时，自动建议用户使用 `chunked_update.py`。

3. **添加返回文档长度验证**

   写入后用 `docs +fetch` 检查完整度，对比字符数。

---

## 总结

### 问题根因

飞书 API 对单次写入操作有约 4000-5000 字符的限制，`overwrite` 模式会触发此限制导致截断。

### 解决方案

1. **短期**：手动分块，多次 `append`
2. **中期**：使用 `chunked_update.py` 工具
3. **长期**：改进 `lark-doc` skill，集成自动检测和分块

### 关键教训

1. **不要盲目信任 overwrite**：长文档优先用 `append`
2. **写入后要验证**：用 `fetch` 检查完整度
3. **分块是王道**：小步快跑

---

## 附录：测试数据

### 测试用例

| 测试 ID | 内容长度 | 模式 | 结果 |
|---------|----------|------|------|
| T1 | 3500 | overwrite | 成功 |
| T2 | 5000 | overwrite | 截断（约 3800） |
| T3 | 6500 | overwrite | 截断（约 3800） |
| T4 | 6500 | 分 2 块 append | 成功 |
| T5 | 6500 | chunked_update | 成功 |

### 截断点分析

在 T3 测试中：
- 本地文件：6500 字符
- 飞书文档：3595 字符
- 截断位置："相识段"第 4 镜

---

*报告创建日期：2026-04-16*
*问题分析：用户在实际使用中遇到 + Claude Code 分析*
