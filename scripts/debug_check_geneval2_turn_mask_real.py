#!/usr/bin/env python
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace

from transformers import AutoProcessor, AutoTokenizer, Seq2SeqTrainingArguments


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    import peft  # noqa: F401
except ModuleNotFoundError:
    peft_stub = types.ModuleType("peft")
    peft_stub.PeftModel = object
    sys.modules["peft"] = peft_stub
    peft_utils_stub = types.ModuleType("peft.utils")
    peft_utils_stub.SAFETENSORS_WEIGHTS_NAME = "adapter_model.safetensors"
    peft_utils_stub.WEIGHTS_NAME = "adapter_model.bin"
    sys.modules["peft.utils"] = peft_utils_stub

from llamafactory.data import get_dataset, get_template_and_fix_tokenizer  # noqa: E402
from llamafactory.data.processor.processor_utils import infer_seqlen  # noqa: E402
from llamafactory.extras.constants import IGNORE_INDEX  # noqa: E402


MODEL_PATH = os.getenv("GENEVAL2_MODEL_PATH", "/home/develop/biocloudplantform/xxr/models/Qwen3-VL-8B-Instruct")
TEMPLATE = os.getenv("GENEVAL2_TEMPLATE", "qwen3_vl_nothink")
DATASET_NAME = "geneval2_retry_masked_multiturn_sft_train"
DATA_PATH = REPO_ROOT / "data/llamafactory/geneval2_retry_masked_multiturn_sft_train.jsonl"
REPORT_PATH = REPO_ROOT / "data/llamafactory/geneval2_retry_turn_mask_real_check.md"
CUTOFF_LEN = int(os.getenv("GENEVAL2_CHECK_CUTOFF_LEN", "32768"))

POSITIVE_TAGS = {"branch_best_so_far_recovery", "positive_retry_passed", "improved_no_regression", "stop_passed"}
RISKY_TAGS = {"risky_retry_regressed", "risky_large_drop"}


def data_args(max_samples: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        dataset=[DATASET_NAME],
        eval_dataset=None,
        dataset_dir=str(REPO_ROOT / "data"),
        media_dir=str(REPO_ROOT / "data"),
        template=TEMPLATE,
        cutoff_len=CUTOFF_LEN,
        train_on_prompt=False,
        mask_history=False,
        streaming=False,
        buffer_size=16384,
        mix_strategy="concat",
        interleave_probs=None,
        max_samples=max_samples,
        val_size=0.0,
        eval_on_each_dataset=False,
        packing=False,
        neat_packing=False,
        tokenized_path=None,
        data_shared_file_system=False,
        tool_format=None,
        default_system=None,
        enable_thinking=True,
        preserve_thinking=False,
        preprocessing_batch_size=1,
        preprocessing_num_workers=None,
        overwrite_cache=True,
        turn_mask=True,
    )


def read_rows() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def has_trajectory_tag(row: dict, tag: str) -> bool:
    return row.get("trajectory_group") == tag or tag in set(row.get("trajectory_tags") or [])


def has_action_tag(row: dict, tag: str) -> bool:
    for item in row.get("assistant_turn_tags") or []:
        if tag in set(item.get("action_tags") or []):
            return True

    return False


def select_indices(rows: list[dict]) -> list[int]:
    selected: list[int] = []

    def add(predicate, limit: int) -> None:
        for index, row in enumerate(rows):
            if len([i for i in selected if predicate(rows[i])]) >= limit:
                break
            if index not in selected and predicate(row):
                selected.append(index)

    add(lambda row: has_trajectory_tag(row, "monotonic_success"), 3)
    add(lambda row: has_trajectory_tag(row, "non_monotonic_recovery_success"), 3)
    add(lambda row: has_trajectory_tag(row, "high_score_unresolved"), 2)
    add(lambda row: has_trajectory_tag(row, "narrow_failure_unresolved"), 2)
    for tag in ["risky_retry_regressed", "risky_large_drop", *sorted(POSITIVE_TAGS)]:
        add(lambda row, tag=tag: has_action_tag(row, tag), 1)

    for index in range(len(rows)):
        if len(selected) >= 10:
            break
        if index not in selected:
            selected.append(index)

    return selected


def align_messages(row: dict) -> tuple[list[dict[str, str]], str, list[dict], list[bool]]:
    messages = row["messages"]
    if messages and messages[0]["from"] == "system":
        system = messages[0]["value"]
        messages = messages[1:]
    else:
        system = ""

    role_map = {"human": "user", "gpt": "assistant"}
    aligned = [{"role": role_map[msg["from"]], "content": msg["value"]} for msg in messages]
    assistant_messages = [msg for msg in messages if msg["from"] == "gpt"]
    turn_masks = [bool(msg.get("turn_mask", False)) for msg in assistant_messages]
    return aligned, system, assistant_messages, turn_masks


def load_processed_dataset(tokenizer, processor):
    args = data_args()
    template = get_template_and_fix_tokenizer(tokenizer, args)
    model_args = SimpleNamespace(cache_dir=None, hf_hub_token=None, ms_hub_token=None, om_hub_token=None)
    with tempfile.TemporaryDirectory() as output_dir:
        training_args = Seq2SeqTrainingArguments(
            output_dir=output_dir,
            do_train=True,
            logging_strategy="no",
            report_to="none",
            disable_tqdm=True,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            dataset_module = get_dataset(
                template=template,
                model_args=model_args,
                data_args=args,
                training_args=training_args,
                stage="sft",
                tokenizer=tokenizer,
                processor=processor,
            )

    return template, dataset_module["train_dataset"]


def validate_sample(row: dict, processed: dict, template, tokenizer, processor) -> tuple[list[str], dict]:
    failures: list[str] = []
    stats = {"masked": 0, "trainable": 0, "risky": 0, "positive": 0}
    input_ids = processed["input_ids"]
    labels = processed["labels"]
    aligned, system, assistant_messages, turn_masks = align_messages(row)
    turn_tags = row.get("assistant_turn_tags") or []

    if len(assistant_messages) != len(turn_tags):
        failures.append(f"assistant message/tag count mismatch: {len(assistant_messages)} vs {len(turn_tags)}")

    messages = template.mm_plugin.process_messages(aligned, [], [], [], processor)
    encoded_pairs = template.encode_multiturn(tokenizer, messages, system, "", False)
    turn_masks = turn_masks[: len(encoded_pairs)] + [False] * max(0, len(encoded_pairs) - len(turn_masks))

    cursor = 0
    total_length = 0
    for turn_idx, (source_ids, target_ids) in enumerate(encoded_pairs):
        if total_length >= CUTOFF_LEN:
            failures.append(f"turn {turn_idx}: sequence stopped before assistant target")
            continue

        source_len, target_len = infer_seqlen(len(source_ids), len(target_ids), CUTOFF_LEN - total_length)
        source_part = source_ids[:source_len]
        target_part = target_ids[:target_len]
        source_span = slice(cursor, cursor + source_len)
        target_span = slice(cursor + source_len, cursor + source_len + target_len)

        if input_ids[source_span] != source_part:
            failures.append(f"turn {turn_idx}: source span mismatch")
        if input_ids[target_span] != target_part:
            failures.append(f"turn {turn_idx}: assistant target span missing from input_ids")
        if any(label != IGNORE_INDEX for label in labels[source_span]):
            failures.append(f"turn {turn_idx}: user/system source span has trainable labels")
        if target_len < len(target_ids):
            failures.append(f"turn {turn_idx}: assistant target JSON is partially truncated")

        try:
            json.loads(assistant_messages[turn_idx]["value"])
        except Exception as exc:
            failures.append(f"turn {turn_idx}: raw assistant target is invalid JSON: {exc}")

        target_labels = labels[target_span]
        is_masked = bool(turn_masks[turn_idx])
        action_tags = set(turn_tags[turn_idx].get("action_tags") or []) if turn_idx < len(turn_tags) else set()

        if is_masked:
            stats["masked"] += 1
            if any(label != IGNORE_INDEX for label in target_labels):
                failures.append(f"turn {turn_idx}: turn_mask=true target has trainable labels")
        else:
            stats["trainable"] += 1
            if target_labels != target_part:
                failures.append(f"turn {turn_idx}: turn_mask=false target is not fully trainable")

        if action_tags & RISKY_TAGS:
            stats["risky"] += 1
            if any(label != IGNORE_INDEX for label in target_labels):
                failures.append(f"turn {turn_idx}: risky action is trainable: {sorted(action_tags & RISKY_TAGS)}")
        if action_tags & POSITIVE_TAGS:
            stats["positive"] += 1
            if target_labels != target_part:
                failures.append(
                    f"turn {turn_idx}: positive/recovery action is not trainable: "
                    f"{sorted(action_tags & POSITIVE_TAGS)}"
                )

        cursor += source_len + target_len
        total_length += source_len + target_len

    if cursor != len(input_ids):
        failures.append(f"reconstructed length {cursor} != processed input length {len(input_ids)}")

    return failures, stats


def main() -> int:
    rows = read_rows()
    selected = select_indices(rows)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
    template, train_dataset = load_processed_dataset(tokenizer, processor)

    failures: list[str] = []
    sample_stats = []
    if len(train_dataset) != len(rows):
        failures.append(f"processed dataset length {len(train_dataset)} != raw row count {len(rows)}")

    for index in selected:
        sample_failures, stats = validate_sample(rows[index], train_dataset[index], template, tokenizer, processor)
        sample_stats.append((index, rows[index], stats, sample_failures))
        failures.extend([f"{rows[index]['trajectory_id']}: {failure}" for failure in sample_failures])

    inspected_tags = {
        "monotonic_success": sum(has_trajectory_tag(rows[i], "monotonic_success") for i in selected),
        "non_monotonic_recovery_success": sum(
            has_trajectory_tag(rows[i], "non_monotonic_recovery_success") for i in selected
        ),
        "high_score_or_narrow_unresolved": sum(
            has_trajectory_tag(rows[i], "high_score_unresolved")
            or has_trajectory_tag(rows[i], "narrow_failure_unresolved")
            for i in selected
        ),
    }
    if len(selected) < 10:
        failures.append(f"selected only {len(selected)} samples")
    if inspected_tags["monotonic_success"] < 3:
        failures.append("selected fewer than 3 monotonic_success trajectories")
    if inspected_tags["non_monotonic_recovery_success"] < 3:
        failures.append("selected fewer than 3 non_monotonic_recovery_success trajectories")
    if inspected_tags["high_score_or_narrow_unresolved"] < 2:
        failures.append("selected fewer than 2 high_score/narrow unresolved trajectories")

    lines = [
        "# GenEval2 Real Turn Mask Check",
        "",
        f"- Dataset: `{DATASET_NAME}`",
        f"- Model/tokenizer: `{MODEL_PATH}`",
        f"- Template: `{TEMPLATE}`",
        f"- Cutoff length: `{CUTOFF_LEN}`",
        f"- Raw rows: `{len(rows)}`",
        f"- Processed rows: `{len(train_dataset)}`",
        f"- Inspected samples: `{len(selected)}`",
        f"- Selection coverage: `{inspected_tags}`",
        "",
        "## Inspected Samples",
        "",
    ]
    for index, row, stats, sample_failures in sample_stats:
        status = "PASS" if not sample_failures else "FAIL"
        lines.append(
            f"- `{status}` row={index} trajectory_id=`{row['trajectory_id']}` "
            f"group=`{row.get('trajectory_group')}` tags=`{row.get('trajectory_tags')}` stats=`{stats}`"
        )
        for failure in sample_failures:
            lines.append(f"  - {failure}")

    lines.extend(["", "## Result", "", "PASS" if not failures else "FAIL"])
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in failures)

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS" if not failures else "FAIL")
    print(f"Report: {REPORT_PATH}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
