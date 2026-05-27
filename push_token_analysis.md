# push_token.py 脚本问题分析与修复

## 发现的问题

### 1. 显示百分比类型不一致
**问题**：在 `fetch_antigravity_live` 函数中，第307行打印的是剩余百分比 `{remaining:.0f}% remaining (live)`，但 `services` 列表中存储的是已使用百分比（`used_pct`）。

### 2. 模型显示过多
**问题**：脚本显示所有模型，但没有分组，导致输出过多。

### 3. 缺少时间戳显示
**问题**：脚本没有显示重置时间戳。

### 4. 缺少可用积分显示
**问题**：脚本没有显示可用 AI 积分。

### 5. remainingFraction 为 null 时的处理问题
**问题**：当 `remainingFraction` 为 null 时，脚本默认使用 1（100%剩余），但根据缓存数据，实际剩余百分比可能是20%。

## 修复后的输出示例

```
▸ Antigravity:
[Antigravity] Claude: 20% remaining (cached)
[Antigravity] Gemini Pro: 20% remaining (cached)
[Antigravity] Gemini Flash: 20% remaining (cached)

── 共 4 个服务 ──
{
  "services": [
    {
      "name": "CodeX",
      "used": 1,
      "limit": 100
    },
    {
      "name": "Claude",
      "used": 80,
      "limit": 100
    },
    {
      "name": "Gemini Pro",
      "used": 80,
      "limit": 100
    },
    {
      "name": "Gemini Flash",
      "used": 80,
      "limit": 100
    }
  ]
}
```

## 与 getagy.py 的一致性

1. **显示百分比**：两个脚本现在都显示剩余百分比（20%）
2. **模型分组**：两个脚本都将模型分组为 Claude、Gemini Pro、Gemini Flash
3. **数据来源**：`push_token.py` 优先使用缓存数据，`getagy.py` 使用本地语言服务器

## 修复内容

1. **修正 remainingFraction 为 null 时的处理**：当 `remainingFraction` 为 null 时，使用缓存数据中的百分比
2. **模型分组显示**：将模型分组为 Claude、Gemini Pro、Gemini Flash
3. **优先使用缓存数据**：因为缓存数据更准确（显示20%剩余）
4. **显示剩余百分比**：统一显示剩余百分比，而不是已使用百分比

## 建议

1. 考虑添加时间戳显示功能
2. 考虑添加可用积分显示功能
3. 考虑添加命令行选项来选择显示剩余百分比或已使用百分比
4. 考虑添加 JSON 输出格式，便于其他程序解析