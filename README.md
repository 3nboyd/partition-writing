# Partition Writing

I made Partition Writing to collect my writing samples, style guides, and background
in one organized reference folder for ChatGPT. I wanted to use my own work as context
and do the writing directly in ChatGPT.

I upload my files here, let Codex organize them by style, and add the prepared
references to a ChatGPT Project. Anyone can use it with their own samples; a fresh
installation starts empty.

## Setup

Install Python 3.11+ and Codex CLI, then sign in with `codex login`.

```sh
git clone https://github.com/3nboyd/partition-writing.git
cd partition-writing
python3 writing.py serve --bootstrap
```

On macOS, I can also use **Start Writing.command**. Keep its terminal open while
using the upload page.

## Use the reference folder

1. Upload PDF, DOCX, TXT, or Markdown files. A batch is fine.
2. Click **Organize folder**, then **Open folder**.
3. In a ChatGPT Project, add the individual files inside **Upload to ChatGPT** as
   sources and paste **PROJECT INSTRUCTIONS.txt** into the project instructions.
4. Write normally in that project. The writing map points ChatGPT to the relevant style.

```text
My Writing/
  START HERE.md
  PROJECT INSTRUCTIONS.txt
  Upload to ChatGPT/       # writing map, style references, relevant background
  Academic/               # original samples, extracted text, and a style guide
  Professional/
  Background/
  Needs review/           # uncertain material stays out of the upload set
```

The folders reflect the samples provided. Academic, personal, professional, and
creative writing stay separate; résumés are background. I can correct a category
under **Adjust** and rebuild.

The folder does not automatically sync with ChatGPT. When I add samples or change
preferences, I rebuild it and replace the affected project files. Once the references
are uploaded, I can close Partition and keep working in ChatGPT.
[How ChatGPT Projects use shared files](https://learn.chatgpt.com/docs/projects).

## Files and context

My originals stay unchanged. The generated **My Writing** folder and private storage
are excluded from Git; this public repository contains code and synthetic test data.

Codex receives sample excerpts and saved guidance when organizing the library.
Its account limits apply. This creates reference files and guides, not trained model
weights. ChatGPT memory can be added through a summary I paste and review; it is
not read automatically.

## Bring an existing Partition library

Run this before opening the new installation for the first time:

```sh
python3 writing.py import-partition /path/to/old/partition
python3 writing.py serve --bootstrap
```

The import copies existing uploads, preferences, profiles, and reviewed memories.
It leaves the old library intact and refuses conflicting destination files.

## More detail

- [Setup for an AI assistant](SETUP_FOR_AGENTS.md)
- [Folder layout and storage](docs/library.md)
- [Model choice](MODEL_MAP.md)
- [Coding orchestrator](https://github.com/3nboyd/partition-code)

```sh
python3 writing.py status
python3 writing.py build
python3 writing.py export  # prepare the folder from an existing analysis
```

For development:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-onboarding.txt
.venv/bin/python -m unittest discover -s tests -v
node --check onboarding-web/app.js
python3 scripts/check_public.py
```
