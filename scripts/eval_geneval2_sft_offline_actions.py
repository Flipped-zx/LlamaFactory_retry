#!/usr/bin/env python3
"""
Offline Action Evaluation for GenEval2 SFT Controller.

Evaluates whether the SFT LoRA controller can generate correct structured actions
from held-out trajectory states (without actual image generation).
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
from tqdm import tqdm

# Add src to path for llamafactory imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer, Qwen3VLForConditionalGeneration
from peft import PeftModel


# Constants
BASE_MODEL_PATH = "/home/develop/biocloudplantform/xxr/models/Qwen3-VL-8B-Instruct"
ADAPTER_PATH = "saves/qwen3-vl-8b/lora/geneval2_retry_masked_multiturn_sft_6gpu"
TEST_DATA_PATH = "data/llamafactory/geneval2_retry_masked_multiturn_sft_test.jsonl"
OUTPUT_PREDICTIONS_PATH = "data/llamafactory/geneval2_retry_sft_offline_eval_predictions.jsonl"
OUTPUT_REPORT_PATH = "data/llamafactory/geneval2_retry_sft_offline_eval_report.md"

MAX_NEW_TOKENS = 2048
TEMPERATURE = 0.1
TOP_P = 0.9


def load_model_and_processor(use_adapter: bool = False):
    """Load base model and optionally apply LoRA adapter."""
    print(f"\n{'='*60}")
    print(f"Loading model: {BASE_MODEL_PATH}")
    print(f"Use adapter: {use_adapter}")
    print(f"{'='*60}")

    # Load processor/tokenizer
    processor = AutoProcessor.from_pretrained(
        BASE_MODEL_PATH,
        trust_remote_code=True
    )

    # Load base model - Qwen3VL requires specific model class
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE_MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )

    # Apply LoRA adapter if requested
    if use_adapter:
        print(f"Loading adapter from: {ADAPTER_PATH}")
        model = PeftModel.from_pretrained(model, ADAPTER_PATH)
        model = model.merge_and_unload()  # Merge for faster inference

    model.eval()

    return model, processor


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
                "action_tags": tag.get("action_tags", []),
                "message_idx": msg_idx,
                "ground_truth": messages[msg_idx]["value"],
                "input_messages": messages[:msg_idx]  # All messages before target
            }
            targets.append(target)

    return targets


def generate_action(model, processor, input_messages: list[dict]) -> str:
    """Generate action from input messages."""
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

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            do_sample=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id
        )

    # Decode
    generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
    generated_text = processor.decode(generated_ids, skip_special_tokens=True)

    return generated_text.strip()


def parse_json_action(text: str) -> tuple[dict | None, str]:
    """Try to parse action as JSON."""
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    # Try to find JSON object in text
    if not text.strip().startswith('{'):
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)

    try:
        return json.loads(text), ""
    except json.JSONDecodeError as e:
        return None, str(e)


def check_field_exists(data: dict, field: str) -> bool:
    """Check if a field exists and is not None/empty."""
    if field not in data:
        return False
    val = data[field]
    if val is None:
        return False
    if isinstance(val, (list, dict, str)) and len(val) == 0:
        return False
    return True


def evaluate_initial_plan(pred: dict, target: dict) -> dict:
    """Evaluate initial_plan action."""
    metrics = {}

    # Required fields
    required_fields = [
        "action_type", "parsed_constraints", "selected_skills",
        "generation_strategy", "initial_prompt", "generation_guards"
    ]

    # Schema completeness
    pred_fields = {f for f in required_fields if check_field_exists(pred, f)}
    target_fields = {f for f in required_fields if check_field_exists(target, f)}
    metrics["schema_complete"] = len(pred_fields) == len(required_fields)
    metrics["schema_complete_rate"] = len(pred_fields) / len(required_fields)

    # Action type accuracy
    metrics["action_type_correct"] = pred.get("action_type") == target.get("action_type")

    return metrics


def evaluate_retry_replan(pred: dict, target: dict) -> dict:
    """Evaluate retry_replan action."""
    metrics = {}

    # Required fields
    required_fields = [
        "action_type", "decision", "branch_source", "diagnosis",
        "preserve_constraints", "repair_constraints", "regression_risks",
        "skill_revision", "regeneration_strategy", "retry_prompt", "expected_improvement"
    ]

    # Schema completeness
    pred_fields = {f for f in required_fields if check_field_exists(pred, f)}
    target_fields = {f for f in required_fields if check_field_exists(target, f)}
    metrics["schema_complete"] = len(pred_fields) == len(required_fields)
    metrics["schema_complete_rate"] = len(pred_fields) / len(required_fields)

    # Action type accuracy
    metrics["action_type_correct"] = pred.get("action_type") == target.get("action_type")

    # Decision accuracy
    metrics["decision_correct"] = pred.get("decision") == target.get("decision")

    # Branch source accuracy
    metrics["branch_source_correct"] = pred.get("branch_source") == target.get("branch_source")

    # Retry prompt present
    metrics["retry_prompt_present"] = check_field_exists(pred, "retry_prompt")

    # Repair constraints present
    metrics["repair_constraints_present"] = check_field_exists(pred, "repair_constraints")

    # Preserve constraints present
    metrics["preserve_constraints_present"] = check_field_exists(pred, "preserve_constraints")

    # Constraint overlap with target
    if check_field_exists(pred, "repair_constraints") and check_field_exists(target, "repair_constraints"):
        pred_set = set(pred.get("repair_constraints", []))
        target_set = set(target.get("repair_constraints", []))
        if len(target_set) > 0:
            metrics["repair_constraints_overlap"] = len(pred_set & target_set) / len(target_set)
        else:
            metrics["repair_constraints_overlap"] = 1.0 if len(pred_set) == 0 else 0.0
    else:
        metrics["repair_constraints_overlap"] = 0.0

    if check_field_exists(pred, "preserve_constraints") and check_field_exists(target, "preserve_constraints"):
        pred_set = set(pred.get("preserve_constraints", []))
        target_set = set(target.get("preserve_constraints", []))
        if len(target_set) > 0:
            metrics["preserve_constraints_overlap"] = len(pred_set & target_set) / len(target_set)
        else:
            metrics["preserve_constraints_overlap"] = 1.0 if len(pred_set) == 0 else 0.0
    else:
        metrics["preserve_constraints_overlap"] = 0.0

    return metrics


def evaluate_stop(pred: dict, target: dict) -> dict:
    """Evaluate stop action."""
    metrics = {}

    # Required fields
    metrics["action_type_correct"] = pred.get("action_type") == target.get("action_type")
    metrics["decision_correct"] = pred.get("decision") == target.get("decision")

    # Stop reason present (can be 'reason', 'final_answer', or 'stop_reason')
    has_reason = any(check_field_exists(pred, f) for f in ["reason", "final_answer", "stop_reason"])
    metrics["stop_reason_present"] = has_reason

    return metrics


def evaluate_prediction(pred_text: str, target_text: str, task_type: str) -> dict:
    """Evaluate a single prediction against target."""
    metrics = {
        "valid_json": False,
        "schema_complete": False,
        "schema_complete_rate": 0.0,
        "action_type_correct": False,
        "decision_correct": False,
    }

    # Parse prediction
    pred_json, parse_error = parse_json_action(pred_text)
    if pred_json is None:
        metrics["parse_error"] = parse_error
        return metrics

    metrics["valid_json"] = True

    # Parse target
    target_json, _ = parse_json_action(target_text)
    if target_json is None:
        return metrics

    # Route to specific evaluator
    if task_type == "initial_plan":
        task_metrics = evaluate_initial_plan(pred_json, target_json)
    elif task_type == "retry_replan":
        task_metrics = evaluate_retry_replan(pred_json, target_json)
    elif task_type == "stop":
        task_metrics = evaluate_stop(pred_json, target_json)
    else:
        task_metrics = {}

    metrics.update(task_metrics)
    return metrics


def run_evaluation(model, processor, test_data: list[dict], use_adapter: bool) -> list[dict]:
    """Run evaluation on all test data."""
    results = []

    setting_name = "sft" if use_adapter else "base"

    for trajectory in tqdm(test_data, desc=f"Evaluating ({setting_name})"):
        trajectory_id = trajectory.get("trajectory_id", "unknown")
        targets = get_eval_targets(trajectory)

        for target in targets:
            # Generate prediction
            generated = generate_action(model, processor, target["input_messages"])

            # Evaluate
            metrics = evaluate_prediction(
                generated,
                target["ground_truth"],
                target["task_type"]
            )

            result = {
                "trajectory_id": trajectory_id,
                "sample_id": target["sample_id"],
                "task_type": target["task_type"],
                "target_round": target["target_round"],
                "action_tags": target["action_tags"],
                "setting": setting_name,
                "generated": generated,
                "ground_truth": target["ground_truth"],
                "metrics": metrics
            }
            results.append(result)

    return results


def compute_aggregate_metrics(results: list[dict]) -> dict:
    """Compute aggregate metrics from results."""
    if not results:
        return {}

    metrics = defaultdict(list)
    task_type_counts = defaultdict(int)

    for r in results:
        task_type = r["task_type"]
        task_type_counts[task_type] += 1

        m = r["metrics"]
        for key, value in m.items():
            if isinstance(value, (int, float, bool)):
                metrics[key].append(float(value))

    # Compute means
    aggregate = {}
    for key, values in metrics.items():
        if values:
            aggregate[key] = sum(values) / len(values)

    aggregate["total_samples"] = len(results)
    aggregate["task_type_distribution"] = dict(task_type_counts)

    return aggregate


def generate_report(base_results: list[dict], sft_results: list[dict]) -> str:
    """Generate markdown report."""
    lines = []

    lines.append("# GenEval2 SFT Offline Action Evaluation Report")
    lines.append(f"\nGenerated: {datetime.now().isoformat()}")
    lines.append(f"\n## Summary")

    # Count samples
    lines.append(f"\n- **Total evaluated target turns**: {len(base_results)}")

    # Task type distribution
    task_counts = defaultdict(int)
    for r in base_results:
        task_counts[r["task_type"]] += 1

    lines.append(f"\n### Task Type Distribution")
    for task_type, count in sorted(task_counts.items()):
        lines.append(f"- {task_type}: {count}")

    # Aggregate metrics
    base_agg = compute_aggregate_metrics(base_results)
    sft_agg = compute_aggregate_metrics(sft_results)

    lines.append(f"\n## Base vs SFT Comparison")
    lines.append("\n| Metric | Base Model | SFT LoRA | Improvement |")
    lines.append("|--------|------------|----------|-------------|")

    key_metrics = [
        ("valid_json_rate", "valid_json"),
        ("schema_complete_rate", "schema_complete_rate"),
        ("action_type_accuracy", "action_type_correct"),
        ("decision_accuracy", "decision_correct"),
    ]

    for display_name, metric_key in key_metrics:
        base_val = base_agg.get(metric_key, 0) * 100
        sft_val = sft_agg.get(metric_key, 0) * 100
        improvement = sft_val - base_val
        lines.append(f"| {display_name} | {base_val:.1f}% | {sft_val:.1f}% | {improvement:+.1f}% |")

    # Retry-specific metrics
    lines.append(f"\n### Retry/Replan Specific Metrics")
    lines.append("\n| Metric | Base Model | SFT LoRA | Improvement |")
    lines.append("|--------|------------|----------|-------------|")

    retry_metrics = [
        ("branch_source_accuracy", "branch_source_correct"),
        ("retry_prompt_present_rate", "retry_prompt_present"),
        ("repair_constraints_present_rate", "repair_constraints_present"),
        ("preserve_constraints_present_rate", "preserve_constraints_present"),
        ("repair_constraints_overlap", "repair_constraints_overlap"),
        ("preserve_constraints_overlap", "preserve_constraints_overlap"),
    ]

    for display_name, metric_key in retry_metrics:
        base_val = base_agg.get(metric_key, 0) * 100
        sft_val = sft_agg.get(metric_key, 0) * 100
        improvement = sft_val - base_val
        lines.append(f"| {display_name} | {base_val:.1f}% | {sft_val:.1f}% | {improvement:+.1f}% |")

    # Stop action metrics
    lines.append(f"\n### Stop Action Metrics")
    lines.append("\n| Metric | Base Model | SFT LoRA | Improvement |")
    lines.append("|--------|------------|----------|-------------|")

    stop_metrics = [
        ("stop_action_accuracy", "action_type_correct"),
        ("stop_reason_present_rate", "stop_reason_present"),
    ]

    for display_name, metric_key in stop_metrics:
        base_val = base_agg.get(metric_key, 0) * 100
        sft_val = sft_agg.get(metric_key, 0) * 100
        improvement = sft_val - base_val
        lines.append(f"| {display_name} | {base_val:.1f}% | {sft_val:.1f}% | {improvement:+.1f}% |")

    # Per-action-type metrics
    lines.append(f"\n## Per-Action-Type Metrics")

    for task_type in sorted(task_counts.keys()):
        lines.append(f"\n### {task_type}")

        base_task = [r for r in base_results if r["task_type"] == task_type]
        sft_task = [r for r in sft_results if r["task_type"] == task_type]

        base_task_agg = compute_aggregate_metrics(base_task)
        sft_task_agg = compute_aggregate_metrics(sft_task)

        lines.append(f"\nSamples: {len(base_task)}")
        lines.append("\n| Metric | Base | SFT |")
        lines.append("|--------|------|-----|")

        for _, metric_key in key_metrics:
            base_val = base_task_agg.get(metric_key, 0) * 100
            sft_val = sft_task_agg.get(metric_key, 0) * 100
            lines.append(f"| {metric_key} | {base_val:.1f}% | {sft_val:.1f}% |")

    # Find examples where SFT is better
    lines.append(f"\n## Examples: SFT Better Than Base")

    improvements = []
    for base_r, sft_r in zip(base_results, sft_results):
        base_valid = base_r["metrics"].get("valid_json", False)
        sft_valid = sft_r["metrics"].get("valid_json", False)

        if not base_valid and sft_valid:
            improvements.append((base_r, sft_r, "json_parse"))
        elif base_valid and sft_valid:
            base_score = sum([
                base_r["metrics"].get("action_type_correct", 0),
                base_r["metrics"].get("decision_correct", 0),
                base_r["metrics"].get("schema_complete", 0)
            ])
            sft_score = sum([
                sft_r["metrics"].get("action_type_correct", 0),
                sft_r["metrics"].get("decision_correct", 0),
                sft_r["metrics"].get("schema_complete", 0)
            ])
            if sft_score > base_score:
                improvements.append((base_r, sft_r, f"score_{sft_score-base_score}"))

    # Sort by improvement type and take top 5
    improvements.sort(key=lambda x: x[2], reverse=True)

    for i, (base_r, sft_r, reason) in enumerate(improvements[:5], 1):
        lines.append(f"\n### Example {i} ({reason})")
        lines.append(f"- Sample ID: {base_r['sample_id']}")
        lines.append(f"- Task Type: {base_r['task_type']}")
        lines.append(f"- Action Tags: {', '.join(base_r['action_tags'])}")
        lines.append(f"\n**Base Output:**")
        lines.append(f"```json")
        lines.append(base_r['generated'][:500] + "..." if len(base_r['generated']) > 500 else base_r['generated'])
        lines.append(f"```")
        lines.append(f"\n**SFT Output:**")
        lines.append(f"```json")
        lines.append(sft_r['generated'][:500] + "..." if len(sft_r['generated']) > 500 else sft_r['generated'])
        lines.append(f"```")
        lines.append(f"\n**Ground Truth:**")
        lines.append(f"```json")
        lines.append(base_r['ground_truth'][:500] + "..." if len(base_r['ground_truth']) > 500 else base_r['ground_truth'])
        lines.append(f"```")

    # Find SFT failures
    lines.append(f"\n## Examples: SFT Failures")

    failures = []
    for base_r, sft_r in zip(base_results, sft_results):
        sft_valid = sft_r["metrics"].get("valid_json", False)
        if not sft_valid:
            failures.append((base_r, sft_r, "invalid_json"))
        elif not sft_r["metrics"].get("action_type_correct", True):
            failures.append((base_r, sft_r, "wrong_action_type"))
        elif not sft_r["metrics"].get("schema_complete", True):
            failures.append((base_r, sft_r, "incomplete_schema"))

    for i, (base_r, sft_r, reason) in enumerate(failures[:5], 1):
        lines.append(f"\n### Failure {i} ({reason})")
        lines.append(f"- Sample ID: {sft_r['sample_id']}")
        lines.append(f"- Task Type: {sft_r['task_type']}")
        lines.append(f"- Action Tags: {', '.join(sft_r['action_tags'])}")
        lines.append(f"\n**SFT Output:**")
        lines.append(f"```")
        lines.append(sft_r['generated'][:500] + "..." if len(sft_r['generated']) > 500 else sft_r['generated'])
        lines.append(f"```")
        lines.append(f"\n**Ground Truth:**")
        lines.append(f"```json")
        lines.append(sft_r['ground_truth'][:500] + "..." if len(sft_r['ground_truth']) > 500 else sft_r['ground_truth'])
        lines.append(f"```")

    # Assessment
    lines.append(f"\n## Assessment: Ready for Closed-Loop GenEval2?")
    lines.append(f"\n### Key Criteria:")

    valid_json_rate = sft_agg.get("valid_json", 0)
    schema_rate = sft_agg.get("schema_complete_rate", 0)
    action_type_rate = sft_agg.get("action_type_correct", 0)

    lines.append(f"\n1. **Valid JSON Rate**: {valid_json_rate*100:.1f}% (target: >95%)")
    lines.append(f"   - Status: {'✅ PASS' if valid_json_rate > 0.95 else '⚠️ MARGINAL' if valid_json_rate > 0.85 else '❌ FAIL'}")

    lines.append(f"\n2. **Schema Completeness**: {schema_rate*100:.1f}% (target: >80%)")
    lines.append(f"   - Status: {'✅ PASS' if schema_rate > 0.80 else '⚠️ MARGINAL' if schema_rate > 0.65 else '❌ FAIL'}")

    lines.append(f"\n3. **Action Type Accuracy**: {action_type_rate*100:.1f}% (target: >95%)")
    lines.append(f"   - Status: {'✅ PASS' if action_type_rate > 0.95 else '⚠️ MARGINAL' if action_type_rate > 0.85 else '❌ FAIL'}")

    overall_ready = valid_json_rate > 0.90 and schema_rate > 0.70 and action_type_rate > 0.90
    lines.append(f"\n### Overall Assessment")
    if overall_ready:
        lines.append(f"\n✅ **SFT model appears ready for small closed-loop GenEval2 evaluation.**")
        lines.append(f"The model demonstrates sufficient action generation quality to proceed with")
        lines.append(f"limited closed-loop testing (recommend 50-100 samples first).")
    else:
        lines.append(f"\n⚠️ **SFT model needs improvement before closed-loop evaluation.**")
        lines.append(f"Consider:")
        if valid_json_rate <= 0.90:
            lines.append(f"- Increasing training epochs or data diversity for JSON formatting")
        if schema_rate <= 0.70:
            lines.append(f"- Adding more diverse schema examples to training data")
        if action_type_rate <= 0.90:
            lines.append(f"- Reviewing action type distribution in training data")

    lines.append(f"\n---")
    lines.append(f"\n*Report generated by eval_geneval2_sft_offline_actions.py*")

    return "\n".join(lines)


def main():
    print("="*70)
    print("GenEval2 SFT Offline Action Evaluation")
    print("="*70)

    # Load test data
    print(f"\nLoading test data from: {TEST_DATA_PATH}")
    test_data = []
    with open(TEST_DATA_PATH, 'r') as f:
        for line in f:
            test_data.append(json.loads(line))
    print(f"Loaded {len(test_data)} trajectories")

    # Count total eval targets
    total_targets = sum(len(get_eval_targets(t)) for t in test_data)
    print(f"Total evaluation targets (turn_mask=false): {total_targets}")

    # Run base model evaluation
    print("\n" + "="*70)
    print("RUNNING BASE MODEL EVALUATION")
    print("="*70)
    model_base, processor = load_model_and_processor(use_adapter=False)
    base_results = run_evaluation(model_base, processor, test_data, use_adapter=False)

    # Clean up base model
    del model_base
    torch.cuda.empty_cache()

    # Run SFT model evaluation
    print("\n" + "="*70)
    print("RUNNING SFT LoRA EVALUATION")
    print("="*70)
    model_sft, _ = load_model_and_processor(use_adapter=True)
    sft_results = run_evaluation(model_sft, processor, test_data, use_adapter=True)

    # Save predictions
    print(f"\nSaving predictions to: {OUTPUT_PREDICTIONS_PATH}")
    with open(OUTPUT_PREDICTIONS_PATH, 'w') as f:
        for base_r, sft_r in zip(base_results, sft_results):
            f.write(json.dumps({"base": base_r, "sft": sft_r}, ensure_ascii=False) + "\n")

    # Generate and save report
    print(f"Generating report: {OUTPUT_REPORT_PATH}")
    report = generate_report(base_results, sft_results)

    with open(OUTPUT_REPORT_PATH, 'w') as f:
        f.write(report)

    print("\n" + "="*70)
    print("EVALUATION COMPLETE")
    print("="*70)
    print(f"\nResults saved:")
    print(f"  - Predictions: {OUTPUT_PREDICTIONS_PATH}")
    print(f"  - Report: {OUTPUT_REPORT_PATH}")

    # Print summary
    base_agg = compute_aggregate_metrics(base_results)
    sft_agg = compute_aggregate_metrics(sft_results)

    print(f"\nQuick Summary:")
    print(f"  Valid JSON - Base: {base_agg.get('valid_json', 0)*100:.1f}%, SFT: {sft_agg.get('valid_json', 0)*100:.1f}%")
    print(f"  Action Type Acc - Base: {base_agg.get('action_type_correct', 0)*100:.1f}%, SFT: {sft_agg.get('action_type_correct', 0)*100:.1f}%")
    print(f"  Schema Complete - Base: {base_agg.get('schema_complete_rate', 0)*100:.1f}%, SFT: {sft_agg.get('schema_complete_rate', 0)*100:.1f}%")


if __name__ == "__main__":
    main()
