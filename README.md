# Vi Spritesheet Tool

A simple utility for converting folders of rendered sprites into texture atlases suitable for Doom-style, boomer-shooter, and billboard sprite workflows.

## Features

* Combines image sequences into texture atlases
* Supports multiple input folders
* Optional image resizing
* Chroma key background removal
* Green edge despill
* Alpha cleanup and thresholding
* Automatic sprite grounding
* Configurable atlas and cell sizes
* PNG output with transparency

---

## Installation

### Requirements

* Python 3.10+
* Pillow

Install Pillow:

```bash
pip install pillow
```

Run:

```bash
python ViSpriteSheetTool.py
```

---

## Basic Workflow

### 1. Render Your Sprites

Render your character or object as a sequence of PNG images.

Example:

```
Goblin_Idle/
    0001.png
    0002.png
    0003.png
    ...
```

Each folder becomes one atlas.

---

### 2. Add Input Folders

Click:

```
Add Input Folder
```

Select one or more sprite folders.

Each folder will generate its own atlas.

---

### 3. Choose Output Folder

Click:

```
Choose Output Folder
```

Select where finished atlases should be saved.

---

### 4. Configure Atlas Settings

#### Atlas Size

Total texture size.

Common values:

| Size | Use Case                    |
| ---- | --------------------------- |
| 1024 | Small animations            |
| 2048 | Medium animations           |
| 4096 | Large character sets        |
| 8192 | Very large sprite libraries |

---

#### Cell Size

Size of each sprite slot.

Common values:

| Size | Use Case           |
| ---- | ------------------ |
| 128  | Small sprites      |
| 256  | Medium sprites     |
| 512  | Character sprites  |
| 1024 | Very large renders |

Atlas Size must be evenly divisible by Cell Size.

---

#### Resize Images To Fit Cells

When enabled, oversized images are automatically resized to fit inside their assigned cell.

Recommended for most workflows.

---

#### Resize Filter

##### Nearest

Best for:

* Pixel art
* Retro sprites
* Sharp edges

##### Lanczos

Best for:

* High resolution renders
* Smooth scaling

##### Bicubic / Bilinear

General-purpose alternatives.

---

## Chroma Key Removal

Enable:

```
Remove Background Color
```

The tool removes a specified color from the image and converts it to transparency.

Default values are tuned for Blender's common green-screen workflow.

### Recommended Settings

| Setting   | Value |
| --------- | ----- |
| R         | 110   |
| G         | 197   |
| B         | 81    |
| Tolerance | 45    |
| Feather   | 35    |

---

### Despill

Reduces green fringing around sprite edges after chroma removal.

Recommended: Enabled

---

## Alpha Cleanup

Converts semi-transparent edge pixels into cleaner transparency values.

Useful when rendering anti-aliased sprites.

### Recommended Values

| Setting       | Value |
| ------------- | ----- |
| Alpha Floor   | 24    |
| Alpha Ceiling | 224   |

Pixels below the floor become fully transparent.

Pixels above the ceiling become fully opaque.

---

## Sprite Grounding

Sprite grounding aligns the lowest visible pixel of each sprite to the bottom of its atlas cell.

This helps maintain consistent foot placement between animation frames.

Unlike cropping-based solutions, grounding does not alter sprite dimensions or scaling.

Only the vertical placement inside the cell is adjusted.

### Bottom Padding

Controls how many pixels of space remain beneath the sprite.

Default:

```
1
```

---

## Output

Each input folder produces one atlas:

Example:

```
Goblin_Idle_atlas.png
Goblin_Run_atlas.png
Goblin_Attack_atlas.png
```

The atlas is arranged left-to-right, top-to-bottom.

---

## Recommended Blender Workflow

1. Render character against green background.
2. Export PNG sequence.
3. Import sequence folder into Doom Sprite Maker.
4. Enable background removal.
5. Enable despill.
6. Enable grounding.
7. Build atlas.
8. Import atlas into Unreal Engine, Godot, or your preferred engine.

---

## Known Limitations

* Atlas generation is limited by available texture space.
* Atlas size must be divisible by cell size.
* Extremely large sprite counts may require larger atlas dimensions.
* Animated sprites must fit within the selected cell size.

---

## License

See LICENSE file for usage terms.
