

# =========================================================================== Shotrover icon set + colour scheme
# Two looks for file, folder and drive icons: "system" (whatever icon theme the desktop uses) and "shotrover",
# a built-in set in the spirit of a classic desktop file manager: yellow folders, white sheets with a coloured
# mark per file type, grey drives. The set is drawn here as small SVGs so the app stays one file and looks the
# same on every distribution. Toolbar glyphs stay the desktop's symbolic icons in both modes.
#
# The pictures are original to Shotrover. If librsvg's pixbuf loader is missing the set quietly falls back to
# the system icons.

_SR_FOLDER_GLYPHS = {
    "desktop": "<rect x='2' y='4' width='20' height='13' rx='2'/><rect x='10.5' y='17' width='3' height='2.5'/><rect x='7' y='19.5' width='10' height='2' rx='1'/>",
    "documents": "<rect x='4' y='5' width='16' height='2.6' rx='1.3'/><rect x='4' y='10.7' width='16' height='2.6' rx='1.3'/><rect x='4' y='16.4' width='10' height='2.6' rx='1.3'/>",
    "downloads": "<path d='M10.4 3h3.2v8.5h4.6L12 18 5.8 11.5h4.6z'/><rect x='5' y='19.6' width='14' height='2.2' rx='1.1'/>",
    "music": "<circle cx='8' cy='18' r='3.3'/><rect x='9.4' y='5' width='2' height='13'/><path d='M9.4 4.5l9-2.3v4.6l-9 2.3z'/><circle cx='17' cy='15.6' r='2.6'/><rect x='17.6' y='3' width='1.9' height='12.6'/>",
    "pictures": "<path d='M2 20l6.5-9 4.5 6 3-3.6 6 6.6z'/><circle cx='17' cy='6.5' r='2.4'/>",
    "videos": "<path d='M7 4l13 8-13 8z'/>",
    "home": "<path d='M12 2.5L1.8 12H5v9.5h5v-6.3h4v6.3h5V12h3.2z'/>",
}


def _sr_folder(glyph: str = "") -> str:
    g = ""
    if glyph:
        g = f"<g transform='translate(20,27.5)' fill='#9A6200' fill-opacity='0.82'>{_SR_FOLDER_GLYPHS[glyph]}</g>"
    return ("<defs><linearGradient id='f' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#FFE08A'/>"
            "<stop offset='1' stop-color='#FFC42E'/></linearGradient></defs>"
            "<path d='M6 15a4 4 0 0 1 4-4h13.5a3 3 0 0 1 2.2 1l3.6 4H54a4 4 0 0 1 4 4v30a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4z' fill='#E5A50A'/>"
            "<rect x='6' y='21' width='52' height='35' rx='4' fill='url(#f)'/>"
            "<rect x='6' y='21' width='52' height='4' rx='2' fill='#FFF3C4' fill-opacity='0.75'/>" + g)


def _sr_sheet(inner: str, fill: str = "#FBFCFD", edge: str = "#AEB8C4", fold: str = "#D9E0E8") -> str:
    return (f"<path d='M14 5h25l13 13v37a4 4 0 0 1-4 4H14a4 4 0 0 1-4-4V9a4 4 0 0 1 4-4z' fill='{fill}' stroke='{edge}' stroke-width='1.6'/>"
            f"<path d='M39 5v9a4 4 0 0 0 4 4h9z' fill='{fold}' stroke='{edge}' stroke-width='1.6' stroke-linejoin='round'/>" + inner)


def _sr_lines(colour: str) -> str:
    return "".join(f"<rect x='17' y='{y}' width='{w}' height='3' rx='1.5' fill='{colour}'/>" for y, w in ((26, 28), (33, 28), (40, 28), (47, 17)))


def _sr_drive(extra: str = "", y: int = 20) -> str:
    return ("<defs><linearGradient id='d' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#F1F4F6'/>"
            "<stop offset='1' stop-color='#C3CDD4'/></linearGradient></defs>"
            f"<rect x='5' y='{y}' width='54' height='27' rx='5' fill='url(#d)' stroke='#8799A5' stroke-width='1.6'/>"
            f"<path d='M5 {y + 16}h54v6a5 5 0 0 1-5 5H10a5 5 0 0 1-5-5z' fill='#8799A5'/>"
            f"<rect x='11' y='{y + 20}' width='24' height='3' rx='1.5' fill='#566772'/>"
            f"<circle cx='50' cy='{y + 21.5}' r='2.7' fill='#4FC3F7'/>" + extra)


_SR_ICONS: Dict[str, str] = {
    "folder": _sr_folder(),
    "folder-home": _sr_folder("home"), "folder-desktop": _sr_folder("desktop"), "folder-documents": _sr_folder("documents"),
    "folder-downloads": _sr_folder("downloads"), "folder-music": _sr_folder("music"), "folder-pictures": _sr_folder("pictures"),
    "folder-videos": _sr_folder("videos"),
    "file": _sr_sheet(_sr_lines("#C5CCD5")),
    "text": _sr_sheet(_sr_lines("#7B8CA3")),
    "image": _sr_sheet("<rect x='15' y='25' width='34' height='26' rx='3' fill='#4FC3F7'/>"
                       "<circle cx='41' cy='32' r='3.2' fill='#FFF59D'/>"
                       "<path d='M15 48v-3l10-10 7 8 5-5 12 10v0a3 3 0 0 1-3 3H18a3 3 0 0 1-3-3z' fill='#43A047'/>"),
    "video": _sr_sheet("<rect x='15' y='25' width='34' height='26' rx='3' fill='#7E57C2'/><path d='M27.5 31l12 7-12 7z' fill='#fff'/>"),
    "audio": _sr_sheet("<g transform='translate(19.5,25) scale(1.08)' fill='#FB8C00'>" + _SR_FOLDER_GLYPHS["music"] + "</g>"),
    "pdf": _sr_sheet("<rect x='4' y='30' width='43' height='18' rx='3' fill='#E53935'/>"
                     "<text x='25.5' y='44' text-anchor='middle' font-family='sans-serif' font-weight='bold' font-size='13' fill='#fff'>PDF</text>"),
    "archive": _sr_sheet("".join(f"<rect x='{24 if i % 2 else 28}' y='{8 + i * 4.5}' width='4' height='3.2' fill='#8D6E63'/>" for i in range(7))
                         + "<rect x='22.5' y='40' width='11' height='12' rx='2.5' fill='#fff' stroke='#8D6E63' stroke-width='2.4'/>"
                           "<rect x='26.5' y='44' width='3' height='4' fill='#8D6E63'/>", fill="#FFF4D0", edge="#CFA43A", fold="#F2DC9C"),
    "code": _sr_sheet("<g fill='none' stroke='#1E88E5' stroke-width='3.6' stroke-linecap='round' stroke-linejoin='round'>"
                      "<path d='M25 30l-8 8 8 8'/><path d='M39 30l8 8-8 8'/></g>"
                      "<path d='M35 27l-6 22' stroke='#90A4AE' stroke-width='3' stroke-linecap='round'/>"),
    "model": _sr_sheet("<path d='M32 23l13 6.5-13 6.5-13-6.5z' fill='#4DD0E1'/><path d='M19 29.5l13 6.5v16l-13-6.5z' fill='#00ACC1'/>"
                       "<path d='M45 29.5v16L32 52V36z' fill='#00838F'/>"),
    "volume": _sr_sheet("<g fill='#9575CD'><circle cx='24.5' cy='42' r='7.5'/><circle cx='34' cy='36' r='10'/><circle cx='42' cy='43' r='6.5'/>"
                        "<rect x='22' y='41' width='24' height='8.5' rx='4'/></g>"),
    "scene": _sr_sheet("<g stroke='#66BB6A' stroke-width='2.8'><path d='M22 31l20 8.5M22 48l20-8.5'/></g>"
                       "<circle cx='22' cy='31' r='5' fill='#66BB6A'/><circle cx='22' cy='48' r='5' fill='#66BB6A'/><circle cx='42' cy='39.5' r='6' fill='#2E7D32'/>"),
    "sheet": _sr_sheet("<rect x='15.5' y='26' width='33' height='25' rx='2.5' fill='#fff' stroke='#43A047' stroke-width='2'/>"
                       "<path d='M15.5 28.5a2.5 2.5 0 0 1 2.5-2.5h28a2.5 2.5 0 0 1 2.5 2.5V33h-33z' fill='#43A047'/>"
                       "<path d='M26.5 33v18M37.5 33v18M15.5 42h33' stroke='#43A047' stroke-width='2'/>"),
    "font": _sr_sheet("<text x='31' y='49' text-anchor='middle' font-family='serif' font-weight='bold' font-size='22' fill='#455A64'>Aa</text>"),
    "exec": _sr_sheet("<rect x='15' y='25' width='34' height='26' rx='3' fill='#37474F'/>"
                      "<path d='M20.5 32l6 6-6 6' fill='none' stroke='#80CBC4' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'/>"
                      "<rect x='29' y='42.5' width='10' height='2.8' rx='1.4' fill='#80CBC4'/>"),
    "drive": _sr_drive(),
    "drive-usb": ("<rect x='8' y='21' width='34' height='22' rx='5' fill='#607D8B'/><rect x='8' y='21' width='34' height='9' rx='4.5' fill='#78909C'/>"
                  "<rect x='42' y='25' width='15' height='14' fill='#DCE3E8' stroke='#8799A5' stroke-width='1.6'/>"
                  "<rect x='47' y='28.5' width='5' height='2.4' fill='#8799A5'/><rect x='47' y='33.1' width='5' height='2.4' fill='#8799A5'/>"
                  "<circle cx='16.5' cy='36' r='2.7' fill='#4FC3F7'/>"),
    "drive-network": _sr_drive("<rect x='30.3' y='41' width='3.4' height='9' fill='#566772'/><rect x='9' y='52' width='46' height='3.4' rx='1.7' fill='#566772'/>"
                               "<circle cx='32' cy='53.7' r='5' fill='#26A69A' stroke='#fff' stroke-width='1.4'/>", y=13),
    "computer": ("<defs><linearGradient id='s' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#63CDF8'/><stop offset='1' stop-color='#1976D2'/></linearGradient></defs>"
                 "<rect x='5' y='9' width='54' height='36' rx='4' fill='#37474F'/><rect x='9' y='13' width='46' height='28' rx='2' fill='url(#s)'/>"
                 "<rect x='27.5' y='45' width='9' height='6' fill='#78909C'/><rect x='19' y='51' width='26' height='4.4' rx='2.2' fill='#90A4AE'/>"),
    "network": ("<circle cx='32' cy='32' r='23' fill='#29B6F6' stroke='#0277BD' stroke-width='2'/>"
                "<g fill='none' stroke='#fff' stroke-width='2.2' stroke-opacity='0.85'><ellipse cx='32' cy='32' rx='9.5' ry='23'/>"
                "<path d='M9 32h46M13.5 20.5h37M13.5 43.5h37'/></g>"),
    "trash": ("<rect x='15' y='19' width='34' height='38' rx='5' fill='#90A4AE'/><rect x='11' y='13' width='42' height='7' rx='3.5' fill='#607D8B'/>"
              "<path d='M26 13V9.5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2V13' fill='none' stroke='#607D8B' stroke-width='3'/>"
              + "".join(f"<rect x='{x}' y='26' width='3.4' height='24' rx='1.7' fill='#ECEFF1'/>" for x in (22.3, 30.3, 38.3))),
    "recent": ("<circle cx='32' cy='32' r='22' fill='#F4F6F8' stroke='#546E7A' stroke-width='4.5'/>"
               "<path d='M32 18.5V32l9.5 6' fill='none' stroke='#1E88E5' stroke-width='4.5' stroke-linecap='round' stroke-linejoin='round'/>"),
    "star": "<path d='M32 6l7.9 16.4 18 2.4-13.2 12.5 3.3 17.9L32 46.4 16 55.2l3.3-17.9L6.1 24.8l18-2.4z' fill='#FFC42E' stroke='#E5A50A' stroke-width='2' stroke-linejoin='round'/>",
}

# extension → picture, for the formats a desktop MIME database knows least about (or guesses wrong)
_SR_EXT_KIND: Dict[str, str] = {}
for _kind, _exts in (
        ("model", "obj fbx abc stl ply usd usda usdc usdz gltf glb dae 3ds lwo x3d ztl zpr"),
        ("volume", "vdb bgeo geo sim bhclassic ifd"),
        ("scene", "ma mb hip hiplc hipnc hda hdalc otl nk nknc blend c4d max mud spp sbs sbsar aep prproj drp katana gaffer"),
        ("image", "exr dpx cin tif tiff png jpg jpeg jpe tga iff hdr sgi rgb psd psb tx tex rat pic bmp gif webp svg ico heic avif xcf kra cr2 cr3 nef arw dng raf"),
        ("video", "mov mp4 m4v mkv avi webm mxf mpg mpeg wmv flv r3d braw ari ogv"),
        ("audio", "wav aif aiff mp3 flac ogg oga opus m4a aac wma"),
        ("archive", "zip tar gz tgz bz2 tbz2 xz txz zst 7z rar cpio iso rpm deb jar"),
        ("code", "py pyw sh bash zsh csh js ts jsx tsx c h cpp hpp cc cs java go rs rb pl lua mel vex vfl osl glsl frag vert json xml yaml yml toml ini cfg conf html htm css"),
        ("text", "txt md rst log nfo doc docx odt rtf tex"),
        ("sheet", "csv tsv xls xlsx ods"),
        ("pdf", "pdf"),
        ("font", "ttf otf woff woff2 pfb"),
        ("exec", "run appimage exe msi desktop")):
    for _x in _exts.split():
        _SR_EXT_KIND.setdefault("." + _x, _kind)

# system icon name (exact, then prefix) → picture, for everything that is not a plain file
_SR_NAME_KIND = (
    ("user-home", "folder-home"), ("user-desktop", "folder-desktop"), ("folder-documents", "folder-documents"),
    ("folder-download", "folder-downloads"), ("folder-music", "folder-music"), ("folder-pictures", "folder-pictures"),
    ("folder-videos", "folder-videos"), ("folder", "folder"), ("inode-directory", "folder"),
    ("drive-removable", "drive-usb"), ("media-removable", "drive-usb"), ("media-flash", "drive-usb"),
    ("network-server", "drive-network"), ("folder-remote", "drive-network"), ("drive-", "drive"), ("media-", "drive"),
    ("computer", "computer"), ("network", "network"), ("user-trash", "trash"), ("document-open-recent", "recent"),
    ("starred", "star"), ("user-bookmarks", "star"),
    ("application-pdf", "pdf"), ("x-office-spreadsheet", "sheet"), ("x-office-document", "text"), ("font-", "font"),
    ("package-", "archive"), ("application-x-executable", "exec"), ("application-x-shellscript", "code"), ("text-x-script", "code"),
    ("text-html", "code"), ("image-", "image"), ("video-", "video"), ("audio-", "audio"), ("text-", "text"),
    ("application-x-generic", "file"), ("unknown", "file"),
)


def sr_icon_kind(icon, entry=None) -> Optional[str]:
    """Which Shotrover picture stands for this icon / entry, or None to keep the system icon."""
    names: List[str] = []
    if isinstance(icon, Gio.ThemedIcon):
        names = list(icon.get_names())
    if entry is not None and not getattr(entry, "is_dir", False) and getattr(entry, "name", "") \
            and not getattr(entry, "drive_kind", "") and getattr(entry, "usage", None) is None:
        low = entry.name.lower()
        ext = os.path.splitext(low)[1]
        if low.endswith((".bgeo.sc", ".bgeo.gz", ".geo.sc", ".geo.gz")):
            return "volume"
        if low.endswith((".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst")):
            return "archive"
        k = _SR_EXT_KIND.get(ext)
        if k:
            return k
    for n in names:
        base = n[:-9] if n.endswith("-symbolic") else n
        for key, kind in _SR_NAME_KIND:
            if base == key or (key.endswith("-") and base.startswith(key)) or base.startswith(key + "-"):
                return kind
    if entry is not None and not getattr(entry, "is_dir", False) and getattr(entry, "name", "") and names:
        return "file"
    return None


_SR_SVG_OK: Optional[bool] = None


def sr_icon_pixbuf(kind: str, size: int) -> Optional[GdkPixbuf.Pixbuf]:
    """Render one picture of the built-in set at `size` px. None if this system cannot rasterise SVG."""
    global _SR_SVG_OK
    body = _SR_ICONS.get(kind)
    if body is None or _SR_SVG_OK is False:
        return None
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' viewBox='0 0 64 64'>{body}</svg>"
    try:
        stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(svg.encode()))
        pb = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, size, size, True, None)
        _SR_SVG_OK = True
        return pb
    except GLib.Error:
        if _SR_SVG_OK is None:
            _SR_SVG_OK = False
        return None


# ---- colour scheme: follow the desktop, or force a light / dark look for this app only
_THEME_ORIG: Optional[Tuple[str, bool]] = None


def _gtk_theme_exists(name: str) -> bool:
    if name in ("Adwaita", "HighContrast", "HighContrastInverse"):
        return True                                   # built into GTK
    dirs = [os.path.join(HOME, ".themes"), os.path.join(GLib.get_user_data_dir(), "themes")]
    dirs += [os.path.join(d, "themes") for d in GLib.get_system_data_dirs()]
    return any(os.path.isfile(os.path.join(d, name, "gtk-3.0", "gtk.css")) for d in dirs)


def theme_variant(name: str, dark: bool) -> Tuple[str, bool]:
    """(theme name, prefer-dark flag) that shows `name` in its light or dark form. Themes differ: some honour
    the prefer-dark flag (Adwaita, anything shipping a gtk-dark.css), most ship the two looks as separate
    themes (Foo / Foo-Dark, Foo-Light / Foo-Dark, Foo-light / Foo-dark). When this theme has neither, GTK's
    own Adwaita is used so the choice always takes effect."""
    import re
    if name in ("Adwaita", "Adwaita-dark"):
        return "Adwaita", dark
    tok = re.search(r"(?i)[-_ ](dark|light)(?=$|[-_ ])", name)
    has = tok.group(1).lower() if tok else ""
    if has == ("dark" if dark else "light"):
        return name, dark
    base, tail = (name[:tok.start()], name[tok.end():]) if tok else (name, "")
    if dark:
        cands = [base + "-Dark" + tail, base + "-dark" + tail]
    else:
        cands = [base + "-Light" + tail, base + "-light" + tail] + ([base + tail] if has else [])
    for c in cands:
        if _gtk_theme_exists(c):
            return c, dark
    if not has:
        if not dark:
            return name, False                        # a plain theme is its own light form
        dirs = [os.path.join(HOME, ".themes"), os.path.join(GLib.get_user_data_dir(), "themes")]
        dirs += [os.path.join(d, "themes") for d in GLib.get_system_data_dirs()]
        if any(os.path.isfile(os.path.join(d, name, "gtk-3.0", "gtk-dark.css")) for d in dirs):
            return name, True
    return "Adwaita", dark


def apply_theme_mode(mode: str):
    """'system' restores what the desktop asked for; 'light' / 'dark' override it for this process only."""
    global _THEME_ORIG
    st = Gtk.Settings.get_default()
    if st is None:
        return
    if _THEME_ORIG is None:
        _THEME_ORIG = (st.get_property("gtk-theme-name") or "Adwaita", bool(st.get_property("gtk-application-prefer-dark-theme")))
    name, prefer = _THEME_ORIG
    if mode in ("light", "dark"):
        name, prefer = theme_variant(_THEME_ORIG[0], mode == "dark")
    if st.get_property("gtk-theme-name") != name:
        st.set_property("gtk-theme-name", name)
    if bool(st.get_property("gtk-application-prefer-dark-theme")) != prefer:
        st.set_property("gtk-application-prefer-dark-theme", prefer)


# ---- first start: pick the look once (Preferences → View changes it later)
class WelcomeDialog(Gtk.Dialog):
    SAMPLES = (("folder", None), ("folder-documents", None), ("drive-harddisk", None), ("image-x-generic", "a.png"),
               ("video-x-generic", "a.mp4"), ("application-x-generic", "a.abc"), ("application-pdf", "a.pdf"))

    def __init__(self, parent, cfg: dict, on_done: Callable):
        super().__init__(title="Welcome to Shotrover", transient_for=parent, modal=True)
        self.cfg, self.on_done = cfg, on_done
        self.set_resizable(False)
        self.add_button("_Continue", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        box = self.get_content_area()
        box.set_border_width(18)
        box.set_spacing(10)
        head = Gtk.Label(xalign=0)
        head.set_markup("<span size='x-large' weight='bold'>Choose how Shotrover looks</span>")
        box.pack_start(head, False, False, 0)
        sub = Gtk.Label(label="You can change both later in Preferences → View.", xalign=0)
        sub.get_style_context().add_class("dim-label")
        box.pack_start(sub, False, False, 0)

        lab = Gtk.Label(xalign=0, margin_top=8)
        lab.set_markup("<b>Icons</b>")
        box.pack_start(lab, False, False, 0)
        self.icon_radios = {}
        group = None
        for value, title, note in (("shotrover", "Shotrover icons", "Yellow folders and a clear picture for every production file type"),
                                   ("system", "System icons", "The icon theme your desktop already uses")):
            rb = Gtk.RadioButton.new_from_widget(group)
            group = group or rb
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=8)
            t = Gtk.Label(xalign=0)
            t.set_markup(f"<b>{title}</b>\n<small>{GLib.markup_escape_text(note)}</small>")
            card.pack_start(t, False, False, 0)
            row = Gtk.Box(spacing=10)
            for name, fname in self.SAMPLES:
                ent = None
                if fname:
                    ent = Entry()
                    ent.name = fname
                pb = ICONS.pixbuf(Gio.ThemedIcon.new_with_default_fallbacks(name), 48, ent, mode=value)
                row.pack_start(Gtk.Image.new_from_pixbuf(pb) if pb is not None else Gtk.Image.new_from_icon_name(name, Gtk.IconSize.DIALOG), False, False, 0)
            card.pack_start(row, False, False, 0)
            rb.add(card)
            rb.set_active(cfg.get("icons", "shotrover") == value)
            box.pack_start(rb, False, False, 0)
            self.icon_radios[value] = rb

        lab = Gtk.Label(xalign=0, margin_top=8)
        lab.set_markup("<b>Colours</b>")
        box.pack_start(lab, False, False, 0)
        trow = Gtk.Box(spacing=18)
        self.theme_radios = {}
        group = None
        for value, title in (("system", "Follow my desktop"), ("light", "Light"), ("dark", "Dark")):
            rb = Gtk.RadioButton.new_with_label_from_widget(group, title)
            group = group or rb
            rb.set_active(cfg.get("theme", "system") == value)
            rb.connect("toggled", lambda b, v=value: b.get_active() and apply_theme_mode(v))     # live, so the choice is seen
            trow.pack_start(rb, False, False, 0)
            self.theme_radios[value] = rb
        box.pack_start(trow, False, False, 0)
        self.connect("response", self._response)
        self.show_all()

    def _response(self, d, r):
        # closing the window any other way keeps what is selected too: the question is asked once
        self.cfg["icons"] = next((v for v, rb in self.icon_radios.items() if rb.get_active()), "shotrover")
        self.cfg["theme"] = next((v for v, rb in self.theme_radios.items() if rb.get_active()), "system")
        self.cfg["setup_done"] = True
        self.destroy()
        self.on_done()
