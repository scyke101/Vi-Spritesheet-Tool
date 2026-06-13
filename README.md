# Vi Spritesheet Tool

A utility for converting folders of rendered sprites into texture atlases for Doom-style, boomer-shooter, billboard, and 2.5D sprite workflows.

## Features

* Combines image sequences into texture atlases
* Supports multiple input folders in a single build
* Custom output names per atlas
* Automatic animation detection from filenames
* Optional image resizing
* Chroma key background removal
* Green edge despill
* Alpha cleanup and thresholding
* Automatic sprite grounding
* Per-frame grounding exclusions
* Import animation ordering from CSV
* Export animation ordering to CSV
* Export animation index maps to TXT
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

```text
Goblin_Run/
    Run000.png
    Run001.png
    Run002.png

Goblin_Attack/
    Attack000.png
    Attack001.png
    Attack002.png
```

Each folder becomes one atlas.

Animation names are automatically determined from filename prefixes.

Examples:

```text
Idle000.png
Idle001.png
Idle002.png

Run000.png
Run001.png
Run002.png

Attack000.png
Attack001.png
Attack002.png
```

Produces three animation groups:

```text
Idle
Run
Attack
```

---

### 2. Add Input Folders

Click:

```text
Add Input Folder
```

Select one or more sprite folders.

Each folder generates its own atlas.

You can optionally assign a custom output name to each atlas.

Example:

```text
Goblin_Combat.png
Goblin_Civilian.png
Goblin_Armored.png
```

instead of:

```text
Goblin_Run_atlas.png
```

---

### 3. Choose Output Folder

Click:

```text
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
* Crisp edges

##### Lanczos

Best for:

* High-resolution renders
* Smooth downscaling

##### Bicubic / Bilinear

General-purpose alternatives.

---

## Animation Ordering

The tool can automatically organize animation groups and export their ordering information.

### Export Animation Order as CSV

Creates a CSV containing each unique animation name in the order used by the atlas.

Example:

```text
Idle
Run
Attack
Death
```

Useful for:

* Reusing animation order across characters
* Maintaining consistent atlas layouts
* Standardizing large sprite libraries

---

### Import Animation Order CSV

Imports a previously exported animation order file.

Animations matching the CSV order are placed first.

Any animations not present in the CSV are appended afterward.

This allows multiple characters to share identical atlas layouts.

---

### Export Animation Index Map (.txt)

When CSV export is enabled, the tool also creates a companion TXT file describing where each animation exists inside the final atlas frame array.

Example:

```text
Idle
0
1
2
3

Run
4
5
6
7
8

Attack
9
10
11
12
```

This is useful when:

* Building runtime animation lookup tables
* Creating import scripts
* Generating engine-side animation metadata
* Mapping atlas frame indexes back to animation groups

The TXT file contains only atlas frame indexes and animation names.

Original sprite filenames are omitted.

---

## Chroma Key Removal

Enable:

```text
Remove Background Color
```

The tool removes a specified color from the image and converts it to transparency.

Default values are tuned for Blender green-screen rendering.

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

Recommended:

```text
Enabled
```

---

## Alpha Cleanup

Converts semi-transparent edge pixels into cleaner transparency values.

Useful for anti-aliased renders and chroma-key workflows.

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

Unlike cropping-based workflows, grounding does not alter image dimensions or scaling.

Only vertical placement is adjusted.

---

### Bottom Padding

Controls the gap beneath grounded sprites.

Default:

```text
1
```

---

### Skip Grounding On Selected Frames

Certain frames may require custom positioning.

Enable:

```text
Skip grounding on listed frames
```

Then provide frame numbers:

```text
0, 5, 12-16
```

Supported formats:

```text
0
5
8-12
0,5,8-12
```

These frames retain normal centered placement.

---

## Output

Each input folder produces:

### Atlas PNG

Example:

```text
Goblin_Combat.png
```

---

### Animation Order CSV (Optional)

Example:

```text
Goblin_Combat_animation_order.csv
```

---

### Animation Index TXT (Optional)

Example:

```text
Goblin_Combat_animation_index.txt
```

---

The atlas is arranged:

```text
Left → Right
Top → Bottom
```

Frame indexes correspond directly to atlas placement order.

## Known Limitations

* Atlas generation is limited by available texture space.
* Atlas size must be divisible by cell size.
* Extremely large sprite counts may require larger atlas dimensions.
* Animated sprites must fit within the selected cell size.
* Imported CSV animation names must match detected animation prefixes.

---

## License

See LICENSE file for usage terms.
