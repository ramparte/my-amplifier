#!/usr/bin/env bash
# Start an OpenAI-profile Amplifier session in the current project.
set -euo pipefail

readonly BUNDLE="my-amplifier-oai"
readonly PROVIDER="openai"
readonly MODEL="gpt-5.6-sol"
readonly MATRIX="openai"

usage() {
    cat <<'EOF'
Usage: amplifier-oai [AMPLIFIER RUN ARGUMENTS OR PROMPT]

Starts chat with the OpenAI profile. It sets PROJECT-LOCAL OpenAI routing,
which persists in .amplifier/settings.local.yaml.

Bundle, provider, model, mode, and resume are fixed by this command.
--output-format is incompatible with its forced interactive chat mode.
EOF
}

for argument in "$@"; do
    [[ "$argument" == "--" ]] && break
    case "$argument" in
        --help)
            usage
            exit 0
            ;;
        --output-format|--output-format=*)
            printf 'ERROR: --output-format is incompatible with amplifier-oai interactive chat mode\n' >&2
            exit 2
            ;;
        -B|-B?*|--bundle|--bundle=*|-p|-p?*|--provider|--provider=*|\
        -m|-m?*|--model|--model=*|--mode|--mode=*|--resume|--resume=*)
            printf 'ERROR: bundle, provider, model, mode, and resume are fixed by amplifier-oai\n' >&2
            exit 2
            ;;
        --*)
            ;;
        -*B*|-*p*|-*m*)
            printf 'ERROR: bundle, provider, and model short options are fixed by amplifier-oai\n' >&2
            exit 2
            ;;
    esac
done

amplifier_bin="$(type -P amplifier || true)"
if [[ -z "$amplifier_bin" ]]; then
    printf 'ERROR: amplifier was not found on PATH\n' >&2
    exit 127
fi

printf 'Setting PROJECT-LOCAL routing to openai; it persists in .amplifier/settings.local.yaml.\n'
if routing_output="$("$amplifier_bin" routing use "$MATRIX" --scope local 2>&1)"; then
    :
else
    routing_status=$?
    printf 'ERROR: failed to set PROJECT-LOCAL routing to openai:\n%s\n' \
        "$routing_output" >&2
    exit "$routing_status"
fi
if ! grep -Fq -- "Routing matrix set to '$MATRIX' (local scope)" <<<"$routing_output"; then
    printf 'ERROR: routing returned success without confirming PROJECT-LOCAL openai routing:\n%s\n' \
        "$routing_output" >&2
    exit 1
fi

exec "$amplifier_bin" run --mode chat \
    --bundle "$BUNDLE" \
    --provider "$PROVIDER" \
    --model "$MODEL" \
    "$@"