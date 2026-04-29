# 使用示例

## 示例 1：更新视频脚本策划文档

场景：更新 EP02 阿冷的完整策划文档到飞书

```bash
# 1. 干运行预览（推荐第一步）
python chunked_update.py \
  --doc "DXwRdeid2oYoavxzAVqcnyy1neC" \
  --file "脚本_断舍离_最终打磨版.md" \
  --dry-run

# 输出：
# 文档 ID: DXwRdeid2oYoavxzAVqcnyy1neC
# 文件路径：脚本_断舍离_最终打磨版.md
# 总字符数：6500
# 分块大小：4000
# 分块数量：3
#
# === 干运行模式：预览分块 ===
# --- 块 1/3 ---
# 字符数：3200
# 内容预览：# 「一年后的我们」EP02｜阿冷（虎仔妈咪）完整策划...
# --- 块 2/3 ---
# 字符数：2100
# 内容预览：## 📝 发布文案...
# --- 块 3/3 ---
# 字符数：1200
# 内容预览：## 💬 核心金句...

# 2. 执行实际更新
python chunked_update.py \
  --doc "DXwRdeid2oYoavxzAVqcnyy1neC" \
  --file "脚本_断舍离_最终打磨版.md"

# 输出：
# === 开始更新飞书文档 ===
# [1/3] 写入块 1 (overwrite 模式)... ✓ 成功
# [2/3] 写入块 2 (append 模式)... ✓ 成功
# [3/3] 写入块 3 (append 模式)... ✓ 成功
# === 更新完成 ===
# 成功：3/3 块
# ✓ 所有块写入成功！
```

## 示例 2：处理超大章节

场景：单个章节超过 4000 字符

```bash
# 使用更小的分块大小
python chunked_update.py \
  --doc "DXwRdeid2oYoavxzAVqcnyy1neC" \
  --file "长文档.md" \
  --chunk-size 3000 \
  --verbose
```

## 示例 3：从 URL 更新

场景：使用飞书文档 URL 而非 ID

```bash
python chunked_update.py \
  --doc "https://my.feishu.cn/docx/DXwRdeid2oYoavxzAVqcnyy1neC" \
  --file "document.md"
```

## 示例 4：错误处理演示

场景：某块写入失败

```bash
python chunked_update.py \
  --doc "DXwRdeid2oYoavxzAVqcnyy1neC" \
  --file "document.md"

# 输出：
# [3/5] 写入块 3 (append 模式)... ✗ 失败
# 错误：块 3 写入失败，是否继续？(y/n): n
# 更新中止。成功写入 2/5 块
```

## 示例 5：在 Claude Code 中使用

```
/chunked-update DXwRdeid2oYoavxzAVqcnyy1neC 脚本_断舍离_最终打磨版.md
```

---

## 常见问题

### Q: 如何确认分块大小是否合适？

A: 先用 `--dry-run` 查看每块的字符数：
- 如果所有块都 < 3500，可以增大 `--chunk-size`
- 如果有块 > 4500，减小 `--chunk-size`

### Q: 写入失败后如何继续？

A: 有两种方式：

1. **从中断点继续**（手动）：
   ```bash
   # 假设块 3 失败，前 2 块成功
   # 手动追加剩余块
   lark-cli docs +update --doc XXX --mode append --markdown "块 3 内容"
   ```

2. **自动继续**（修改脚本）：
   ```bash
   # 修改 chunked_update.py，移除暂停逻辑
   python chunked_update.py --doc XXX --file doc.md --verbose
   ```

### Q: 如何验证更新后的文档完整性？

A: 使用 `docs +fetch` 检查：

```bash
# 获取飞书文档内容
lark-cli docs +fetch --doc "DXwRdeid2oYoavxzAVqcnyy1neC" > fetched.md

# 比较字符数
wc -c 脚本_断舍离_最终打磨版.md  # 本地
wc -c fetched.md                 # 飞书

# 应该相近（允许 10% 误差，因为飞书会转换 Markdown 语法）
```
