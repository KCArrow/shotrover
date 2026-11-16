

# =========================================================================== encrypted file index
# An optional, opt-in map of the user's folders (name, kind, size, mtime per entry, keyed by directory) that
# makes two things instant: painting a folder the moment you navigate to it (the real listing replaces the
# indexed one a moment later, like the progressive listing does today), and name search across whole trees
# without walking the disk. Because such a map is a complete inventory of the machine, it never touches the
# disk in the clear: the index file is AES-256-CBC (via the system `openssl`, PBKDF2-stretched key) with an
# HMAC-SHA256 over the ciphertext (encrypt-then-MAC), and the key lives in the desktop keyring through
# libsecret's `secret-tool` when available, otherwise in a 0600 file in ~/.config/shotrover. Plaintext exists
# only in this process's memory.
INDEX_FILE = os.path.join(GLib.get_user_cache_dir(), "shotrover", "index.enc")
INDEX_KEYFILE = os.path.join(CONFIG_DIR, "index.key")
INDEX_EXCLUDE_DIRS = {".cache", ".git", ".svn", "node_modules", "__pycache__", ".Trash", ".local/share/Trash", "proc", "sys", "dev", "run",
                      ".thumbnails", ".mozilla", ".var", "snap", "lost+found", ".npm", ".cargo", ".rustup", ".conda", ".pyenv", "site-packages"}
INDEX_SYSTEM_PREFIXES = ("/proc", "/sys", "/dev", "/run", "/tmp", "/var/tmp", "/var/cache", "/var/lib", "/snap")


class IndexKey:
    """32-byte key for the index. Keyring first (secret-tool / libsecret), file fallback. `source` tells the UI
    where it ended up so the user knows what the protection actually is."""

    def __init__(self):
        self.source = ""

    def get(self, create: bool = True) -> Optional[bytes]:
        st = shutil.which("secret-tool")
        if st:
            try:
                r = subprocess.run([st, "lookup", "application", "shotrover", "purpose", "index-key"], capture_output=True, text=True, timeout=15)
                if r.returncode == 0 and len(r.stdout.strip()) == 64:
                    self.source = "desktop keyring"
                    return bytes.fromhex(r.stdout.strip())
                # stored before the rename (Kestrel): move it to the new name so the existing index stays readable
                r = subprocess.run([st, "lookup", "application", "kestrel", "purpose", "index-key"], capture_output=True, text=True, timeout=15)
                if r.returncode == 0 and len(r.stdout.strip()) == 64:
                    key = r.stdout.strip()
                    w = subprocess.run([st, "store", "--label=Shotrover file index key", "application", "shotrover", "purpose", "index-key"],
                                       input=key, capture_output=True, text=True, timeout=30)
                    if w.returncode == 0:
                        subprocess.run([st, "clear", "application", "kestrel", "purpose", "index-key"], capture_output=True, timeout=15)
                    self.source = "desktop keyring"
                    return bytes.fromhex(key)
                if create:
                    key = os.urandom(32)
                    r = subprocess.run([st, "store", "--label=Shotrover file index key", "application", "shotrover", "purpose", "index-key"],
                                       input=key.hex(), capture_output=True, text=True, timeout=30)
                    if r.returncode == 0:
                        self.source = "desktop keyring"
                        return key
            except (OSError, subprocess.TimeoutExpired):
                pass
        try:
            if os.path.exists(INDEX_KEYFILE):
                with open(INDEX_KEYFILE, "rb") as f:
                    data = f.read().strip()
                if len(data) == 64:
                    self.source = "key file (install libsecret-tools / a keyring daemon for keyring storage)"
                    return bytes.fromhex(data.decode())
            if create:
                key = os.urandom(32)
                os.makedirs(CONFIG_DIR, exist_ok=True)
                fd = os.open(INDEX_KEYFILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(key.hex())
                self.source = "key file (install libsecret-tools / a keyring daemon for keyring storage)"
                return key
        except OSError:
            pass
        return None

    def forget(self):
        st = shutil.which("secret-tool")
        if st:
            for app in ("shotrover", "kestrel"):
                subprocess.run([st, "clear", "application", app, "purpose", "index-key"], capture_output=True, timeout=15)
        try:
            os.remove(INDEX_KEYFILE)
        except OSError:
            pass


def _openssl(args: List[str], data: bytes, key: bytes) -> bytes:
    """Run openssl enc with the key passed over a pipe fd (never argv/env, which other users can read)."""
    rfd, wfd = os.pipe()
    try:
        os.write(wfd, key.hex().encode())
        os.close(wfd)
        r = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-salt", "-pass", f"fd:{rfd}"] + args,
                           input=data, capture_output=True, pass_fds=(rfd,), timeout=600)
    finally:
        try:
            os.close(rfd)
        except OSError:
            pass
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace").strip().splitlines()[-1:] or "openssl failed")
    return r.stdout


def _mac(key: bytes, blob: bytes) -> bytes:
    import hmac, hashlib
    return hmac.new(hashlib.sha256(key + b"kestrel-index-mac").digest(), blob, hashlib.sha256).digest()


class FileIndex:
    MAGIC = b"KSTRLIDX1"

    def __init__(self):
        self.data: Dict[str, Tuple[float, list]] = {}      # dir → (dir mtime, [(name, is_dir, size, mtime), …])
        self.lock = threading.RLock()
        self.key = IndexKey()
        self._k: Optional[bytes] = None
        self.loaded = False
        self.dirty = False
        self.crawling = False
        self.cancel = threading.Event()
        self.progress = {"dirs": 0, "files": 0, "current": "", "started": 0.0, "finished": 0.0}
        self.last_error = ""
        self._flat: Optional[List[Tuple[str, str, int]]] = None    # (lower name, dir, idx) for search
        self.on_status: Optional[Callable] = None

    # ---- persistence
    def _key(self) -> Optional[bytes]:
        if self._k is None:
            self._k = self.key.get()
        return self._k

    def load(self) -> bool:
        if not os.path.exists(INDEX_FILE):
            self.loaded = True
            return False
        k = self._key()
        if not k:
            self.last_error = "no key available"
            return False
        try:
            with open(INDEX_FILE, "rb") as f:
                blob = f.read()
            if not blob.startswith(self.MAGIC):
                raise ValueError("not a Shotrover index")
            mac, body = blob[len(self.MAGIC):len(self.MAGIC) + 32], blob[len(self.MAGIC) + 32:]
            import hmac as _h
            if not _h.compare_digest(mac, _mac(k, body)):
                raise ValueError("index authentication failed (wrong key or tampered file) — it will be rebuilt")
            import zlib
            raw = zlib.decompress(_openssl(["-d"], body, k))
            # The index is read and written one folder at a time. Parsing it as a single JSON document (the
            # first format) is one C call that keeps the interpreter lock for its whole length: with 100,000
            # folders the window did not react for a second and a half, shortly after every start and again
            # after each save. A loop of small steps lets the interface thread in between them.
            nl = raw.find(b"\n")
            if nl < 0:                               # first format: one document. Read it once more, rewrite it
                obj = json.loads(raw.decode("utf-8"))
                data = {d: (m, [tuple(x) for x in ents]) for d, (m, ents) in obj["dirs"].items()}
                finished, old_format = obj.get("finished", 0.0), True
            else:
                finished, old_format = json.loads(raw[:nl]).get("finished", 0.0), False
                data, pos, end = {}, nl + 1, len(raw)
                while pos < end:
                    nl = raw.find(b"\n", pos)
                    if nl < 0:
                        nl = end
                    if nl > pos:
                        d, m, ents = json.loads(raw[pos:nl])
                        data[d] = (m, [tuple(x) for x in ents])
                    pos = nl + 1
            with self.lock:
                self.data = data
                self._flat = None
            self.progress["finished"] = finished
            self.loaded = True
            if old_format:
                self.save()
            return True
        except Exception as ex:
            self.last_error = str(ex)
            self.loaded = True
            return False

    def save(self) -> bool:
        k = self._key()
        if not k:
            return False
        try:
            import zlib
            with self.lock:
                items = list(self.data.items())
            # one line per folder, compressed a few hundred folders at a time: see load() for why
            co = zlib.compressobj(6)
            parts = [co.compress((json.dumps({"version": 2, "finished": self.progress["finished"]}) + "\n").encode("utf-8"))]
            for i in range(0, len(items), 400):
                chunk = "".join(json.dumps([d, m, ents], separators=(",", ":")) + "\n" for d, (m, ents) in items[i:i + 400])
                parts.append(co.compress(chunk.encode("utf-8")))
            parts.append(co.flush())
            raw = b"".join(parts)
            body = _openssl([], raw, k)
            blob = self.MAGIC + _mac(k, body) + body
            os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
            tmp = INDEX_FILE + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(blob)
            os.replace(tmp, INDEX_FILE)
            self.dirty = False
            return True
        except Exception as ex:
            self.last_error = f"save: {ex}"
            return False

    def wipe(self):
        with self.lock:
            self.data = {}
            self._flat = None
        try:
            os.remove(INDEX_FILE)
        except OSError:
            pass
        self.key.forget()
        self._k = None

    # ---- queries
    def lookup(self, path: str) -> Optional[list]:
        with self.lock:
            hit = self.data.get(path.rstrip("/") or "/")
        return hit[1] if hit else None

    def update_dir(self, path: str, entries: List["Entry"]):
        """Called with a freshly listed folder: keep the index current for places the user actually visits."""
        try:
            mt = os.stat(path).st_mtime
        except OSError:
            return
        self.put_dir(path, mt, [(e.name, e.is_dir, e.size or 0, e.mtime or 0.0) for e in entries])

    def put_dir(self, path: str, mtime: float, rows: list):
        with self.lock:
            self.data[path.rstrip("/") or "/"] = (mtime, rows)
            self._flat = None
            self.dirty = True
        self._schedule_save()

    def _schedule_save(self, delay: float = 20.0):
        """Write the encrypted file a little after the last change (coalesces a burst of visits)."""
        t = getattr(self, "_save_timer", None)
        if t is not None:
            t.cancel()

        def go():
            self._save_timer = None
            if self.dirty and not self.crawling:
                pin_worker()
                self.save()
        self._save_timer = threading.Timer(delay, go)
        self._save_timer.daemon = True
        self._save_timer.start()

    def search(self, pattern: str, root: Optional[str] = None, limit: int = 5000) -> List[Tuple[str, bool, int, float]]:
        """Case-insensitive substring or glob match over every indexed name. ~1M names in well under a second."""
        pat = pattern.lower()
        globby = any(c in pat for c in "*?[")
        with self.lock:
            if self._flat is None:
                self._flat = [(ents, d) for d, (m, ents) in self.data.items()]
            flat = self._flat
        out = []
        rootp = (root.rstrip("/") + "/") if root and root != "/" else None
        for ents, d in flat:
            if rootp and not (d == root.rstrip("/") or d.startswith(rootp)):
                continue
            for name, is_dir, size, mtime in ents:
                low = name.lower()
                if (fnmatch.fnmatch(low, pat) if globby else pat in low):
                    out.append((os.path.join(d, name), is_dir, size, mtime))
                    if len(out) >= limit:
                        return out
        return out

    def stats(self) -> dict:
        with self.lock:
            dirs = len(self.data)
            files = sum(len(v[1]) for v in self.data.values())
        try:
            size = os.path.getsize(INDEX_FILE)
        except OSError:
            size = 0
        return {"dirs": dirs, "files": files, "size": size, "finished": self.progress["finished"], "key": self.key.source or "—",
                "crawling": self.crawling, "error": self.last_error}

    # ---- crawling
    def crawl(self, roots: List[str], include_network: bool, include_hidden: bool, full: bool = False):
        """Walk the roots in a low-priority thread. Directories whose mtime hasn't changed since they were
        indexed are skipped (full=False), so re-crawls touch only what moved. Saves every 60 s and at the end."""
        if self.crawling:
            return
        self.crawling = True
        self.cancel.clear()
        self.progress.update(dirs=0, files=0, current="", started=time.time())

        def work():
            pin_worker()
            try:
                os.nice(10)
            except OSError:
                pass
            last_save = time.time()
            seen_dev = {}
            for root in roots:
                root = os.path.abspath(os.path.expanduser(root))
                if not os.path.isdir(root):
                    continue
                stack = [root]
                while stack and not self.cancel.is_set():
                    d = stack.pop()
                    if d != root and d.startswith(INDEX_SYSTEM_PREFIXES) and not root.startswith(INDEX_SYSTEM_PREFIXES):
                        continue            # never wander into /proc, /sys, /run… unless that IS the chosen root
                    if not include_network and is_network_path(d):
                        continue
                    try:
                        st = os.stat(d)
                    except OSError:
                        continue
                    self.progress["current"] = d
                    with self.lock:
                        old = self.data.get(d)
                    if old is not None and not full and abs(old[0] - st.st_mtime) < 1e-6:
                        # unchanged directory: still descend (subfolders may have changed)
                        for name, is_dir, _, _ in old[1]:
                            if is_dir and (include_hidden or not name.startswith(".")) and name not in INDEX_EXCLUDE_DIRS:
                                stack.append(os.path.join(d, name))
                        self.progress["dirs"] += 1
                        continue
                    ents = []
                    try:
                        with os.scandir(d) as it:
                            for de in it:
                                if not include_hidden and de.name.startswith("."):
                                    continue
                                try:
                                    is_dir = de.is_dir(follow_symlinks=False)
                                    s = de.stat(follow_symlinks=False)
                                except OSError:
                                    continue
                                ents.append((de.name, is_dir, 0 if is_dir else s.st_size, s.st_mtime))
                                if is_dir and de.name not in INDEX_EXCLUDE_DIRS:
                                    stack.append(de.path)
                    except OSError:
                        continue
                    with self.lock:
                        self.data[d] = (st.st_mtime, ents)
                        self._flat = None
                    self.dirty = True
                    self.progress["dirs"] += 1
                    self.progress["files"] += len(ents)
                    if time.time() - last_save > 60:
                        self.save()
                        last_save = time.time()
                        if self.on_status:
                            self.on_status()
            self.progress["finished"] = time.time()
            self.progress["current"] = ""
            self.save()
            self.crawling = False
            if self.on_status:
                self.on_status()             # called on this thread: the caller takes it where it wants it
        threading.Thread(target=work, daemon=True, name="shotrover-indexer").start()

    def stop(self):
        self.cancel.set()


def _index_serve(conn, other, parent: int, key: Optional[bytes]):
    """The index helper process: it owns the FileIndex and answers IndexClient until the pipe closes or the
    application is gone. Loading, crawling and saving run in threads of this process, where they can keep
    its interpreter lock as long as they like."""
    try:
        other.close()                        # the application's end; open here it would hide its closing
    except Exception:
        pass
    pin_worker()
    idx = FileIndex()
    idx._k = key
    slock = threading.Lock()

    def send(msg):
        with slock:
            try:
                conn.send(msg)
            except (OSError, ValueError):
                os._exit(0)

    def state(notify: bool = False):
        send(("s", {"loaded": idx.loaded, "crawling": idx.crawling, "progress": dict(idx.progress),
                    "last_error": idx.last_error}, notify))

    def load(rid):
        ok = idx.load()
        state()
        send(("r", rid, ok))
    idx.on_status = lambda: state(True)
    was = False
    while True:
        try:
            if not conn.poll(0.5):
                if os.getppid() != parent:
                    os._exit(0)
                if idx.crawling or was:
                    state()
                was = idx.crawling
                continue
            rid, op, args = conn.recv()
        except (EOFError, OSError):
            os._exit(0)
        res = None
        try:
            if op == "load":
                threading.Thread(target=load, args=(rid,), daemon=True).start()
                continue
            if op == "lookup":
                res = idx.lookup(*args)
            elif op == "search":
                res = idx.search(*args)
            elif op == "put":
                idx.put_dir(*args)
            elif op == "stats":
                res = idx.stats()
            elif op == "crawl":
                idx.crawl(*args)
                state()
            elif op == "stop":
                idx.stop()
            elif op == "wipe":
                idx.wipe()
                state()
        except Exception as ex:
            idx.last_error = f"{op}: {ex}"
        if rid:
            send(("r", rid, res))


class IndexClient:
    """The file index as the application sees it. The index itself (FileIndex) lives in a helper process.

    Reading a big index is a long Python loop, and so is walking the disk to refresh it. In a thread of
    this process each of them took the interpreter lock back faster than the GTK thread could get hold of
    it: the window stuttered badly for the first seconds after every start, and for as long as a crawl
    ran. Here only small messages cross a pipe. `loaded`, `crawling` and `progress` are kept up to date by
    the helper; a question it does not answer in time counts as "not in the index"."""

    def __init__(self, key: Optional[bytes] = None):
        self.loaded = False
        self.crawling = False
        self.progress = {"dirs": 0, "files": 0, "current": "", "started": 0.0, "finished": 0.0}
        self.last_error = ""
        self.on_status: Optional[Callable] = None
        self._key = key                      # tests only: otherwise the helper fetches the key itself
        self._proc = None
        self._conn = None
        self._lock = threading.Lock()
        self._wait: Dict[int, list] = {}     # request number → [Event, answer]
        self._n = 0

    def _start(self) -> bool:
        with self._lock:
            if self._proc is not None and self._proc.is_alive():
                return True
            try:
                import multiprocessing
                ctx = multiprocessing.get_context("fork")
                mine, theirs = ctx.Pipe()
                proc = ctx.Process(target=_index_serve, args=(theirs, mine, os.getpid(), self._key), daemon=True, name="shotrover-index")
                proc.start()
                theirs.close()
            except Exception as ex:
                self.last_error = f"index helper: {ex}"
                return False
            self._proc, self._conn = proc, mine
            threading.Thread(target=self._read, args=(mine,), daemon=True, name="shotrover-index-reader").start()
            return True

    def _read(self, conn):
        """Everything the helper sends: answers, and news about its state."""
        while True:
            try:
                msg = conn.recv()
            except (EOFError, OSError, ValueError):
                break
            if msg[0] == "r":
                w = self._wait.pop(msg[1], None)
                if w is not None:
                    w[1] = msg[2]
                    w[0].set()
            elif msg[0] == "s":
                st = msg[1]
                self.progress.update(st["progress"])
                self.last_error = st["last_error"]
                self.loaded, self.crawling = st["loaded"], st["crawling"]
                cb = self.on_status
                if msg[2] and cb is not None:
                    GLib.idle_add(lambda cb=cb: (cb(), False)[1])
        if conn is self._conn:               # the helper is gone: the next load() starts another
            self.loaded = self.crawling = False
        for w in list(self._wait.values()):
            w[0].set()

    def _call(self, op: str, *args, timeout: Optional[float] = None, reply: bool = True):
        conn = self._conn
        if conn is None:
            return None
        w = None
        with self._lock:
            rid = 0
            if reply:
                self._n += 1
                rid = self._n
                w = self._wait[rid] = [threading.Event(), None]
            try:
                conn.send((rid, op, args))
            except (OSError, ValueError):
                self._wait.pop(rid, None)
                return None
        if w is None:
            return None
        w[0].wait(timeout)
        self._wait.pop(rid, None)
        return w[1]

    def load(self) -> bool:
        """Blocks until the helper has read the index: call it from a worker thread."""
        if not self._start():
            return False
        return bool(self._call("load"))

    def lookup(self, path: str) -> Optional[list]:
        return self._call("lookup", path, timeout=0.1)

    def search(self, pattern: str, root: Optional[str] = None, limit: int = 5000) -> list:
        return self._call("search", pattern, root, limit, timeout=3.0) or []

    def update_dir(self, path: str, entries: List["Entry"]):
        try:
            mt = os.stat(path).st_mtime
        except OSError:
            return
        self._call("put", path, mt, [(e.name, e.is_dir, e.size or 0, e.mtime or 0.0) for e in entries], reply=False)

    def stats(self) -> dict:
        return self._call("stats", timeout=1.0) or {"dirs": 0, "files": 0, "size": 0, "finished": self.progress["finished"], "key": "—",
                                                    "crawling": self.crawling, "error": self.last_error}

    def crawl(self, roots: List[str], include_network: bool, include_hidden: bool, full: bool = False):
        if self.crawling or self._conn is None:
            return
        self.crawling = True
        self._call("crawl", roots, include_network, include_hidden, full, reply=False)

    def stop(self):
        self._call("stop", reply=False)

    def wipe(self):
        self._call("wipe", timeout=30.0)

    def close(self):
        """Quit: end the helper at once (a crawl in it is simply dropped; the last save is on disk)."""
        proc, self._proc, self._conn = self._proc, None, None
        self.loaded = self.crawling = False
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass


INDEX = IndexClient()


def index_entries_for(path: str, rows: list) -> List["Entry"]:
    """Index tuples → Entry objects (icons/types from the extension cache) for the instant first paint."""
    out = []
    for name, is_dir, size, mtime in rows:
        e = Entry()
        e.name, e.path, e.is_dir = name, os.path.join(path, name), bool(is_dir)
        e.size = None if is_dir else int(size)
        e.mtime = float(mtime)
        e.hidden = name.startswith(".")
        if is_dir:
            e.content_type, e.type, e.icon = "inode/directory", "File folder", _FOLDER_ICON
        else:
            e.content_type, e.type, e.icon = _ct_info(name)
        out.append(e)
    return out
