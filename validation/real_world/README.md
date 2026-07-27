# Real-World Validation V1

This directory is for blind, manually annotated validation using lawful local
intro clips. It is separate from the synthetic golden dataset.

## Workflow

1. Add a case:

   ```powershell
   python tools/create_real_world_case.py --case-id rw-001 --title "Static talking-head intro" --category education --clip "C:\path\intro.mp4"
   ```

2. Copy the relevant entries from `expectation_template.json` into the case's
   `expectations` list in `manifest.json`. Remove metrics you cannot annotate
   and replace every example value.

3. Lock the annotations before analysis:

   ```powershell
   python tools/create_real_world_case.py --lock-case rw-001 --annotator "YOUR NAME"
   ```

4. Run locally, with network access disabled:

   ```powershell
   python tools/run_real_world_validation.py --case rw-001
   ```

Use `--reference` during case creation if a clip must remain in its original
location. Referenced paths are machine-specific. Empty expectations are valid,
but must still be deliberately locked; reports will then show zero annotation
coverage and an unevaluable accuracy result.

Never place clips here unless you have the right to use them. Stratify does not
download source material for this workflow.
