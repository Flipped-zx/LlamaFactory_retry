# GenEval2 SFT Offline Evaluation Audit Report

Generated: 2026-07-09T18:35:35.177487

======================================================================
# Task 2: Verify SFT Adapter Loading
======================================================================

## Loading Base Model...

**Base Model Class:** `Qwen3VLForConditionalGeneration`
**Base Model Device:** `cuda:0`
**Base Model Total Parameters:** 8,767,123,696

## Loading with LoRA Adapter...

**Adapter Path:** `saves/qwen3-vl-8b/lora/geneval2_retry_masked_multiturn_sft_6gpu`
**adapter_model.safetensors exists:** True
**adapter_config.json exists:** True
**Adapter size:** 83.32 MB

**Model with Adapter Class:** `PeftModelForCausalLM`
**Is PeftModel:** True
**Active Adapters:** ['default']
**Active Adapter:** default

**PEFT Config:**
  - Adapter: `default`
    - r: 8
    - lora_alpha: 16
    - target_modules: {'up_proj', 'k_proj', 'v_proj', 'q_proj', 'gate_proj', 'o_proj', 'down_proj'}
    - peft_type: PeftType.LORA

**Parameter Statistics:**
  - Total parameters: 8,788,947,184
  - Trainable parameters: 0
  - Trainable %: 0.0000%

**Adapter Parameter Names (first 20):**

**Verification:**
  - Base model should be frozen (no trainable non-adapter params)

======================================================================
# Task 3: Debug Comparison (3 Samples)
======================================================================

**Selected 3 samples for debug comparison**


## Loading Models...

------------------------------------------------------------
## Sample 1: geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_00__retry_r1_to_r2
------------------------------------------------------------
**Trajectory ID:** geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_00
**Task Type:** retry_replan
**Action Tags:** branch_best_so_far, branch_best_so_far_recovery, improved_no_regression, retry_unresolved_after_action
**Turn Mask:** False
**Include in Clean SFT:** True

### Base Model Generation:
**Input tokens:** 10149
**Output tokens:** 926
**Complete JSON:** True

```json
{"action_type":"retry_replan","branch_source":"latest","branch_source_round":1,"decision":"regenerate","diagnosis":"The image failed to show exactly four flamingos (count_mismatch) and failed to show the flamingos chasing the horse (relation_mismatch). It also regressed by failing to show exactly four chairs (new count_mismatch). The previous prompt was too verbose and ambiguous for the generator to enforce precise counts and directional chasing. The generator likely misinterpreted 'chasing' as mere proximity or failed to separate the flamingos clearly enough for counting.","expected_improvement":["Force a simple, side-view layout with four flamingos in a row on the left, each clearly separated and labeled as 1, 2, 3, 4 to ensure count accuracy.","Make the horse positioned ahead of the flamingos, with all four flamingos behind it, facing forward toward the horse, and visually oriented as if in pursuit.","Explicitly state that the horse is moving away from the flamingos to reinforce the...
```

### SFT Model Generation:
**Input tokens:** 10149
**Output tokens:** 1007
**Complete JSON:** True

```json
{"action_type":"retry_replan","branch_source":"latest","branch_source_round":1,"decision":"regenerate","diagnosis":"The image passed pink flamingos, flamingo presence, one horse, horse presence, horse left of chairs, four chairs, wooden chairs, and chair presence. It failed the exact flamingo count, the chasing relation, and the exact chair count: the scene did not clearly show exactly four flamingos, the flamingos were not clearly chasing the horse, and the scene did not clearly show exactly four chairs.","expected_improvement":["Exact flamingo count should improve by using a simple side-view lineup of four separate, fully visible pink flamingos with visible gaps between them.","The chasing relation should improve by placing all four flamingos behind the horse, facing and moving toward the horse, while the horse moves away from them.","Exact chair count should improve by using a simple side-view lineup of four separate, fully visible wooden chairs with visible gaps between them.","Pre...
```

### Ground Truth:
```json
{"action_type":"retry_replan","branch_source":"best_so_far","branch_source_round":0,"decision":"regenerate","diagnosis":"The latest retry still failed the persistent constraints for exactly four flamingos and for the flamingos chasing the horse, and it regressed the previously passed exact count of four chairs. The passed constraints that remain important are pink flamingos, visible flamingos, exactly one visible horse, the horse left of the chairs, wooden chairs, and visible chairs. The next retry should branch from the best earlier attempt because that attempt preserved the four-chair count while only failing flamingo count and chasing relation.","expected_improvement":["Exact flamingo count should improve by presenting four pink flamingos as four large, separated, full-body birds in a single countable row with clear gaps and no overlap.","The chasing relation should improve by using a stronger left-to-right pursuit layout: all four flamingos behind the horse on the left, all facing ...
```

### Comparison:
**Outputs identical:** False
**Base output length:** 4383
**SFT output length:** 5018
**Ground truth length:** 5954
**Base valid JSON:** True
**SFT valid JSON:** True
**Base keys:** ['action_type', 'branch_source', 'branch_source_round', 'decision', 'diagnosis', 'expected_improvement', 'preserve_constraints', 'regeneration_strategy', 'repair_constraints', 'retry_prompt', 'skill_revision']
**SFT keys:** ['action_type', 'branch_source', 'branch_source_round', 'decision', 'diagnosis', 'expected_improvement', 'preserve_constraints', 'previous_plan_error', 'regeneration_strategy', 'regression_risks', 'repair_constraints', 'retry_prompt', 'skill_revision']
**Common keys:** ['action_type', 'branch_source', 'branch_source_round', 'decision', 'diagnosis', 'expected_improvement', 'preserve_constraints', 'regeneration_strategy', 'repair_constraints', 'retry_prompt', 'skill_revision']
**Base only keys:** []
**SFT only keys:** ['previous_plan_error', 'regression_risks']

------------------------------------------------------------
## Sample 2: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00__initial_plan
------------------------------------------------------------
**Trajectory ID:** geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00
**Task Type:** initial_plan
**Action Tags:** high_score_after_action, initial_generation_failed, initial_plan_valid, narrow_failure_after_action
**Turn Mask:** False
**Include in Clean SFT:** True

### Base Model Generation:
**Input tokens:** 288
**Output tokens:** 374
**Complete JSON:** True

```json
{
  "plan": [
    {
      "skill": "object_presence",
      "action": "Ensure the sparkling bagel is explicitly visible and not cropped out."
    },
    {
      "skill": "object_presence",
      "action": "Ensure each of the six black croissants is explicitly visible and not cropped out."
    },
    {
      "skill": "object_presence",
      "action": "Ensure each of the seven pink mushrooms is explicitly visible and not cropped out."
    },
    {
      "skill": "spatial_layout",
      "action": "Place the sparkling bagel in front of the six black croissants."
    },
    {
      "skill": "spatial_layout",
      "action": "Place the six black croissants on top of the seven pink mushrooms."
    },
    {
      "skill": "clarity_visibility",
      "action": "Make the sparkling bagel, six black croissants, and seven pink mushrooms clear, centered, and unobstructed."
    },
    {
      "skill": "anti_occlusion",
      "action": "Arrange objects so the sparkling bagel is not hidden, merged, or...
```

### SFT Model Generation:
**Input tokens:** 288
**Output tokens:** 974
**Complete JSON:** True

```json
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
      "action": "Ensure the six black croissants are explicitly named, visible, and not cropped out."
    },
    {
      "skill": "object_presence",
      "target": "seven pink mushrooms",
      "action": "Ensure the seven pink mushrooms are explicitly named, visible, and not cropped out."
    },
    {
      "skill": "spatial_layout",
      "target": "a sparkling bagel in front of six black croissants",
      "action": "Place the sparkling bagel in front of the six black croissants using unambiguous left/right/above/below/in-front/behind relations."
    },
    {
      "skill": "spatial_layout",
      "target": "six black croissants on top of seven pink mushrooms",
      "action": "Place the six black croissants on to...
```

### Ground Truth:
```json
{"action_type":"initial_plan","generation_guards":["Depict exactly one bagel, exactly six croissants, and exactly seven mushrooms.","Bind attributes correctly: the single bagel is sparkling, all six croissants are black, and all seven mushrooms are pink.","Preserve spatial relations: the sparkling bagel is in front of the six black croissants; the six black croissants are on top of the seven pink mushrooms.","Keep all objects clearly visible and countable; arrange objects with enough separation to avoid occlusion that would hide counts."],"generation_strategy":"Create a clear multi-object composition with three visible layers: seven pink mushrooms forming the bottom support row, six black croissants resting on top of the mushrooms, and one sparkling bagel placed in the foreground in front of the croissants. Use spacing and slight separation so each individual mushroom and croissant can be counted while maintaining the stated on-top and in-front relations.","initial_prompt":"A clear, co...
```

### Comparison:
**Outputs identical:** False
**Base output length:** 1603
**SFT output length:** 4119
**Ground truth length:** 2007
**Base valid JSON:** True
**SFT valid JSON:** True
**Base keys:** ['plan']
**SFT keys:** ['plan']
**Common keys:** ['plan']
**Base only keys:** []
**SFT only keys:** []

------------------------------------------------------------
## Sample 3: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00__stop_passed_r1
------------------------------------------------------------
**Trajectory ID:** geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00
**Task Type:** stop
**Action Tags:** stop_passed
**Turn Mask:** False
**Include in Clean SFT:** True

### Base Model Generation:
**Input tokens:** 8436
**Output tokens:** 88
**Complete JSON:** True

```json
{"action_type":"stop","final_score":0.9893764569820434,"reason":"All constraints are now satisfied: the image correctly shows one sparkling bagel in front of six black croissants on top of seven pink mushrooms. The croissant count is now accurate, and all other attributes, positions, and object presence are preserved. No further retries are needed."}
```

### SFT Model Generation:
**Input tokens:** 8436
**Output tokens:** 996
**Complete JSON:** True

```json
{"action_type":"stop","final_score":0.9893764569820434,"final_summary":{"critical_failure_types":[],"failed_count":0,"passed_count":11,"passed":true,"score":0.9893764569820434,"passed_constraints":[{"atom_index":0,"detected":"soft_score=0.999986","expected":"one","score":0.9999861505747284,"skill":"count","target":"How many bagels are in the image?","type":"count_mismatch"},{"atom_index":1,"detected":"soft_score=0.99999","expected":"Yes","score":0.9999898203276931,"skill":"attribute","target":"Is the bagel sparkling?","type":"attribute_mismatch"},{"atom_index":2,"detected":"soft_score=0.999997","expected":"Yes","score":0.999996987024133,"skill":"object","target":"Are there any bagels in the image?","type":"missing_object"},{"atom_index":3,"detected":"soft_score=1","expected":"Yes","score":0.9999998957478056,"skill":"position","target":"Is the bagel in front of the croissants?","type":"spatial_mismatch"},{"atom_index":4,"detected":"soft_score=0.906684","expected":"six","score":0.9066841...
```

### Ground Truth:
```json
{"action_type":"stop","decision":"stop","reason":"passed"}
```

### Comparison:
**Outputs identical:** False
**Base output length:** 352
**SFT output length:** 3052
**Ground truth length:** 58
**Base valid JSON:** True
**SFT valid JSON:** True
**Base keys:** ['action_type', 'final_score', 'reason']
**SFT keys:** ['action_type', 'final_score', 'final_summary']
**Common keys:** ['action_type', 'final_score']
**Base only keys:** ['reason']
**SFT only keys:** ['final_summary']

======================================================================
# Task 4: Check Generation Truncation
======================================================================

**Sample:** geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_00__retry_r1_to_r2
**Task Type:** retry_replan
**Ground truth length:** 5954 chars
**Ground truth token count:** ~1186 tokens

### max_new_tokens = 512
  - Generated tokens: 512
  - Generated chars: 2617
  - Complete JSON: False
  - ⚠️ **Likely truncated!** (generated 512 tokens, limit was 512)
  - Last 100 chars: ` chairs as a separate right-side group so the horse remains clearly left of all chairs.","regression`

### max_new_tokens = 1024
  - Generated tokens: 1007
  - Generated chars: 5018
  - Complete JSON: True
  - ✅ Not truncated (generated 1007 tokens, limit was 1024)
  - Last 100 chars: ` and a directional behind-to-ahead pursuit layout to make chasing the horse visually unambiguous."}}`

### max_new_tokens = 2048
  - Generated tokens: 1007
  - Generated chars: 5018
  - Complete JSON: True
  - ✅ Not truncated (generated 1007 tokens, limit was 2048)
  - Last 100 chars: ` and a directional behind-to-ahead pursuit layout to make chasing the horse visually unambiguous."}}`

======================================================================
# Task 5: Verify Target Selection
======================================================================

**Total trajectories:** 14

**Total assistant turns:** 34
**Turn mask = True (excluded):** 0
**Turn mask = False (evaluated):** 34

**Verification:**
- Only evaluating turn_mask == False: ✅

### Target Distribution by Task Type
- initial_plan: 2
- retry_replan: 30
- stop: 2

### Target Distribution by Action Tags
- improved_no_regression: 28
- retry_unresolved_after_action: 28
- narrow_failure_after_action: 23
- branch_latest: 21
- fixed_more_than_regressed: 19
- high_score_after_action: 16
- branch_best_so_far: 9
- branch_best_so_far_recovery: 9
- round4_normal_selective: 2
- initial_generation_failed: 2
- initial_plan_valid: 2
- positive_retry_passed: 2
- stop_passed: 2
- regressed_constraints_present: 1

### Include in Clean SFT Distribution
- include_in_clean_sft=True: 34

======================================================================
# Task 6: Inspect Schema Failures
======================================================================

**Total predictions:** 34

**Predictions with missing fields:** 14

### Missing Field Counts
- decision: 12
- skill_revision: 10
- branch_source_round: 10
- regeneration_strategy: 10
- repair_constraints: 10
- diagnosis: 10
- previous_plan_error: 10
- preserve_constraints: 10
- branch_source: 10
- regression_risks: 10
- retry_prompt: 10
- expected_improvement: 10
- action_type: 2
- generation_strategy: 2
- generation_guards: 2
- initial_prompt: 2
- selected_skills: 2
- parsed_constraints: 2
- reason: 1

### Schema Failure Examples (first 10)

**Example 1:**
- Sample ID: geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_02__retry_r0_to_r1
- Task Type: retry_replan
- Missing Keys: ['skill_revision', 'branch_source_round', 'regeneration_strategy', 'repair_constraints', 'diagnosis', 'previous_plan_error', 'preserve_constraints', 'branch_source', 'regression_risks', 'retry_prompt', 'decision', 'expected_improvement']
- Generated Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Preview:
```json
{"action_type":"retry_replan","generation_guards":["Show exactly four pink flamingos, exactly one horse, and exactly four wooden chairs.","Keep all flamingos, the horse, and all chairs fully visible and separated enough to count.","Bind pink color only to the flamingos and wooden material to the chairs.","Place the horse clearly to the left of the group of four wooden chairs.","Depict the four pink flamingos actively chasing the horse, with their orientation and motion directed toward the horse.
```

**Example 2:**
- Sample ID: geneval2_00616_b58d8daf__geneval2_00616_b58d8daf_cand_04__retry_r0_to_r1
- Task Type: retry_replan
- Missing Keys: ['skill_revision', 'branch_source_round', 'regeneration_strategy', 'repair_constraints', 'diagnosis', 'previous_plan_error', 'preserve_constraints', 'branch_source', 'regression_risks', 'retry_prompt', 'decision', 'expected_improvement']
- Generated Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Preview:
```json
{"action_type":"retry_replan","generation_guards":["Show exactly four pink flamingos, exactly one horse, and exactly four wooden chairs.","Keep all flamingos, the horse, and all chairs fully visible and separated enough to count.","Bind pink color only to the flamingos and wooden material to the chairs.","Place the horse clearly to the left of the group of four wooden chairs.","Depict the four pink flamingos actively chasing the horse, with their orientation and motion directed toward the horse.
```

**Example 3:**
- Sample ID: geneval2_00734_4aedb898__geneval2_00734_4aedb898_cand_04__retry_r0_to_r1
- Task Type: retry_replan
- Missing Keys: ['skill_revision', 'branch_source_round', 'regeneration_strategy', 'repair_constraints', 'diagnosis', 'previous_plan_error', 'preserve_constraints', 'branch_source', 'regression_risks', 'retry_prompt', 'decision', 'expected_improvement']
- Generated Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Preview:
```json
{"action_type":"retry_replan","generation_guards":["Show exactly three raccoons, exactly two violins, and exactly two umbrellas.","Bind white color only to the three raccoons, stone material only to the two violins, and red color only to the two umbrellas.","Place all three white raccoons to the left of both stone violins.","Keep all seven objects clearly visible and separated, with no object hidden behind another."],"generation_strategy":"Use a simple wide composition with three white raccoons 
```

**Example 4:**
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00__initial_plan
- Task Type: initial_plan
- Missing Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Keys: ['plan']
- Generated Preview:
```json
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
      "action": "Ensure seven pink mushro
```

**Example 5:**
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00__retry_r0_to_r1
- Task Type: retry_replan
- Missing Keys: ['skill_revision', 'branch_source_round', 'regeneration_strategy', 'repair_constraints', 'diagnosis', 'previous_plan_error', 'preserve_constraints', 'branch_source', 'regression_risks', 'retry_prompt', 'decision', 'expected_improvement']
- Generated Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Preview:
```json
{"action_type":"retry_replan","generation_guards":["Depict exactly one bagel, exactly six croissants, and exactly seven mushrooms.","Bind attributes correctly: the single bagel is sparkling, all six croissants are black, and all seven mushrooms are pink.","Preserve spatial relations: the sparkling bagel is in front of the six black croissants; the six black croissants are on top of the seven pink mushrooms.","Keep all objects clearly visible and countable; arrange objects with enough separation 
```

**Example 6:**
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_00__stop_passed_r1
- Task Type: stop
- Missing Keys: ['reason', 'decision']
- Generated Keys: ['action_type', 'final_score', 'final_summary']
- Generated Preview:
```json
{"action_type":"stop","final_score":0.9893764569820434,"final_summary":{"passed":true,"passed_count":11,"failed_count":0,"critical_failure_types":[],"score":0.9893764569820434,"image_path":"data/qwen_geneval2_balanced_100x5_round1_retry_gpt55/00236/samples/00000.png","prompt_used":"A clear, countable scene with exactly seven pink mushrooms arranged as a visible bottom base row. Directly on top of the mushrooms, show exactly six black croissants in one simple horizontal row: six separate croissan
```

**Example 7:**
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_03__retry_r0_to_r1
- Task Type: retry_replan
- Missing Keys: ['skill_revision', 'branch_source_round', 'regeneration_strategy', 'repair_constraints', 'diagnosis', 'previous_plan_error', 'preserve_constraints', 'branch_source', 'regression_risks', 'retry_prompt', 'decision', 'expected_improvement']
- Generated Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Preview:
```json
{"action_type":"retry_replan","generation_guards":["Depict exactly one bagel, exactly six croissants, and exactly seven mushrooms.","Bind attributes correctly: the single bagel is sparkling, all six croissants are black, and all seven mushrooms are pink.","Preserve spatial relations: the sparkling bagel is in front of the six black croissants; the six black croissants are on top of the seven pink mushrooms.","Keep all objects clearly visible and countable; arrange objects with enough separation 
```

**Example 8:**
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_04__initial_plan
- Task Type: initial_plan
- Missing Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Keys: ['plan']
- Generated Preview:
```json
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
      "action": "Ensure seven pink mushro
```

**Example 9:**
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_04__retry_r0_to_r1
- Task Type: retry_replan
- Missing Keys: ['skill_revision', 'branch_source_round', 'regeneration_strategy', 'repair_constraints', 'diagnosis', 'previous_plan_error', 'preserve_constraints', 'branch_source', 'regression_risks', 'retry_prompt', 'decision', 'expected_improvement']
- Generated Keys: ['action_type', 'generation_strategy', 'generation_guards', 'initial_prompt', 'selected_skills', 'parsed_constraints']
- Generated Preview:
```json
{"action_type":"retry_replan","generation_guards":["Depict exactly one bagel, exactly six croissants, and exactly seven mushrooms.","Bind attributes correctly: the single bagel is sparkling, all six croissants are black, and all seven mushrooms are pink.","Preserve spatial relations: the sparkling bagel is in front of the six black croissants; the six black croissants are on top of the seven pink mushrooms.","Keep all objects clearly visible and countable; arrange objects with enough separation 
```

**Example 10:**
- Sample ID: geneval2_00737_d97f3ec5__geneval2_00737_d97f3ec5_cand_04__stop_passed_r4
- Task Type: stop
- Missing Keys: ['decision']
- Generated Keys: ['action_type', 'reason']
- Generated Preview:
```json
{"action_type":"stop","reason":"The image successfully satisfies all required constraints: exactly one sparkling bagel in front of the croissants, exactly six black croissants on top of the mushrooms, exactly seven pink mushrooms, and all objects are present, visible, and correctly attributed. The only remaining minor mismatches are attribute and object presence mismatches for the bagel and croissants, which are not critical failures and do not affect the core count or spatial relations. The sco
```

======================================================================
# Task 7: Train-Set Sanity Check
======================================================================

**Total train trajectories:** 179
**Evaluating 20 train targets**

### Results
**Base action type accuracy:** 15/20 (75.0%)
**SFT action type accuracy:** 15/20 (75.0%)
**Identical outputs:** 0/20 (0.0%)

⚠️ **SFT equals base on train set** - possible adapter loading issue

### Detailed Results
| Sample | Task Type | Base OK | SFT OK | Identical |
|--------|-----------|---------|--------|-----------|
| 2_00531_278a7825_cand_00__retry_r0_to_r1 | retry_replan | True | True | False |
| 2_00531_278a7825_cand_00__retry_r1_to_r2 | retry_replan | True | True | False |
| 2_00531_278a7825_cand_00__retry_r2_to_r3 | retry_replan | True | True | False |
| al2_00531_278a7825_cand_01__initial_plan | initial_plan | False | False | False |
| 2_00531_278a7825_cand_01__retry_r0_to_r1 | retry_replan | True | True | False |
| 2_00531_278a7825_cand_01__retry_r1_to_r2 | retry_replan | True | True | False |
| 2_00531_278a7825_cand_01__stop_passed_r2 | stop | True | True | False |
| al2_00531_278a7825_cand_02__initial_plan | initial_plan | False | False | False |
| 2_00531_278a7825_cand_02__retry_r0_to_r1 | retry_replan | True | True | False |
| 2_00531_278a7825_cand_02__stop_passed_r1 | stop | True | True | False |
| 2_00531_278a7825_cand_03__retry_r1_to_r2 | retry_replan | True | True | False |
| 2_00531_278a7825_cand_03__retry_r2_to_r3 | retry_replan | True | True | False |
| al2_00531_278a7825_cand_04__initial_plan | initial_plan | False | False | False |
| 2_00531_278a7825_cand_04__retry_r0_to_r1 | retry_replan | True | True | False |
| 2_00531_278a7825_cand_04__stop_passed_r1 | stop | True | True | False |
| al2_00545_01edf866_cand_00__initial_plan | initial_plan | False | False | False |
| 2_00545_01edf866_cand_00__retry_r0_to_r1 | retry_replan | True | True | False |
| 2_00545_01edf866_cand_00__retry_r1_to_r2 | retry_replan | True | True | False |
| 2_00545_01edf866_cand_00__stop_passed_r2 | stop | True | True | False |
| al2_00545_01edf866_cand_02__initial_plan | initial_plan | False | False | False |

======================================================================
# Summary and Recommendations
======================================================================

## Key Findings
1. Check if adapter is properly loaded (see Task 2)
2. Compare base vs SFT outputs (see Task 3)
3. Check if generation is truncated (see Task 4)
4. Verify target selection is correct (see Task 5)
5. Analyze schema failures (see Task 6)
6. Check if SFT improves on train set (see Task 7)