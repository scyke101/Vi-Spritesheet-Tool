import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from PIL import Image


# Supported image file types for atlas input.
VALID_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
# Legacy regex retained only for compatibility; filename parsing is underscore-token based.
TRAILING_NUMBER_RE = re.compile(r"^(.*?)(\d+)$")


# Snap feathered alpha values to fully transparent or opaque edges.
def clamp_alpha(alpha, alpha_floor, alpha_ceiling):
    if alpha < alpha_floor:
        return 0
    if alpha > alpha_ceiling:
        return 255
    return alpha


# Split a filename into its animation name and optional numeric frame number.
#
# This is intentionally underscore-token based. A frame number may appear
# anywhere in the filename as long as that token is purely numeric:
#
#   Human_1H_Block_3      -> Human_1H_Block, 3
#   3_Human_1H_Block      -> Human_1H_Block, 3
#   Human_3_1H_Block_n    -> Human_1H_Block_n, 3
#
# Tokens such as 1H are preserved because they are not purely numeric.
def split_animation_name(path):
    tokens = [token for token in path.stem.split("_") if token]

    frame_number = None
    name_tokens = []

    for token in tokens:
        if token.isdigit():
            frame_number = int(token)
        else:
            name_tokens.append(token)

    base_name = "_".join(name_tokens)

    return base_name, frame_number


# Sort images by animation name, frame number, and filename.
def frame_sort_key(path):
    base_name, frame_number = split_animation_name(path)

    if frame_number is None:
        frame_rank = -1
        frame_value = -1
    else:
        frame_rank = 0
        frame_value = frame_number

    return (base_name.lower(), frame_rank, frame_value, path.name.lower())


# Split a normalized animation name into meaningful underscore-separated tokens.
def split_animation_tokens(animation_name):
    animation_name = normalize_animation_csv_name(animation_name)
    return [token for token in animation_name.split("_") if token]


# Build reduced animation names by preserving only tokens that identify
# a unique animation after splitting names on underscores.
#
# Important detail: names with the same token set are treated as the same
# animation before token frequency is counted. This lets both of these reduce
# to LAttack instead of destroying the only useful token:
#
#   Human_1H_LAttack
#   1H_LAttack_Human
#
# Purely numeric frame tokens are already removed by split_animation_name.
def build_unique_token_name_map(animation_names):
    tokenized_names = {}
    unique_token_sets = []
    seen_token_sets = set()

    for animation_name in animation_names:
        normalized_name = normalize_animation_csv_name(animation_name)
        tokens = split_animation_tokens(normalized_name)
        tokenized_names[normalized_name] = tokens

        token_set_key = tuple(sorted(set(token.lower() for token in tokens)))

        if token_set_key not in seen_token_sets:
            seen_token_sets.add(token_set_key)
            unique_token_sets.append(set(token.lower() for token in tokens))

    token_counts = {}

    for token_set in unique_token_sets:
        for token in token_set:
            token_counts[token] = token_counts.get(token, 0) + 1

    name_map = {}

    for animation_name in animation_names:
        normalized_name = normalize_animation_csv_name(animation_name)
        tokens = tokenized_names.get(normalized_name, [])
        kept_tokens = [
            token
            for token in tokens
            if token_counts.get(token.lower(), 0) == 1
        ]

        if kept_tokens:
            name_map[normalized_name] = "_".join(kept_tokens)
        else:
            name_map[normalized_name] = normalized_name

    return name_map


# Reduce one animation name using a prebuilt unique-token map.
def reduce_animation_name(animation_name, unique_name_map):
    normalized_name = normalize_animation_csv_name(animation_name)
    return unique_name_map.get(normalized_name, normalized_name)


# Clean frame-number separators from names written to or read from CSV.
def normalize_animation_csv_name(animation_name):
    return animation_name.strip().rstrip("_- ")


# Collect unique animation names in their current image order.
def get_animation_order_from_images(images, strip_shared_prefix=False):
    raw_order = []
    seen_raw = set()

    for img_path in images:
        base_name, _ = split_animation_name(img_path)
        base_name = normalize_animation_csv_name(base_name)
        key = base_name.lower()

        if key not in seen_raw:
            seen_raw.add(key)
            raw_order.append(base_name)

    if strip_shared_prefix:
        unique_name_map = build_unique_token_name_map(raw_order)
        candidate_order = [reduce_animation_name(name, unique_name_map) for name in raw_order]
    else:
        candidate_order = raw_order

    order = []
    seen = set()

    for animation_name in candidate_order:
        animation_name = normalize_animation_csv_name(animation_name)
        key = animation_name.lower()

        if animation_name and key not in seen:
            seen.add(key)
            order.append(animation_name)

    return order


# Read animation names from the first column of a CSV file.
def read_animation_order_csv(csv_path):
    order = []
    seen = set()

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)

        for row in reader:
            if not row:
                continue

            value = normalize_animation_csv_name(row[0])

            if not value:
                continue

            if value.lower() in {"animation", "animation_name", "name"}:
                continue

            key = value.lower()

            if key not in seen:
                seen.add(key)
                order.append(value)

    return order


# Write one animation name per row to an order CSV file.
def write_animation_order_csv(csv_path, animation_order):
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        for animation_name in animation_order:
            writer.writerow([animation_name])


# Choose display names for atlas index output.
def build_animation_display_name_map(images, imported_order=None):
    display_name_map = {}
    raw_order = []
    seen_raw = set()

    for img_path in images:
        base_name, _ = split_animation_name(img_path)
        base_name = normalize_animation_csv_name(base_name)
        key = base_name.lower()

        if key not in seen_raw:
            seen_raw.add(key)
            raw_order.append(base_name)

    if imported_order is not None:
        for base_name in raw_order:
            matched_animation = find_matching_import_animation(base_name, imported_order)
            display_name_map[base_name.lower()] = matched_animation if matched_animation else base_name
        return display_name_map

    unique_name_map = build_unique_token_name_map(raw_order)

    for base_name in raw_order:
        display_name_map[base_name.lower()] = reduce_animation_name(base_name, unique_name_map)

    return display_name_map


# Collect CSV animation names that actually matched the current image set.
def get_animation_order_from_imported_order(images, imported_order):
    matched_keys = set()

    for img_path in images:
        base_name, _ = split_animation_name(img_path)
        base_name = normalize_animation_csv_name(base_name)
        matched_animation = find_matching_import_animation(base_name, imported_order)

        if matched_animation:
            matched_keys.add(matched_animation.lower())

    return [animation_name for animation_name in imported_order if animation_name.lower() in matched_keys]


# Write animation section names followed by their final atlas frame indexes.
def write_animation_index_txt(txt_path, images, imported_order=None):
    display_name_map = build_animation_display_name_map(images, imported_order)

    with open(txt_path, "w", encoding="utf-8") as file:
        current_animation = None

        for index, img_path in enumerate(images):
            base_name, _ = split_animation_name(img_path)
            base_name = normalize_animation_csv_name(base_name)
            display_name = display_name_map.get(base_name.lower(), base_name)

            if display_name != current_animation:
                if current_animation is not None:
                    file.write("\n")

                file.write(f"{display_name}\n")
                current_animation = display_name

            file.write(f"{index}\n")


# Return True when a CSV animation name matches tokens in a source filename.
def animation_tokens_match_filename(csv_animation_name, filename_base_name):
    csv_tokens = [token.lower() for token in split_animation_tokens(csv_animation_name)]
    filename_tokens = {token.lower() for token in split_animation_tokens(filename_base_name)}

    if not csv_tokens:
        return False

    return all(token in filename_tokens for token in csv_tokens)


# Find the imported CSV animation name that best matches a source filename.
def find_matching_import_animation(base_name, imported_order):
    matches = []

    for order_index, animation_name in enumerate(imported_order):
        if animation_tokens_match_filename(animation_name, base_name):
            token_count = len(split_animation_tokens(animation_name))
            matches.append((token_count, -order_index, animation_name))

    if not matches:
        return None

    matches.sort(reverse=True)
    return matches[0][2]


# Reorder image groups to follow an imported animation order CSV.
def order_images_by_animation_csv(images, imported_order):
    groups = {}
    leftovers = []

    for img_path in images:
        base_name, frame_number = split_animation_name(img_path)
        base_name = normalize_animation_csv_name(base_name)
        matched_animation = find_matching_import_animation(base_name, imported_order)

        if matched_animation is None:
            leftovers.append((base_name, frame_number, img_path))
            print(f"CSV animation not matched for file: {img_path.name}")
            continue

        key = matched_animation.lower()
        groups.setdefault(key, []).append((frame_number, img_path))

    ordered_images = []
    used_keys = set()

    for animation_name in imported_order:
        key = animation_name.lower()

        if key not in groups:
            print(f"CSV animation not matched: {animation_name}")
            continue

        frames = sorted(
            groups[key],
            key=lambda item: (
                -1 if item[0] is None else item[0],
                item[1].name.lower()
            )
        )

        ordered_images.extend([img_path for _, img_path in frames])
        used_keys.add(key)

    leftover_keys = sorted(
        [key for key in groups.keys() if key not in used_keys],
        key=lambda value: value.lower()
    )

    for key in leftover_keys:
        frames = sorted(
            groups[key],
            key=lambda item: (
                -1 if item[0] is None else item[0],
                item[1].name.lower()
            )
        )
        ordered_images.extend([img_path for _, img_path in frames])

    leftovers = sorted(
        leftovers,
        key=lambda item: (
            item[0].lower(),
            -1 if item[1] is None else item[1],
            item[2].name.lower()
        )
    )
    ordered_images.extend([img_path for _, _, img_path in leftovers])

    return ordered_images


# Remove a target background color using tolerance, feathering, and optional despill.
def remove_color(
    img,
    target_rgb=(110, 197, 81),
    tolerance=45,
    feather=35,
    despill=True,
    use_alpha_clamp=True,
    alpha_floor=24,
    alpha_ceiling=224
):
    img = img.convert("RGBA")
    pixels = img.load()

    tr, tg, tb = target_rgb

    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            dist = ((r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2) ** 0.5

            if dist <= tolerance:
                pixels[x, y] = (r, g, b, 0)

            elif dist <= tolerance + feather:
                fade = (dist - tolerance) / feather
                new_alpha = int(a * fade)

                if use_alpha_clamp:
                    new_alpha = clamp_alpha(new_alpha, alpha_floor, alpha_ceiling)

                if despill:
                    g = min(g, int((r + b) / 2))

                pixels[x, y] = (r, g, b, new_alpha)

            else:
                if despill and g > r and g > b:
                    green_excess = g - max(r, b)
                    if green_excess > 20:
                        g = max(r, b) + 20

                pixels[x, y] = (r, g, b, a)

    return img


# Find the lowest row containing any visible pixel.
def find_lowest_visible_pixel_y(img):
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")

    for y in range(rgba.height - 1, -1, -1):
        for x in range(rgba.width):
            if alpha.getpixel((x, y)) > 0:
                return y

    return None


# Parse comma-separated frame indexes and ranges into a set.
def parse_frame_skip_list(text):
    skipped = set()
    text = text.strip()

    if not text:
        return skipped

    parts = text.split(",")

    for part in parts:
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            start, end = part.split("-", 1)
            start = int(start.strip())
            end = int(end.strip())

            if start > end:
                start, end = end, start

            skipped.update(range(start, end + 1))
        else:
            skipped.add(int(part))

    return skipped


# Main Tkinter application for building sprite atlases.
class ViSheetMaker:
    # Initialize app state, settings, and UI.
    def __init__(self, root):
        self.root = root
        self.root.title("Vi's Spritesheet Tool")

        # Store selected source folders and their output names.
        self.input_folders = []
        self.output_folder = None
        self.import_order_csv_path = None

        # Store atlas sizing and resize settings.
        self.atlas_size = tk.IntVar(value=4096)
        self.cell_size = tk.IntVar(value=512)
        self.resize_images = tk.BooleanVar(value=True)
        self.resize_filter = tk.StringVar(value="Nearest")

        # Store animation order CSV import/export settings.
        self.export_animation_order_csv = tk.BooleanVar(value=False)
        self.import_animation_order_csv = tk.BooleanVar(value=False)

        # Store sprite grounding and frame-skip settings.
        self.ground_sprites = tk.BooleanVar(value=True)
        self.bottom_padding = tk.IntVar(value=1)
        self.skip_grounding_frames = tk.BooleanVar(value=False)
        self.grounding_skip_list = tk.StringVar(value="")

        # Store chroma key and green-despill settings.
        self.use_chroma = tk.BooleanVar(value=False)
        self.bg_r = tk.IntVar(value=110)
        self.bg_g = tk.IntVar(value=197)
        self.bg_b = tk.IntVar(value=81)
        self.tolerance = tk.IntVar(value=45)
        self.feather = tk.IntVar(value=35)
        self.despill = tk.BooleanVar(value=False)

        # Store alpha cleanup thresholds.
        self.use_alpha_clamp = tk.BooleanVar(value=True)
        self.alpha_floor = tk.IntVar(value=24)
        self.alpha_ceiling = tk.IntVar(value=224)

        # Build the window controls after all variables exist.
        self.build_ui()

        self.root.update_idletasks()
        width = self.main_frame.winfo_reqwidth()
        height = self.main_frame.winfo_reqheight()
        self.root.geometry(f"{width}x{height}")

    # Bring the app window back to the front after native dialogs.
    def summon_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.update()

    # Shorten long paths to the last few folders.
    def get_display_path_tail(self, path, folder_count=3):
        path = Path(path)
        parts = list(path.parts)

        if len(parts) <= folder_count:
            return str(path)

        return ".../" + "/".join(parts[-folder_count:])

    # Find the shared leading path parts across all input folders.
    def get_common_folder_parts(self):
        # Require at least one source folder.
        if not self.input_folders:
            return []

        all_parts = [entry["path"].parts for entry in self.input_folders]
        common = []

        for parts_group in zip(*all_parts):
            first = parts_group[0]
            if all(part == first for part in parts_group):
                common.append(first)
            else:
                break

        return common

    # Display folder names relative to their shared root when possible.
    def get_display_folder_name(self, path):
        common_parts = self.get_common_folder_parts()
        path_parts = list(path.parts)

        relative_parts = path_parts[len(common_parts):]

        if not relative_parts:
            relative_parts = [path.name]

        if len(relative_parts) > 3:
            relative_parts = relative_parts[-3:]

        return "/".join(relative_parts)

    # Redraw the input folder list while preserving selection.
    def refresh_folder_list(self):
        selected = self.folder_list.curselection()
        selected_index = selected[0] if selected else None

        self.folder_list.delete(0, tk.END)

        # Build one atlas for each selected input folder.
        for entry in self.input_folders:
            display_name = self.get_display_folder_name(entry["path"])
            self.folder_list.insert(
                tk.END,
                f"{display_name}  ->  {entry['output_name']}.png"
            )

        if selected_index is not None and selected_index < len(self.input_folders):
            self.folder_list.selection_set(selected_index)

    # Create a scrollable canvas that contains the full UI.
    def build_scrollable_ui_root(self):
        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.main_frame = tk.Frame(self.canvas)
        self.main_window = self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        self.main_frame.bind("<Configure>", self.on_main_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.bind_mousewheel(self.canvas)

    # Update the canvas scroll area when content size changes.
    def on_main_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # Keep the inner UI frame matched to the canvas width.
    def on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.main_window, width=event.width)

    # Bind mouse wheel scrolling for Windows, macOS, and Linux events.
    def bind_mousewheel(self, widget):
        widget.bind_all("<MouseWheel>", self.on_mousewheel)
        widget.bind_all("<Button-4>", self.on_mousewheel)
        widget.bind_all("<Button-5>", self.on_mousewheel)

    # Scroll the canvas in response to mouse wheel movement.
    def on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Build every visible control in the application window.
    def build_ui(self):
        self.build_scrollable_ui_root()

        # Build source folder management controls.
        folder_frame = tk.Frame(self.main_frame)
        folder_frame.pack(fill="x", padx=15)

        tk.Button(folder_frame, text="Add Input Folder", command=self.add_folder).pack(side="left", padx=5)
        tk.Button(folder_frame, text="Rename Output", command=self.rename_selected_output).pack(side="left", padx=5)
        tk.Button(folder_frame, text="Remove Selected", command=self.remove_selected_folder).pack(side="left", padx=5)
        tk.Button(folder_frame, text="Clear Folders", command=self.clear_folders).pack(side="left", padx=5)

        self.folder_list = tk.Listbox(self.main_frame, width=100, height=8)
        self.folder_list.pack(padx=15, pady=10)

        # Build output folder controls.
        output_frame = tk.Frame(self.main_frame)
        output_frame.pack(fill="x", padx=15, pady=5)

        tk.Button(output_frame, text="Choose Output Folder", command=self.choose_output_folder).pack(side="left", padx=5)

        self.output_label = tk.Label(output_frame, text="No output folder selected", anchor="w")
        self.output_label.pack(side="left", padx=10)

        # Build atlas size and resize controls.
        settings_frame = tk.LabelFrame(self.main_frame, text="Atlas Settings")
        settings_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(settings_frame, text="Atlas Size").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.OptionMenu(settings_frame, self.atlas_size, 1024, 2048, 4096, 8192).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(settings_frame, text="Cell Size").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        tk.OptionMenu(settings_frame, self.cell_size, 128, 256, 512, 1024).grid(row=0, column=3, padx=5, pady=5)

        tk.Checkbutton(
            settings_frame,
            text="Resize images to fit cells",
            variable=self.resize_images
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        tk.Label(settings_frame, text="Resize Filter").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        tk.OptionMenu(
            settings_frame,
            self.resize_filter,
            "Nearest",
            "Lanczos",
            "Bicubic",
            "Bilinear"
        ).grid(row=1, column=3, padx=5, pady=5)

        # Build animation order CSV controls.
        order_frame = tk.LabelFrame(self.main_frame, text="Animation Order CSV")
        order_frame.pack(fill="x", padx=15, pady=10)

        tk.Checkbutton(
            order_frame,
            text="Export Animation Order as CSV",
            variable=self.export_animation_order_csv
        ).grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        tk.Checkbutton(
            order_frame,
            text="Import Animation Order CSV",
            variable=self.import_animation_order_csv,
            command=self.on_import_animation_order_toggled
        ).grid(row=1, column=0, padx=5, pady=5, sticky="w")

        tk.Button(
            order_frame,
            text="Choose CSV",
            command=self.choose_animation_order_csv
        ).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.import_csv_label = tk.Label(order_frame, text="No CSV selected", anchor="w")
        self.import_csv_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        # Build sprite grounding controls.
        grounding_frame = tk.LabelFrame(self.main_frame, text="Grounding")
        grounding_frame.pack(fill="x", padx=15, pady=10)

        tk.Checkbutton(
            grounding_frame,
            text="Ground sprites to bottom of cell",
            variable=self.ground_sprites
        ).grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        tk.Label(grounding_frame, text="Bottom Padding").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(grounding_frame, textvariable=self.bottom_padding, width=6).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        tk.Checkbutton(
            grounding_frame,
            text="Skip grounding on listed frames",
            variable=self.skip_grounding_frames
        ).grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        tk.Label(grounding_frame, text="Frames to Skip").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(grounding_frame, textvariable=self.grounding_skip_list, width=18).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        tk.Label(
            grounding_frame,
            text="Example: 0, 3, 8-10"
        ).grid(row=3, column=2, padx=5, pady=5, sticky="w")

        # Build chroma key and despill controls.
        chroma_frame = tk.LabelFrame(self.main_frame, text="Chroma Key / Background Removal")
        chroma_frame.pack(fill="x", padx=15, pady=10)

        tk.Checkbutton(
            chroma_frame,
            text="Remove background color",
            variable=self.use_chroma
        ).grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky="w")

        tk.Checkbutton(
            chroma_frame,
            text="Despill green edge pixels",
            variable=self.despill
        ).grid(row=0, column=4, columnspan=4, padx=5, pady=5, sticky="w")

        tk.Label(chroma_frame, text="R").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(chroma_frame, textvariable=self.bg_r, width=6).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(chroma_frame, text="G").grid(row=1, column=2, padx=5, pady=5)
        tk.Entry(chroma_frame, textvariable=self.bg_g, width=6).grid(row=1, column=3, padx=5, pady=5)

        tk.Label(chroma_frame, text="B").grid(row=1, column=4, padx=5, pady=5)
        tk.Entry(chroma_frame, textvariable=self.bg_b, width=6).grid(row=1, column=5, padx=5, pady=5)

        tk.Label(chroma_frame, text="Tolerance").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(chroma_frame, textvariable=self.tolerance, width=6).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(chroma_frame, text="Feather").grid(row=2, column=2, padx=5, pady=5)
        tk.Entry(chroma_frame, textvariable=self.feather, width=6).grid(row=2, column=3, padx=5, pady=5)

        # Build alpha cleanup controls.
        alpha_frame = tk.LabelFrame(self.main_frame, text="Alpha Cleanup")
        alpha_frame.pack(fill="x", padx=15, pady=10)

        tk.Checkbutton(
            alpha_frame,
            text="Use alpha floor / ceiling cleanup",
            variable=self.use_alpha_clamp
        ).grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky="w")

        tk.Label(alpha_frame, text="Alpha Floor").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(alpha_frame, textvariable=self.alpha_floor, width=6).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(alpha_frame, text="Alpha Ceiling").grid(row=1, column=2, padx=5, pady=5)
        tk.Entry(alpha_frame, textvariable=self.alpha_ceiling, width=6).grid(row=1, column=3, padx=5, pady=5)

        # Show recommended values for common sprite workflows.
        hint = (
            "Recommended: Tolerance 45, Feather 35, Alpha Floor 24, Alpha Ceiling 224.\n"
            "Nearest resize is best for crisp pixel/retro sprites."
        )
        tk.Label(self.main_frame, text=hint, justify="left").pack(fill="x", padx=20, pady=5)

        tk.Button(
            self.main_frame,
            text="Build Atlases",
            command=self.build_atlases,
            height=2,
            width=25
        ).pack(pady=20)

        self.status_label = tk.Label(self.main_frame, text="Ready", anchor="w")
        self.status_label.pack(fill="x", padx=15, pady=5)

    # Prompt for a CSV when import is enabled without a selected file.
    def on_import_animation_order_toggled(self):
        if self.import_animation_order_csv.get() and not self.import_order_csv_path:
            self.choose_animation_order_csv()

    # Let the user choose an animation order CSV to import.
    def choose_animation_order_csv(self):
        csv_file = filedialog.askopenfilename(
            title="Select Animation Order CSV",
            parent=self.root,
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        self.summon_window()

        if csv_file:
            self.import_order_csv_path = Path(csv_file)
            self.import_csv_label.config(
                text=self.get_display_path_tail(self.import_order_csv_path, 2)
            )
            self.import_animation_order_csv.set(True)

    # Add a source folder and prompt for its atlas output name.
    def add_folder(self):
        folder = filedialog.askdirectory(
            title="Select Input Folder",
            parent=self.root
        )

        if not folder:
            self.summon_window()
            return

        folder_path = Path(folder)

        if any(entry["path"] == folder_path for entry in self.input_folders):
            self.summon_window()
            return

        default_name = f"{folder_path.name}_atlas"

        self.summon_window()

        output_name = simpledialog.askstring(
            "Output Name",
            "Name this output atlas:",
            initialvalue=default_name,
            parent=self.root
        )

        if not output_name:
            return

        output_name = output_name.strip()

        if not output_name:
            return

        self.input_folders.append({
            "path": folder_path,
            "output_name": output_name
        })

        self.refresh_folder_list()

    # Rename the output file for the selected source folder.
    def rename_selected_output(self):
        selected = self.folder_list.curselection()

        if not selected:
            return

        index = selected[0]
        entry = self.input_folders[index]

        self.summon_window()

        new_name = simpledialog.askstring(
            "Rename Output",
            "New output atlas name:",
            initialvalue=entry["output_name"],
            parent=self.root
        )

        if not new_name:
            return

        new_name = new_name.strip()

        if not new_name:
            return

        entry["output_name"] = new_name
        self.refresh_folder_list()
        self.folder_list.selection_set(index)

    # Remove the currently selected source folder.
    def remove_selected_folder(self):
        selected = self.folder_list.curselection()

        if not selected:
            return

        index = selected[0]
        del self.input_folders[index]
        self.refresh_folder_list()

    # Remove all selected source folders.
    def clear_folders(self):
        self.input_folders.clear()
        self.refresh_folder_list()

    # Let the user choose where atlas files will be saved.
    def choose_output_folder(self):
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            parent=self.root
        )

        self.summon_window()

        if folder:
            self.output_folder = Path(folder)
            self.output_label.config(text=str(self.output_folder))

    # Convert the selected resize filter name to a Pillow resampling mode.
    def get_resample_filter(self):
        filters = {
            "Nearest": Image.Resampling.NEAREST,
            "Lanczos": Image.Resampling.LANCZOS,
            "Bicubic": Image.Resampling.BICUBIC,
            "Bilinear": Image.Resampling.BILINEAR,
        }

        return filters.get(self.resize_filter.get(), Image.Resampling.NEAREST)

    # Validate settings, process each folder, and write atlas outputs.
    def build_atlases(self):
        if not self.input_folders:
            messagebox.showerror("Error", "No input folders selected.", parent=self.root)
            return

        # Require an output folder before processing.
        if not self.output_folder:
            messagebox.showerror("Error", "No output folder selected.", parent=self.root)
            return

        # Load imported animation order only when enabled.
        imported_order = None

        if self.import_animation_order_csv.get():
            if not self.import_order_csv_path:
                messagebox.showerror("Error", "Import Animation Order CSV is enabled, but no CSV is selected.", parent=self.root)
                return

            try:
                imported_order = read_animation_order_csv(self.import_order_csv_path)
            except Exception:
                messagebox.showerror("Error", f"Could not read CSV:\n{self.import_order_csv_path}", parent=self.root)
                return

            if not imported_order:
                messagebox.showerror("Error", "The selected animation order CSV is empty.", parent=self.root)
                return

        # Calculate the grid capacity from atlas and cell size.
        atlas_size = int(self.atlas_size.get())
        cell_size = int(self.cell_size.get())

        if atlas_size % cell_size != 0:
            messagebox.showerror("Error", "Atlas size must be divisible by cell size.", parent=self.root)
            return

        grid_cols = atlas_size // cell_size
        grid_rows = atlas_size // cell_size
        max_images = grid_cols * grid_rows

        # Validate all numeric user settings before touching files.
        try:
            target_rgb = (
                int(self.bg_r.get()),
                int(self.bg_g.get()),
                int(self.bg_b.get())
            )

            tolerance = int(self.tolerance.get())
            feather = int(self.feather.get())
            alpha_floor = int(self.alpha_floor.get())
            alpha_ceiling = int(self.alpha_ceiling.get())
            bottom_padding = int(self.bottom_padding.get())
            grounding_skip_frames = parse_frame_skip_list(self.grounding_skip_list.get())

            if not all(0 <= value <= 255 for value in target_rgb):
                raise ValueError

            if tolerance < 0 or feather < 0:
                raise ValueError

            if not 0 <= alpha_floor <= 255:
                raise ValueError

            if not 0 <= alpha_ceiling <= 255:
                raise ValueError

            if alpha_floor > alpha_ceiling:
                raise ValueError

            if bottom_padding < 0:
                raise ValueError

            if any(frame < 0 for frame in grounding_skip_frames):
                raise ValueError

        except Exception:
            messagebox.showerror(
                "Error",
                "RGB, tolerance, feather, alpha floor, alpha ceiling, bottom padding, and frames to skip must be valid numbers.",
                parent=self.root
            )
            return

        # Make sure the destination folder exists.
        self.output_folder.mkdir(parents=True, exist_ok=True)

        resample_filter = self.get_resample_filter()
        built_count = 0

        for entry in self.input_folders:
            folder = entry["path"]
            output_name = entry["output_name"]

            # Gather supported image files from the current folder.
            images = [
                p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in VALID_EXTS
            ]

            # Default atlas placement order is plain alphabetical.
            # Exporting CSV/index files must NEVER change atlas placement order.
            # Only CSV import is allowed to reorder the actual atlas.
            images = sorted(images, key=lambda path: path.name.lower())

            # Reorder atlas placement by imported animation order only when provided.
            if imported_order is not None:
                images = order_images_by_animation_csv(images, imported_order)

            if not images:
                continue

            if len(images) > max_images:
                messagebox.showerror(
                    "Too Many Images",
                    f"{folder.name} has {len(images)} images, but this grid only fits {max_images}.",
                    parent=self.root
                )
                return

            # Export the unique animation order and frame index map used by this atlas.
            if self.export_animation_order_csv.get():
                if imported_order is not None:
                    animation_order = get_animation_order_from_imported_order(images, imported_order)
                else:
                    animation_order = get_animation_order_from_images(images, strip_shared_prefix=True)

                csv_output_path = self.output_folder / f"{output_name}_animation_order.csv"
                txt_output_path = self.output_folder / f"{output_name}_animation_indexes.txt"

                try:
                    write_animation_order_csv(csv_output_path, animation_order)
                    write_animation_index_txt(txt_output_path, images, imported_order)
                except Exception:
                    messagebox.showerror(
                        "Error",
                        f"Could not write animation order files:\n{csv_output_path}\n{txt_output_path}",
                        parent=self.root
                    )
                    return

            # Create a transparent atlas canvas.
            atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))

            # Process and place every frame into its grid cell.
            for index, img_path in enumerate(images):
                try:
                    img = Image.open(img_path).convert("RGBA")
                except Exception:
                    messagebox.showerror("Error", f"Could not open image:\n{img_path}", parent=self.root)
                    return

                # Remove the keyed background color when enabled.
                if self.use_chroma.get():
                    img = remove_color(
                        img,
                        target_rgb=target_rgb,
                        tolerance=tolerance,
                        feather=feather,
                        despill=self.despill.get(),
                        use_alpha_clamp=self.use_alpha_clamp.get(),
                        alpha_floor=alpha_floor,
                        alpha_ceiling=alpha_ceiling
                    )

                # Resize images proportionally to fit inside a cell.
                if self.resize_images.get():
                    img.thumbnail((cell_size, cell_size), resample_filter)

                if img.width > cell_size or img.height > cell_size:
                    messagebox.showerror(
                        "Image Too Large",
                        f"{img_path.name} is larger than the cell size and resizing is off.",
                        parent=self.root
                    )
                    return

                # Convert the image index into a grid position.
                col = index % grid_cols
                row = index // grid_cols

                x = col * cell_size + (cell_size - img.width) // 2

                # Check whether this frame should skip grounding.
                skip_this_frame = (
                    self.skip_grounding_frames.get()
                    and index in grounding_skip_frames
                )

                # Ground sprites to the cell bottom unless skipped.
                if self.ground_sprites.get() and not skip_this_frame:
                    lowest_y = find_lowest_visible_pixel_y(img)

                    if lowest_y is not None:
                        cell_bottom_y = row * cell_size + cell_size
                        y = cell_bottom_y - bottom_padding - lowest_y - 1
                    else:
                        y = row * cell_size + (cell_size - img.height) // 2
                else:
                    y = row * cell_size + (cell_size - img.height) // 2

                # Paste the frame into the atlas using alpha compositing.
                atlas.alpha_composite(img, (x, y))

            # Save the finished atlas for this folder.
            output_path = self.output_folder / f"{output_name}.png"
            atlas.save(output_path)
            built_count += 1

        # Report completion in both the status bar and a dialog.
        self.status_label.config(text=f"Done. Built {built_count} atlas file(s).")
        messagebox.showinfo("Done", f"Built {built_count} atlas file(s).", parent=self.root)


# Start the Tkinter app when this file is run directly.
if __name__ == "__main__":
    root = tk.Tk()
    app = ViSheetMaker(root)
    root.mainloop()
