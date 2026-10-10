# The three XBEN eval arms (plan T4 / decision D9). Source one, then run_arm.sh.
# These set only the knobs that differ between arms; XBEN_DIR, Docker, and the
# self-hosted stack come from your environment. Fill in the model/keys.

# --- Arm 1: baseline — stock behaviour + a hosted model -------------------
# The reference number. Run against UPSTREAM strix (pip install strix, or a
# checkout at the pre-fork base) so no fork behaviour is in the baseline.
baseline_hosted() {
  export ARM_NAME="baseline-hosted"
  export STRIX_LLM="openrouter/z-ai/glm-5.3"     # a strong hosted model
  export LLM_API_KEY="…"
  export STRIX_DISABLE_BLIND_CHALLENGER=1         # baseline has no fork challenger
  unset STRIX_SKILLS_DIR
}

# --- Arm 2: fork + local model, challenger OFF ----------------------------
# Isolates the local model's effect vs the hosted baseline.
local_model() {
  export ARM_NAME="local-model"
  export STRIX_LLM="ollama_chat/…"                # your local model id
  export LLM_API_KEY="local"
  export STRIX_DISABLE_BLIND_CHALLENGER=1
  export STRIX_SKILLS_DIR="$PWD/fork_skills"
}

# --- Arm 3: fork + local model, challenger ON -----------------------------
# Isolates the blind challenger's effect on top of arm 2.
challenger_on() {
  export ARM_NAME="challenger-on"
  export STRIX_LLM="ollama_chat/…"
  export LLM_API_KEY="local"
  unset STRIX_DISABLE_BLIND_CHALLENGER            # challenger on (fork default)
  export STRIX_SKILLS_DIR="$PWD/fork_skills"
}

# Usage:
#   source evals/xben/arms.example.sh
#   baseline_hosted  && XBEN_DIR=/path/to/XBEN ./evals/xben/run_arm.sh
#   local_model      && XBEN_DIR=/path/to/XBEN ./evals/xben/run_arm.sh
#   challenger_on    && XBEN_DIR=/path/to/XBEN ./evals/xben/run_arm.sh
#   python3 evals/xben/compare.py --baseline evals/xben/results/baseline-hosted.json \
#       --arm evals/xben/results/local-model.json --arm evals/xben/results/challenger-on.json
