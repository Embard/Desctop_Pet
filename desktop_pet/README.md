# Desktop Pet v2

Windows desktop pet with **realistic face from your photos**, true frame-by-frame walk animation, contextual phrases, and light interaction with windows and desktop icons.

## Features

- Real photo face (not cartoon/chibi)
- Walk / idle / sit / jump / interact sprite animations
- Context phrases based on location: desktop floor, taskbar, windows, shortcuts, folders
- Can sit on icons and window title bars
- Light nudge of windows and desktop icons (with cooldown)
- Full process exit from Task Manager when closed

## Run From Source

```powershell
cd desktop_pet
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python sprite_builder.py
python main.py
```

## Build EXE Locally

```powershell
.\build.ps1
```

Output: `dist\DesktopPet.exe`

## Build EXE Online (GitHub Actions)

1. Push `desktop_pet/` and `.github/` to GitHub
2. Actions → **Build Windows EXE** → Run workflow
3. Download artifact `DesktopPet-windows`

Use a **private** repository if you include personal photos.

## Controls

- **Left click + drag** — move character
- **Double click** — jump
- **Right click** — menu (jump, wave, close)
- Character walks, approaches icons/windows, reacts to cursor

## Replace Character / Animations

Put your master sprite sheet as `assets/master_spritesheet.png` and adjust crop regions in `assets/sheet_manifest.json` if needed, then run:

```powershell
python sprite_importer.py
```

Fallback: replace `assets/reference_face.png` and run `python sprite_builder.py`.

## Safety

- Does not open files or type text automatically
- Window/icon nudge has 7 second cooldown
- Skips maximized and system windows

## Close / Task Manager

Use right-click → **Закрыть**. The process fully exits (no leftover entry in Task Manager).
