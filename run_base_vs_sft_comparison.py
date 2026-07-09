#!/usr/bin/env python3
"""
Base vs SFT 实际推理对比
针对 geneval2 测试数据的一条轨迹进行多轮对比
"""

import json
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llamafactory.chat import ChatModel


def load_test_trajectory():
    """加载测试轨迹"""
    with open('data/llamafactory/geneval2_retry_masked_multiturn_sft_test.jsonl', 'r') as f:
        first_line = f.readline()
        return json.loads(first_line)


def run_comparison():
    """运行 Base vs SFT 对比"""

    # 加载测试数据
    data = load_test_trajectory()
    messages = data['messages']

    print("="*80)
    print("🧪 Base 模型 vs SFT 模型 - 实际推理对比")
    print("="*80)
    print(f"\n轨迹 ID: {data['trajectory_id']}")
    print(f"原始提示: four pink flamingos chasing a horse to the left of four wooden chairs")
    print(f"总轮数: 5 (INITIAL_PLAN + 4次 RETRY_REPLAN)")

    # 模型配置
    base_config = {
        "model_name_or_path": "/home/develop/biocloudplantform/xxr/models/Qwen3-VL-8B-Instruct",
        "template": "qwen3_vl_nothink",
        "infer_backend": "huggingface",
        "trust_remote_code": True,
    }

    sft_config = {
        "model_name_or_path": "/home/develop/biocloudplantform/xxr/models/Qwen3-VL-8B-Instruct",
        "adapter_name_or_path": "saves/qwen3-vl-8b/lora/geneval2_retry_masked_multiturn_sft_6gpu/checkpoint-150",
        "template": "qwen3_vl_nothink",
        "infer_backend": "huggingface",
        "trust_remote_code": True,
    }

    print("\n📥 正在加载模型...")
    print("  [1/2] Base 模型...")
    base_model = ChatModel(base_config)
    print("  [2/2] SFT 模型...")
    sft_model = ChatModel(sft_config)
    print("✅ 模型加载完成!\n")

    # 准备多轮对话
    conversation = []
    round_num = 0

    for i, msg in enumerate(messages):
        role = msg['from']
        value = msg['value']

        if role == 'system':
            # 系统指令在第一轮加入
            pass

        elif role == 'human':
            # 用户输入
            task_type = value.split('Task: ')[1].split('\n')[0] if 'Task: ' in value else 'UNKNOWN'

            print("="*80)
            print(f"🔄 Round {round_num}: {task_type}")
            print("="*80)

            # 添加用户消息到对话历史
            conversation.append({"role": "user", "content": value})

            # 获取 Ground Truth
            gt_msg = messages[i + 1] if i + 1 < len(messages) and messages[i + 1]['from'] == 'gpt' else None
            ground_truth = gt_msg['value'] if gt_msg else None

            # Base 模型推理
            print("\n🟦 [Base 模型] 输出:")
            print("-" * 60)
            try:
                base_response = base_model.chat(conversation, max_new_tokens=2048)
                base_output = base_response[0].response_text
                print(base_output[:2000])
                if len(base_output) > 2000:
                    print("...")
            except Exception as e:
                print(f"错误: {e}")
                base_output = ""

            # SFT 模型推理
            print("\n🟩 [SFT 模型] 输出:")
            print("-" * 60)
            try:
                sft_response = sft_model.chat(conversation, max_new_tokens=2048)
                sft_output = sft_response[0].response_text
                print(sft_output[:2000])
                if len(sft_output) > 2000:
                    print("...")
            except Exception as e:
                print(f"错误: {e}")
                sft_output = ""

            # Ground Truth
            if ground_truth:
                print("\n🟨 [Ground Truth] 期望输出:")
                print("-" * 60)
                try:
                    gt_json = json.loads(ground_truth)
                    print(json.dumps(gt_json, indent=2, ensure_ascii=False)[:2000])
                except:
                    print(ground_truth[:2000])

            # 差异分析
            print("\n💡 差异分析:")
            print("-" * 60)

            # 检查 JSON 有效性
            base_valid = False
            sft_valid = False
            try:
                json.loads(base_output)
                base_valid = True
            except:
                pass
            try:
                json.loads(sft_output)
                sft_valid = True
            except:
                pass

            print(f"  Base 输出 JSON 有效: {base_valid}")
            print(f"  SFT 输出 JSON 有效: {sft_valid}")

            # 检查关键字段
            if sft_valid:
                sft_json = json.loads(sft_output)
                if 'action_type' in sft_json:
                    print(f"  SFT action_type: {sft_json['action_type']}")
                if 'generation_guards' in sft_json:
                    print(f"  SFT generation_guards 数量: {len(sft_json['generation_guards'])}")

            # 将 SFT 输出加入对话历史（用于下一轮）
            conversation.append({"role": "assistant", "content": sft_output})

            round_num += 1
            print("\n")

            # 只测试前3轮以节省时间
            if round_num >= 3:
                print("\n⚠️  为节省时间和显存，只演示前 3 轮")
                break


if __name__ == "__main__":
    run_comparison()
