# Validation record

Checked 2026-10-20.

- 91 automated tests passed locally. CI repeats them on Python 3.11 and 3.13.
- Public tracked-tree audit passed, including checks for private/generated paths, credentials and machine-specific paths.
- Browser test uploaded academic and personal fixtures together, ran the one-button model analysis, produced distinct guides and copied an editing prompt containing the task and matching sample.
- A separate local library migration preserved every content file byte-for-byte; original source storage remained unchanged. Personal data was excluded from the public tree.
- PDF/DOCX extraction, local HTTP protections, context selection, guide evidence validation, classification overrides, unchanged-build skipping, concurrent-change rejection, archives, failure preservation and prompt assembly are covered.
- The real local writing library was analyzed successfully. Its guides and samples are local outputs, not public fixtures.

These checks establish observed behavior, not a guarantee of perfect model judgments.
Review uncertain classifications, and use task-specific checks for generated work.
