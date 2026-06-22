# Desktop Pet

Windows desktop pet: a small transparent always-on-top character that walks on
the desktop, reacts to the mouse, can be dragged, and performs safe playful
actions.

## Run From Source

Open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Build EXE

Open PowerShell in this folder and run:

```powershell
.\build.ps1
```

The executable will be created here:

```text
dist\DesktopPet.exe
```

## Build Online With GitHub Actions

Push this project to GitHub, then open the repository page:

1. Go to `Actions`.
2. Select `Build Windows EXE`.
3. Click `Run workflow`.
4. Open the finished run and download the `DesktopPet-windows` artifact.

The artifact contains `DesktopPet.exe`.

Use a private repository if you add personal photos to `assets`.

## Controls

- Left mouse button: drag the character.
- Double left click: jump.
- Right mouse button: open the menu.
- The character also reacts when the cursor comes close.

## Replace The Character

Put transparent PNG images into `assets`:

- `pet_idle.png`
- `pet_walk_1.png`
- `pet_walk_2.png`
- `pet_jump.png`
- `pet_action.png`

Recommended source material: a full-body or half-body photo on a plain
background. Remove the background and export PNG files with transparency.

If no images are present, the app draws a temporary placeholder character.

## Safety Notes

This version does not click inside other windows, type text, change system
settings, or move files. The playful actions are visual only.
