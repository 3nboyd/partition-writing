# Partition Writing

Partition Writing organizes writing samples, style guides, and background material
into a reference folder for ChatGPT Projects. Upload your files, organize the folder,
and add the prepared references to ChatGPT. The writing happens there.

I started this because I wanted ChatGPT to draw on my own work while keeping
academic, professional, and personal writing separate. Anyone can use it with
their own samples; a fresh installation starts empty.

## Get started

Requires Python 3.11+ and Codex CLI. Sign in with `codex login`, then run:

```sh
git clone https://github.com/3nboyd/partition-writing.git
cd partition-writing
python3 writing.py serve --bootstrap
```

This starts a local server and opens its upload page in your browser. The first
run prepares a local Python environment with PDF support. Keep this Terminal
window open while using the page; closing the server stops the page's controls.

### On a Mac

Run `python3 install_macos.py` to add **Partition Writing** to your Applications
folder. This requires Apple Command Line Tools (`xcode-select --install`). The
launcher opens Terminal and starts the local upload page. Keep the repository
in place; the launcher uses that copy. **Start Writing.command** also works.

## Use it with ChatGPT

1. Upload PDF, DOCX, TXT, or Markdown files. You can select a batch.
2. Click **Organize folder**, then **Open folder**.
3. Create a ChatGPT Project. In the generated **My Writing** folder, open
   **Upload to ChatGPT** and add its individual files as the project's sources.
4. Open **PROJECT INSTRUCTIONS.txt** from **My Writing**. Copy its text into the
   ChatGPT project's instructions.
5. Start a chat in that project and write or edit as usual. The files supply your
   references; the pasted instructions explain how to use them.

The writing map helps ChatGPT choose the right style for the task. Once the files
are uploaded, Partition can be closed. After adding samples or changing preferences,
organize again and replace the affected project files; there is no automatic sync.
[More about ChatGPT Projects](https://learn.chatgpt.com/docs/projects).

## What the folder contains

```text
My Writing/
  START HERE.md
  PROJECT INSTRUCTIONS.txt
  Upload to ChatGPT/       # writing map and combined reference files
  Academic/               # originals, extracted text, and a style guide
  Professional/
  Background/
  Needs review/
```

Only styles supported by your writing samples get guides. **Background** holds
material such as résumés and outside references: useful facts, not examples of
your writing voice. **Needs review** holds files whose authorship or category is
uncertain; these stay out of the ChatGPT upload set until reviewed.

Use **Adjust** to correct a category, then organize the folder again.

Originals remain unchanged. The generated folder, preferences, memories, and other
private files are excluded from Git. This repository contains source code and
synthetic test data.

Organizing sends document excerpts and saved guidance through your signed-in Codex
account, subject to its usage limits. The result is a set of reference files, not
model training. ChatGPT memory can be included through a summary you paste and
review; Partition cannot retrieve it automatically.

## Bring an existing library

Before opening a fresh installation, import the old library:

```sh
python3 writing.py import-partition /path/to/old/partition
python3 writing.py serve --bootstrap
```

This copies uploads, profiles, preferences, and reviewed memories while leaving
the source intact. Conflicting destination files are preserved rather than replaced.

## Commands and documentation

```sh
python3 writing.py status
python3 writing.py build
python3 writing.py export  # prepare the folder from an existing analysis
```

- [Setup for AI assistants](SETUP_FOR_AGENTS.md)
- [Storage and folder layout](docs/library.md)
- [Model settings](MODEL_MAP.md)
- [Partition Code](https://github.com/3nboyd/partition-code)

For development:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-onboarding.txt
.venv/bin/python -m unittest discover -s tests -v
node --check onboarding-web/app.js
python3 scripts/check_public.py
```
