# Library and context contract

Everything below is local and ignored by Git under `.partition/private/`:

| Path | Purpose |
| --- | --- |
| onboarding/uploads/ | Unchanged uploaded originals, UUID filenames |
| onboarding/extracted/ | Canonical extracted text and legacy metadata |
| onboarding/setup.json | Existing document IDs, profiles and reviewed context |
| onboarding/archive/ | Recoverable archived documents |
| writing/library.json | Validated classifications, confidence, sources and build fingerprint |
| writing/library/samples/STYLE/ | Organized text copies, by writing audience |
| writing/library/background/TYPE/ | Résumés and external references |
| writing/styles/STYLE/GUIDE.md | Evidence-grounded generated guide |
| writing/styles/STYLE/NEW.md | New-writing prompt template |
| writing/styles/STYLE/EDIT.md | Editing prompt template |
| writing/preferences.md | User-owned preferences from the UI |
| writing/history/ | Previous generated versions, before replacement |
| preferences.md, instructions.md | Existing user context, preserved |
| memories/ | Selected structured memory records |

Originals are never relocated or rewritten by organization. Low confidence (<0.65)
becomes Needs review. Every document ID must appear exactly once. Guide source IDs
must be writing samples from the same category; background cannot teach voice.
Corrections are durable overrides; rerun analysis to rebuild the affected guide.
The UI permits up to 40 files, 12 MB each, 120 PDF pages, and 180,000 extracted
characters per file. Scans need OCR before uploading. DOCX tables are extracted
as paragraphs; unsupported/broken files receive a per-file error without losing
successful uploads in the same batch.

Writes are atomic per file and prior generated files are backed up. A build is not
a multi-file database transaction: an OS interruption can leave a partially updated
export set. The validated library manifest is written last; rerun Build after an
interruption. A process restart interrupts an in-flight model request; retry in the
new process. File changes during analysis reject that result instead of hiding a
new upload. Run one server per project; do not edit private files concurrently in
multiple processes. Model failures before persistence leave old guides active.

The per-process browser token plus Host/Origin checks restrict local HTTP access.
The app does not offer multi-user hosting, OCR, encryption at rest, model training,
or a complete ChatGPT memory export. Prompt exports may contain personal guidance
and short sample excerpts: review them before pasting into another service.

To edit an enduring style preference, use Preferences rather than editing generated
guides that will be rebuilt. Existing manually authored profiles remain respected.
For a requested style with no samples, add examples; the app does not invent a
personal voice guide for an empty category. When writing elsewhere, adapt to the
specific subgenre, current task and audience instead of imposing academic voice
on a personal message. Private histories and old legacy active references survive;
consult the current writing/library.json rather than broad searches through backups.
