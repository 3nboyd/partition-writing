# Partition Writing

Upload your writing. Build distinct style guides. Use them in any AI chat.

Partition Writing is a local sample library with automatic document organization:
PDFs, DOCX, text and Markdown go in together. One button asks your signed-in Codex
to distinguish academic, personal, professional and creative writing from résumés
and background references. It creates grounded style guides and separate prompts
for new writing and editing. Ambiguous documents go to **Needs review**.

The separate [Partition Code](https://github.com/3nboyd/partition-code) repository
handles coding orchestration. This public repository contains application source
and empty templates, never the user's private sample library.

## Start

Requires Python 3.11+ and a recent Codex CLI. Sign in with `codex login` first.

```sh
git clone https://github.com/3nboyd/partition-writing.git
cd partition-writing
python3 writing.py serve --bootstrap
```

On macOS, double-click **Start Writing.command**. Bootstrap creates an isolated
Python environment for PDF extraction; it does not alter system Python. The local
browser opens automatically (default port 8767). Keep the terminal running.

1. Drop all your files or choose a batch. No labels required.
2. Click **Organize & build guides**. The button shows progress; you can leave and
   reopen the page while the same server continues running.
3. Open a style. Choose **New writing** or **Edit my draft**, optionally describe
   the task, and copy or download the prompt for your current chat.

No model weights are trained. Guides and curated excerpts supply context. Analysis
sends excerpts and relevant saved guidance to the selected model through Codex;
local storage does not mean offline inference. Codex plan usage and account limits
apply; an API key is not required for supported ChatGPT sign-in. This app cannot
read ChatGPT saved memory automatically. An optional prompt helps you request a
summary in ChatGPT, review individual items, and import selected context.

## Existing Partition library: no repeat onboarding

```sh
# Before the first serve in the new clone:
python3 writing.py import-partition /path/to/old/partition
python3 writing.py serve --bootstrap
```

Migration copies the old `.partition/private/` files, IDs, uploads, profiles,
preferences and reviewed memories. It leaves the source untouched and refuses
conflicting destination data. The old private storage name is deliberately retained
for compatibility. Runtime environments and server status are recreated. Back up
the old project before migration; this repository's .gitignore protects the new copy.

Your originals stay in `.partition/private/onboarding/uploads/`. Organized text
copies, guides and prompts live in `.partition/private/writing/`. Private files
are ignored by Git and served only through an authenticated loopback UI. They are
not encryption-protected by this app: use normal device security and backups.
See [docs/library.md](docs/library.md) for the complete storage contract.

## Your guidance comes first

Preferences & memory is optional. Existing preferences, custom voice profiles and
instructions survive migration. Write your durable writing preferences in the UI;
rebuild once to incorporate them. Old source claims, fictional experiences, résumé
facts and academic citations must not become invented facts in new work.

Guides distinguish subgenres inside a category (for example, discussion posts
versus research papers). You can correct any document's type/category under
**Adjust**, then rebuild. A résumé is background, not a voice sample. Uncertain
authorship stays under review. Guides describe evidence and uncertainty rather than
pretending five papers establish a complete personality.

## Terminal and AI setup

```sh
python3 writing.py status
python3 writing.py build             # skips unchanged libraries
python3 writing.py build --force     # intentionally regenerate guides
python3 writing.py prompt --style academic --mode edit "Revise this draft for my seminar"
```

Another assistant can follow [SETUP_FOR_AGENTS.md](SETUP_FOR_AGENTS.md).
[MODEL_MAP.md](MODEL_MAP.md) explains the analysis model, limits and changes.
The compatibility `partition.py` module provides local memory/context utilities;
new users should use `writing.py` and the writing UI.

## Development

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-onboarding.txt
.venv/bin/python -m unittest discover -s tests -v
node --check onboarding-web/app.js
python3 scripts/check_public.py
```

CI tests supported Python versions. No credentials or real personal samples are
needed for the automated suite. Generated guides are versioned privately before
replacement. Archives preserve originals locally. Rebuild after archiving so new
guides reflect the reduced corpus.
