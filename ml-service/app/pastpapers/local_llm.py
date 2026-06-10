"""Fully-offline, in-process tutor inference.

Loads the LoRA-fine-tuned tutor (or its base model) with transformers +
peft and generates answers on-device — no API, no separate model server,
no network at answer time. Runs on Apple-Silicon MPS, CUDA, or CPU.

Enabled by setting LOCAL_LLM=1 (and optionally LOCAL_LLM_ADAPTER /
LOCAL_LLM_BASE). The model is loaded lazily on first use and cached for
the process lifetime, so startup stays fast and offline-only.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

ADAPTER_DIR = Path(
    os.getenv(
        "LOCAL_LLM_ADAPTER",
        str(Path(__file__).resolve().parent.parent.parent / "models" / "tutor-lora"),
    )
)
BASE_MODEL = os.getenv("LOCAL_LLM_BASE", "Qwen/Qwen2.5-0.5B-Instruct")
MAX_NEW_TOKENS = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "512"))
TEMPERATURE = float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("LOCAL_LLM_TOP_P", "0.9"))

_lock = threading.Lock()
_pipeline = None
_load_failed = False


def is_enabled() -> bool:
    return os.getenv("LOCAL_LLM", "").lower() in ("1", "true", "yes")


def _pick_device():
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load():
    """Build the text-generation callable once. Prefers the fine-tuned
    adapter; falls back to the base model if no adapter is present."""
    global _pipeline, _load_failed
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = _pick_device()
    dtype = torch.float16 if device == "cuda" else torch.float32

    has_adapter = (ADAPTER_DIR / "adapter_config.json").exists()
    source = str(ADAPTER_DIR) if has_adapter else BASE_MODEL
    tokenizer_source = source if has_adapter else BASE_MODEL

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=dtype)

    if has_adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))
        logger.info("Loaded fine-tuned tutor adapter from %s", ADAPTER_DIR)
    else:
        logger.info("No adapter at %s — using base model %s", ADAPTER_DIR, BASE_MODEL)

    model.to(device).eval()
    _pipeline = (model, tokenizer, device)


def generate(question: str, system_prompt: str, context: str = "") -> str | None:
    """Generate a tutor answer locally. Returns None if local inference is
    disabled or the model can't be loaded (caller falls back to retrieval)."""
    global _load_failed
    if not is_enabled() or _load_failed:
        return None

    with _lock:
        if _pipeline is None:
            try:
                _load()
            except Exception as exc:  # missing deps / OOM — degrade gracefully
                logger.warning("Local LLM unavailable: %s", exc)
                _load_failed = True
                return None

    import torch

    model, tokenizer, device = _pipeline
    system = system_prompt
    if context:
        system += "\n\nReference material:\n" + context

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(
        output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
    )
    return text.strip() or None
