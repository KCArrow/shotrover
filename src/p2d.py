

# =========================================================================== Find large files (disk cleanup)
# Tools → Find large files…: walk a folder in the background and list what takes the most space — big files,
# and frame sequences (render.1001.exr … render.1240.exr, cache.0001.vdb …) as ONE item with their total,
# since a VFX disk fills up with thousands of medium-sized frames rather than a few huge files. Optional
# duplicate check (same size → same head/tail → same full hash). Nothing is ever deleted from here: picked
# items go to the Recycle Bin through the normal file operation (undoable).

CLEANUP_KINDS = [
    ("Video", (".mov", ".mp4", ".mkv", ".avi", ".webm", ".mxf", ".m4v", ".mpg", ".mpeg", ".wmv", ".r3d", ".braw", ".ari", ".prores")),
    ("Renders & images", (".exr", ".dpx", ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".tga", ".hdr", ".psd", ".psb", ".tx", ".tex",
                          ".iff", ".cin", ".jp2", ".kra", ".xcf", ".dds", ".bmp", ".webp", ".heic", ".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng")),
    ("Caches & sims", (".vdb", ".bgeo", ".sc", ".geo", ".abc", ".usd", ".usdc", ".usda", ".usdz", ".bphys", ".ass", ".rs", ".vrmesh",
                       ".vrscene", ".pc2", ".mc", ".mcx", ".xml_cache", ".fur", ".ptc", ".bkm", ".sim", ".simdata", ".hipnc_cache", ".npz")),
    ("Scenes & projects", (".ma", ".mb", ".blend", ".blend1", ".hip", ".hipnc", ".hiplc", ".nk", ".max", ".c4d", ".fbx", ".obj",
                           ".ztl", ".zpr", ".spp", ".sbsar", ".sbs", ".uasset", ".umap", ".unity", ".prefab", ".aep", ".prproj", ".drp")),
    ("Archives & disk images", (".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".zst", ".iso", ".img", ".dmg",
                                ".qcow2", ".vdi", ".vmdk", ".vhd", ".vhdx", ".wim")),
    ("Audio", (".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg", ".m4a", ".aac")),
    ("Packages & installers", (".rpm", ".deb", ".flatpak", ".appimage", ".run", ".msi", ".exe", ".pkg", ".whl", ".snap")),
    ("Logs, dumps & temp", (".log", ".tmp", ".temp", ".bak", ".old", ".swp", ".dmp", ".crash", ".core", ".part", ".crdownload", ".autosave")),
]
_CLEANUP_EXT = {ext: k for k, exts in CLEANUP_KINDS for ext in exts}
_CLEANUP_SKIP = ("/proc", "/sys", "/dev", "/run", "/tmp/.X11-unix", "/var/lib/docker/overlay2", "/snap")
_SEQ_RE = re.compile(r"^(.*?)(\d{3,})(\.[A-Za-z0-9_]+(?:\.sc)?)$")


def cleanup_kind(name: str) -> str:
    """Broad type of a file for the cleanup list (by extension; core dumps, ~ backups and the like by name)."""
    low = name.lower()
    if re.match(r"^core(\.\d+)?$", low) or low.endswith("~") or low.startswith(".~lock"):
        return "Logs, dumps & temp"
    ext = low[low.rfind("."):] if "." in low else ""
    if ext in _CLEANUP_EXT:
        return _CLEANUP_EXT[ext]
    if re.search(r"\.(?:blend|ma|mb|hip)\d+$", low):                 # foo.blend1, scene.ma.bak3 …
        return "Scenes & projects"
    return "Other"


class CleanupItem:
    """One row of the cleanup list: a file, or a frame sequence (many paths, one total)."""
    __slots__ = ("name", "folder", "paths", "size", "mtime", "atime", "kind", "frames", "dup", "flag", "reason")

    def __init__(self, name, folder, paths, size, mtime, atime, kind, frames=None):
        self.name, self.folder, self.paths, self.size = name, folder, paths, size
        self.mtime, self.atime, self.kind, self.frames = mtime, atime, kind, frames
        self.dup = 0                     # duplicate group id (0 = none)
        self.flag = ""                   # "system" (warn before removing) | "info" (a hint) | ""
        self.reason = ""

    @property
    def is_sequence(self) -> bool:
        return self.frames is not None


# Where the operating system and installed software live. Removing files here breaks programs or the
# system itself (or, for the package caches and logs, should be done with the tool that owns them).
_SYSTEM_DIRS = [
    ("/boot/", "Boot file (kernel / initramfs) — removing it can stop the machine from starting"),
    ("/usr/", "System file — part of the operating system or an installed package"),
    ("/bin/", "System program"), ("/sbin/", "System program"), ("/lib/", "System library"), ("/lib64/", "System library"),
    ("/etc/", "System configuration"),
    ("/opt/", "Installed application (remove it with its uninstaller or the package manager)"),
    ("/var/lib/rpm/", "Package database"), ("/var/lib/dnf/", "Package manager data"), ("/var/lib/apt/", "Package manager data"),
    ("/var/lib/flatpak/", "Installed Flatpak app or runtime (remove with: flatpak uninstall --unused)"),
    ("/var/lib/docker/", "Docker data (clean up with: docker system prune)"),
    ("/var/lib/containers/", "Container storage (clean up with: podman system prune)"),
    ("/var/lib/libvirt/", "Virtual machine disk managed by libvirt"),
    ("/var/lib/", "Service data owned by the system"),
    ("/var/cache/dnf/", "Package manager cache (clean with: sudo dnf clean all)"),
    ("/var/cache/PackageKit/", "Package manager cache (clean with: pkcon refresh force -c -1)"),
    ("/var/cache/", "System cache"),
    ("/var/log/", "System log (trim with: sudo journalctl --vacuum-size=500M)"),
    ("/var/spool/", "System queue (mail / print / cron)"),
    ("/snap/", "Installed Snap package"), ("/nix/", "Nix store"), ("/root/", "The administrator's (root) files"),
    ("/srv/", "Data served by this machine"), ("/swapfile", "Swap file"),
]
_USER_MANAGED = [
    (".local/share/flatpak/", "info", "Installed Flatpak app (remove with: flatpak uninstall)"),
    (".var/app/", "info", "Flatpak app data — that app's settings and files"),
    (".local/share/containers/", "info", "Container images (clean up with: podman system prune)"),
    (".local/share/Steam/", "info", "Steam game or library file (remove games from Steam)"),
    (".steam/", "info", "Steam file (remove games from Steam)"),
    (".local/share/libvirt/", "info", "Virtual machine disk (remove the VM in Virtual Machine Manager)"),
    ("VirtualBox VMs/", "info", "Virtual machine disk (remove the VM in VirtualBox)"),
    (".cache/", "info", "Cache — safe to remove, the app rebuilds it"),
    (".local/share/Trash/", "info", "Already in the Recycle Bin"),
]


def _active_swaps() -> set:
    try:
        with open("/proc/swaps") as f:
            return {line.split()[0] for line in f.read().splitlines()[1:] if line.split()}
    except OSError:
        return set()


def classify_cleanup_items(items: List["CleanupItem"], home: Optional[str] = None, uid: Optional[int] = None) -> None:
    """Flag items that belong to the system ("system": warn before removing) and add hints for files a tool
    should clean up instead ("info"). Based on where the file lives, who owns it, whether you could move it
    at all, and whether it is a swap file in use."""
    home = (home or os.path.expanduser("~")).rstrip("/") + "/"
    uid = os.getuid() if uid is None else uid
    swaps = _active_swaps()
    for it in items:
        p = it.paths[0]
        reason, flag = "", ""
        if p in swaps:
            flag, reason = "system", "Swap file in use — the system needs it while it's active"
        if not flag:
            for pre, why in _SYSTEM_DIRS:
                if p.startswith(pre) or p == pre.rstrip("/"):
                    flag, reason = "system", why
                    break
        if not flag:
            try:
                st = os.lstat(p)
                owner = st.st_uid
            except OSError:
                owner = uid
            if owner != uid:
                try:
                    import pwd as _pwd
                    who = _pwd.getpwuid(owner).pw_name
                except (KeyError, ImportError):
                    who = str(owner)
                flag, reason = "system", f"Owned by {who}" + (" (the system)" if owner == 0 else " — another account's file")
        if not flag and not os.access(os.path.dirname(p), os.W_OK):
            flag, reason = "system", "Its folder is read-only for you — it would need administrator rights to remove"
        if not flag and p.startswith(home):
            rel = p[len(home):]
            for pre, fl, why in _USER_MANAGED:
                if rel.startswith(pre) or ("/" + pre) in rel:
                    flag, reason = fl, why
                    break
        if flag == "system" and it.kind in ("Logs, dumps & temp",) and p.startswith("/var/log/"):
            reason = "System log (trim with: sudo journalctl --vacuum-size=500M)"
        it.flag, it.reason = flag, reason


def _tree_bytes(path: str, cancel=None) -> int:
    total = 0
    for dp, dns, fns in os.walk(path):
        if cancel is not None and cancel.is_set():
            break
        for f in fns:
            try:
                st = os.lstat(os.path.join(dp, f))
                total += min(st.st_size, getattr(st, "st_blocks", st.st_size // 512 + 1) * 512)
            except OSError:
                pass
    return total


def scan_large_files(root: str, min_size: int, cancel: Optional[threading.Event] = None, progress=None,
                     group_sequences: bool = True, one_filesystem: bool = True, include_hidden: bool = True,
                     limit: int = 5000) -> Tuple[List[CleanupItem], dict]:
    """Walk root (no symlinks followed; optionally staying on root's filesystem so a scan of / doesn't
    descend into network shares) and return (items ≥ min_size, largest first; stats). Sizes are allocated
    blocks, so sparse files count what they really use. progress(stats, current_dir) is called every ~0.2 s."""
    root = os.path.abspath(root)
    try:
        dev = os.stat(root).st_dev
    except OSError as ex:
        raise ValueError(f"Can't read {root}: {ex.strerror or ex}")
    stats = {"files": 0, "dirs": 0, "bytes": 0, "errors": 0, "skipped_mounts": 0, "seconds": 0.0, "trash_bytes": 0}
    trash_home = os.path.join(os.path.expanduser("~"), ".local", "share", "Trash")
    t0 = last = time.monotonic()
    items: List[CleanupItem] = []
    stack = [root]
    while stack:
        if cancel is not None and cancel.is_set():
            stats["cancelled"] = True
            break
        d = stack.pop()
        stats["dirs"] += 1
        seqs: Dict[Tuple[str, str, int], list] = {}
        try:
            it = os.scandir(d)
        except OSError:
            stats["errors"] += 1
            continue
        with it:
            for de in it:
                name = de.name
                if not include_hidden and name.startswith("."):
                    continue
                try:
                    if de.is_symlink():
                        continue
                    if de.is_dir(follow_symlinks=False):
                        p = de.path
                        if p in _CLEANUP_SKIP or p.startswith(("/proc/", "/sys/")):
                            continue
                        if p == trash_home or name.startswith(".Trash-") or name == ".Trash":
                            stats["trash_bytes"] += _tree_bytes(p, cancel)        # report, don't list
                            continue
                        if one_filesystem:
                            try:
                                if de.stat(follow_symlinks=False).st_dev != dev:
                                    stats["skipped_mounts"] += 1
                                    continue
                            except OSError:
                                continue
                        stack.append(p)
                        continue
                    if not de.is_file(follow_symlinks=False):
                        continue
                    st = de.stat(follow_symlinks=False)
                except OSError:
                    stats["errors"] += 1
                    continue
                # what deleting it would free: allocated blocks for sparse files, the length for the rest
                blocks = getattr(st, "st_blocks", None)
                size = min(st.st_size, blocks * 512) if blocks is not None else st.st_size
                stats["files"] += 1
                stats["bytes"] += size
                if group_sequences:
                    m = _SEQ_RE.match(name)
                    if m:
                        head, digits, ext = m.groups()
                        seqs.setdefault((head, ext.lower(), len(digits)), []).append((int(digits), de.path, size, st.st_mtime, st.st_atime, name))
                        continue
                if size >= min_size:
                    items.append(CleanupItem(name, d, [de.path], size, st.st_mtime, st.st_atime, cleanup_kind(name)))
        for (head, ext, pad), frames in seqs.items():
            if len(frames) < 3:                                       # v001 / v002 files aren't a sequence
                for n, p, size, mt, at, name in frames:
                    if size >= min_size:
                        items.append(CleanupItem(name, d, [p], size, mt, at, cleanup_kind(name)))
                continue
            total = sum(f[2] for f in frames)
            if total < min_size:
                continue
            frames.sort()
            nums = [f[0] for f in frames]
            gaps = (nums[-1] - nums[0] + 1) - len(nums)
            label = f"{head}{'#' * pad}{frames[0][5][len(head) + pad:]}"
            item = CleanupItem(label, d, [f[1] for f in frames], total, max(f[3] for f in frames), max(f[4] for f in frames),
                               cleanup_kind(frames[0][5]), (nums[0], nums[-1], len(nums), gaps))
            items.append(item)
        now = time.monotonic()
        if progress is not None and now - last > 0.2:
            last = now
            progress(dict(stats), d)
    items.sort(key=lambda x: -x.size)
    stats["found"] = len(items)
    stats["found_bytes"] = sum(x.size for x in items)
    if len(items) > limit:
        stats["truncated"] = len(items) - limit
        items = items[:limit]
    stats["seconds"] = time.monotonic() - t0
    return items, stats


def find_duplicates(items: List[CleanupItem], cancel: Optional[threading.Event] = None, progress=None) -> int:
    """Mark single files with identical content (item.dup = group id): same size, then same first and last
    64 KB, then same SHA-256. Sequences are left out. Returns the number of duplicate groups."""
    import hashlib
    by_size: Dict[int, list] = {}
    for it in items:
        if not it.is_sequence:
            try:
                by_size.setdefault(os.path.getsize(it.paths[0]), []).append(it)
            except OSError:
                pass
    cands = [g for g in by_size.values() if len(g) > 1]

    def sample(p, size):
        with open(p, "rb") as f:
            a = f.read(65536)
            if size > 131072:
                f.seek(-65536, 2)
            return a + f.read(65536)

    def full(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(4 << 20), b""):
                if cancel is not None and cancel.is_set():
                    return None
                h.update(chunk)
        return h.digest()
    gid = 0
    done = 0
    for group in cands:
        size = os.path.getsize(group[0].paths[0]) if os.path.exists(group[0].paths[0]) else 0
        quick: Dict[bytes, list] = {}
        for it in group:
            try:
                quick.setdefault(sample(it.paths[0], size), []).append(it)
            except OSError:
                pass
        for g2 in quick.values():
            if len(g2) < 2:
                continue
            fullh: Dict[bytes, list] = {}
            for it in g2:
                if cancel is not None and cancel.is_set():
                    return gid
                try:
                    h = full(it.paths[0])
                except OSError:
                    continue
                if h is None:
                    return gid
                fullh.setdefault(h, []).append(it)
                done += 1
                if progress is not None:
                    progress(done, it.paths[0])
            for g3 in fullh.values():
                if len(g3) > 1:
                    gid += 1
                    for it in g3:
                        it.dup = gid
    return gid


class LargeFilesWindow(Gtk.Window):
    """Tools → Find large files…: scan a folder, review the biggest files and frame sequences, tick the
    ones to remove and send them to the Recycle Bin."""

    SIZES = [("10 MB", 10 << 20), ("100 MB", 100 << 20), ("500 MB", 500 << 20), ("1 GB", 1 << 30), ("5 GB", 5 << 30), ("20 GB", 20 << 30)]
    AGES = [("Any age", 0), ("Not modified in 3 months", 91), ("Not modified in 6 months", 182),
            ("Not modified in a year", 365), ("Not modified in 2 years", 730)]

    def __init__(self, win, folder: str):
        super().__init__(title="Find large files", transient_for=win)
        self.win = win
        self.cfg = win.cfg
        self.set_default_size(*self.cfg.get("cleanup_size", (980, 640)))
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.items: List[CleanupItem] = []
        self.cancel: Optional[threading.Event] = None
        self.scanning = False
        self._alive = True
        self.connect("delete-event", self._closing)
        self.connect("destroy", lambda w: setattr(self, "_alive", False))
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
        self.add(v)
        # where + what
        row = Gtk.Box(spacing=6)
        row.pack_start(Gtk.Label(label="Look in"), False, False, 0)
        self.folder = Gtk.Entry(text=folder, hexpand=True)
        self.folder.connect("activate", lambda e: self.start())
        row.pack_start(self.folder, True, True, 0)
        b = Gtk.Button(label="Browse…")
        b.connect("clicked", self._browse)
        row.pack_start(b, False, False, 0)
        self.scan_btn = Gtk.Button(label="Scan")
        self.scan_btn.get_style_context().add_class("suggested-action")
        self.scan_btn.connect("clicked", lambda b: self.stop() if self.scanning else self.start())
        row.pack_start(self.scan_btn, False, False, 0)
        v.pack_start(row, False, False, 0)
        opts = Gtk.Box(spacing=10)
        opts.pack_start(Gtk.Label(label="At least"), False, False, 0)
        self.min_combo = Gtk.ComboBoxText()
        for label, _ in self.SIZES:
            self.min_combo.append_text(label)
        self.min_combo.set_active(int(self.cfg.get("cleanup_min", 2)))
        opts.pack_start(self.min_combo, False, False, 0)
        self.seq_check = Gtk.CheckButton(label="Count frame sequences as one item", active=bool(self.cfg.get("cleanup_seq", True)))
        self.seq_check.set_tooltip_text("render.1001.exr … render.1240.exr shows as one row with the total size; "
                                        "a folder of medium-sized frames is usually where the space went")
        opts.pack_start(self.seq_check, False, False, 0)
        self.fs_check = Gtk.CheckButton(label="Stay on this drive", active=bool(self.cfg.get("cleanup_onefs", True)))
        self.fs_check.set_tooltip_text("Don't follow into other drives or network shares mounted inside this folder")
        opts.pack_start(self.fs_check, False, False, 0)
        self.dup_check = Gtk.CheckButton(label="Look for duplicates", active=bool(self.cfg.get("cleanup_dups", False)))
        self.dup_check.set_tooltip_text("Reads files of equal size to find identical copies (slower on big files)")
        opts.pack_start(self.dup_check, False, False, 0)
        v.pack_start(opts, False, False, 0)
        # filter the results
        frow = Gtk.Box(spacing=6)
        self.kind_combo = Gtk.ComboBoxText()
        for k in ["All types"] + [k for k, _ in CLEANUP_KINDS] + ["Other", "Duplicates only", "System files only"]:
            self.kind_combo.append_text(k)
        self.kind_combo.set_active(0)
        self.kind_combo.connect("changed", lambda c: self._refilter())
        frow.pack_start(self.kind_combo, False, False, 0)
        self.age_combo = Gtk.ComboBoxText()
        for label, _ in self.AGES:
            self.age_combo.append_text(label)
        self.age_combo.set_active(0)
        self.age_combo.connect("changed", lambda c: self._refilter())
        frow.pack_start(self.age_combo, False, False, 0)
        self.hide_sys = Gtk.CheckButton(label="Hide system files", active=bool(self.cfg.get("cleanup_hide_system", False)))
        self.hide_sys.set_tooltip_text("Files that belong to the operating system, installed programs or another account")
        self.hide_sys.connect("toggled", lambda c: (self.cfg.__setitem__("cleanup_hide_system", c.get_active()), self._refilter()))
        frow.pack_start(self.hide_sys, False, False, 0)
        self.name_filter = Gtk.SearchEntry(placeholder_text="Filter names and folders")
        self.name_filter.connect("search-changed", lambda e: self._refilter())
        frow.pack_start(self.name_filter, True, True, 0)
        v.pack_start(frow, False, False, 0)
        # results: check, name, size text, size, type, modified text, mtime, folder, index, tooltip, visible,
        # notes, colour (system files are drawn in the warning colour)
        self.store = Gtk.ListStore(bool, str, str, GObject.TYPE_INT64, str, str, float, str, int, str, bool, str, str)
        self.filtered = self.store.filter_new()
        self.filtered.set_visible_column(10)
        self.sorted = Gtk.TreeModelSort(model=self.filtered)
        self.sorted.set_sort_column_id(3, Gtk.SortType.DESCENDING)
        tv = Gtk.TreeView(model=self.sorted)
        tv.set_tooltip_column(9)
        tv.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        tv.connect("row-activated", lambda t, p, c: self._reveal_rows([p]))
        tv.connect("button-press-event", self._button)
        tv.connect("key-press-event", self._key)
        tog = Gtk.CellRendererToggle()
        tog.connect("toggled", self._toggled)
        c = Gtk.TreeViewColumn("", tog, active=0)
        tv.append_column(c)
        for title, col, sort, expand, ell in (("Name", 1, 1, True, Pango.EllipsizeMode.MIDDLE), ("Size", 2, 3, False, None),
                                              ("Type", 4, 4, False, None), ("Modified", 5, 6, False, None),
                                              ("Notes", 11, 11, False, Pango.EllipsizeMode.END),
                                              ("Folder", 7, 7, True, Pango.EllipsizeMode.START)):
            r = Gtk.CellRendererText()
            if ell:
                r.set_property("ellipsize", ell)
            if col == 2:
                r.set_property("xalign", 1.0)
            if col == 11:
                r.set_property("max-width-chars", 34)
            cc = Gtk.TreeViewColumn(title, r, text=col)
            cc.add_attribute(r, "foreground", 12)
            cc.set_sort_column_id(sort)
            cc.set_resizable(True)
            cc.set_expand(expand)
            cc.set_min_width(70 if not expand else 160)
            tv.append_column(cc)
        self.view = tv
        sw = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        sw.add(tv)
        self.stack = Gtk.Stack()
        self.empty = Gtk.Label(label="Pick a folder (or a whole drive) and press Scan.\nThe biggest files and frame sequences "
                                     "are listed here; nothing is removed until you tick items and choose Move to Recycle Bin.",
                               justify=Gtk.Justification.CENTER, wrap=True)
        self.empty.get_style_context().add_class("dim-label")
        self.stack.add_named(self.empty, "empty")
        self.stack.add_named(sw, "list")
        v.pack_start(self.stack, True, True, 0)
        # status + actions
        self.status = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE)
        self.status.get_style_context().add_class("dim-label")
        v.pack_start(self.status, False, False, 0)
        act = Gtk.Box(spacing=6)
        self.spinner = Gtk.Spinner()
        act.pack_start(self.spinner, False, False, 0)
        self.sel_label = Gtk.Label(xalign=0)
        act.pack_start(self.sel_label, True, True, 0)
        self.reveal_btn = Gtk.Button(label="Show in folder")
        self.reveal_btn.connect("clicked", lambda b: self._reveal_rows(self.view.get_selection().get_selected_rows()[1]))
        act.pack_end(self.reveal_btn, False, False, 0)
        self.trash_btn = Gtk.Button(label="Move to Recycle Bin")
        self.trash_btn.get_style_context().add_class("destructive-action")
        self.trash_btn.set_sensitive(False)
        self.trash_btn.connect("clicked", lambda b: self._trash_checked())
        act.pack_end(self.trash_btn, False, False, 0)
        v.pack_start(act, False, False, 0)
        self._update_selection()
        self.show_all()

    # ---- scanning
    def _browse(self, btn):
        d = pick_folder(self, "Look for large files in", self.folder.get_text() or HOME)
        if d:
            self.folder.set_text(d)

    def start(self):
        root = os.path.expanduser(self.folder.get_text().strip()) or HOME
        if not os.path.isdir(root):
            self.status.set_text(f"Not a folder: {root}")
            return
        self.cfg["cleanup_min"] = self.min_combo.get_active()
        self.cfg["cleanup_seq"] = self.seq_check.get_active()
        self.cfg["cleanup_onefs"] = self.fs_check.get_active()
        self.cfg["cleanup_dups"] = self.dup_check.get_active()
        save_config(self.cfg)
        min_size = self.SIZES[max(0, self.min_combo.get_active())][1]
        self.cancel = threading.Event()
        cancel = self.cancel
        self.scanning = True
        self.scan_btn.set_label("Stop")
        self.spinner.start()
        self.store.clear()
        self.items = []
        self.stack.set_visible_child_name("list")
        self._update_selection()
        seq, onefs, dups = self.seq_check.get_active(), self.fs_check.get_active(), self.dup_check.get_active()
        self.status.set_text(f"Scanning {root}…")

        def prog(stats, d):
            GLib.idle_add(lambda: (self._alive and cancel is self.cancel and self.status.set_text(
                f"Scanning… {stats['files']:,} files in {stats['dirs']:,} folders, {fmt_size(stats['bytes'])} · {d}"), False)[1])

        def work():
            try:
                items, stats = scan_large_files(root, min_size, cancel, prog, seq, onefs)
                classify_cleanup_items(items)
                if dups and not cancel.is_set():
                    GLib.idle_add(lambda: (self._alive and self.status.set_text("Checking for duplicates…"), False)[1])
                    stats["dup_groups"] = find_duplicates(items, cancel, lambda n, p: GLib.idle_add(
                        lambda: (self._alive and cancel is self.cancel and self.status.set_text(f"Checking for duplicates… {n:,} compared · {p}"), False)[1]))
                err = None
            except Exception as ex:
                items, stats, err = [], {}, str(ex)
            GLib.idle_add(done, items, stats, err)

        def done(items, stats, err):
            if not self._alive or cancel is not self.cancel:
                return False
            self.scanning = False
            self.scan_btn.set_label("Scan")
            self.spinner.stop()
            if err:
                self.status.set_text(err)
                return False
            self._fill(items)
            s = (f"{stats.get('files', 0):,} files, {fmt_size(stats.get('bytes', 0))} looked at in {stats.get('seconds', 0):.1f} s · "
                 f"{len(items):,} items of {self.min_combo.get_active_text()} or more, {fmt_size(stats.get('found_bytes', 0))} in all")
            if stats.get("truncated"):
                s += f" (largest {len(items):,} shown)"
            if stats.get("dup_groups"):
                s += f" · {stats['dup_groups']} sets of duplicates"
            if stats.get("skipped_mounts"):
                s += f" · {stats['skipped_mounts']} other drive{'s' if stats['skipped_mounts'] != 1 else ''} skipped"
            if stats.get("errors"):
                s += f" · {stats['errors']:,} unreadable"
            if stats.get("trash_bytes", 0) >= (100 << 20):
                s += f" · the Recycle Bin holds {fmt_size(stats['trash_bytes'])} (Tools → Empty Recycle Bin)"
            if stats.get("cancelled"):
                s = "Stopped early — " + s
            self.status.set_text(s)
            if not items:
                self.empty.set_text(f"Nothing of {self.min_combo.get_active_text()} or more in {root}.")
                self.stack.set_visible_child_name("empty")
            return False
        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        if self.cancel is not None:
            self.cancel.set()

    def _closing(self, *a):
        self.stop()
        try:
            self.cfg["cleanup_size"] = tuple(self.get_size())
            save_config(self.cfg)
        except Exception:
            pass
        return False

    # ---- list
    def _fill(self, items: List[CleanupItem]):
        self.items = items
        self.store.clear()
        fmt = self.cfg.get("date_format", "%Y-%m-%d %H:%M")
        for i, it in enumerate(items):
            name = it.name
            tip = os.path.join(it.folder, it.name)
            if it.is_sequence:
                a, b, n, gaps = it.frames
                name = f"{it.name}  ({a}–{b}, {n:,} frames)"
                tip = f"{os.path.join(it.folder, it.name)}\n{n:,} frames, {a}–{b}" + (f", {gaps:,} missing" if gaps else "")
            if it.dup:
                others = [x for x in items if x.dup == it.dup and x is not it]
                name += "  · duplicate"
                tip += "\nSame content as:\n" + "\n".join(os.path.join(x.folder, x.name) for x in others[:6])
            kind = it.kind + (" (sequence)" if it.is_sequence else "")
            notes, colour = "", None
            if it.flag == "system":
                notes, colour = "⚠ System · " + it.reason, "#d9822b"
                tip += "\n⚠ " + it.reason
            elif it.flag == "info":
                notes = it.reason
                tip += "\n" + it.reason
            self.store.append([False, name, fmt_size(it.size), it.size, kind, fmt_date(it.mtime, fmt), float(it.mtime),
                               it.folder, i, GLib.markup_escape_text(tip), True, notes, colour])
        self._refilter()
        self._update_selection()

    def _refilter(self):
        kind = self.kind_combo.get_active_text() or "All types"
        days = self.AGES[max(0, self.age_combo.get_active())][1]
        q = self.name_filter.get_text().strip().lower()
        cutoff = time.time() - days * 86400 if days else None
        for row in self.store:
            it = self.items[row[8]]
            vis = True
            if kind == "Duplicates only":
                vis = bool(it.dup)
            elif kind == "System files only":
                vis = it.flag == "system"
            elif kind != "All types":
                vis = it.kind == kind
            if vis and cutoff is not None:
                vis = it.mtime < cutoff
            if vis and q:
                vis = q in it.name.lower() or q in it.folder.lower()
            if vis and self.hide_sys.get_active() and it.flag == "system" and kind != "System files only":
                vis = False
            row[10] = vis
        self.filtered.refilter()
        self._update_selection()

    def _toggled(self, cell, path):
        it = self.sorted.get_iter(Gtk.TreePath(path))
        child = self.filtered.convert_iter_to_child_iter(self.sorted.convert_iter_to_child_iter(it))
        self.store.set_value(child, 0, not self.store.get_value(child, 0))
        self._update_selection()

    def _checked(self) -> List[CleanupItem]:
        return [self.items[row[8]] for row in self.store if row[0] and row[10]]

    def _update_selection(self):
        chk = self._checked()
        shown = sum(1 for r in self.store if r[10])
        shown_b = sum(self.items[r[8]].size for r in self.store if r[10]) if self.items else 0
        if chk:
            nsys = sum(1 for x in chk if x.flag == "system")
            text = f"{len(chk):,} ticked · {fmt_size(sum(x.size for x in chk))} would be freed"
            if nsys:
                self.sel_label.set_markup(GLib.markup_escape_text(text) +
                                          f"  <span foreground='#d9822b'>⚠ {nsys} system file{'s' if nsys != 1 else ''}</span>")
            else:
                self.sel_label.set_text(text)
        else:
            self.sel_label.set_text(f"{shown:,} shown · {fmt_size(shown_b)}" if self.items else "")
        self.trash_btn.set_sensitive(bool(chk))

    def _rows_items(self, tree_paths) -> List[CleanupItem]:
        out = []
        for p in tree_paths:
            it = self.sorted.get_iter(p)
            out.append(self.items[self.sorted.get_value(it, 8)])
        return out

    def _reveal_rows(self, tree_paths):
        its = self._rows_items(tree_paths)
        if not its:
            return
        it = its[0]
        self.win.tab.remember[it.folder] = os.path.basename(it.paths[0])
        self.win.navigate(it.folder)
        self.win.present()

    def _button(self, tv, event):
        if event.button != 3:
            return False
        hit = tv.get_path_at_pos(int(event.x), int(event.y))
        if not hit:
            return False
        sel = tv.get_selection()
        if not sel.path_is_selected(hit[0]):
            sel.unselect_all()
            sel.select_path(hit[0])
        rows = sel.get_selected_rows()[1]
        its = self._rows_items(rows)
        menu = Gtk.Menu()
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        def set_checks(on):
            for p in rows:
                it = self.sorted.get_iter(p)
                child = self.filtered.convert_iter_to_child_iter(self.sorted.convert_iter_to_child_iter(it))
                self.store.set_value(child, 0, on)
            self._update_selection()
        for label, fn in (("Tick", lambda *_: set_checks(True)), ("Untick", lambda *_: set_checks(False)), (None, None),
                          ("Show in folder", lambda *_: self._reveal_rows(rows)),
                          ("Open", lambda *_: self._open(its[0])),
                          ("Copy path", lambda *_: cb.set_text("\n".join(os.path.join(x.folder, x.name) for x in its), -1))):
            if label is None:
                menu.append(Gtk.SeparatorMenuItem())
                continue
            mi = Gtk.MenuItem(label=label)
            mi.connect("activate", fn)
            menu.append(mi)
        menu.show_all()
        menu.attach_to_widget(tv, None)
        menu.popup_at_pointer(event)
        return True

    def _open(self, it: CleanupItem):
        try:
            Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(it.paths[0], None), None)
        except GLib.Error as ex:
            self.status.set_text(f"Couldn't open {it.paths[0]}: {ex.message}")

    def _key(self, tv, event):
        if event.keyval == Gdk.KEY_space:
            rows = tv.get_selection().get_selected_rows()[1]
            if rows:
                first = self.sorted.get_value(self.sorted.get_iter(rows[0]), 0)
                for p in rows:
                    child = self.filtered.convert_iter_to_child_iter(self.sorted.convert_iter_to_child_iter(self.sorted.get_iter(p)))
                    self.store.set_value(child, 0, not first)
                self._update_selection()
            return True
        if event.keyval == Gdk.KEY_Delete:
            self._trash_checked()
            return True
        return False

    # ---- removing
    def _confirm_system(self, sysitems: List[CleanupItem]) -> str:
        """Warn about system files among the ticked items. Returns "skip", "all" or "cancel"."""
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                              buttons=Gtk.ButtonsType.NONE,
                              text=f"{len(sysitems)} of the ticked items {'are system files' if len(sysitems) != 1 else 'is a system file'}")
        lines = [f"• {it.name} — {it.reason}" for it in sysitems[:8]]
        if len(sysitems) > 8:
            lines.append(f"• … and {len(sysitems) - 8} more")
        d.format_secondary_text("Removing these can break installed programs or the system itself, and files you don't own "
                                "can't be moved without administrator rights anyway.\n\n" + "\n".join(lines))
        d.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        d.add_button("Remove them _too", 2)
        skip = d.add_button("_Skip system files", 1)
        d.get_widget_for_response(2).get_style_context().add_class("destructive-action")
        d.set_default_response(1)
        skip.grab_focus()
        r = d.run()
        d.destroy()
        return {1: "skip", 2: "all"}.get(r, "cancel")

    def _trash_checked(self):
        chk = self._checked()
        if not chk:
            return
        sysitems = [x for x in chk if x.flag == "system"]
        if sysitems:
            ans = self._confirm_system(sysitems)
            if ans == "cancel":
                return
            if ans == "skip":
                chk = [x for x in chk if x.flag != "system"]
                if not chk:
                    self.status.set_text("Nothing left to remove: only system files were ticked.")
                    return
            elif not ask_yes_no(self, "Remove system files?", "Are you sure? Programs or the system may stop working "
                                "if these are removed. They go to the Recycle Bin, so you can restore them.", True):
                return
        paths = [p for it in chk for p in it.paths if os.path.lexists(p)]
        total = sum(x.size for x in chk)
        nseq = sum(1 for x in chk if x.is_sequence)
        what = f"{len(chk):,} item{'s' if len(chk) != 1 else ''}" + (f" ({len(paths):,} files, including {nseq} frame sequence{'s' if nseq != 1 else ''})" if nseq else "")
        if not ask_yes_no(self, "Move to Recycle Bin", f"Move {what} to the Recycle Bin?\n\nThis frees {fmt_size(total)} once the "
                          "Recycle Bin is emptied. You can restore them from the Recycle Bin (or Edit → Undo) until then."):
            return
        op = self.win.run_op("trash", paths, None)
        self.status.set_text(f"Moving {len(paths):,} files to the Recycle Bin…")
        GLib.timeout_add(400, self._after_trash, op, chk)

    def _after_trash(self, op, chk):
        if not self._alive:
            return False
        if op is not None and not getattr(op, "finished", True):
            return True
        gone = {id(x) for x in chk if not any(os.path.lexists(p) for p in x.paths)}
        if gone:
            keep = [x for x in self.items if id(x) not in gone]
            freed = sum(x.size for x in self.items if id(x) in gone)
            self._fill(keep)
            self.status.set_text(f"Moved {len(gone):,} item{'s' if len(gone) != 1 else ''} ({fmt_size(freed)}) to the Recycle Bin. "
                                 "Empty the Recycle Bin (Tools menu) to get the space back.")
        return False
