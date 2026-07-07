# SWE-Lego-Style `turn_mask` for Multi-Turn SFT

This patch adds message-level assistant turn masking for ShareGPT-style supervised fine-tuning data.

## Behavior

Set `turn_mask: true` in the training data arguments to enable the feature. When enabled, each assistant message may include:

```json
{"from": "gpt", "value": "assistant text", "turn_mask": true}
```

`turn_mask: true` means the assistant turn remains in `input_ids` as context, but every token in that assistant response is labeled `-100` (`IGNORE_INDEX`) and does not contribute to loss.

`turn_mask: false` means the assistant turn is trainable under the normal LLaMA-Factory SFT rules. If `turn_mask` is missing, it defaults to `false`. This default is intentional for backward compatibility with existing ShareGPT datasets.

User, system, and observation/tool-response messages remain prompt/context messages and are masked by the existing preprocessing logic.

## Modified Files

- `src/llamafactory/hparams/data_args.py`: adds the `turn_mask` data argument.
- `src/llamafactory/data/parser.py`: adds a configurable ShareGPT message tag, `turn_mask_tag`, defaulting to `turn_mask`.
- `src/llamafactory/data/converter.py`: preserves per-assistant message masks as `_turn_mask` during dataset alignment.
- `src/llamafactory/data/processor/supervised.py`: masks target labels for assistant turns whose `_turn_mask` entry is true.
- `data/dataset_info.json`: adds the local `turn_mask_tiny` debug dataset.
- `data/gen_retry_debug/turn_mask_tiny.jsonl`: tiny ShareGPT fixture.
- `scripts/debug_check_turn_mask.py`: preprocessing verification script.
- `examples/train_lora/qwen_gen_retry_turn_mask_debug.yaml`: minimal debug training YAML with `turn_mask: true`.

## Training YAML

Add the following data argument to an SFT config:

```yaml
turn_mask: true
```

Example:

```yaml
dataset: turn_mask_tiny
template: qwen3_nothink
turn_mask: true
```

When `turn_mask: false` or omitted, supervised preprocessing follows the original behavior.

## Tiny Test

Run:

```bash
python scripts/debug_check_turn_mask.py
```

Expected result:

```text
PASS turn_mask preprocessing check
```

The script verifies that:

- `BAD_ACTION_SHOULD_NOT_BE_LEARNED` appears in `input_ids` and has only `-100` labels.
- `GOOD_RECOVERY_ACTION_SHOULD_BE_LEARNED` appears in `input_ids` and has trainable labels.
