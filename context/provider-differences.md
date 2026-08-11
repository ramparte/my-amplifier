# Amplifier: OpenAI vs Anthropic — Behavioral Differences and Mitigations

Shareable notes for anyone whose OpenAI sessions "spin off in uncontrolled ways"
while the same bundle behaves fine on Claude. Written from forensics on a real
runaway session (gpt-5.6, 6 user turns, 30 LLM calls, 28 tool calls, zero of which
did task work) plus a read of both provider modules.

Everything below is mechanical and verifiable. Line references are to the provider
modules as of 2026-08.

---

## TL;DR

Your prompts are probably fine on Claude and too heavy for gpt-5.x. But instruction
density is a **multiplier**, not the root cause. Four independent things compound:

| # | Difference | Effect on OpenAI | Anthropic equivalent |
|---|---|---|---|
| 1 | Server-side response chaining is ON by default | Context grows where local compaction can't see it | None — stateless, immune |
| 2 | Instructions are one flat string, no cache breakpoints | Whole preamble re-sent every call | 3 explicit `cache_control` breakpoints |
| 3 | High reasoning effort × dense instructions | Model executes your bundle instead of your task | Claude soft-weights standing orders |
| 4 | Orchestrator iteration limit defaults to unlimited | Nothing stops a spin | Same default — but #1 makes it bite harder |

---

## 1. Response chaining — the big one

`provider-openai` is **stateful by default**. `provider-anthropic` is not.

`enable_response_chaining` defaults to `"auto"`, which resolves to **ON for every
reasoning model** (`__init__.py:746-751`). When on, the provider sets `store=true`
and passes `previous_response_id`, sending only a 1–5 item delta per call. The
server holds the rest.

**Why that hurts:** your local context manager measures the local transcript, which
is now tiny. It never crosses `compact_threshold`, so compaction never fires, while
the server-side context grows without limit. In the session I analyzed, input tokens
went 31,380 → 190,354 across 30 calls with `compact_threshold` nominally set to
fire at 140K. Nothing fired. Nothing errored. It just would not stop.

The provider's own comments say so (`__init__.py:142-155`, `605-613`): chaining
"drives unbounded input-token growth → context_length_exceeded." Its only guards are
a one-shot chain reset on a compaction event, and a reactive retry *after* a 400 has
already been returned. Both are cleanup, not prevention.

Anthropic has no comparable mechanism. It resends the full message array every call
with explicit cache breakpoints, so what compaction measures is what the model sees.

**Mitigation** — in your bundle's `providers:` block, or the provider config in
`~/.amplifier/settings.yaml`:

```yaml
providers:
  - module: provider-openai
    config:
      enable_response_chaining: false
```

This makes OpenAI stateless per call, exactly like Anthropic, so your
`compact_threshold` becomes meaningful again. Prefix caching still works — that runs
off `prompt_cache_key` / `prompt_cache_retention`, which are separate knobs.

**Verify it took:** find `llm:request` in your session's `events.jsonl` and confirm
`data.raw.store == false` and no `previous_response_id`.

---

## 2. Context window assumptions

Most bundles were tuned when Claude was primary, so `max_tokens: 200000` (the Opus
window) is baked in. That number is wrong for gpt-5.x in both directions:

- gpt-5.6's measured hard ceiling is ~900K, but the provider's capability table
  deliberately reports **272,000** — the long-context *pricing* threshold — as the
  effective window, so unpinned sessions compact before crossing into ~2x billing
  (`_capabilities.py:360-369`).
- gpt-5.3 is 400K. gpt-5.2 and below are 200K.

**Mitigation** — set the context config to match the model you actually run:

```yaml
session:
  context:
    config:
      max_tokens: 272000        # gpt-5.6 standard-priced window
      compact_threshold: 0.7    # fires ~190K, below the pricing cliff
      compaction_notice_enabled: true
```

The notice matters. Silent compaction is how you discover the problem three hours in.

---

## 3. Instruction density — where your prompts do matter

Claude treats a large standing-orders block as a set of priors. A Responses-API model
at `effort: high` treats it as an executable specification and spends reasoning budget
satisfying it.

Measured on the runaway session:

| | Bytes | ≈ Tokens |
|---|---|---|
| `instructions` | 71,580 | 17,900 |
| `tools` schema | 67,093 | 16,800 |
| **Fixed preamble per call** | **138,673** | **~34,700** |

133 markdown headers. `MUST`×5, `STOP`×7, `NEVER`×3, `MANDATORY`×2, plus
`ALWAYS`/`REQUIRED`/`CRITICAL`. Behavioral result: 28 tool calls, **none** of them
`read_file`/`bash`/`grep`/`edit_file`. The agent only delegated (×10), re-loaded the
same skill with byte-identical args (×6), fought a mode gate (×4), and updated todos
(×5) — because the prompt told it to.

Patterns that reliably backfire on gpt-5.x:

1. **"Check before every response, even at 1% probability"** — turns every turn into a
   discovery phase. Superpowers-style mandates are the usual source.
2. **Trigger phrases on common English** — a rule that fires a multi-agent workflow on
   "I need help with…" will fire constantly. Support/story intake rules are the usual
   source.
3. **Contradictions** — e.g. skill auto-visibility disabled while another document says
   skills must always be checked. Claude picks one. gpt-5.x tries to satisfy both.
4. **Procedural personal-preference docs** — intake questionnaires, mandatory phase
   reports, "always delegate" rules. State preferences declaratively instead.
5. **Agent-roster bloat** — every registered agent's full description is inlined into
   the `delegate` tool schema. One bundle had `delegate` at 28,513 bytes, 42.5% of the
   entire tool block, largely from 12 agents that were never called.

**Mitigation:** move to a small principle-based base. The `anchors` bundle ships
~1.9 KB of static context (four behavioral principles) versus ~68 KB for the older
`exp-lean` base and ~107 KB for full Foundation. Re-add capabilities one at a time
when a real task shows they're missing. Keep methodology (superpowers, support intake,
memory) behind modes/skills that load on demand rather than every turn.

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md
```

**Measured result** of moving one personal bundle from `exp-lean` to `anchors`:

| | Before | After | Δ |
|---|---|---|---|
| `instructions` | 71,580 B | 16,233 B | **−77%** |
| `tools` schema | 67,093 B | 49,879 B | −26% |
| Total request payload | 138,673 B | 69,054 B | **−50%** |
| Registered agents | 30+ | 11 | — |

---

## 4. Reasoning effort and summary verbosity

Two defaults worth changing for an orchestrator role:

- **Effort.** Routing matrices commonly map roles to `high`/`xhigh`. High effort on a
  dense preamble is exactly the combination that produces spinning. Use `medium` for
  the main loop and raise per-delegation via `model_role`.
- **Summary.** `reasoning_summary` defaults to `"detailed"` (`_constants.py:22`).
  Valid values are `auto | concise | detailed`. Detailed summaries cost real tokens for
  no operational benefit in most sessions.

```yaml
providers:
  - module: provider-openai
    config:
      reasoning_effort: medium
      reasoning_summary: concise
```

**Known gap:** gpt-5.x's `text.verbosity` parameter is **not implemented** in
`provider-openai` — zero occurrences in the source. The primary output-length control
is unwired. Worth an upstream issue.

---

## 5. No iteration ceiling

The shared orchestrator's `max_iterations` defaults to `-1` = unlimited
(`loop-streaming/__init__.py:581-582`, `2346`). This is provider-agnostic, but chaining
means an OpenAI spin has no natural termination.

In the analyzed session, a single user prompt drove **10 internal orchestrator turns**.

```yaml
session:
  orchestrator:
    config:
      max_iterations: 40   # backstop, not a leash
```

---

## 6. Mode gates can trap the user

Not provider-specific, but it is what "uncontrolled" feels like from the driver's seat.

The superpowers `debug` mode ships `allow_clear: false` with
`allowed_transitions: [verify, brainstorm, execute-plan]`. A user who types `mode off`
gets:

```
clear_denied: Cannot clear mode while in 'debug'.
Transition to a valid next mode instead.
```

In the analyzed session the user hit cancel three times. Meanwhile the model retried
`mode(set, debug)` four times against a `warn` gate, getting denied twice.

**Mitigation:** either drop an override in `~/.amplifier/modes/debug.md` with
`allow_clear: true`, or use a base (like `anchors`) that registers `hooks-mode` with
`search_paths: []` so no external mode files load at all.

---

## Diagnosing your own session

Session events live at
`~/.amplifier/projects/<slug>/sessions/<id>/events.jsonl`. Lines are enormous — stream
them, never `cat`. Event kind is in the `event` key (not `type`); provider payloads are
under `data.raw`.

```python
import json, collections
sizes = collections.Counter()
for line in open("events.jsonl"):
    e = json.loads(line)
    sizes[e.get("event")] += len(line)
print(sizes.most_common(10))
```

Then on the first `llm:request`, check `len(data.raw.instructions)`,
`len(json.dumps(data.raw.tools))`, `data.raw.store`, `data.raw.previous_response_id`,
and `data.raw.reasoning`.

**Important caveat on file size:** a multi-megabyte `events.jsonl` is usually a
*logging* artifact, not evidence of context bloat. Amplifier serializes the full
`instructions` and `tools` blobs into both `llm:request` and `llm:response`, plus the
agent registry into `session:config` once per turn. In the analyzed session that
duplicated boilerplate was **89.6% of an 11 MB file**; actual conversation content was
~170 KB. Measure tokens, not bytes on disk.

---

## Checklist

For any bundle you intend to run against OpenAI:

1. `enable_response_chaining: false` on `provider-openai`.
2. `max_tokens` / `compact_threshold` matched to the OpenAI model, with the compaction
   notice enabled.
3. `max_iterations` set to something finite.
4. `reasoning_effort: medium` for the main loop; `reasoning_summary: concise`.
5. System prompt under ~20 KB. Audit for "check before every response" mandates,
   trigger phrases on common English, and unused agents inflating the `delegate` schema.

Items 1 and 4 are provider-scoped and cannot affect Anthropic sessions. Items 2, 3 and
5 are shared, and improve both.

---

## After the fix, tool schemas dominate

Post-migration measurement on one bundle: `tools` was 49,879 B of a 69,054 B payload —
**72%**. The largest contributors were `delegate` (11,917 B, scaling with agent count)
and 12 `team_pulse_*` tools (9,725 B). Once instructions are under control, the next
lever is trimming the tool roster and the agent registry, not the prose.
