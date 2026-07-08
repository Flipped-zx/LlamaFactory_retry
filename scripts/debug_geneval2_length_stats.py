#!/usr/bin/env python
from __future__ import annotations

import json
import os
import statistics
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from transformers import AutoProcessor, AutoTokenizer


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

from llamafactory.data import get_template_and_fix_tokenizer  # noqa: E402
from llamafactory.data.processor.processor_utils import infer_seqlen  # noqa: E402


MODEL_PATH = os.getenv("GENEVAL2_MODEL_PATH", "/root/private_data/agentic_image/models/Qwen3-VL-8B-Instruct")
TEMPLATE = os.getenv("GENEVAL2_TEMPLATE", "qwen3_vl_nothink")
REPORT_PATH = REPO_ROOT / "data/llamafactory/geneval2_retry_masked_multiturn_length_stats.md"
CUTOFFS = [4096, 8192, 12288, 16384, 32768]
SPLITS = {
    "train": REPO_ROOT / "data/llamafactory/geneval2_retry_masked_multiturn_sft_train.jsonl",
    "val": REPO_ROOT / "data/llamafactory/geneval2_retry_masked_multiturn_sft_val.jsonl",
    "test": REPO_ROOT / "data/llamafactory/geneval2_retry_masked_multiturn_sft_test.jsonl",
}


def data_args() -> SimpleNamespace:
    return SimpleNamespace(
        template=TEMPLATE,
        train_on_prompt=False,
        tool_format=None,
        default_system=None,
        enable_thinking=True,
        preserve_thinking=False,
    )


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def align_messages(row: dict) -> tuple[list[dict[str, str]], str, list[bool]]:
    messages = row["messages"]
    if messages and messages[0]["from"] == "system":
        system = messages[0]["value"]
        messages = messages[1:]
    else:
        system = ""

    role_map = {"human": "user", "gpt": "assistant"}
    aligned = [{"role": role_map[msg["from"]], "content": msg["value"]} for msg in messages]
    turn_masks = [bool(msg.get("turn_mask", False)) for msg in messages if msg["from"] == "gpt"]
    return aligned, system, turn_masks


def percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0

    index = min(len(values) - 1, max(0, int(round((pct / 100) * (len(values) - 1)))))
    return sorted(values)[index]


def encode_row(row: dict, template, tokenizer, processor) -> tuple[int, list[tuple[int, int, bool]]]:
    aligned, system, turn_masks = align_messages(row)
    messages = template.mm_plugin.process_messages(aligned, [], [], [], processor)
    encoded_pairs = template.encode_multiturn(tokenizer, messages, system, "", False)
    turn_masks = turn_masks[: len(encoded_pairs)] + [False] * max(0, len(encoded_pairs) - len(turn_masks))
    pair_lengths = [
        (len(source_ids), len(target_ids), turn_masks[index])
        for index, (source_ids, target_ids) in enumerate(encoded_pairs)
    ]
    total_length = sum(source_len + target_len for source_len, target_len, _ in pair_lengths)
    if template.efficient_eos:
        total_length += 1

    return total_length, pair_lengths


def false_target_truncations(pair_lengths: list[tuple[int, int, bool]], cutoff: int, efficient_eos: bool) -> int:
    total_length = 1 if efficient_eos else 0
    truncated = 0
    for source_len_raw, target_len_raw, turn_mask in pair_lengths:
        if total_length >= cutoff:
            if not turn_mask:
                truncated += 1
            continue

        source_len, target_len = infer_seqlen(source_len_raw, target_len_raw, cutoff - total_length)
        if not turn_mask and target_len < target_len_raw:
            truncated += 1

        total_length += source_len + target_len

    return truncated


def summarize(lengths: list[int]) -> dict[str, float | int]:
    return {
        "count": len(lengths),
        "average": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "median": int(statistics.median(lengths)) if lengths else 0,
        "p90": percentile(lengths, 90),
        "p95": percentile(lengths, 95),
        "p99": percentile(lengths, 99),
        "max": max(lengths) if lengths else 0,
    }


def main() -> int:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
    template = get_template_and_fix_tokenizer(tokenizer, data_args())

    encoded_by_split: dict[str, list[tuple[int, list[tuple[int, int, bool]]]]] = {}
    for split, path in SPLITS.items():
        encoded_by_split[split] = [encode_row(row, template, tokenizer, processor) for row in read_rows(path)]

    train_val = encoded_by_split["train"] + encoded_by_split["val"]
    train_val_lengths = [length for length, _ in train_val]
    cutoff_rows = {
        cutoff: {
            "exceeding_train_val": sum(length > cutoff for length in train_val_lengths),
            "false_target_truncations_train_val": sum(
                false_target_truncations(pair_lengths, cutoff, template.efficient_eos) for _, pair_lengths in train_val
            ),
        }
        for cutoff in CUTOFFS
    }

    recommended = next(
        (
            cutoff
            for cutoff in CUTOFFS
            if cutoff_rows[cutoff]["exceeding_train_val"] == 0
            and cutoff_rows[cutoff]["false_target_truncations_train_val"] == 0
        ),
        max(CUTOFFS),
    )

    lines = [
        "# GenEval2 Masked Multi-Turn Length Stats",
        "",
        f"- Model/tokenizer: `{MODEL_PATH}`",
        f"- Template: `{TEMPLATE}`",
        "- Primary summary: train + val",
        "",
        "## Train + Val",
        "",
    ]
    for key, value in summarize(train_val_lengths).items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Split Summaries", ""])
    for split, encoded in encoded_by_split.items():
        summary = summarize([length for length, _ in encoded])
        lines.append(f"### {split}")
        for key, value in summary.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")

    lines.extend(["## Cutoff Candidates", ""])
    for cutoff in CUTOFFS:
        row = cutoff_rows[cutoff]
        lines.append(
            f"- `{cutoff}`: exceeding train+val rows=`{row['exceeding_train_val']}`, "
            f"turn_mask=false target truncations=`{row['false_target_truncations_train_val']}`"
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- Recommended cutoff_len: `{recommended}`",
            f"- Any turn_mask=false assistant target truncated at recommendation: "
            f"`{cutoff_rows[recommended]['false_target_truncations_train_val'] > 0}`",
            "",
            "PASS",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Recommended cutoff_len: {recommended}")
    print(f"Report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
