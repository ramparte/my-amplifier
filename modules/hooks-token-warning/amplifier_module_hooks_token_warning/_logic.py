"""Pure token-accounting logic for the token-warning hook.

Kept free of any ``amplifier_core`` imports so it can be unit-tested with a bare
``python3`` interpreter (no framework install required).

Token accounting notes (calibrated against the normalized ``llm:response`` usage
schema emitted by provider modules):

- ``input_tokens`` in the emitted event ALREADY folds in cache-read tokens for the
  Anthropic provider. Its ``_convert_to_chat_response`` computes
  ``input_tokens = raw_input + cache_read_input_tokens`` before emitting, and ALSO
  emits ``cache_read_tokens`` separately. Therefore summing
  ``input_tokens + cache_read_tokens`` would DOUBLE-COUNT the cache reads.
- ``cache_write_tokens`` (a.k.a. cache-creation tokens) are NOT included in
  ``input_tokens`` and represent real prompt tokens processed this call.

So the true size of the context processed on a turn is:

    effective = input_tokens + cache_write_tokens

which reproduces the audited opening-prompt figure (20,122 + 25,329 = 45,451).

Defaults below therefore count cache-write but NOT cache-read. For providers that
report ``input_tokens`` EXCLUSIVE of cache reads, set ``count_cache_read=True``.
"""

from __future__ import annotations

from typing import Any


def effective_input_tokens(
    usage: dict[str, Any],
    *,
    count_cache_read: bool = False,
    count_cache_write: bool = True,
) -> int:
    """Best-effort 'size of context processed this turn' from a usage dict.

    Missing/None fields are treated as zero. Never raises on malformed input.
    """

    def _int(key: str) -> int:
        try:
            return int(usage.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    total = _int("input_tokens")
    if count_cache_read:
        total += _int("cache_read_tokens")
    if count_cache_write:
        total += _int("cache_write_tokens")
    return total


def band_for(effective: int, threshold: int, step: int) -> int:
    """Escalation band for an effective token count.

    - band 0  => below threshold (no warning)
    - band 1  => [threshold, threshold + step)
    - band 2  => [threshold + step, threshold + 2*step)
    - ...

    Warning once per band means the user is nudged when first crossing the budget
    and again each time context grows by another ``step``, without per-turn spam.
    """
    if step <= 0:
        step = max(threshold, 1)
    if effective < threshold:
        return 0
    return 1 + (effective - threshold) // step


def format_warning(effective: int, threshold: int, model: str | None) -> str:
    """Human-facing one-line budget warning."""
    over = effective - threshold
    model_bit = f" · model: {model}" if model else ""
    return (
        f"context budget: this turn's input is ~{effective:,} tokens, "
        f"over the {threshold:,} budget by ~{over:,}{model_bit}. "
        f"Consider /compact, starting a fresh session, or trimming context."
    )
