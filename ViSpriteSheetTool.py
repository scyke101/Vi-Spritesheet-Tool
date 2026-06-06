import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image


VALID_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def clamp_alpha(alpha, alpha_floor, alpha_ceiling):
    if alpha < alpha_floor:
        return 0
    if alpha > alpha_ceiling:
        return 255
    return alpha


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


def find_lowest_visible_pixel_y(img):
    """
    Return the lowest Y coordinate containing a non-transparent pixel.
    Does not crop, resize, or mutate the image.
    """
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")

    for y in range(rgba.height - 1, -1, -1):
        for x in range(rgba.width):
            if alpha.getpixel((x, y)) > 0:
                return y

    return None


def parse_frame_skip_list(text):
    """
    Parse a comma-separated list of frame indices and ranges.
    Examples: "0, 3, 8-10" -> {0, 3, 8, 9, 10}
    """
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


class ViSheetMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("Vi's Spritesheet Tool")

        self.input_folders = []
        self.output_folder = None

        self.atlas_size = tk.IntVar(value=4096)
        self.cell_size = tk.IntVar(value=512)
        self.resize_images = tk.BooleanVar(value=True)
        self.resize_filter = tk.StringVar(value="Nearest")

        self.ground_sprites = tk.BooleanVar(value=True)
        self.bottom_padding = tk.IntVar(value=1)
        self.skip_grounding_frames = tk.BooleanVar(value=False)
        self.grounding_skip_list = tk.StringVar(value="")

        self.use_chroma = tk.BooleanVar(value=False)
        self.bg_r = tk.IntVar(value=110)
        self.bg_g = tk.IntVar(value=197)
        self.bg_b = tk.IntVar(value=81)
        self.tolerance = tk.IntVar(value=45)
        self.feather = tk.IntVar(value=35)
        self.despill = tk.BooleanVar(value=False)

        self.use_alpha_clamp = tk.BooleanVar(value=True)
        self.alpha_floor = tk.IntVar(value=24)
        self.alpha_ceiling = tk.IntVar(value=224)

        self.build_ui()

        self.root.update_idletasks()
        width = self.main_frame.winfo_reqwidth()
        height = self.main_frame.winfo_reqheight()
        self.root.geometry(f"{width}x{height}")

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

    def on_main_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.main_window, width=event.width)

    def bind_mousewheel(self, widget):
        widget.bind_all("<MouseWheel>", self.on_mousewheel)
        widget.bind_all("<Button-4>", self.on_mousewheel)
        widget.bind_all("<Button-5>", self.on_mousewheel)

    def on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_ui(self):
        self.build_scrollable_ui_root()

        folder_frame = tk.Frame(self.main_frame)
        folder_frame.pack(fill="x", padx=15)

        tk.Button(folder_frame, text="Add Input Folder", command=self.add_folder).pack(side="left", padx=5)
        tk.Button(folder_frame, text="Remove Selected", command=self.remove_selected_folder).pack(side="left", padx=5)
        tk.Button(folder_frame, text="Clear Folders", command=self.clear_folders).pack(side="left", padx=5)

        self.folder_list = tk.Listbox(self.main_frame, width=100, height=8)
        self.folder_list.pack(padx=15, pady=10)

        output_frame = tk.Frame(self.main_frame)
        output_frame.pack(fill="x", padx=15, pady=5)

        tk.Button(output_frame, text="Choose Output Folder", command=self.choose_output_folder).pack(side="left", padx=5)

        self.output_label = tk.Label(output_frame, text="No output folder selected", anchor="w")
        self.output_label.pack(side="left", padx=10)

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

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            folder_path = Path(folder)
            if folder_path not in self.input_folders:
                self.input_folders.append(folder_path)
                self.folder_list.insert(tk.END, str(folder_path))

    def remove_selected_folder(self):
        selected = self.folder_list.curselection()
        if not selected:
            return

        index = selected[0]
        self.folder_list.delete(index)
        del self.input_folders[index]

    def clear_folders(self):
        self.input_folders.clear()
        self.folder_list.delete(0, tk.END)

    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = Path(folder)
            self.output_label.config(text=str(self.output_folder))

    def get_resample_filter(self):
        filters = {
            "Nearest": Image.Resampling.NEAREST,
            "Lanczos": Image.Resampling.LANCZOS,
            "Bicubic": Image.Resampling.BICUBIC,
            "Bilinear": Image.Resampling.BILINEAR,
        }

        return filters.get(self.resize_filter.get(), Image.Resampling.NEAREST)

    def build_atlases(self):
        if not self.input_folders:
            messagebox.showerror("Error", "No input folders selected.")
            return

        if not self.output_folder:
            messagebox.showerror("Error", "No output folder selected.")
            return

        atlas_size = int(self.atlas_size.get())
        cell_size = int(self.cell_size.get())

        if atlas_size % cell_size != 0:
            messagebox.showerror("Error", "Atlas size must be divisible by cell size.")
            return

        grid_cols = atlas_size // cell_size
        grid_rows = atlas_size // cell_size
        max_images = grid_cols * grid_rows

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
                "RGB, tolerance, feather, alpha floor, alpha ceiling, bottom padding, and frames to skip must be valid numbers."
            )
            return

        self.output_folder.mkdir(parents=True, exist_ok=True)

        resample_filter = self.get_resample_filter()
        built_count = 0

        for folder in self.input_folders:
            images = sorted([
                p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in VALID_EXTS
            ])

            if not images:
                continue

            if len(images) > max_images:
                messagebox.showerror(
                    "Too Many Images",
                    f"{folder.name} has {len(images)} images, but this grid only fits {max_images}."
                )
                return

            atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))

            for index, img_path in enumerate(images):
                try:
                    img = Image.open(img_path).convert("RGBA")
                except Exception:
                    messagebox.showerror("Error", f"Could not open image:\n{img_path}")
                    return

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

                if self.resize_images.get():
                    img.thumbnail((cell_size, cell_size), resample_filter)

                if img.width > cell_size or img.height > cell_size:
                    messagebox.showerror(
                        "Image Too Large",
                        f"{img_path.name} is larger than the cell size and resizing is off."
                    )
                    return

                col = index % grid_cols
                row = index // grid_cols

                x = col * cell_size + (cell_size - img.width) // 2

                skip_this_frame = (
                    self.skip_grounding_frames.get()
                    and index in grounding_skip_frames
                )

                if self.ground_sprites.get() and not skip_this_frame:
                    lowest_y = find_lowest_visible_pixel_y(img)

                    if lowest_y is not None:
                        cell_bottom_y = row * cell_size + cell_size
                        y = cell_bottom_y - bottom_padding - lowest_y - 1
                    else:
                        y = row * cell_size + (cell_size - img.height) // 2
                else:
                    y = row * cell_size + (cell_size - img.height) // 2

                atlas.alpha_composite(img, (x, y))

            output_path = self.output_folder / f"{folder.name}_atlas.png"
            atlas.save(output_path)
            built_count += 1

        self.status_label.config(text=f"Done. Built {built_count} atlas file(s).")
        messagebox.showinfo("Done", f"Built {built_count} atlas file(s).")


if __name__ == "__main__":
    root = tk.Tk()
    app = ViSheetMaker(root)
    root.mainloop()
