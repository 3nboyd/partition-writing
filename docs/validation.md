# Validation record

Checked 2026-10-20.

- 108 automated tests passed locally. CI repeats them on Python 3.11 and 3.13.
- Public tracked-tree audit passed, including checks for private/generated paths, credentials and machine-specific paths.
- Browser checks cover batch uploads, separate style guides, reference-folder export, and copying reusable ChatGPT project instructions.
- A separate local library migration preserved every content file byte-for-byte; original source storage remained unchanged. Personal data was excluded from the public tree.
- PDF/DOCX extraction, local HTTP protections, context selection, guide evidence validation, classification overrides, unchanged-build skipping, concurrent-change rejection, archives, failure preservation and prompt assembly are covered.
- The real local writing library was analyzed successfully. Its guides and samples are local outputs, not public fixtures.

These checks establish observed behavior, not a guarantee of perfect model judgments.
Review uncertain classifications, and use task-specific checks for generated work.

- Folder export tests verify unchanged original copies, category separation, exclusion of uncertain authorship, reusable ChatGPT project instructions, stale-analysis rejection, export ownership and private export history.

Mac launchers include tests for argument handling, existing-application preservation, and stopping on project conflicts. Native compilation is also checked in CI.

A review through Partition Code identified a cross-filesystem installer backup issue. Backup now supports that case and has a regression test.
