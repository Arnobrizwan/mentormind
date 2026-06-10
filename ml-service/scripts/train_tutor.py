#!/usr/bin/env python3
"""Fine-tune the MentorMind tutor on the aligned past-paper dataset.

Two modes, chosen by what's installed / configured:

1. **Local LoRA fine-tune** (default when `unsloth` or `peft`+`trl` are
   available and a GPU is present). Trains a small open model
   (default: unsloth/Qwen2.5-3B-Instruct) on data/dataset.jsonl and
   writes the adapter to models/tutor-lora/. Serve it with vLLM:
       vllm serve <base> --enable-lora --lora-modules tutor=models/tutor-lora
   then point the ml-service at it:  CUSTOM_LLM_URL=http://localhost:8000

2. **Dry run / planning** (default on a laptop with no GPU). Validates
   the dataset, prints token/length stats and the exact commands to run
   on a GPU box or a managed fine-tuning API (Together / Fireworks),
   without pretending to train.

Usage:
    python scripts/train_tutor.py                 # auto-detect
    python scripts/train_tutor.py --dry-run       # force planning mode
    python scripts/train_tutor.py --base <model>  # override base model
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "dataset.jsonl"
ADAPTER_OUT = ROOT / "models" / "tutor-lora"
DEFAULT_BASE = "unsloth/Qwen2.5-3B-Instruct"


def load_dataset() -> list[dict]:
    if not DATASET.exists():
        raise SystemExit(
            f"No dataset at {DATASET}. Run scripts/export_dataset.py first."
        )
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    if not rows:
        raise SystemExit("Dataset is empty — run the pipeline on more papers.")
    return rows


def dataset_stats(rows: list[dict]) -> dict:
    q_lens, a_lens = [], []
    for row in rows:
        for message in row["messages"]:
            if message["role"] == "user":
                q_lens.append(len(message["content"]))
            elif message["role"] == "assistant":
                a_lens.append(len(message["content"]))

    def stats(values):
        values = sorted(values)
        n = len(values)
        return {
            "count": n,
            "min": values[0],
            "median": values[n // 2],
            "max": values[-1],
            "mean": round(sum(values) / n, 1),
        }

    return {"questions": stats(q_lens), "answers": stats(a_lens)}


def detect_device() -> str | None:
    """Return 'cuda', 'mps' (Apple Silicon), or None when no trainable
    accelerator + training stack is present."""
    try:
        import torch
        from trl import SFTTrainer  # noqa: F401

        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return None


def run_local_finetune(
    rows: list[dict], base: str, epochs: int, max_seq: int, device: str
) -> None:
    """LoRA SFT via TRL — runs on CUDA or Apple-Silicon MPS."""
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    tokenizer = AutoTokenizer.from_pretrained(base)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def to_text(example):
        return {
            "text": tokenizer.apply_chat_template(
                example["messages"], tokenize=False, add_generation_prompt=False
            )
        }

    dataset = Dataset.from_list(rows).map(to_text)

    # bf16 on CUDA; fp32 on MPS (half precision is unstable there).
    use_bf16 = device == "cuda"
    model = AutoModelForCausalLM.from_pretrained(
        base,
        torch_dtype=torch.bfloat16 if use_bf16 else torch.float32,
        device_map="auto" if device == "cuda" else None,
    )
    if device == "mps":
        model = model.to("mps")

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=str(ADAPTER_OUT),
            num_train_epochs=epochs,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=2e-4,
            max_length=max_seq,
            logging_steps=5,
            save_strategy="epoch",
            bf16=use_bf16,
            use_cpu=False,  # MPS/CUDA auto-selected by Accelerate
            report_to=[],
        ),
        peft_config=LoraConfig(
            r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        ),
    )
    trainer.train()
    trainer.save_model(str(ADAPTER_OUT))
    tokenizer.save_pretrained(str(ADAPTER_OUT))
    print(f"\n✓ LoRA adapter written to {ADAPTER_OUT}")
    print("Serve it:")
    print(f"  vllm serve {base} --enable-lora --lora-modules tutor={ADAPTER_OUT}")
    print("Then point the ml-service tutor at it:")
    print("  export CUSTOM_LLM_URL=http://localhost:8000")
    print("  export CUSTOM_LLM_MODEL=tutor")


def print_plan(rows: list[dict], stats: dict, base: str) -> None:
    print("=" * 64)
    print(" MentorMind tutor — training plan (no GPU detected: dry run)")
    print("=" * 64)
    print(f"\nDataset: {len(rows)} examples at {DATASET}")
    print(f"  question chars: {stats['questions']}")
    print(f"  answer chars:   {stats['answers']}")
    print("\nThe retrieval tutor already serves these verbatim from the corpus.")
    print("Fine-tuning generalises them to unseen questions. To train:\n")
    print("Option A — GPU box (LoRA, ~15 min on an A100 for a few k rows):")
    print("  pip install unsloth trl peft transformers datasets")
    print(f"  python scripts/train_tutor.py --base {base}")
    print("\nOption B — managed API (no GPU needed):")
    print("  # Together AI")
    print("  together files upload data/dataset.jsonl")
    print("  together fine-tuning create --training-file <id> \\")
    print(f"      --model {base} --lora")
    print("\nServe the result and wire it in:")
    print("  export CUSTOM_LLM_URL=http://<host>/v1   # OpenAI-compatible")
    print("  export CUSTOM_LLM_MODEL=mentormind-tutor")
    print("\nUntil then the ml-service answers from the aligned corpus, so the")
    print("tutor already gives real mark-scheme answers for covered questions.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--max-seq", type=int, default=2048)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = load_dataset()
    stats = dataset_stats(rows)

    device = None if args.dry_run else detect_device()
    if device:
        print(f"{device.upper()} detected — fine-tuning {args.base} on {len(rows)} examples…")
        run_local_finetune(rows, args.base, args.epochs, args.max_seq, device)
    else:
        print_plan(rows, stats, args.base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
