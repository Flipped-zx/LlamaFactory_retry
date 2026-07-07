# GenEval2 Retry Masked Multi-Turn SFT Summary

## Files
- Main: `data/llamafactory/geneval2_retry_masked_multiturn_sft.jsonl`
- Train: `data/llamafactory/geneval2_retry_masked_multiturn_sft_train.jsonl`
- Val: `data/llamafactory/geneval2_retry_masked_multiturn_sft_val.jsonl`
- Test: `data/llamafactory/geneval2_retry_masked_multiturn_sft_test.jsonl`

## Inclusion
- Total included trajectories: 207
- Monotonic success count: 88
- Non-monotonic recovery success count: 24
- Selected high-score/narrow unresolved count: 95
- Selected high_score_unresolved count: 79
- Selected narrow_failure_unresolved count: 50
- Skipped stats: `{"not_selected": 293}`

## Messages And Masks
- Total messages: 1811
- Total assistant turns: 802
- Assistant turns with turn_mask=false: 514
- Assistant turns with turn_mask=true: 288
- Masked risky_retry_regressed count: 148
- Masked risky_large_drop count: 7
- Unmasked branch_best_so_far_recovery count: 82
- Unmasked stop_passed count: 112

## Length
- Average token length estimate: 15511.7
- Max token length estimate: 29651

## Validity
- Invalid JSON target count: 0
- Missing teacher_action count: 0
- Leakage check result: passed

## Prompt-Level Split
- Prompt_id counts by split: `{"test": 6, "train": 53, "val": 7}`
- Row counts by split: `{"test": 14, "train": 179, "val": 14}`

## Validation Warnings
- None
