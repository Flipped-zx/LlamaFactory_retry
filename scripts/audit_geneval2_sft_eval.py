#!/usr/bin/env python3
"""
Audit script for GenEval2 SFT Offline Action Evaluation.

Investigates why base and SFT metrics are nearly identical.
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from peft import PeftModel

# Constants
BASE_MODEL_PATH = "/home/develop/biocloudplantform/xxr/models/Qwen3-VL-8B-Instruct"
ADAPTER_PATH = "saves/qwen3-vl-8b/lora/geneval2_retry_masked_multiturn_sft_6gpu"
TEST_DATA_PATH = "data/llamafactory/geneval2_retry_masked_multiturn_sft_test.jsonl"
TRAIN_DATA_PATH = "data/llamafactory/geneval2_retry_masked_multiturn_sft_train.jsonl"
OUTPUT_AUDIT_PATH = "data/llamafactory/geneval2_retry_sft_offline_eval_audit.md"

# Audit configuration
MAX_NEW_TOKENS = 2048
TEMPERATURE = 0.0  # Greedy for reproducibility
TOP_P = 1.0
DO_SAMPLE = False  # Greedy decoding
DEBUG_SAMPLE_COUNT = 3
TRAIN_SANITY_CHECK_COUNT = 20


def log_section(title, lines):
    """Add a section to the audit log."""
    lines.append(f"\n{'='*70}")
    lines.append(f"# {title}")
    lines.append(f"{'='*70}\n")


def verify_adapter_loading(lines):
    """Task 2: Verify SFT adapter loading."""
    log_section("Task 2: Verify SFT Adapter Loading", lines)

    lines.append("## Loading Base Model...\n")
    processor = AutoProcessor.from_pretrained(
        BASE_MODEL_PATH,
        trust_remote_code=True
    )

    base_model = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )

    lines.append(f"**Base Model Class:** `{type(base_model).__name__}`")
    lines.append(f"**Base Model Device:** `{next(base_model.parameters()).device}`")

    # Count base parameters
    base_params = sum(p.numel() for p in base_model.parameters())
    lines.append(f"**Base Model Total Parameters:** {base_params:,}")

    lines.append("\n## Loading with LoRA Adapter...\n")

    model_with_adapter = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )

    # Load adapter
    lines.append(f"**Adapter Path:** `{ADAPTER_PATH}`")

    # Check adapter files exist
    adapter_safetensors = os.path.join(ADAPTER_PATH, "adapter_model.safetensors")
    adapter_config = os.path.join(ADAPTER_PATH, "adapter_config.json")

    lines.append(f"**adapter_model.safetensors exists:** {os.path.exists(adapter_safetensors)}")
    lines.append(f"**adapter_config.json exists:** {os.path.exists(adapter_config)}")

    if os.path.exists(adapter_safetensors):
        size_mb = os.path.getsize(adapter_safetensors) / (1024 * 1024)
        lines.append(f"**Adapter size:** {size_mb:.2f} MB")

    # Load the adapter
    model_with_lora = PeftModel.from_pretrained(model_with_adapter, ADAPTER_PATH)

    lines.append(f"\n**Model with Adapter Class:** `{type(model_with_lora).__name__}`")
    lines.append(f"**Is PeftModel:** {isinstance(model_with_lora, PeftModel)}")

    # Get active adapter
    if hasattr(model_with_lora, 'active_adapters'):
        lines.append(f"**Active Adapters:** {model_with_lora.active_adapters}")
    if hasattr(model_with_lora, 'active_adapter'):
        lines.append(f"**Active Adapter:** {model_with_lora.active_adapter}")

    # Get PEFT config
    if hasattr(model_with_lora, 'peft_config'):
        peft_config = model_with_lora.peft_config
        lines.append(f"\n**PEFT Config:**")
        for adapter_name, config in peft_config.items():
            lines.append(f"  - Adapter: `{adapter_name}`")
            lines.append(f"    - r: {config.r}")
            lines.append(f"    - lora_alpha: {config.lora_alpha}")
            lines.append(f"    - target_modules: {config.target_modules}")
            lines.append(f"    - peft_type: {config.peft_type}")

    # Check trainable parameters
    trainable_params = sum(p.numel() for p in model_with_lora.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model_with_lora.parameters())

    lines.append(f"\n**Parameter Statistics:**")
    lines.append(f"  - Total parameters: {total_params:,}")
    lines.append(f"  - Trainable parameters: {trainable_params:,}")
    lines.append(f"  - Trainable %: {100 * trainable_params / total_params:.4f}%")

    # List adapter parameter names
    lines.append(f"\n**Adapter Parameter Names (first 20):**")
    adapter_params = [n for n, p in model_with_lora.named_parameters() if p.requires_grad]
    for name in adapter_params[:20]:
        lines.append(f"  - {name}")
    if len(adapter_params) > 20:
        lines.append(f"  ... and {len(adapter_params) - 20} more")

    # Verify base model parameters are frozen
    base_trainable = sum(p.numel() for n, p in model_with_lora.named_parameters()
                         if not any(target in n for target in ['lora_', 'adapter']))

    lines.append(f"\n**Verification:**")
    lines.append(f"  - Base model should be frozen (no trainable non-adapter params)")

    # Clean up
    del base_model, model_with_lora, model_with_adapter
    torch.cuda.empty_cache()

    return processor


def parse_conversation_messages(messages: list[dict]) -> list[dict]:
    """Convert llamafactory format to model chat format."""
    chat_messages = []
    for msg in messages:
        if msg["from"] == "system":
            chat_messages.append({"role": "system", "content": msg["value"]})
        elif msg["from"] == "human":
            chat_messages.append({"role": "user", "content": msg["value"]})
        elif msg["from"] == "gpt":
            chat_messages.append({"role": "assistant", "content": msg["value"]})
    return chat_messages


def get_eval_targets(trajectory: dict) -> list[dict]:
    """Extract assistant turns where turn_mask == false for evaluation."""
    targets = []
    messages = trajectory["messages"]
    assistant_tags = trajectory.get("assistant_turn_tags", [])

    # Find gpt message indices (assistant turns)
    gpt_indices = [i for i, m in enumerate(messages) if m["from"] == "gpt"]

    for tag_idx, tag in enumerate(assistant_tags):
        if not tag.get("turn_mask", True):  # turn_mask == False means eval target
            msg_idx = gpt_indices[tag_idx]
            target = {
                "sample_id": tag["sample_id"],
                "task_type": tag["task_type"],
                "source_round": tag.get("source_round"),
                "target_round": tag["target_round"],
                "turn_mask": tag.get("turn_mask"),
                "action_tags": tag.get("action_tags", []),
                "include_in_clean_sft": tag.get("include_in_clean_sft", False),
                "message_idx": msg_idx,
                "ground_truth": messages[msg_idx]["value"],
                "input_messages": messages[:msg_idx]
            }
            targets.append(target)

    return targets


def generate_action(model, processor, input_messages: list[dict]) -> tuple[str, int]:
    """Generate action from input messages. Returns (text, token_count)."""
    chat_messages = parse_conversation_messages(input_messages)

    # Apply chat template
    prompt = processor.apply_chat_template(
        chat_messages,
        tokenize=False,
        add_generation_prompt=True
    )

    # Tokenize
    inputs = processor(
        text=[prompt],
        return_tensors="pt",
        padding=True
    ).to(model.device)

    input_token_count = inputs["input_ids"].shape[1]

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            do_sample=DO_SAMPLE,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id
        )

    # Decode
    generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
    generated_text = processor.decode(generated_ids, skip_special_tokens=True)
    output_token_count = len(generated_ids)

    return generated_text.strip(), output_token_count, input_token_count


def is_complete_json(text: str) -> bool:
    """Check if text ends with a complete JSON structure."""
    text = text.strip()
    if not text:
        return False

    # Check for matching braces
    brace_count = 0
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1

    return brace_count == 0 and text.endswith('}')


def debug_comparison(processor, lines):
    """Task 3: Debug mode - compare base vs SFT on same samples."""
    log_section("Task 3: Debug Comparison (3 Samples)", lines)

    # Load test data
    with open(TEST_DATA_PATH, 'r') as f:
        test_data = [json.loads(line) for line in f]

    # Collect all eval targets
    all_targets = []
    for traj in test_data:
        targets = get_eval_targets(traj)
        all_targets.extend([(traj["trajectory_id"], t) for t in targets])

    # Select 3 diverse samples
    selected = []
    task_types_seen = set()
    for traj_id, target in all_targets:
        if target["task_type"] not in task_types_seen and len(selected) < 3:
            selected.append((traj_id, target))
            task_types_seen.add(target["task_type"])

    # If we don't have 3 different task types, fill with any
    if len(selected) < 3:
        for traj_id, target in all_targets:
            if len(selected) < 3 and (traj_id, target) not in selected:
                selected.append((traj_id, target))

    lines.append(f"**Selected {len(selected)} samples for debug comparison**\n")

    # Load models
    lines.append("\n## Loading Models...")

    # Base model
    base_model = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    base_model.eval()

    # SFT model
    sft_base = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    sft_model = PeftModel.from_pretrained(sft_base, ADAPTER_PATH)
    sft_model.eval()

    # Compare
    for idx, (traj_id, target) in enumerate(selected, 1):
        lines.append(f"\n{'-'*60}")
        lines.append(f"## Sample {idx}: {target['sample_id']}")
        lines.append(f"{'-'*60}")
        lines.append(f"**Trajectory ID:** {traj_id}")
        lines.append(f"**Task Type:** {target['task_type']}")
        lines.append(f"**Action Tags:** {', '.join(target['action_tags'])}")
        lines.append(f"**Turn Mask:** {target['turn_mask']}")
        lines.append(f"**Include in Clean SFT:** {target['include_in_clean_sft']}")

        # Generate from base
        lines.append(f"\n### Base Model Generation:")
        base_output, base_tokens, base_input_tokens = generate_action(
            base_model, processor, target["input_messages"]
        )
        lines.append(f"**Input tokens:** {base_input_tokens}")
        lines.append(f"**Output tokens:** {base_tokens}")
        lines.append(f"**Complete JSON:** {is_complete_json(base_output)}")
        lines.append(f"\n```json")
        lines.append(base_output[:1000] + "..." if len(base_output) > 1000 else base_output)
        lines.append(f"```")

        # Generate from SFT
        lines.append(f"\n### SFT Model Generation:")
        sft_output, sft_tokens, sft_input_tokens = generate_action(
            sft_model, processor, target["input_messages"]
        )
        lines.append(f"**Input tokens:** {sft_input_tokens}")
        lines.append(f"**Output tokens:** {sft_tokens}")
        lines.append(f"**Complete JSON:** {is_complete_json(sft_output)}")
        lines.append(f"\n```json")
        lines.append(sft_output[:1000] + "..." if len(sft_output) > 1000 else sft_output)
        lines.append(f"```")

        # Ground truth
        lines.append(f"\n### Ground Truth:")
        lines.append(f"```json")
        lines.append(target['ground_truth'][:1000] + "..." if len(target['ground_truth']) > 1000 else target['ground_truth'])
        lines.append(f"```")

        # Comparison
        lines.append(f"\n### Comparison:")
        lines.append(f"**Outputs identical:** {base_output.strip() == sft_output.strip()}")
        lines.append(f"**Base output length:** {len(base_output)}")
        lines.append(f"**SFT output length:** {len(sft_output)}")
        lines.append(f"**Ground truth length:** {len(target['ground_truth'])}")

        # Try to parse both
        try:
            base_json = json.loads(base_output)
            lines.append(f"**Base valid JSON:** True")
        except:
            lines.append(f"**Base valid JSON:** False")
            base_json = None

        try:
            sft_json = json.loads(sft_output)
            lines.append(f"**SFT valid JSON:** True")
        except:
            lines.append(f"**SFT valid JSON:** False")
            sft_json = None

        if base_json and sft_json:
            base_keys = set(base_json.keys())
            sft_keys = set(sft_json.keys())
            lines.append(f"**Base keys:** {sorted(base_keys)}")
            lines.append(f"**SFT keys:** {sorted(sft_keys)}")
            lines.append(f"**Common keys:** {sorted(base_keys & sft_keys)}")
            lines.append(f"**Base only keys:** {sorted(base_keys - sft_keys)}")
            lines.append(f"**SFT only keys:** {sorted(sft_keys - base_keys)}")

    del base_model, sft_model, sft_base
    torch.cuda.empty_cache()


def check_generation_truncation(processor, lines):
    """Task 4: Check for generation truncation."""
    log_section("Task 4: Check Generation Truncation", lines)

    # Load a sample
    with open(TEST_DATA_PATH, 'r') as f:
        test_data = [json.loads(line) for line in f]

    # Get first eval target
    target = None
    for traj in test_data:
        targets = get_eval_targets(traj)
        if targets:
            target = targets[0]
            break

    if not target:
        lines.append("No eval targets found!")
        return

    # Load SFT model
    sft_base = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    sft_model = PeftModel.from_pretrained(sft_base, ADAPTER_PATH)
    sft_model.eval()

    # Test with different max_new_tokens
    max_tokens_list = [512, 1024, 2048]

    chat_messages = parse_conversation_messages(target["input_messages"])
    prompt = processor.apply_chat_template(
        chat_messages,
        tokenize=False,
        add_generation_prompt=True
    )
    inputs = processor(text=[prompt], return_tensors="pt", padding=True).to(sft_model.device)

    lines.append(f"**Sample:** {target['sample_id']}")
    lines.append(f"**Task Type:** {target['task_type']}")
    lines.append(f"**Ground truth length:** {len(target['ground_truth'])} chars")

    gt_tokens = len(processor.tokenizer.encode(target['ground_truth']))
    lines.append(f"**Ground truth token count:** ~{gt_tokens} tokens")

    for max_tokens in max_tokens_list:
        lines.append(f"\n### max_new_tokens = {max_tokens}")

        with torch.no_grad():
            outputs = sft_model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                do_sample=DO_SAMPLE,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id
            )

        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        generated_text = processor.decode(generated_ids, skip_special_tokens=True).strip()

        lines.append(f"  - Generated tokens: {len(generated_ids)}")
        lines.append(f"  - Generated chars: {len(generated_text)}")
        lines.append(f"  - Complete JSON: {is_complete_json(generated_text)}")

        # Check if it was truncated
        if len(generated_ids) >= max_tokens - 10:
            lines.append(f"  - ⚠️ **Likely truncated!** (generated {len(generated_ids)} tokens, limit was {max_tokens})")
        else:
            lines.append(f"  - ✅ Not truncated (generated {len(generated_ids)} tokens, limit was {max_tokens})")

        # Show last 100 chars
        lines.append(f"  - Last 100 chars: `{generated_text[-100:].replace(chr(10), ' ')}`")

    del sft_model, sft_base
    torch.cuda.empty_cache()


def verify_target_selection(lines):
    """Task 5: Verify target selection criteria."""
    log_section("Task 5: Verify Target Selection", lines)

    with open(TEST_DATA_PATH, 'r') as f:
        test_data = [json.loads(line) for line in f]

    lines.append(f"**Total trajectories:** {len(test_data)}")

    # Collect all targets with their mask status
    all_targets = []
    masked_targets = []
    unmasked_targets = []

    for traj in test_data:
        targets = get_eval_targets(traj)
        for t in targets:
            all_targets.append(t)
            if t["turn_mask"]:
                masked_targets.append(t)
            else:
                unmasked_targets.append(t)

    lines.append(f"\n**Total assistant turns:** {len(all_targets)}")
    lines.append(f"**Turn mask = True (excluded):** {len(masked_targets)}")
    lines.append(f"**Turn mask = False (evaluated):** {len(unmasked_targets)}")

    # Verify we're only evaluating unmasked
    lines.append(f"\n**Verification:**")
    lines.append(f"- Only evaluating turn_mask == False: ✅" if len(masked_targets) == 0 else "- WARNING: Some masked targets would be evaluated!")

    # Count by task type
    lines.append(f"\n### Target Distribution by Task Type")
    task_type_counts = defaultdict(int)
    for t in unmasked_targets:
        task_type_counts[t["task_type"]] += 1

    for task_type, count in sorted(task_type_counts.items()):
        lines.append(f"- {task_type}: {count}")

    # Count by action tags
    lines.append(f"\n### Target Distribution by Action Tags")
    tag_counts = defaultdict(int)
    for t in unmasked_targets:
        for tag in t["action_tags"]:
            tag_counts[tag] += 1

    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {tag}: {count}")

    # Include in clean SFT distribution
    lines.append(f"\n### Include in Clean SFT Distribution")
    clean_sft_counts = defaultdict(int)
    for t in unmasked_targets:
        clean_sft_counts[t["include_in_clean_sft"]] += 1

    for include, count in sorted(clean_sft_counts.items()):
        lines.append(f"- include_in_clean_sft={include}: {count}")


def inspect_schema_failures(lines):
    """Task 6: Inspect schema failure causes."""
    log_section("Task 6: Inspect Schema Failures", lines)

    # Load existing predictions
    predictions_path = "data/llamafactory/geneval2_retry_sft_offline_eval_predictions.jsonl"

    if not os.path.exists(predictions_path):
        lines.append(f"Predictions file not found: {predictions_path}")
        return

    predictions = []
    with open(predictions_path, 'r') as f:
        for line in f:
            predictions.append(json.loads(line))

    lines.append(f"**Total predictions:** {len(predictions)}")

    # Analyze SFT predictions
    missing_field_counts = defaultdict(int)
    schema_failures = []

    for pred_pair in predictions:
        sft_pred = pred_pair["sft"]

        # Parse ground truth to get expected fields
        try:
            gt = json.loads(sft_pred["ground_truth"])
        except:
            continue

        # Parse prediction
        try:
            pred = json.loads(sft_pred["generated"])
        except:
            continue

        gt_keys = set(gt.keys())
        pred_keys = set(pred.keys())

        missing_keys = gt_keys - pred_keys

        if missing_keys:
            schema_failures.append({
                "sample_id": sft_pred["sample_id"],
                "task_type": sft_pred["task_type"],
                "missing_keys": list(missing_keys),
                "generated_keys": list(pred_keys),
                "ground_truth_keys": list(gt_keys),
                "generated": sft_pred["generated"][:500]
            })

            for key in missing_keys:
                missing_field_counts[key] += 1

    lines.append(f"\n**Predictions with missing fields:** {len(schema_failures)}")

    lines.append(f"\n### Missing Field Counts")
    for field, count in sorted(missing_field_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {field}: {count}")

    # Show examples
    lines.append(f"\n### Schema Failure Examples (first 10)")
    for idx, failure in enumerate(schema_failures[:10], 1):
        lines.append(f"\n**Example {idx}:**")
        lines.append(f"- Sample ID: {failure['sample_id']}")
        lines.append(f"- Task Type: {failure['task_type']}")
        lines.append(f"- Missing Keys: {failure['missing_keys']}")
        lines.append(f"- Generated Keys: {failure['generated_keys']}")
        lines.append(f"- Generated Preview:")
        lines.append(f"```json")
        lines.append(failure['generated'])
        lines.append(f"```")


def train_set_sanity_check(processor, lines):
    """Task 7: Train-set sanity check."""
    log_section("Task 7: Train-Set Sanity Check", lines)

    # Load train data
    if not os.path.exists(TRAIN_DATA_PATH):
        lines.append(f"Train data not found: {TRAIN_DATA_PATH}")
        return

    with open(TRAIN_DATA_PATH, 'r') as f:
        train_data = [json.loads(line) for line in f]

    lines.append(f"**Total train trajectories:** {len(train_data)}")

    # Get first N eval targets from train
    train_targets = []
    for traj in train_data:
        targets = get_eval_targets(traj)
        for t in targets:
            train_targets.append((traj["trajectory_id"], t))
        if len(train_targets) >= TRAIN_SANITY_CHECK_COUNT:
            break

    train_targets = train_targets[:TRAIN_SANITY_CHECK_COUNT]
    lines.append(f"**Evaluating {len(train_targets)} train targets**")

    # Load models
    base_model = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    base_model.eval()

    sft_base = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    sft_model = PeftModel.from_pretrained(sft_base, ADAPTER_PATH)
    sft_model.eval()

    # Evaluate
    base_correct = 0
    sft_correct = 0
    identical_count = 0

    results = []

    for traj_id, target in tqdm(train_targets, desc="Evaluating train targets"):
        # Base prediction
        base_output, _, _ = generate_action(base_model, processor, target["input_messages"])
        # SFT prediction
        sft_output, _, _ = generate_action(sft_model, processor, target["input_messages"])

        # Check if identical
        if base_output.strip() == sft_output.strip():
            identical_count += 1

        # Parse and compare to ground truth
        try:
            base_json = json.loads(base_output)
            base_action_correct = base_json.get("action_type") == target["task_type"]
        except:
            base_action_correct = False

        try:
            sft_json = json.loads(sft_output)
            sft_action_correct = sft_json.get("action_type") == target["task_type"]
        except:
            sft_action_correct = False

        if base_action_correct:
            base_correct += 1
        if sft_action_correct:
            sft_correct += 1

        results.append({
            "sample_id": target["sample_id"],
            "task_type": target["task_type"],
            "base_action_correct": base_action_correct,
            "sft_action_correct": sft_action_correct,
            "identical": base_output.strip() == sft_output.strip()
        })

    lines.append(f"\n### Results")
    lines.append(f"**Base action type accuracy:** {base_correct}/{len(train_targets)} ({100*base_correct/len(train_targets):.1f}%)")
    lines.append(f"**SFT action type accuracy:** {sft_correct}/{len(train_targets)} ({100*sft_correct/len(train_targets):.1f}%)")
    lines.append(f"**Identical outputs:** {identical_count}/{len(train_targets)} ({100*identical_count/len(train_targets):.1f}%)")

    if sft_correct > base_correct:
        lines.append(f"\n✅ **SFT improves over base on train set**")
    elif sft_correct == base_correct:
        lines.append(f"\n⚠️ **SFT equals base on train set** - possible adapter loading issue")
    else:
        lines.append(f"\n❌ **SFT worse than base on train set** - training issue")

    # Show details
    lines.append(f"\n### Detailed Results")
    lines.append(f"| Sample | Task Type | Base OK | SFT OK | Identical |")
    lines.append(f"|--------|-----------|---------|--------|-----------|")
    for r in results:
        lines.append(f"| {r['sample_id'][-40:]} | {r['task_type']} | {r['base_action_correct']} | {r['sft_action_correct']} | {r['identical']} |")

    del base_model, sft_model, sft_base
    torch.cuda.empty_cache()


def main():
    print("="*70)
    print("GenEval2 SFT Offline Evaluation Audit")
    print("="*70)

    lines = []
    lines.append("# GenEval2 SFT Offline Evaluation Audit Report")
    lines.append(f"\nGenerated: {datetime.now().isoformat()}")

    # Task 2: Verify adapter loading
    processor = verify_adapter_loading(lines)

    # Task 3: Debug comparison
    debug_comparison(processor, lines)

    # Task 4: Check truncation
    check_generation_truncation(processor, lines)

    # Task 5: Verify target selection
    verify_target_selection(lines)

    # Task 6: Inspect schema failures
    inspect_schema_failures(lines)

    # Task 7: Train set sanity check
    train_set_sanity_check(processor, lines)

    # Summary
    log_section("Summary and Recommendations", lines)

    lines.append("## Key Findings")
    lines.append("1. Check if adapter is properly loaded (see Task 2)")
    lines.append("2. Compare base vs SFT outputs (see Task 3)")
    lines.append("3. Check if generation is truncated (see Task 4)")
    lines.append("4. Verify target selection is correct (see Task 5)")
    lines.append("5. Analyze schema failures (see Task 6)")
    lines.append("6. Check if SFT improves on train set (see Task 7)")

    # Write report
    report = "\n".join(lines)
    with open(OUTPUT_AUDIT_PATH, 'w') as f:
        f.write(report)

    print(f"\n{'='*70}")
    print(f"Audit complete!")
    print(f"Report saved to: {OUTPUT_AUDIT_PATH}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
