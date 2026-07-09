# Base vs SFT 模型输出对比报告

## 测试信息

| 项目 | 值 |
|------|-----|
| 轨迹 ID | geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_00 |
| 原始提示 | four pink flamingos chasing a horse to the left of four wooden chairs |
| Base 模型 | Qwen3-VL-8B-Instruct |
| SFT 模型 | Qwen3-VL-8B-Instruct + LoRA (checkpoint-150) |
| 测试轮数 | 3 (INITIAL_PLAN + 2次 RETRY_REPLAN) |

---

## ROUND 0: INITIAL_PLAN

### Base 模型输出

```json
{
  "plan": [
    {"skill": "object_presence", "action": "Ensure four pink flamingos are explicitly visible and not cropped out."},
    {"skill": "object_presence", "action": "Ensure four wooden chairs are explicitly visible and not cropped out."},
    {"skill": "spatial_layout", "action": "Position the horse to the left of the four wooden chairs."},
    {"skill": "spatial_layout", "action": "Arrange the four pink flamingos to be chasing the horse, maintaining clear directional movement."},
    {"skill": "clarity_visibility", "action": "Make all objects clear, unobstructed, and easy to verify in the scene."},
    {"skill": "anti_occlusion", "action": "Arrange objects so no flamingos, horse, or chairs are hidden, merged, or blocked."},
    {"skill": "negative_constraints", "action": "Avoid any extra or forbidden objects; preserve only the required content."},
    {"skill": "multi_object_composition", "action": "Keep flamingos, horse, and chairs distinct, complete, and jointly visible in one coherent scene."}
  ]
}
```

**特点:**
- 8 个 plan items
- 输出格式为 plan (skill-action 列表)
- JSON 有效

---

### SFT 模型输出

```json
{
  "plan": [
    {"skill": "object_presence", "action": "Ensure four pink flamingos are explicitly visible and not cropped out."},
    {"skill": "object_presence", "action": "Ensure four wooden chairs are explicitly visible and not cropped out."},
    {"skill": "spatial_layout", "action": "Place the horse to the left of the four wooden chairs."},
    {"skill": "spatial_layout", "action": "Position the four pink flamingos chasing the horse, ensuring their movement direction is clear."},
    {"skill": "multi_object_composition", "action": "Keep all objects distinct, complete, and jointly visible in one coherent scene."},
    {"skill": "clarity_visibility", "action": "Make the horse, flamingos, and chairs clear, centered enough, and unobstructed for easy verification."},
    {"skill": "anti_occlusion", "action": "Arrange objects so the horse, flamingos, and chairs are not hidden, merged, or blocked by other elements."},
    {"skill": "negative_constraints", "action": "Avoid any forbidden or extra objects while preserving the required content."},
    {"skill": "attribute_binding", "action": "Bind the color 'pink' explicitly to the flamingos and 'wooden' explicitly to the chairs, avoiding attribute leakage."},
    {"skill": "quantity_counting", "action": "State the exact number: four flamingos and four chairs, require separate visible instances, avoid overlap or merging, and ensure each instance is countable."}
  ]
}
```

**特点:**
- 10 个 plan items (比 Base 多 2 个)
- **新增 skills:**
  - `attribute_binding`: 从训练数据中学到的概念
  - `quantity_counting`: 从训练数据中学到的概念
- action 描述更详细（如增加 "avoiding attribute leakage"）
- JSON 有效

---

### Ground Truth (期望输出)

```json
{
  "action_type": "initial_plan",
  "generation_guards": [
    "Show exactly four pink flamingos, exactly one horse, and exactly four wooden chairs.",
    "Keep all flamingos, the horse, and all chairs fully visible and separated enough to count.",
    "Bind pink color only to the flamingos and wooden material to the chairs.",
    "Place the horse clearly to the left of the group of four wooden chairs.",
    "Depict the four pink flamingos actively chasing the horse, with their orientation and motion directed toward the horse.",
    "Avoid extra flamingos, extra horses, extra chairs, or occlusion that hides counts."
  ],
  "generation_strategy": "Use a clear side-view composition with three countable groups: four pink flamingos on the left/mid-left chasing one horse, and four wooden chairs arranged separately on the right. Keep the horse spatially left of all four chairs, and maintain open spacing so each object is distinct and visible.",
  "initial_prompt": "A clear scene showing exactly four pink flamingos chasing exactly one horse. The horse is positioned to the left of exactly four wooden chairs. Arrange the four wooden chairs as a separate visible group on the right side, all made of wood. The four pink flamingos are distinct, fully visible, and moving toward the horse as if chasing it. The single horse is fully visible and clearly left of all four chairs. Keep every flamingo, the horse, and each chair unobstructed and easy to count; do not include any extra flamingos, horses, or chairs.",
  "parsed_constraints": {
    "attributes": {"chairs": ["wooden"], "flamingos": ["pink"]},
    "counts": {"chairs": 4, "flamingos": 4, "horse": 1},
    "objects": ["flamingos", "horse", "chairs"],
    "relations": [
      "four pink flamingos are chasing the horse",
      "the horse is to the left of four wooden chairs"
    ]
  },
  "selected_skills": [
    "quantity_counting", "attribute_binding", "object_presence", "spatial_layout",
    "clarity_visibility", "anti_occlusion", "multi_object_composition", "negative_constraints"
  ]
}
```

**关键字段:**
- `action_type`: "initial_plan"
- `generation_guards`: 6条约束规则
- `generation_strategy`: 详细生成策略
- `initial_prompt`: 完整图像生成提示词
- `parsed_constraints`: 解析后的约束条件
- `selected_skills`: 选中的技能列表

---

### ROUND 0 对比分析

| 维度 | Base | SFT | GT |
|------|------|-----|-----|
| 格式 | plan | plan | initial_plan |
| 是否符合 GT | ❌ | ❌ | ✅ |
| action_type | ❌ | ❌ | ✅ "initial_plan" |
| generation_guards | ❌ | ❌ | ✅ 6条约束 |
| generation_strategy | ❌ | ❌ | ✅ 详细策略 |
| initial_prompt | ❌ | ❌ | ✅ 完整提示词 |

**SFT 的细微改进:**
- ✅ 增加了 `attribute_binding` skill
- ✅ 增加了 `quantity_counting` skill
- ✅ action 描述更详细

**严重问题:**
- ❌ 两种模型都没有输出 Ground Truth 的格式
- ❌ 没有 `action_type` 字段
- ❌ 没有 `generation_guards` 数组
- ❌ 没有 `generation_strategy`
- ❌ 没有 `initial_prompt`

---

## ROUND 1: RETRY_REPLAN

### Base 模型输出

```json
{
  "plan": [
    {"skill": "quantity_counting", "action": "Explicitly enforce four distinct, non-overlapping, countable flamingos in the scene."},
    {"skill": "spatial_layout", "action": "Clearly position the horse to the left of the four wooden chairs, with the flamingos chasing the horse toward the left."},
    {"skill": "attribute_binding", "action": "Bind 'pink' explicitly to each flamingo and 'wooden' explicitly to each chair to prevent attribute leakage."},
    {"skill": "clarity_visibility", "action": "Ensure the flamingos, horse, and chairs are unobstructed, centered, and easy to verify individually."},
    {"skill": "anti_occlusion", "action": "Arrange objects so no flamingo, horse, or chair is hidden, merged, or blocked by other elements."},
    {"skill": "negative_constraints", "action": "Strictly avoid any extra flamingos, horses, or chairs beyond the required four flamingos, one horse, and four chairs."},
    {"skill": "multi_object_composition", "action": "Maintain distinct visibility of all objects in one coherent scene without visual clutter or overlap."},
    {"skill": "verb", "action": "Explicitly describe the flamingos as actively chasing the horse to ensure the dynamic relation is unambiguous."}
  ]
}
```

---

### SFT 模型输出

```json
{
  "plan": [
    {"skill": "quantity_counting", "action": "Explicitly state and enforce exactly four distinct, separate, and countable flamingos; avoid any overlap, merging, or partial visibility."},
    {"skill": "spatial_layout", "action": "Clearly position the horse to the left of the four wooden chairs, ensuring the relative arrangement is unambiguous."},
    {"skill": "attribute_binding", "action": "Bind the color 'pink' explicitly to each flamingo and 'wooden' explicitly to each chair, avoiding attribute leakage to other objects."},
    {"skill": "clarity_visibility", "action": "Make the flamingos, horse, and chairs clear, centered, unobstructed, and easy to verify; ensure the flamingos are visibly moving toward the horse as if chasing it."},
    {"skill": "anti_occlusion", "action": "Arrange the scene so the flamingos, horse, and chairs are not hidden, merged, or blocked by any other elements."},
    {"skill": "multi_object_composition", "action": "Keep the four flamingos, one horse, and four wooden chairs distinct, complete, and jointly visible in one coherent scene."},
    {"skill": "negative_constraints", "action": "Avoid any extra flamingos, horses, or chairs; ensure only the required objects are present."},
    {"skill": "object_presence", "action": "Ensure every flamingo, the horse, and each chair is explicitly visible and not cropped out."}
  ]
}
```

**SFT vs Base 差异:**
- SFT action 描述更详细（如"avoid any overlap, merging, or partial visibility"）
- SFT 增加了 "ensuring the relative arrangement is unambiguous"
- Base 有一个 skill 叫 "verb"，SFT 换成了 "object_presence"

---

### Ground Truth (期望输出)

```json
{
  "action_type": "retry_replan",
  "branch_source": "latest",
  "branch_source_round": 0,
  "decision": "regenerate",
  "diagnosis": "The image passed pink flamingos, flamingo presence, one horse, horse presence, horse left of chairs, four chairs, wooden chairs, and chair presence. It failed the exact flamingo count and the action relation: the scene did not clearly show exactly four flamingos, and the flamingos were not clearly chasing the horse.",
  "expected_improvement": [
    "Exact flamingo count should improve by using a simple side-view lineup of four separate, fully visible pink flamingos with visible gaps between them.",
    "The chasing relation should improve by placing all four flamingos behind the horse, facing and moving toward the horse, while the horse moves away from them.",
    "Previously passed constraints should remain stable by keeping one horse left of a separate group of four wooden chairs."
  ],
  "preserve_constraints": [
    "The flamingos must be pink.",
    "There must be flamingos visible in the image.",
    "There must be exactly one horse, fully visible.",
    "The horse must be to the left of the chairs.",
    "There must be exactly four chairs.",
    "The chairs must be wooden.",
    "The chairs must be visible as chairs."
  ],
  "previous_plan_error": {
    "details": "The previous prompt stated the correct count and chasing action, but did not force a simple enough layout for the verifier to count four flamingos or recognize pursuit...",
    "error_source": "Prompt layout and relation depiction were too general for the count and chasing constraints."
  },
  "regeneration_strategy": "Use a clean side-view composition with three separated zones: four pink flamingos in a visible row on the left, one horse just ahead of them toward the middle-left, and four wooden chairs farther right..."
}
```

**关键字段:**
- `action_type`: "retry_replan"
- `branch_source`: "latest"
- `branch_source_round`: 0
- `decision`: "regenerate"
- `diagnosis`: 详细诊断信息
- `expected_improvement`: 改进计划数组
- `preserve_constraints`: 需要保留的约束
- `previous_plan_error`: 错误分析
- `regeneration_strategy`: 重新生成策略

---

### ROUND 1 对比分析

**两者都缺失的关键字段:**
- ❌ `action_type`: 'retry_replan'
- ❌ `branch_source`: 'latest'
- ❌ `branch_source_round`: 0
- ❌ `decision`: 'regenerate'
- ❌ `diagnosis`: 详细诊断信息
- ❌ `expected_improvement`: 改进计划数组
- ❌ `preserve_constraints`: 需要保留的约束
- ❌ `previous_plan_error`: 错误分析
- ❌ `regeneration_strategy`: 重新生成策略

**问题:** 两种模型都没有学会根据 verifier 反馈进行 replan 的逻辑！

---

## ROUND 2: RETRY_REPLAN (Best So Far)

### Base 模型输出

```json
{
  "plan": [
    {"skill": "quantity_counting", "action": "Explicitly enforce exactly four distinct, non-overlapping, and countable flamingos; ensure each flamingo is fully visible and separable for accurate counting."},
    {"skill": "spatial_layout", "action": "Position the horse clearly to the left of the four wooden chairs, with the flamingos arranged behind the horse, moving toward it as if chasing."},
    {"skill": "clarity_visibility", "action": "Ensure all objects are clear, unobstructed, and centered enough for easy verification; emphasize the chasing motion of the flamingos toward the horse."},
    {"skill": "attribute_binding", "action": "Bind 'pink' explicitly to each flamingo and 'wooden' explicitly to each chair, avoiding any attribute leakage."},
    {"skill": "anti_occlusion", "action": "Arrange the scene to prevent any occlusion or merging between the flamingos, horse, or chairs."},
    {"skill": "multi_object_composition", "action": "Keep the four flamingos, one horse, and four wooden chairs distinct, complete, and jointly visible in one coherent scene."},
    {"skill": "negative_constraints", "action": "Strictly avoid any extra flamingos, horses, or chairs; ensure only the required objects are present."},
    {"skill": "object_presence", "action": "Ensure every flamingo, the horse, and each chair is explicitly visible and not cropped out."}
  ]
}
```

---

### SFT 模型输出

```json
{
  "plan": [
    {"skill": "quantity_counting", "action": "Explicitly enforce exactly four distinct, separate, and countable flamingos; require each flamingo to be fully visible, non-overlapping, and labeled as one, two, three, four to ensure accurate counting."},
    {"skill": "spatial_layout", "action": "Position the horse clearly to the left of all four chairs, and place the four flamingos behind the horse, facing toward it, with their movement direction explicitly showing them chasing the horse."},
    {"skill": "clarity_visibility", "action": "Make the flamingos, horse, and chairs clear, centered, unobstructed, and easy to verify; ensure the flamingos are visibly moving toward the horse as if actively chasing it."},
    {"skill": "attribute_binding", "action": "Bind the color 'pink' explicitly to each flamingo and 'wooden' explicitly to each chair, avoiding attribute leakage to other objects."},
    {"skill": "anti_occlusion", "action": "Arrange the scene so the flamingos, horse, and chairs are not hidden, merged, or blocked by any other elements."},
    {"skill": "multi_object_composition", "action": "Keep the four flamingos, one horse, and four wooden chairs distinct, complete, and jointly visible in one coherent scene."},
    {"skill": "negative_constraints", "action": "Avoid any extra flamingos, horses, or chairs; ensure only the required objects are present."},
    {"skill": "object_presence", "action": "Ensure every flamingo, the horse, and each chair is explicitly visible and not cropped out."}
  ]
}
```

**SFT 显著改进:**
- ✅ **学会了训练数据中的具体技巧:** "labeled as one, two, three, four to ensure accurate counting"
- ✅ action 描述更具体详细

---

### Ground Truth (期望输出)

```json
{
  "action_type": "retry_replan",
  "branch_source": "best_so_far",
  "branch_source_round": 0,
  "decision": "regenerate",
  "diagnosis": "The latest retry still failed the persistent constraints for exactly four flamingos and for the flamingos chasing the horse, and it regressed the previously passed exact count of four chairs...",
  "expected_improvement": [
    "Exact flamingo count should improve by presenting four pink flamingos as four large, separated, full-body birds in a single countable row with clear gaps and no overlap.",
    "The chasing relation should improve by using a stronger left-to-right pursuit layout...",
    "The four-chair count should recover by making the chairs a simple, separate right-side row...",
    "Previously passed constraints should remain stable by keeping exactly one horse fully visible..."
  ],
  "preserve_constraints": [
    "The flamingos must be pink and visible.",
    "There must be exactly one horse, fully visible.",
    "The horse must be clearly to the left of all chairs.",
    "The chairs must be wooden.",
    "The chairs must be visible as chairs."
  ],
  "previous_plan_error": {
    "details": "The previous retry emphasized a side-view row, but it still allowed the generator to lose count accuracy for flamingos and chairs...",
    "error_source": "Layout did not enforce clear gaps for counting or a decisive pursuit line for the action relation."
  },
  "regeneration_strategy": "Use a left-to-right pursuit composition: four large pink flamingos on the far left in a single row with clear gaps, all facing right toward one horse just ahead of them..."
}
```

---

### ROUND 2 对比分析

**SFT 学会的特定技巧:**
- ✅ "labeled as one, two, three, four" - 这是从训练数据中直接学到的表达

**仍然存在的问题:**
- ❌ 没有 `action_type`
- ❌ 没有 `branch_source`: 'best_so_far'
- ❌ 没有体现多轮 retry 的逻辑
- ❌ 没有根据之前的失败进行诊断和重新规划

---

## 总结

### SFT 训练效果评估: **部分有效，但未达到预期**

#### ✅ SFT 有效的地方

1. **增加了 training data 中的 concepts**
   - `attribute_binding`
   - `quantity_counting`

2. **Action 描述更详细具体**
   - Base: "Ensure four pink flamingos..."
   - SFT: "Ensure four pink flamingos are explicitly visible and not cropped out, avoiding attribute leakage"

3. **学会了特定技巧**
   - "labeled as one, two, three, four to ensure accurate counting"

4. **Loss 确实下降了**
   - 从 1.51 降到 1.07 (下降 28.9%)

#### ❌ SFT 失败的地方

1. **完全没有学会 Ground Truth 的 JSON 格式**
   - 期望: `initial_plan` / `retry_replan` 格式
   - 实际: 仍然是 `plan` 格式

2. **关键字段全部缺失**
   - `action_type`
   - `generation_guards`
   - `generation_strategy`
   - `initial_prompt`
   - `parsed_constraints`
   - `selected_skills`

3. **多轮对话逻辑缺失**
   - 没有 `branch_source`
   - 没有 `branch_source_round`
   - 没有 `decision`
   - 没有 `diagnosis`
   - 没有 `expected_improvement`
   - 没有 `preserve_constraints`
   - 没有 `previous_plan_error`
   - 没有 `regeneration_strategy`

4. **没有根据 verifier 反馈进行调整的能力**
   - 每轮输出都是相似的 plan 格式
   - 没有体现出 retry/replan 的逻辑

---

### 根本原因分析

1. **LoRA Rank=8 太小**
   - 不足以改变模型的输出格式偏好
   - 建议: 增加到 32 或 64

2. **5个 epoch 太少**
   - 复杂的 JSON 结构需要更多训练
   - 建议: 增加到 10-20

3. **基础模型是 Instruct 版本**
   - Qwen3-VL-8B-Instruct 已经有固定的输出习惯
   - 可能对我们的特定格式有"偏见"

4. **Loss 下降幅度不够**
   - 只下降了 28.9%
   - 可能需要更大幅度的下降才能学会新格式

5. **学习率可能太小**
   - 当前: 1e-5
   - 建议: 尝试 5e-4

---

### 改进建议

```yaml
# 当前配置
lora_rank: 8
num_train_epochs: 5
learning_rate: 1.0e-5

# 建议配置 1: 增大 LoRA
lora_rank: 32
num_train_epochs: 15
learning_rate: 5.0e-5

# 建议配置 2: Full fine-tuning (如果显存允许)
finetuning_type: full
num_train_epochs: 10
learning_rate: 1.0e-5
```

**其他建议:**
1. 在 system prompt 中更明确地指定输出格式模板
2. 使用 few-shot 示例来强化格式学习
3. 检查训练数据是否有格式不一致的问题
4. 考虑使用更大的基础模型 (32B)

---

### 结论

**当前 SFT 训练不充分，模型没有学会训练数据中的输出格式。**

虽然 SFT 模型在某些方面比 Base 模型有所改进（如增加了 attribute_binding 和 quantity_counting，action 描述更详细），但它**完全没有学会 Ground Truth 的 JSON 结构**。

这是一个典型的 **"部分过拟合"** 现象：模型学到了一些表面的概念，但没有学会核心的输出格式逻辑。

需要调整训练策略，增大 LoRA rank 和训练 epoch，或尝试 full fine-tuning。
