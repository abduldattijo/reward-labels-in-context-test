"""One place for every model call. Counts billed tokens, prices them, and stops at the spend cap.

No temperature is sent to the Claude models, because they reject non default values (project note, 2026-10-15).
The key is read from the ANTHROPIC_API_KEY environment variable and is never printed.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

# US dollars per million tokens. Haiku and Sonnet from agentic-rag-eval/config.py (checked 2026-10-15). GPT-6 Sol from the
# earlier annotation run. Re-check the pages before any run that spends real money.
PRICES = {
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00},
    "gpt-6-sol": {"in": 2.00, "out": 10.00},
}
THINKING = {"claude-haiku-5-5": {"type": "disabled"}, "claude-sonnet-5-5": {"type": "between_tools"}}


class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    def __init__(self, cap_usd: float):
        self.cap, self.usd, self.calls, self.tin, self.tout = cap_usd, 0.0, 0, 0, 0
        self.lock = threading.Lock()

    def add(self, usd, tin, tout):
        with self.lock:
            self.usd += usd
            self.calls += 1
            self.tin += tin
            self.tout += tout
            if self.usd > self.cap:
                raise BudgetExceeded(f"spend {self.usd:.4f} passed the cap {self.cap:.2f} after {self.calls} calls")


def _anthropic_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    raise RuntimeError("Set ANTHROPIC_API_KEY")


def _openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    raise RuntimeError("Set OPENAI_API_KEY")


class Chooser:
    """choose(system, user) returns (reply_text, record) for one model."""

    def __init__(self, model: str, ledger: Ledger, max_tokens: int = 12):
        if model not in PRICES:
            raise RuntimeError(f"no price for {model}")
        self.model, self.ledger, self.max_tokens = model, ledger, max_tokens
        if model.startswith("claude"):
            import anthropic
            self.client = anthropic.Anthropic(api_key=_anthropic_key())
            self.kind = "anthropic"
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=_openai_key())
            self.kind = "openai"

    def choose(self, system: str, user: str):
        p = PRICES[self.model]
        last = None
        for attempt in range(5):
            t0 = time.monotonic()
            try:
                if self.kind == "anthropic":
                    kw = {"thinking": THINKING[self.model]} if self.model in THINKING else {}
                    r = self.client.messages.create(model=self.model, max_tokens=self.max_tokens, system=system,
                                                    messages=[{"role": "user", "content": user}], **kw)
                    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
                    tin, tout = r.usage.input_tokens, r.usage.output_tokens
                else:
                    r = self.client.responses.create(model=self.model, instructions=system, input=user,
                                                     reasoning={"effort": "none"}, max_output_tokens=max(self.max_tokens, 16),
                                                     store=False)
                    text = r.output_text or ""
                    tin, tout = r.usage.input_tokens, r.usage.output_tokens
                usd = (tin * p["in"] + tout * p["out"]) / 1e6
                self.ledger.add(usd, tin, tout)
                return text, {"in": tin, "out": tout, "usd": usd, "s": round(time.monotonic() - t0, 3)}
            except BudgetExceeded:
                raise
            except Exception as e:  # network, rate limit, 5xx: back off and retry. Anything else surfaces after 5 tries.
                last = type(e).__name__
                time.sleep(2 ** attempt)
        raise RuntimeError(f"model call failed after 5 tries ({last})")
