#!/usr/bin/env python3
"""
Trajectory Case Replay for GenEval2 SFT.

Qualitative comparison of base vs SFT vs teacher on selected trajectories.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from peft import PeftModel

# Constants
BASE_MODEL_PATH = "/home/develop/biocloudplantform/xxr/models/Qwen3-VL-8B-Instruct"
ADAPTER_PATH = "saves/qwen3-vl-8b/lora/geneval2_retry_masked_multiturn_sft_6gpu"
TEST_DATA_PATH = "data/llamafactory/geneval2_retry_masked_multiturn_sft_test.jsonl"
OUTPUT_REPORT_PATH = "data/llamafactory/geneval2_retry_sft_case_replay_report.md"
OUTPUT_PREDICTIONS_PATH = "data/llamafactory/geneval2_retry_sft_case_replay_predictions.jsonl"

MAX_NEW_TOKENS = 2048


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
    """Extract assistant turns where turn_mask == false."""
    targets = []
    messages = trajectory["messages"]
    assistant_tags = trajectory.get("assistant_turn_tags", [])

    # Find gpt message indices (assistant turns)
    gpt_indices = [i for i, m in enumerate(messages) if m["from"] == "gpt"]

    for tag_idx, tag in enumerate(assistant_tags):
        if not tag.get("turn_mask", True):  # turn_mask == False
            msg_idx = gpt_indices[tag_idx]
            target = {
                "sample_id": tag["sample_id"],
                "task_type": tag["task_type"],
                "source_round": tag.get("source_round"),
                "target_round": tag["target_round"],
                "turn_mask": tag.get("turn_mask"),
                "action_tags": tag.get("action_tags", []),
                "message_idx": msg_idx,
                "ground_truth": messages[msg_idx]["value"],
                "input_messages": messages[:msg_idx]
            }
            targets.append(target)

    return targets


def generate_action(model, processor, input_messages: list[dict]) -> str:
    """Generate action from input messages (greedy)."""
    chat_messages = parse_conversation_messages(input_messages)

    prompt = processor.apply_chat_template(
        chat_messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = processor(
        text=[prompt],
        return_tensors="pt",
        padding=True
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,  # Greedy
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id
        )

    generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
    generated_text = processor.decode(generated_ids, skip_special_tokens=True)

    return generated_text.strip()


def parse_json_safe(text: str) -> dict | None:
    """Safely parse JSON."""
    try:
        return json.loads(text)
    except:
        return None


def extract_key_fields(data: dict) -> dict:
    """Extract key fields for comparison."""
    return {
        "action_type": data.get("action_type"),
        "decision": data.get("decision"),
        "branch_source": data.get("branch_source"),
        "repair_constraints": data.get("repair_constraints", []),
        "preserve_constraints": data.get("preserve_constraints", []),
        "regression_risks": data.get("regression_risks", []),
        "retry_prompt": data.get("retry_prompt", "")[:200] if data.get("retry_prompt") else "",
        "has_repair_constraints": "repair_constraints" in data and len(data.get("repair_constraints", [])) > 0,
        "has_preserve_constraints": "preserve_constraints" in data and len(data.get("preserve_constraints", [])) > 0,
    }


def find_representative_trajectories(test_data: list[dict]) -> list[tuple[dict, list[dict]]]:
    """Find 3 representative trajectories."""
    selected = []

    # Look for specific patterns
    found_recovery = False
    found_best_so_far = False
    found_stop_passed = False

    for traj in test_data:
        targets = get_eval_targets(traj)
        tags = set()
        for t in targets:
            tags.update(t["action_tags"])

        # Non-monotonic recovery
        if not found_recovery and any("recovery" in t for t in tags):
            selected.append((traj, targets))
            found_recovery = True
            continue

        # Branch best_so_far
        if not found_best_so_far and "branch_best_so_far" in tags:
            selected.append((traj, targets))
            found_best_so_far = True
            continue

        # Stop passed or ordinary success
        if not found_stop_passed and ("stop_passed" in tags or "positive_retry_passed" in tags):
            selected.append((traj, targets))
            found_stop_passed = True
            continue

        if len(selected) >= 3:
            break

    # Fill with any if not enough
    if len(selected) < 3:
        for traj in test_data:
            if len(selected) >= 3:
                break
            targets = get_eval_targets(traj)
            if targets and (traj, targets) not in selected:
                selected.append((traj, targets))

    return selected[:3]


def generate_report(selected_trajectories: list, processor, base_model, sft_model) -> str:
    """Generate the case replay report."""
    lines = []

    lines.append("# GenEval2 SFT Case Replay Report")
    lines.append(f"\nGenerated: {datetime.now().isoformat()}")
    lines.append("\n> Qualitative comparison of Teacher vs Base Model vs SFT LoRA")
    lines.append("\n---\n")

    all_predictions = []

    for traj_idx, (traj, targets) in enumerate(selected_trajectories, 1):
        traj_id = traj["trajectory_id"]
        prompt_id = traj.get("prompt_id", "unknown")

        lines.append(f"\n# Case {traj_idx}: {traj_id}")
        lines.append(f"\n**Prompt ID:** {prompt_id}")

        # Trajectory structure
        lines.append(f"\n## Trajectory Structure\n")

        # Print turn structure
        messages = traj["messages"]
        assistant_tags = traj.get("assistant_turn_tags", [])
        gpt_indices = [i for i, m in enumerate(messages) if m["from"] == "gpt"]

        lines.append("| Round | Target Action Type | Turn Mask | Action Tags | History Len |")
        lines.append("|-------|-------------------|-----------|-------------|-------------|")

        for tag_idx, tag in enumerate(assistant_tags):
            msg_idx = gpt_indices[tag_idx]
            round_num = tag_idx
            target_type = tag["task_type"]
            turn_mask = tag.get("turn_mask", True)
            action_tags = ", ".join(tag.get("action_tags", [])[:3])  # First 3 tags
            history_len = msg_idx  # Number of messages before this

            mask_str = "✓ MASKED" if turn_mask else "✗ UNMASKED"
            lines.append(f"| {round_num} | {target_type} | {mask_str} | {action_tags} | {history_len} |")

        # Process each unmasked target
        for target_idx, target in enumerate(targets, 1):
            if target["turn_mask"]:
                continue  # Skip masked

            lines.append(f"\n## Target Turn: Round {target['target_round']} ({target['task_type']})")
            lines.append(f"\n**Sample ID:** {target['sample_id']}")
            lines.append(f"**Action Tags:** {', '.join(target['action_tags'])}")

            # Context info
            input_msgs = target["input_messages"]
            lines.append(f"\n**Context:**")
            lines.append(f"- Input messages: {len(input_msgs)}")

            # Check for specific context elements
            last_human = None
            for m in reversed(input_msgs):
                if m["from"] == "human":
                    last_human = m["value"]
                    break

            has_report = "Report:" in last_human if last_human else False
            has_memory = "memory" in last_human.lower() if last_human else False
            has_best_so_far = "best_so_far" in last_human.lower() if last_human else False

            lines.append(f"- Has report: {has_report}")
            lines.append(f"- Has memory: {has_memory}")
            lines.append(f"- Has best_so_far: {has_best_so_far}")

            # Generate predictions
            lines.append(f"\n### Generating Predictions...")

            base_output = generate_action(base_model, processor, input_msgs)
            sft_output = generate_action(sft_model, processor, input_msgs)
            teacher_output = target["ground_truth"]

            # Parse JSON
            base_json = parse_json_safe(base_output)
            sft_json = parse_json_safe(sft_output)
            teacher_json = parse_json_safe(teacher_output)

            # Save predictions
            all_predictions.append({
                "trajectory_id": traj_id,
                "sample_id": target["sample_id"],
                "task_type": target["task_type"],
                "action_tags": target["action_tags"],
                "teacher": teacher_output,
                "base": base_output,
                "sft": sft_output
            })

            # Show side-by-side comparison
            lines.append(f"\n### Side-by-Side Comparison\n")

            # Extract key fields
            teacher_fields = extract_key_fields(teacher_json) if teacher_json else {}
            base_fields = extract_key_fields(base_json) if base_json else {}
            sft_fields = extract_key_fields(sft_json) if sft_json else {}

            # Comparison table
            lines.append("| Field | Teacher | Base | SFT | Match Teacher? |")
            lines.append("|-------|---------|------|-----|----------------|")

            fields_to_compare = [
                "action_type", "decision", "branch_source",
                "has_repair_constraints", "has_preserve_constraints"
            ]

            for field in fields_to_compare:
                t_val = teacher_fields.get(field, "N/A")
                b_val = base_fields.get(field, "N/A")
                s_val = sft_fields.get(field, "N/A")

                base_match = "✓" if t_val == b_val else "✗"
                sft_match = "✓" if t_val == s_val else "✗"

                lines.append(f"| {field} | {t_val} | {b_val} | {s_val} | Base:{base_match} SFT:{sft_match} |")

            # Constraint analysis
            lines.append(f"\n### Constraint Analysis\n")

            teacher_repair = set(teacher_fields.get("repair_constraints", []))
            base_repair = set(base_fields.get("repair_constraints", []))
            sft_repair = set(sft_fields.get("repair_constraints", []))

            teacher_preserve = set(teacher_fields.get("preserve_constraints", []))
            base_preserve = set(base_fields.get("preserve_constraints", []))
            sft_preserve = set(sft_fields.get("preserve_constraints", []))

            lines.append("**Repair Constraints:**")
            lines.append(f"- Teacher ({len(teacher_repair)}): {list(teacher_repair)[:3]}")
            lines.append(f"- Base ({len(base_repair)}): {list(base_repair)[:3]}")
            lines.append(f"- SFT ({len(sft_repair)}): {list(sft_repair)[:3]}")
            lines.append(f"- Base overlap with teacher: {len(teacher_repair & base_repair)}/{len(teacher_repair)}")
            lines.append(f"- SFT overlap with teacher: {len(teacher_repair & sft_repair)}/{len(teacher_repair)}")

            lines.append("\n**Preserve Constraints:**")
            lines.append(f"- Teacher ({len(teacher_preserve)}): {list(teacher_preserve)[:3]}")
            lines.append(f"- Base ({len(base_preserve)}): {list(base_preserve)[:3]}")
            lines.append(f"- SFT ({len(sft_preserve)}): {list(sft_preserve)[:3]}")
            lines.append(f"- Base overlap with teacher: {len(teacher_preserve & base_preserve)}/{len(teacher_preserve)}")
            lines.append(f"- SFT overlap with teacher: {len(teacher_preserve & sft_preserve)}/{len(teacher_preserve)}")

            # Full outputs
            lines.append(f"\n### Full Outputs\n")

            lines.append("**Teacher:**")
            lines.append("```json")
            lines.append(teacher_output[:1500] + "..." if len(teacher_output) > 1500 else teacher_output)
            lines.append("```")

            lines.append("\n**Base Model:**")
            lines.append("```json")
            lines.append(base_output[:1500] + "..." if len(base_output) > 1500 else base_output)
            lines.append("```")

            lines.append("\n**SFT Model:**")
            lines.append("```json")
            lines.append(sft_output[:1500] + "..." if len(sft_output) > 1500 else sft_output)
            lines.append("```")

        lines.append("\n---\n")

    # Summary
    lines.append("\n# Summary\n")

    # Count matches
    total_comparisons = 0
    base_matches = 0
    sft_matches = 0

    for pred in all_predictions:
        teacher = parse_json_safe(pred["teacher"])
        base = parse_json_safe(pred["base"])
        sft = parse_json_safe(pred["sft"])

        if teacher and base:
            total_comparisons += 1
            if base.get("action_type") == teacher.get("action_type"):
                base_matches += 1

        if teacher and sft:
            if sft.get("action_type") == teacher.get("action_type"):
                sft_matches += 1

    if total_comparisons > 0:
        lines.append(f"**Action Type Accuracy:**")
        lines.append(f"- Base: {base_matches}/{total_comparisons} ({100*base_matches/total_comparisons:.1f}%)")
        lines.append(f"- SFT: {sft_matches}/{total_comparisons} ({100*sft_matches/total_comparisons:.1f}%)")

    lines.append("\n---")
    lines.append("\n*Report generated by case_replay_geneval2_sft.py*")

    return "\n".join(lines), all_predictions


def main():
    print("="*70)
    print("GenEval2 SFT Case Replay")
    print("="*70)

    # Load test data
    print(f"\nLoading test data from: {TEST_DATA_PATH}")
    with open(TEST_DATA_PATH, 'r') as f:
        test_data = [json.loads(line) for line in f]

    # Find representative trajectories
    print("\nFinding representative trajectories...")
    selected = find_representative_trajectories(test_data)
    print(f"Selected {len(selected)} trajectories")

    for i, (traj, targets) in enumerate(selected, 1):
        print(f"  Case {i}: {traj['trajectory_id']} ({len(targets)} unmasked targets)")
        tags = set()
        for t in targets:
            tags.update(t["action_tags"])
        print(f"    Tags: {', '.join(list(tags)[:5])}")

    # Load models
    print("\nLoading models...")

    processor = AutoProcessor.from_pretrained(
        BASE_MODEL_PATH,
        trust_remote_code=True
    )

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

    print("Models loaded!")

    # Generate report
    print("\nGenerating report...")
    report, predictions = generate_report(selected, processor, base_model, sft_model)

    # Save report
    with open(OUTPUT_REPORT_PATH, 'w') as f:
        f.write(report)
    print(f"Report saved to: {OUTPUT_REPORT_PATH}")

    # Save predictions
    with open(OUTPUT_PREDICTIONS_PATH, 'w') as f:
        for pred in predictions:
            f.write(json.dumps(pred, ensure_ascii=False) + "\n")
    print(f"Predictions saved to: {OUTPUT_PREDICTIONS_PATH}")

    # Cleanup
    del base_model, sft_model, sft_base
    torch.cuda.empty_cache()

    print("\n" + "="*70)
    print("Case replay complete!")
    print("="*70)


if __name__ == "__main__":
    main()
