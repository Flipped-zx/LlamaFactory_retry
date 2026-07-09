# GenEval2 Real Turn Mask Check

- Dataset: `geneval2_retry_masked_multiturn_sft_train`
- Model/tokenizer: `/home/develop/biocloudplantform/xxr/models/Qwen3-VL-8B-Instruct`
- Template: `qwen3_vl_nothink`
- Cutoff length: `32768`
- Raw rows: `179`
- Processed rows: `179`
- Inspected samples: `10`
- Selection coverage: `{'monotonic_success': 5, 'non_monotonic_recovery_success': 3, 'high_score_or_narrow_unresolved': 2}`

## Inspected Samples

- `PASS` row=1 trajectory_id=`geneval2_00531_278a7825__geneval2_00531_278a7825_cand_01` group=`monotonic_success` tags=`['monotonic_success', 'passed']` stats=`{'masked': 0, 'trainable': 4, 'risky': 0, 'positive': 3}`
- `PASS` row=2 trajectory_id=`geneval2_00531_278a7825__geneval2_00531_278a7825_cand_02` group=`monotonic_success` tags=`['monotonic_success', 'passed']` stats=`{'masked': 0, 'trainable': 3, 'risky': 0, 'positive': 2}`
- `PASS` row=4 trajectory_id=`geneval2_00531_278a7825__geneval2_00531_278a7825_cand_04` group=`monotonic_success` tags=`['monotonic_success', 'passed']` stats=`{'masked': 0, 'trainable': 3, 'risky': 0, 'positive': 2}`
- `PASS` row=6 trajectory_id=`geneval2_00545_01edf866__geneval2_00545_01edf866_cand_02` group=`non_monotonic_recovery_success` tags=`['best_so_far_branch_used', 'non_monotonic_recovery_success', 'non_monotonic_score_path', 'passed']` stats=`{'masked': 1, 'trainable': 4, 'risky': 1, 'positive': 3}`
- `PASS` row=20 trajectory_id=`geneval2_00702_d0b30c00__geneval2_00702_d0b30c00_cand_03` group=`non_monotonic_recovery_success` tags=`['best_so_far_branch_used', 'non_monotonic_recovery_success', 'non_monotonic_score_path', 'passed']` stats=`{'masked': 2, 'trainable': 3, 'risky': 1, 'positive': 2}`
- `PASS` row=21 trajectory_id=`geneval2_00702_d0b30c00__geneval2_00702_d0b30c00_cand_04` group=`non_monotonic_recovery_success` tags=`['best_so_far_branch_used', 'has_round4_normal_selective', 'non_monotonic_recovery_success', 'non_monotonic_score_path', 'passed']` stats=`{'masked': 1, 'trainable': 5, 'risky': 1, 'positive': 4}`
- `PASS` row=0 trajectory_id=`geneval2_00531_278a7825__geneval2_00531_278a7825_cand_00` group=`selected_high_score_or_narrow_unresolved` tags=`['high_score_unresolved', 'unresolved']` stats=`{'masked': 1, 'trainable': 3, 'risky': 0, 'positive': 3}`
- `PASS` row=3 trajectory_id=`geneval2_00531_278a7825__geneval2_00531_278a7825_cand_03` group=`selected_high_score_or_narrow_unresolved` tags=`['best_so_far_branch_used', 'has_round4_normal_selective', 'high_score_unresolved', 'regression_failed', 'unresolved']` stats=`{'masked': 3, 'trainable': 2, 'risky': 2, 'positive': 2}`
- `PASS` row=5 trajectory_id=`geneval2_00545_01edf866__geneval2_00545_01edf866_cand_00` group=`monotonic_success` tags=`['monotonic_success', 'passed']` stats=`{'masked': 0, 'trainable': 4, 'risky': 0, 'positive': 3}`
- `PASS` row=7 trajectory_id=`geneval2_00545_01edf866__geneval2_00545_01edf866_cand_03` group=`monotonic_success` tags=`['monotonic_success', 'passed']` stats=`{'masked': 1, 'trainable': 4, 'risky': 1, 'positive': 3}`

## Result

PASS
