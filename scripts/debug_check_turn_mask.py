#!/usr/bin/env python
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace

from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from transformers import PreTrainedTokenizerFast, Seq2SeqTrainingArguments


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

# Importing llamafactory.data also imports collators. This preprocessing-only check
# does not instantiate collators, so avoid requiring peft in minimal debug envs.
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
from llamafactory.extras.constants import IGNORE_INDEX  # noqa: E402


BAD_TEXT = "BAD_ACTION_SHOULD_NOT_BE_LEARNED"
GOOD_TEXT = "GOOD_RECOVERY_ACTION_SHOULD_BE_LEARNED"


def build_debug_tokenizer() -> PreTrainedTokenizerFast:
    vocab = {
        "[UNK]": 0,
        "<|endoftext|>": 1,
        "State": 2,
        "0": 3,
        "1": 4,
        "with": 5,
        "regression": 6,
        BAD_TEXT: 7,
        GOOD_TEXT: 8,
    }
    tokenizer_object = Tokenizer(WordLevel(vocab=vocab, unk_token="[UNK]"))
    tokenizer_object.pre_tokenizer = Whitespace()
    return PreTrainedTokenizerFast(
        tokenizer_object=tokenizer_object,
        unk_token="[UNK]",
        eos_token="<|endoftext|>",
        pad_token="<|endoftext|>",
    )


def find_span(sequence: list[int], subsequence: list[int]) -> tuple[int, int]:
    for start in range(len(sequence) - len(subsequence) + 1):
        end = start + len(subsequence)
        if sequence[start:end] == subsequence:
            return start, end

    raise ValueError(f"Could not find token span: {subsequence}")


def fail(message: str) -> int:
    print(f"FAIL {message}")
    return 1


def main() -> int:
    tokenizer = build_debug_tokenizer()
    data_args = SimpleNamespace(
        dataset=["turn_mask_tiny"],
        eval_dataset=None,
        dataset_dir=str(REPO_ROOT / "data"),
        media_dir=str(REPO_ROOT / "data"),
        template="empty",
        cutoff_len=128,
        train_on_prompt=False,
        mask_history=False,
        streaming=False,
        buffer_size=16384,
        mix_strategy="concat",
        interleave_probs=None,
        max_samples=None,
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
    template = get_template_and_fix_tokenizer(tokenizer, data_args)
    model_args = SimpleNamespace(cache_dir=None, hf_hub_token=None, ms_hub_token=None, om_hub_token=None)

    with tempfile.TemporaryDirectory() as output_dir:
        training_args = Seq2SeqTrainingArguments(
            output_dir=output_dir,
            do_train=True,
            per_device_train_batch_size=1,
            logging_strategy="no",
            report_to="none",
        )
        dataset_module = get_dataset(
            template=template,
            model_args=model_args,
            data_args=data_args,
            training_args=training_args,
            stage="sft",
            tokenizer=tokenizer,
            processor=None,
        )

    train_dataset = dataset_module["train_dataset"]
    if train_dataset is None or len(train_dataset) != 1:
        return fail("expected exactly one preprocessed train example")

    example = train_dataset[0]
    input_ids = example["input_ids"]
    labels = example["labels"]
    decoded = tokenizer.decode(input_ids, skip_special_tokens=False)

    if BAD_TEXT not in decoded:
        return fail(f"{BAD_TEXT} missing from decoded input_ids")
    if GOOD_TEXT not in decoded:
        return fail(f"{GOOD_TEXT} missing from decoded input_ids")

    bad_ids = tokenizer.encode(BAD_TEXT, add_special_tokens=False)
    good_ids = tokenizer.encode(GOOD_TEXT, add_special_tokens=False)
    bad_start, bad_end = find_span(input_ids, bad_ids)
    good_start, good_end = find_span(input_ids, good_ids)

    bad_labels = labels[bad_start:bad_end]
    good_labels = labels[good_start:good_end]
    if any(label != IGNORE_INDEX for label in bad_labels):
        return fail(f"{BAD_TEXT} has trainable labels: {bad_labels}")
    if any(label == IGNORE_INDEX for label in good_labels):
        return fail(f"{GOOD_TEXT} has masked labels: {good_labels}")
    if good_labels != input_ids[good_start:good_end]:
        return fail(f"{GOOD_TEXT} labels do not match input ids: {good_labels}")

    state_id = tokenizer.encode("State", add_special_tokens=False)[0]
    for index, token_id in enumerate(input_ids):
        if token_id == state_id and labels[index] != IGNORE_INDEX:
            return fail("user prompt token has a trainable label")

    print("PASS turn_mask preprocessing check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
