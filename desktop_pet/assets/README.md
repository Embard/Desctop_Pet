# Desktop Pet v2 Assets

## Primary sprite sheet (recommended)

- `master_spritesheet.png` — your full animation sheet
- `sheet_manifest.json` — crop regions for each animation clip

On startup/build, `sprite_importer.py` slices the master sheet into individual clips and writes `animations.json`.

## Fallback (if master sheet missing)

- `reference_face.png` / `reference_pose.png` — used by `sprite_builder.py`

## Rebuild clips

```powershell
python sprite_importer.py
```

## Required for GitHub Actions

Commit `master_spritesheet.png` and `sheet_manifest.json` together.
