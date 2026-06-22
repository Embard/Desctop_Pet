# Character Assets

The app can use source photos directly and turn them into a small desktop pet.

Current source photo names:

- `source_idle.png` - main front pose.
- `source_pose.png` - second pose for jump/action frames.

The app removes the light background at startup, scales the person down, and
adds simple tiny legs so waist-up photos look like a small full-body character.

Recommended file names:

- `pet_idle.png` - standing pose.
- `pet_walk_1.png` - first walking pose.
- `pet_walk_2.png` - second walking pose.
- `pet_jump.png` - jumping pose.
- `pet_action.png` - waving or playful action pose.

These optional `pet_*.png` files should already have transparent background.
They are used only when source photos are missing.

If both source photos and `pet_*.png` files are missing, the app draws a
temporary placeholder character.
