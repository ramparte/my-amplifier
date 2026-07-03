#!/usr/bin/env bash
# local-profile — swap the macstudio local-model routing profile.
#
# Two "hot workhorse" profiles that keep ONE large model resident to avoid
# model-swap thrash on the 128 GB M4 Max:
#
#   coder    — qwen3-coder-next:79B stays hot for general/coding/reasoning/etc.
#   reasoner — deepseek-r1:70B stays hot; gpt-oss:120b auto-takes-over once pulled;
#              coding routes to the small gpt-oss:20b so the reasoner stays resident.
#
# Both: fast -> gemma4:e4b (tiny), vision -> qwen3-vl:32b. The separate oMLX
# "fast-local" agent path (port 8000) is unaffected.
#
# Mechanism: rewrites routing.overrides + the ollama provider default_model in
# ~/.amplifier/settings.yaml (backed up each run). New amplifier sessions pick
# up the change; running sessions are not altered mid-flight. (Verified: under
# my-amplifier-lean, `amplifier run` honors these overrides at runtime.)
#
# Usage:
#   local-profile coder      # activate coder-hot
#   local-profile reasoner   # activate reasoner-hot
#   local-profile show       # print currently-resolved routing
#   local-profile status     # print which profile is active
set -euo pipefail

SETTINGS="$HOME/.amplifier/settings.yaml"
PROFILE="${1:-}"

usage() { sed -n '2,26p' "$0"; exit 1; }
[ -z "$PROFILE" ] && usage

case "$PROFILE" in
  coder|reasoner) ;;
  show)   exec amplifier routing show ;;
  status) grep -q 'x-local-profile: reasoner' "$SETTINGS" 2>/dev/null && echo "active profile: reasoner" || echo "active profile: coder (or unset)"; exit 0 ;;
  *) usage ;;
esac

[ -f "$SETTINGS" ] || { echo "ERROR: $SETTINGS not found"; exit 1; }
cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d-%H%M%S)"

uv run --quiet --with pyyaml python3 - "$SETTINGS" "$PROFILE" <<'PY'
import sys, yaml
settings_path, profile = sys.argv[1], sys.argv[2]

def ol(model, **extra):
    d = {"provider": "ollama", "model": model}; d.update(extra); return [d]

PROFILES = {
    "coder": {
        "workhorse": "qwen3-coder-next:latest",
        "overrides": {
            "general":        ol("qwen3-coder-next:latest"),
            "coding":         ol("qwen3-coder-next:latest"),
            "ui-coding":      ol("qwen3-coder-next:latest"),
            "reasoning":      ol("qwen3-coder-next:latest"),
            "research":       ol("qwen3-coder-next:latest"),
            "critique":       ol("qwen3-coder-next:latest"),
            "critical-ops":   ol("qwen3-coder-next:latest"),
            "security-audit": ol("qwen3-coder-next:latest"),
            "writing":        ol("qwen3.5:35b"),
            "creative":       ol("qwen3.5:35b"),
            "fast":           ol("gemma4:e4b"),
            "vision":         ol("qwen3-vl:32b"),
        },
    },
    "reasoner": {
        "workhorse": "deepseek-r1:70b",
        "overrides": {
            # gpt-oss:120b listed first; resolver skips it until pulled, then it
            # auto-activates ahead of deepseek-r1:70b.
            "general":        [{"provider": "ollama", "model": "gpt-oss:120b"},
                               {"provider": "ollama", "model": "deepseek-r1:70b"}],
            "reasoning":      [{"provider": "ollama", "model": "gpt-oss:120b"},
                               {"provider": "ollama", "model": "deepseek-r1:70b",
                                "config": {"reasoning_effort": "high"}}],
            "research":       [{"provider": "ollama", "model": "gpt-oss:120b"},
                               {"provider": "ollama", "model": "deepseek-r1:70b"}],
            "critique":       ol("deepseek-r1:70b"),
            "critical-ops":   ol("deepseek-r1:70b"),
            "security-audit": ol("deepseek-r1:70b"),
            "coding":         ol("gpt-oss:20b"),
            "ui-coding":      ol("gpt-oss:20b"),
            "writing":        ol("qwen3.5:35b"),
            "creative":       ol("qwen3.5:35b"),
            "fast":           ol("gemma4:e4b"),
            "vision":         ol("qwen3-vl:32b"),
        },
    },
}
spec = PROFILES[profile]
with open(settings_path) as f:
    data = yaml.safe_load(f) or {}
routing = data.setdefault("routing", {})
routing.setdefault("matrix", "balanced")
routing["overrides"] = spec["overrides"]
routing["x-local-profile"] = profile
for p in data.get("config", {}).get("providers", []):
    if p.get("module") == "provider-ollama":
        p.setdefault("config", {})["default_model"] = spec["workhorse"]
with open(settings_path, "w") as f:
    yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
print(f"applied profile: {profile}  (workhorse={spec['workhorse']})")
PY

echo "Done. New 'amplifier' sessions on macstudio now use the '$PROFILE' profile."
echo "(image-gen is intentionally unset — no local image model.)"
