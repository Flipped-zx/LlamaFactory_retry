# GenEval2 SFT Offline Action Evaluation Report

Generated: 2026-07-09T13:46:47.884421

## Summary

- **Total evaluated target turns**: 34

### Task Type Distribution
- initial_plan: 2
- retry_replan: 30
- stop: 2

## Base vs SFT Comparison

| Metric | Base Model | SFT LoRA | Improvement |
|--------|------------|----------|-------------|
| valid_json_rate | 100.0% | 100.0% | +0.0% |
| schema_complete_rate | 62.0% | 61.5% | -0.5% |
| action_type_accuracy | 94.1% | 94.1% | +0.0% |
| decision_accuracy | 58.8% | 58.8% | +0.0% |

### Retry/Replan Specific Metrics

| Metric | Base Model | SFT LoRA | Improvement |
|--------|------------|----------|-------------|
| branch_source_accuracy | 33.3% | 33.3% | +0.0% |
| retry_prompt_present_rate | 73.3% | 66.7% | -6.7% |
| repair_constraints_present_rate | 66.7% | 66.7% | +0.0% |
| preserve_constraints_present_rate | 66.7% | 66.7% | +0.0% |
| repair_constraints_overlap | 4.9% | 4.4% | -0.4% |
| preserve_constraints_overlap | 37.5% | 36.9% | -0.7% |

### Stop Action Metrics

| Metric | Base Model | SFT LoRA | Improvement |
|--------|------------|----------|-------------|
| stop_action_accuracy | 94.1% | 94.1% | +0.0% |
| stop_reason_present_rate | 100.0% | 50.0% | -50.0% |

## Per-Action-Type Metrics

### initial_plan

Samples: 2

| Metric | Base | SFT |
|--------|------|-----|
| valid_json | 100.0% | 100.0% |
| schema_complete_rate | 0.0% | 0.0% |
| action_type_correct | 0.0% | 0.0% |
| decision_correct | 0.0% | 0.0% |

### retry_replan

Samples: 30

| Metric | Base | SFT |
|--------|------|-----|
| valid_json | 100.0% | 100.0% |
| schema_complete_rate | 70.3% | 69.7% |
| action_type_correct | 100.0% | 100.0% |
| decision_correct | 66.7% | 66.7% |

### stop

Samples: 2

| Metric | Base | SFT |
|--------|------|-----|
| valid_json | 100.0% | 100.0% |
| schema_complete_rate | 0.0% | 0.0% |
| action_type_correct | 100.0% | 100.0% |
| decision_correct | 0.0% | 0.0% |

## Examples: SFT Better Than Base

## Examples: SFT Failures

### Failure 1 (incomplete_schema)
- Sample ID: geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_02__retry_r0_to_r1
- Task Type: retry_replan
- Action Tags: branch_latest, fixed_more_than_regressed, high_score_after_action, improved_no_regression, narrow_failure_after_action, retry_unresolved_after_action

**SFT Output:**
```
{"action_type":"retry_replan","generation_guards":["Show exactly four pink flamingos, exactly one horse, and exactly four wooden chairs.","Keep all flamingos, the horse, and all chairs fully visible and separated enough to count.","Bind pink color only to the flamingos and wooden material to the chairs.","Place the horse clearly to the left of the group of four wooden chairs.","Depict the four pink flamingos actively chasing the horse, with their orientation and motion directed toward the horse....
```

**Ground Truth:**
```json
{"action_type":"retry_replan","branch_source":"latest","branch_source_round":0,"decision":"regenerate","diagnosis":"The image passed the pink flamingo attribute, flamingo presence, exactly one horse, horse presence, horse left of chairs, exactly four wooden chairs, wooden chair material, and chair presence. It failed to show exactly four flamingos clearly enough, and it failed to make the flamingos visibly chasing the horse. These are persistent failures from the initial attempt.","expected_impr...
```

### Failure 2 (incomplete_schema)
- Sample ID: geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_04__retry_r0_to_r1
- Task Type: retry_replan
- Action Tags: branch_latest, high_score_after_action, improved_no_regression, narrow_failure_after_action, retry_unresolved_after_action

**SFT Output:**
```
{"action_type":"retry_replan","generation_guards":["Show exactly four pink flamingos, exactly one horse, and exactly four wooden chairs.","Keep all flamingos, the horse, and all chairs fully visible and separated enough to count.","Bind pink color only to the flamingos and wooden material to the chairs.","Place the horse clearly to the left of the group of four wooden chairs.","Depict the four pink flamingos actively chasing the horse, with their orientation and motion directed toward the horse....
```

**Ground Truth:**
```json
{"action_type":"retry_replan","branch_source":"latest","branch_source_round":0,"decision":"regenerate","diagnosis":"The only failed constraint is the relation: the evaluator did not recognize the four pink flamingos as chasing the horse. Counts, object presence, flamingo color, wooden chair attribute, and the horse-left-of-chairs spatial relation all passed and should be preserved. Because this is a persistent relation failure, the next prompt should make the chase visually explicit with a simpl...
```

### Failure 3 (incomplete_schema)
- Sample ID: geneval2_00734_4aedb898__geneval2_00734_4aedb898_cand_04__retry_r0_to_r1
- Task Type: retry_replan
- Action Tags: branch_latest, fixed_more_than_regressed, improved_no_regression, narrow_failure_after_action, retry_unresolved_after_action

**SFT Output:**
```
{"action_type":"retry_replan","generation_guards":["Show exactly three raccoons, exactly two violins, and exactly two umbrellas.","Bind white color only to the three raccoons, stone material only to the two violins, and red color only to the two umbrellas.","Place all three white raccoons to the left of both stone violins.","Keep all seven objects clearly visible and separated, with no object hidden behind another."],"generation_strategy":"Use a simple wide composition with three white raccoons ...
```

**Ground Truth:**
```json
{"action_type":"retry_replan","branch_source":"latest","branch_source_round":0,"decision":"regenerate","diagnosis":"The generation passed object presence, exact counts, the raccoons-left-of-violins relation, and red umbrellas, but failed the two attribute bindings: the three raccoons were not recognized as white and the two violins were not recognized as stone. These are persistent attribute/color failures from the initial attempt, so the retry should make the target attributes visually dominant...
```

### Failure 4 (wrong_action_type)
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00__initial_plan
- Task Type: initial_plan
- Action Tags: high_score_after_action, initial_generation_failed, initial_plan_valid, narrow_failure_after_action

**SFT Output:**
```
{
  "plan": [
    {
      "skill": "object_presence",
      "target": "a sparkling bagel",
      "action": "Ensure the sparkling bagel is explicitly named, visible, and not cropped out."
    },
    {
      "skill": "object_presence",
      "target": "six black croissants",
      "action": "Ensure six black croissants are explicitly named, visible, and not cropped out."
    },
    {
      "skill": "object_presence",
      "target": "seven pink mushrooms",
      "action": "Ensure seven pink mushro...
```

**Ground Truth:**
```json
{"action_type":"initial_plan","generation_guards":["Depict exactly one bagel, exactly six croissants, and exactly seven mushrooms.","Bind attributes correctly: the single bagel is sparkling, all six croissants are black, and all seven mushrooms are pink.","Preserve spatial relations: the sparkling bagel is in front of the six black croissants; the six black croissants are on top of the seven pink mushrooms.","Keep all objects clearly visible and countable; arrange objects with enough separation ...
```

### Failure 5 (incomplete_schema)
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00__retry_r0_to_r1
- Task Type: retry_replan
- Action Tags: branch_latest, fixed_more_than_regressed, improved_no_regression, positive_retry_passed

**SFT Output:**
```
{"action_type":"retry_replan","generation_guards":["Depict exactly one bagel, exactly six croissants, and exactly seven mushrooms.","Bind attributes correctly: the single bagel is sparkling, all six croissants are black, and all seven mushrooms are pink.","Preserve spatial relations: the sparkling bagel is in front of the six black croissants; the six black croissants are on top of the seven pink mushrooms.","Keep all objects clearly visible and countable; arrange objects with enough separation ...
```

**Ground Truth:**
```json
{"action_type":"retry_replan","branch_source":"latest","branch_source_round":0,"decision":"regenerate","diagnosis":"The only failed constraint is the croissant count: the image did not clearly show exactly six croissants. All other constraints passed, including one sparkling bagel, bagel in front of croissants, black croissants present, croissants on top of mushrooms, seven pink mushrooms, and no missing required objects. The retry should preserve those passed constraints while making the six cr...
```

## Assessment: Ready for Closed-Loop GenEval2?

### Key Criteria:

1. **Valid JSON Rate**: 100.0% (target: >95%)
   - Status: ✅ PASS

2. **Schema Completeness**: 61.5% (target: >80%)
   - Status: ❌ FAIL

3. **Action Type Accuracy**: 94.1% (target: >95%)
   - Status: ⚠️ MARGINAL

### Overall Assessment

⚠️ **SFT model needs improvement before closed-loop evaluation.**
Consider:
- Adding more diverse schema examples to training data

---

*Report generated by eval_geneval2_sft_offline_actions.py*