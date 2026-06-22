# Desktop Pet v2 Assets

## Primary (realistic character)

- `reference_face.png` — your photo (face and upper body source)
- `reference_pose.png` — second pose reference
- Generated sprite sheets (built automatically on first run):
  - `spritesheet_walk_right.png`
  - `spritesheet_walk_left.png`
  - `spritesheet_idle.png`
  - `spritesheet_sit.png`
  - `spritesheet_jump.png`
  - `spritesheet_interact.png`
  - `animations.json`

Sprite sheets are built from your real photo — **no cartoon/chibi face**. Legs are drawn to match the grey suit style because photos are waist-up only.

## Rebuild sprites

```powershell
python sprite_builder.py
```

## Optional manual sprites

If you provide ready PNG sprite sheets, update `animations.json` accordingly.
