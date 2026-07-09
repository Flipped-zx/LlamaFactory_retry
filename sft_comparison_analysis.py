#!/usr/bin/env python3
"""
SFT 效果对比分析报告
====================

基于 geneval2 测试数据的实际推理结果对比
"""

import json

def print_section(title, char="="):
    print(f"\n{char*80}")
    print(f"{title}")
    print(f"{char*80}\n")

# 实际测试结果数据
round_0_base = """{
  "plan": [
    {"skill": "object_presence", "action": "Ensure four pink flamingos are explicitly visible..."},
    {"skill": "object_presence", "action": "Ensure four wooden chairs are explicitly visible..."},
    {"skill": "spatial_layout", "action": "Position the horse to the left of the four wooden chairs."},
    {"skill": "spatial_layout", "action": "Arrange the four pink flamingos to be chasing the horse..."},
    {"skill": "clarity_visibility", "action": "Make all objects clear, unobstructed, and easy to verify..."},
    {"skill": "anti_occlusion", "action": "Arrange objects so no flamingos, horse, or chairs are hidden..."},
    {"skill": "negative_constraints", "action": "Avoid any extra or forbidden objects..."},
    {"skill": "multi_object_composition", "action": "Keep flamingos, horse, and chairs distinct..."}
  ]
}"""

round_0_sft = """{
  "plan": [
    {"skill": "object_presence", "action": "Ensure four pink flamingos are explicitly visible..."},
    {"skill": "object_presence", "action": "Ensure four wooden chairs are explicitly visible..."},
    {"skill": "spatial_layout", "action": "Place the horse to the left of the four wooden chairs."},
    {"skill": "spatial_layout", "action": "Position the four pink flamingos chasing the horse..."},
    {"skill": "multi_object_composition", "action": "Keep all objects distinct, complete, and jointly visible..."},
    {"skill": "clarity_visibility", "action": "Make the horse, flamingos, and chairs clear, centered enough..."},
    {"skill": "anti_occlusion", "action": "Arrange objects so the horse, flamingos, and chairs are not hidden..."},
    {"skill": "negative_constraints", "action": "Avoid any forbidden or extra objects..."},
    {"skill": "attribute_binding", "action": "Bind the color 'pink' explicitly to the flamingos..."},
    {"skill": "quantity_counting", "action": "State the exact number: four flamingos and four chairs..."}
  ]
}"""

round_0_gt = """{
  "action_type": "initial_plan",
  "generation_guards": [
    "Show exactly four pink flamingos, exactly one horse, and exactly four wooden chairs.",
    "Keep all flamingos, the horse, and all chairs fully visible and separated enough to count.",
    "Bind pink color only to the flamingos and wooden material to the chairs.",
    "Place the horse clearly to the left of the group of four wooden chairs.",
    "Depict the four pink flamingos actively chasing the horse...",
    "Avoid extra flamingos, extra horses, extra chairs, or occlusion..."
  ],
  "generation_strategy": "Use a clear side-view composition with three countable groups...",
  "initial_prompt": "A clear scene showing exactly four pink flamingos chasing exactly one horse...",
  "parsed_constraints": { ... },
  "selected_skills": ["quantity_counting", "attribute_binding", ...]
}"""

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           Base 模型 vs SFT 模型 - Geneval2 实际推理对比                        ║
║                                                                              ║
║  测试轨迹: geneval2_00616_b58d8daf                                            ║
║  提示: "four pink flamingos chasing a horse to the left of four wooden chairs" ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

print_section("ROUND 0: INITIAL_PLAN")

print("🟦 [Base 模型] 输出:")
print("-" * 60)
print("格式: plan (skill-action 列表)")
print("项目数: 8 个 plan items")
print("主要skills: object_presence, spatial_layout, clarity_visibility...")
print()

print("🟩 [SFT 模型] 输出:")
print("-" * 60)
print("格式: plan (skill-action 列表)")
print("项目数: 10 个 plan items")
print("主要skills: + attribute_binding, quantity_counting (新增)")
print()

print("🟨 [Ground Truth] 期望输出:")
print("-" * 60)
print("格式: initial_plan (action_type + generation_guards + strategy + prompt)")
print("关键字段:")
print("  - action_type: 'initial_plan'")
print("  - generation_guards: 6条约束规则")
print("  - generation_strategy: 详细生成策略")
print("  - initial_prompt: 完整图像生成提示词")
print()

print_section("关键发现", "!")

print("""
❌ SFT 训练效果不佳 - 模型没有学会正确的输出格式！

对比分析:
┌─────────────────┬─────────────────────────────┬─────────────────────────────┐
│     维度        │       Base 模型              │       SFT 后模型            │
├─────────────────┼─────────────────────────────┼─────────────────────────────┤
│ 输出格式        │ plan (8 items)              │ plan (10 items)             │
├─────────────────┼─────────────────────────────┼─────────────────────────────┤
│ 是否符合GT      │ ❌ 否                        │ ❌ 否                        │
├─────────────────┼─────────────────────────────┼─────────────────────────────┤
│ action_type     │ ❌ 无                        │ ❌ 无                        │
├─────────────────┼─────────────────────────────┼─────────────────────────────┤
│ generation_guards│ ❌ 无                       │ ❌ 无                        │
├─────────────────┼─────────────────────────────┼─────────────────────────────┤
│ generation_strategy│ ❌ 无                     │ ❌ 无                        │
├─────────────────┼─────────────────────────────┼─────────────────────────────┤
│ initial_prompt  │ ❌ 无                        │ ❌ 无                        │
└─────────────────┴─────────────────────────────┴─────────────────────────────┘

细微改进:
  ✓ SFT 模型增加了 attribute_binding 和 quantity_counting
  ✓ SFT 模型的 action 描述更详细

严重问题:
  ✗ 两种模型都没有输出 Ground Truth 的格式
  ✗ 没有 action_type 字段
  ✗ 没有 generation_guards 数组
  ✗ 没有 generation_strategy
  ✗ 没有 initial_prompt
""")

print_section("ROUND 1-2: RETRY_REPLAN", "-")

print("""
多轮对话中的问题:

Base 模型:
  - 继续输出 plan 格式
  - 没有根据 verifier 反馈调整
  - 没有 branch_source, decision 等字段

SFT 模型:
  - 仍然输出 plan 格式
  - 虽然增加了一些细节（如"labeled as one, two, three, four"）
  - 但完全没有 Ground Truth 中的关键字段:
    * action_type: "retry_replan"
    * branch_source: "latest" / "best_so_far"
    * branch_source_round: 0
    * decision: "regenerate"
    * diagnosis: "The image passed... but failed..."
    * expected_improvement: [...]
    * preserve_constraints: [...]
    * previous_plan_error: {...}
    * regeneration_strategy: "Use a clean side-view..."
""")

print_section("根本原因分析", "!")

print("""
为什么 SFT 没有生效？

1. 基础模型本身的问题:
   - Qwen3-VL-8B-Instruct 是 Instruct 版本
   - 它已经经过指令微调，有固定的输出偏好
   - 可能对我们的特定格式有"偏见"

2. LoRA 训练可能不足:
   - LoRA Rank=8 可能太小
   - 只训练了 5 个 epoch，可能不够
   - Loss 从 1.51 降到 1.07，下降幅度有限 (28.9%)

3. 数据格式问题:
   - 训练数据是 ShareGPT 格式 (messages)
   - 但模型可能没有学会从 system prompt 中提取格式要求
   - "Output only valid JSON" 的指令没有被正确执行

4. 格式差异:
   - Ground Truth 是复杂的嵌套 JSON
   - 模型可能在预训练时很少见到这种特定格式
   - 需要更强的监督信号才能学会
""")

print_section("改进建议")

print("""
1. 增加训练强度:
   - 增加 LoRA rank (8 → 32 或 64)
   - 增加训练 epoch (5 → 10 或 20)
   - 尝试 full fine-tuning (如果显存允许)

2. 改进数据格式:
   - 在 system prompt 中明确指定输出格式模板
   - 使用 few-shot 示例
   - 添加格式验证和重试机制

3. 调整学习率:
   - 当前 1e-5 可能太小
   - 尝试 1e-4 或 5e-4

4. 使用更大的基础模型:
   - 8B 可能容量有限
   - 尝试 32B 或更大模型

5. 检查训练数据质量:
   - 确保 input/output 格式一致
   - 检查是否有数据泄露或格式错误
""")

print_section("结论")

print("""
📊 SFT 效果评估: **部分有效，但未达到预期**

有效的地方:
  ✓ SFT 模型比 Base 模型输出更详细
  ✓ 增加了一些训练数据中的概念 (attribute_binding, quantity_counting)
  ✓ Loss 确实下降了 28.9%

失败的地方:
  ✗ 没有学会 Ground Truth 的 JSON 格式
  ✗ 没有输出关键的 action_type, generation_guards 等字段
  ✗ 多轮对话中没有体现出 retry/replan 的逻辑

结论: 当前 SFT 训练不充分，需要调整超参数或训练策略。
""")
