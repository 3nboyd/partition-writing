#!/bin/zsh
set -e
cd -- "${0:A:h}"
if ! command -v codex >/dev/null 2>&1; then
  bundled_codex="/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS"
  if [[ -x "$bundled_codex/codex" ]]; then export PATH="$bundled_codex:$PATH"; fi
fi
python3 writing.py serve --bootstrap
