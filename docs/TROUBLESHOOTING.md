# Troubleshooting

Package names below are given for the Fedora / RHEL family (`dnf`) and Debian / Ubuntu (`apt`) where they
differ; on Arch, openSUSE and others the names are similar. **Preferences → Optional** writes the exact
install commands for your distro, so use that when in doubt.

First stop: **Preferences → Optional** shows every optional tool, whether it was found, and a
diagnostics report you can copy. **Tools → Performance report…** shows stalls and timings.

## It won't start

- `ModuleNotFoundError: No module named 'gi'` → install PyGObject:
  `sudo dnf install python3-gobject gtk3` (Fedora/RHEL/Rocky), `sudo apt install python3-gi gir1.2-gtk-3.0`
  (Debian/Ubuntu), `sudo pacman -S python-gobject gtk3` (Arch), or your distro's PyGObject and GTK 3 packages.
- `Namespace Gtk not available` → the GTK 3 typelib is missing: `gtk3` / `gir1.2-gtk-3.0`.
- Running `shotrover` prints "command not found" after `install.sh` → `~/.local/bin` is not on your
  PATH; log out/in or `export PATH="$HOME/.local/bin:$PATH"`.
- Wrong Python picked up → run `python3 shotrover.py` explicitly; Python 3.9+ is required.

## Video / audio preview

- *GStreamer: missing* → install the GStreamer GI bindings and plugins:
  `sudo dnf install python3-gstreamer1 gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-plugins-bad-free`
  (Fedora/RHEL), `sudo apt install gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-good`
  (Debian/Ubuntu), `sudo pacman -S gstreamer gst-plugins-base gst-plugins-good` (Arch).
  The bindings are what make `from gi.repository import Gst` work; the plugins alone are not enough.
- *gtksink missing* → it is in `gstreamer1-plugins-good-gtk` (Fedora/RHEL), `gstreamer1.0-gtk3` (Debian/Ubuntu),
  `gst-plugin-gtk` (Arch).
- Movies show a black or static frame, audio only → no H.264 decoder. On Fedora/RHEL enable RPM Fusion and
  install `gstreamer1-libav` (or `gstreamer1-plugins-ugly` / `openh264`); on Debian/Ubuntu install
  `gstreamer1.0-libav`; on Arch `gst-libav`. The Optional tab lists the
  decoders it found (`H264_DECODERS`).
- The diagnostics report lists each GStreamer element by its actual element name; a package being
  installed but the element still "missing" usually means the plugin was built without that feature
  (`gst-inspect-1.0 gtksink` to confirm).

## 3D previews

- `.vdb` volumes are read by Shotrover itself — no Houdini, licence or library needed — and shown as smoke
  (fog volumes; the `density` grid when there are several) or as a surface (level sets). Houdini, EmberGen,
  Blender and Maya VDBs are supported (float grids, zip/blosc compression, half-float). Blosc decoding is
  faster with `python3-blosc` or Houdini installed but works without either. EmberGen and Blender volumes
  are Z-up and are stood upright. Anything the built-in reader can't parse (vector-only files, frustum
  transforms) falls back to Houdini, `python3-openvdb`, then Blender (surface only).
- `.bgeo`, `.bgeo.sc`, `.geo` need Houdini: Shotrover runs `hython` from PATH, `$HFS/bin` or the newest
  `/opt/hfs*`. The first preview takes a few seconds while Houdini starts and checks out a licence; if no
  licence is free it tries `gconvert` (geometry only).
- No Blender at your studio? FBX, Alembic and USD fall back to Maya's `mayapy` when it's installed
  (slower to start: Maya boots for every preview).
- "No importer could read this file" → see which route applies in **Preferences → Optional**:
  - `.obj .stl .ply`: built in (numpy makes them far faster).
  - `.fbx .gltf .glb .dae .3ds` and friends: Blender (any install, including Flatpak
    `org.blender.Blender`) or `assimp`.
  - `.abc`: Ogawa files need Blender; **legacy HDF5 Alembic** (older Maya exports) can't be read by
    Blender or current Alembic builds — Shotrover reads them directly with `h5py`
    (package `python3-h5py`; `python-h5py` on Arch). `shotrover --probe-model file.abc` tells you which kind it is.
  - `.usd .usda .usdc .usdz`: Blender, or `pip install --user usd-core`.
  - `.blend`: Blender.
- Flatpak Blender not detected → `flatpak info org.blender.Blender` must succeed for your user.
  Shotrover runs it with filesystem grants for the file's folder; a file on a path Flatpak can't see
  (some network mounts) will fail — copy it locally to test.
- Import hangs → the Blender bridge is killed after a timeout (process group), the preview reports
  it. Very large scenes can exceed it; raise the model face cap or use the software renderer.
- Model looks wrong (holes, inside-out) → "All triangles" in the preview context menu disables
  decimation; winding is fixed automatically, but meshes with mixed orientation will show dark
  faces under smooth shading.
- Slow software rendering → check numpy is installed (`python3 -c "import numpy"`); without it the
  pure-Python fallback is used. Enable CPU parking in Preferences → Optional so the window stays
  responsive while frames render.

## OpenGL

- "Unable to create GL context" → run `shotrover --probe-gl`. It tries x11 and wayland backends and
  every GL/GLES version, saves the one that works, and reports the system state.
- Probe says *NVML/driver version mismatch* → the NVIDIA kernel module and the user-space driver
  differ (happens after a driver update). **Reboot.**
- Under Wayland with NVIDIA, x11 (XWayland) is often the backend that works; the probe stores it as
  `gdk_backend` in the config and Shotrover sets `GDK_BACKEND` on startup.
- Models render white in GL mode by design (flat lighting only). Turn OpenGL off in Preferences →
  Optional to get the shaded software renderer back.
- Volumes (smoke) in OpenGL need float render targets (any desktop GL 3; on GLES the
  `EXT_color_buffer_float` extension). Without them Shotrover says so once and draws caches with the
  software renderer; meshes stay on OpenGL.

## Scene breakdowns

- Selecting an Unreal, Unity, Maya or Blender scene shows a breakdown instead of the file's raw text: what's in
  it, its settings, and a **References** section with every file it uses. Missing files are red; paths that
  belong to another machine (`C:/…`, unexpanded variables) are shown as written and marked "not checked".
  Double-click a reference to jump to it; right-click to copy its path. The copy button puts the whole
  breakdown on the clipboard as text.
- `.blend` files open in the breakdown; **3D view** switches to the geometry preview (which starts Blender), and
  **Breakdown** above the 3D view switches back. The choice is remembered.
- Unity: script, prefab, material and mesh GUIDs are resolved through the project's `.meta` files (Assets,
  Packages and `Library/PackageCache`). Scripts from packages that aren't installed show as unresolved GUIDs.
  Binary-serialised scenes can't be read: set Project Settings → Editor → Asset Serialization to Force Text.
- Unreal: hard references come from the import table, soft references (streaming levels, soft pointers) from
  the name table. Actor labels and outliner folders are read where the editor data is present; cooked packages
  show object names instead. World Partition maps also count the actors under `__ExternalActors__`.
- Maya references to files saved on another machine are looked up by name next to the scene and in the
  project's `scenes`, `sourceimages`, `images` and `cache` folders.
- Picking an object shows its **base mesh**: modifiers (Blender), deformers / skinning / smooth preview (Maya)
  and armature poses aren't applied. A Maya mesh that only exists as construction history is shown as the
  primitive it started from (polyCube, polySphere, polyCylinder, polyCone, polyPlane, polyTorus, polyPyramid);
  the caption's tooltip says what was left out.
- `.ma` and `.mb` meshes are read from the file itself. A mesh that exists only as a long modelling
  history, or one deformed by skinning / blend shapes, can't be rebuilt exactly that way. If Maya is installed
  (`mayapy` on PATH, `$MAYA_LOCATION` or `/usr/autodesk/maya*`), Shotrover then opens the scene once in Maya in
  the background and swaps in Maya's result (the caption ends in "via Maya"); every mesh is cached under
  `~/.cache/shotrover/scene-geo`, so the first time takes as long as Maya needs to start (and uses a licence)
  and later picks are instant. Once Maya has read a file, every object picked in it uses Maya's result. Scenes
  with deformers (a rig) always ask Maya, since stored positions there don't match what Maya shows.
- Pick the **Outliner** heading of a Maya breakdown (or a scene row in a Blender one) to see every visible
  object at once — the quickest way to compare with Maya's viewport.
- Transforms driven by constraints or other connections are shown at the values saved in the file, which can
  differ from what Maya shows after it evaluates the rig.

## Shaders, materials and IES files

- The material ball is an approximation from the file's values and textures, not the renderer's own result:
  layered or procedural networks show the surface they end in, with what the ball used listed under "Ball
  preview uses". Textures are looked up next to the file; missing ones are red in **References**.
- Unity material colours are stored in sRGB and the ball converts them; a material whose shader comes from a
  package that isn't installed still shows its colours and textures.
- A GLSL file runs live only when it is a whole fragment shader: Shadertoy (`mainImage`) or glslsandbox /
  Book of Shaders (`main` writing `gl_FragColor` or an `out vec4`). Vertex, compute and include files show the
  breakdown and code only. `iChannel0-3` get a noise texture. Compile errors appear above the breakdown with
  line numbers matching the file. Click or drag for `iMouse`; double-click restarts the clock; it pauses
  when the window loses focus.
- If OpenGL isn't available (or *Hardware-accelerated 3D preview* is off in Preferences) the shader shows its code instead.
- **Code** above the breakdown switches between the tree and the highlighted source; the choice is remembered.
- IES: the wall picture is lit from just in front of it; the polar plot shows the C0–C180 (orange) and
  C90–C270 (blue) planes, 0° pointing down. Beam angle is where intensity falls to 50 % of the peak, field
  angle to 10 %, measured in the C0 plane and only for lights that point down.

## Cache sequences

- Select two or more `.vdb` (or `.bgeo`) files — Ctrl+A in the cache folder is fine, other files are
  ignored — and press **Preview as sequence** above the 3D preview. The selected caches play in name
  order with a time slider; until you press it, only the clicked file is previewed (so a pack of
  separate assets is never mistaken for frames). Selecting something else ends the sequence.
  Space plays/pauses, ← → step a frame, the spin box sets the frame rate (remembered). Playback
  pauses when the window loses focus.
- Frames decode in the background in up to four worker processes, starting at the frame you're on.
  "buffering frame N…" means playback is waiting for that frame; the first loop runs at decoding speed,
  later loops at full speed once the frames are held in memory.
- Memory: decoded frames are kept up to a third of RAM (3 GB at most); longer sequences keep a window
  ahead of the playhead and decode the rest again when it comes round. Each frame is capped at about
  1M volume samples, and the whole sequence uses the first frame's box, brightness and detail level so
  nothing jumps while it plays.

## Find large files

- Tools → **Find large files…** starts in the folder you're viewing (or the selected folder). Point it at `/`
  or a drive to look at everything; **Stay on this drive** keeps it from walking into network shares and other
  disks mounted inside.
- Sizes are what deleting would free: a sparse file counts the blocks it really uses. Files smaller than the
  limit still count when they're frames of a sequence (three or more numbered files with the same name and
  extension in one folder) whose total passes it.
- Nothing is deleted from this window: ticked items go to the Recycle Bin (Ctrl+Z or the Recycle Bin restores
  them), and the space comes back once you empty it. Files in the Recycle Bin are never listed; the status line
  says how much it holds.
- **Look for duplicates** only compares files that made the list, so lower the size limit to catch smaller copies.
- Rows marked **⚠ System** (orange) belong to the operating system or installed software: anything under
  `/usr`, `/boot`, `/etc`, `/opt`, `/var/lib`, `/var/cache`, `/var/log`…, an active swap file, a file owned by
  root or another account, or one in a folder you can't write to. The Notes column says why, and for package
  caches, logs, Flatpak, Docker/Podman it names the command that cleans them up properly. Removing ticked system
  files asks first; **Skip system files** is the default. **Hide system files** takes them out of the list.
- Plain hints (no ⚠) mark things an app manages — `~/.cache` (safe to clear), Flatpak app data, Steam
  libraries, virtual machine disks — so you know where a file comes from before removing it.

## Slow folders / freezes

- Navigation into a network folder is slow the first time: names appear instantly, sizes and
  dates fill in. If names don't appear instantly, run `shotrover --nav-bench /that/path` and attach
  the output to a report.
- A dead network mount (`/mnt/nas` with the NAS off) must not freeze the window; if it does,
  **Tools → Performance report…** will show which call stalled.
- The window froze completely → look in `~/.cache/shotrover/` for `freeze-*.txt`; it holds every
  thread's stack at the moment of the freeze. Attach it to an issue.
- The spinner bottom-left appears after 250 ms of waiting on a listing; it is informational, not
  a hang.

## File index

- Enabling: Preferences → Search → *File index*. Choose roots; network and hidden paths are
  opt-in. The first crawl runs in the background at low priority.
- "Will I ever see a stale listing?" No. Index data only paints first; every folder is re-read
  from disk as you enter it and the view is replaced by what the disk says ("Verifying against the
  disk…" in the status bar). Search hits are checked before being shown.
- Key storage: the keyring via `secret-tool` (install `libsecret-tools`); otherwise a 0600 key
  file at `~/.config/shotrover/index.key`. *Wipe index* in Preferences deletes the data and key.
- Index size: a few MB per 100k files, encrypted. It is excluded from itself.

## Drives

- Folder drives (right-click a folder → *Show in This PC as a drive*) appear in the same section of This PC as
  the drive they live on, right after its tile (network folders under *Network locations*), and after that
  drive in the navigation pane. The bar and "free of" figures are for the disk the folder is on. Renaming or removing one only changes the tile, never the folder. If the folder isn't
  there (a share that isn't mounted yet) the tile is greyed out in the section it was last seen in until it is.
- A plugged-in USB stick doesn't show up → Shotrover listens to `Gio.VolumeMonitor`; if GVFS isn't
  running (minimal installs), start `gvfs-udisks2-volume-monitor` or install `gvfs`.
- Eject / Format are greyed out → needs `udisks2` and a polkit agent (standard on GNOME); the
  Format dialog lists only filesystems whose `mkfs` is installed (`exfatprogs`, `dosfstools`,
  `ntfs-3g`, `e2fsprogs`).
- A Windows/other-Linux partition is missing from This PC → intentional: internal non-removable
  partitions that aren't mounted are hidden. Mount it (Disks app, or `udisksctl mount -b /dev/sdX1`)
  and it appears.

## Archives

- `.7z / .rar / .cab / .iso` need 7-Zip: install `7zip` (or `p7zip` with `p7zip-plugins` / `p7zip-full` on
  older distros). The extract-on-double-click behaviour is in Preferences → General → Archives.

## Reporting a problem

The quickest way: **Help → Report a problem…**, or *Review & report…* on the error bar after a crash.
The report already contains the version, distro, desktop, the stack trace and recent activity;
describe what you were doing at the top and press *Report on GitHub…*.
Reports live in `~/.cache/shotrover/reports/` if you'd rather attach the file yourself.

If you report by hand, include:

Shotrover version (Help → About), distro and desktop (Wayland or X11), the diagnostics
report from Preferences → Optional, and for freezes the newest `~/.cache/shotrover/freeze-*.txt`
or the Performance report. For a preview problem with a specific file type, the output of
`shotrover --probe-model <file>` (3D) or the file's `file --mime-type` result.
