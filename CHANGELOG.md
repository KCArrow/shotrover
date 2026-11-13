# Changelog

## 1.1.2 — 2026-11-12

- Quick look: press Space on a file to open its preview in a window of its own, with every previewer the preview pane has (images, 3D, text, PDF, video, scene breakdowns). The arrow keys move to the next or previous file; Space or Esc closes it. It works with the preview pane hidden, and is also in the Home and right-click menus.
- With nothing selected, Space opens quick look for the item under the mouse pointer.
- Fixed: after starting in an icon layout the keyboard did nothing until the first click (Space, Delete, the arrow keys and type-to-jump were all lost), because the keyboard was on the hidden details list.
- Keyboard shortcuts can be changed in Preferences → Shortcuts: click a shortcut and press the new keys. A key that another action already uses moves to the new action; single letters and the keys that move around the file list can't be assigned. Menus, tooltips and the F1 list show the shortcuts as you have set them.
- Preferences → Optional says under the hardware-accelerated 3D preview option that it needs the PyOpenGL add-on, and whether that is installed.
- Preferences → Optional: OpenVDB (Python) shows "not available" instead of a permanent red "missing" on distros that have no package for it (RHEL 9 and its relatives), where installing it could never work. It is only a fallback; VDB files preview with the built-in reader. Where the package does exist, a failed install is now reported at the end of the install script instead of being hidden.
- Preferences is in the File menu only: the Tools menu no longer has its own Preferences entry or "Optional tools and integrations" (that is the Optional tab in Preferences).
- Space no longer selects the item under the cursor in the icon layouts (it opens quick look); Ctrl+Space still adds it to the selection.

## 1.1.1 — 2026-11-12

- Licence: freelancers working on their own account can now use Shotrover for paid work free of charge, on their own computers. Companies and studios still need a studio licence (see COMMERCIAL-LICENSE.md).
- Shotrover icons: a built-in icon set for files, folders and drives (yellow folders, a picture per file type including 3D models, volumes and scene files), so the app looks the same on every desktop. Choose between it and your desktop's icon theme in Preferences → View.
- Colours: follow the desktop, or force a light or dark look for Shotrover only (Preferences → View). It switches to the light or dark sibling of your GTK theme, and to Adwaita when the theme has none.
- The first start asks once which icons and colours you want.
- Divider lines are one weight and colour everywhere: pane edges, the status bar, column headers and separators all use the same 1px line. The lines either side of the file area were drawn twice and came out much brighter than the rest.
- An unfocused window keeps its background shades and its text dims in one step, instead of some parts darkening and buttons fading on their own. The inactive side of a split view stays dimmer than the active side when the window is unfocused.
- Thumbnails for production files in the icon layouts (and Content): EXR, HDR, PSD, Maya IFF, video, PDF and
  3D models (OBJ, STL, PLY, FBX, USD, Alembic, glTF, Houdini caches) now show their contents instead of a
  file-type icon. Made off the main thread in their own worker processes, kept in memory only
- Fixed: the app's stylesheet was never loaded (the loading code sat after a `return`), so none of the
  intended styling applied. It loads now, with one backdrop for the file area in every layout and one for the
  bars and side panes; status colours and the destructive-button colour come from one set of tokens
- Fixed: the preview pane could stay on the previous file after a rename, paste or jump-to-reference
- Switching layout keeps the selection (and the preview)
- Search results, Recent and Quick access say where each item lives in every layout; in Details the folder
  column sits next to Name instead of off-screen at the far right
- Archives preview as a file list instead of text in the editor; PDFs get previous / next page (buttons or
  the mouse wheel) and a sharper page
- Tabs show the folder name (full path in the tooltip); split-pane headers show `~/…` paths
- Type names for production formats (`.obj` is "OBJ model", not "TGIF document"; also Alembic, USD, Maya,
  Houdini, Nuke, VDB and others)
- Content layout no longer repeats type and size as columns; long names in the icon layouts wrap at
  `_`, `-` and `.` instead of mid-word; the Space used column draws a clean bar

- Runs the same on any distro: Preferences → Optional and the install hints in error messages now give the
  commands for your package manager (dnf, apt, pacman or zypper) instead of always dnf; EPEL / RPM Fusion are
  only suggested on the RHEL family and Fedora. `install.sh` and the docs list every distro family
- Fixed: the generated "install optional tools" script had a shell syntax error when Maya was in the list
- Show any folder in This PC as a drive: right-click a folder → *Show in This PC as a drive*, give it a name;
  it gets a drive tile next to the drive it lives on (same disk section, same capacity bar) and an entry
  after that drive in the navigation pane. Rename or remove it from its tile (the folder itself is never touched); greyed out while the folder
  isn't there (share not mounted)
- Tools → Find large files…: scan a folder or drive in the background for the biggest files; frame
  sequences (renders, caches) count as one item with their total size; filter by type, age and name;
  optional duplicate check (size, then head/tail, then full SHA-256); tick items and move them to the
  Recycle Bin (undoable). Stays on one drive by default, never lists the Recycle Bin itself but says how much
  it holds. System files (OS, installed programs, package caches, logs, active swap, files owned by another
  account or in read-only folders) are marked ⚠ with the reason and the right cleanup tool, can be hidden,
  and removing them asks first — "Skip system files" is the default

## 1.1 — 2026-10-27

**Houdini caches and VDBs**
- Houdini caches in the 3D preview: `.bgeo`/`.bgeo.sc`/`.geo` meshes and particles, `.vdb` volumes
  (smoke) and level sets (surfaces), via Houdini when installed; VDBs also via OpenVDB or Blender
- Built-in VDB reader: fog volumes preview as smoke without Houdini (Houdini, EmberGen, Blender VDBs;
  blosc/zip, half-float), level sets as surfaces; EmberGen/Blender Z-up volumes stood upright
- OpenGL draws Houdini caches too: particles as shaded sprites and volumes as smoke on the GPU
- Cache sequences: select several `.vdb` / `.bgeo` frames and press *Preview as sequence* for a time
  slider with playback (Space, ← →, adjustable fps); frames decode in the background and share one box
  and brightness; playback pauses when the window loses focus

**Scene breakdowns**
- Scene breakdowns in the preview pane for Unreal (.umap/.uasset/.uproject, UE 4.0–5.6), Unity (.unity/.prefab/
  .unitypackage), Maya (.ma/.mb) and Blender (.blend, 2.7x–5.x): outliner, contents, settings and every
  referenced file with its path and a missing-file check; filter, copy as text, double-click to reveal a file
- Blender and Unreal breakdowns show the file's saved thumbnail; Maya and Blender materials render on a
  material ball when picked

**Scene objects in 3D**
- Pick an object in a Blender (2.7x–5.x) or Maya (.ma / .mb) outliner to see its geometry in a 3D view, with
  everything parented under it, in place — read from the file itself, no Maya or Blender needed. Pick a
  texture to see the image (first UDIM tile)
- When a Maya scene has meshes Shotrover can't rebuild (long modelling history) or deformers it doesn't
  apply (skinning, blend shapes), and Maya is installed, the preview shows Shotrover's version at once and then
  Maya's own evaluation of the scene (read once per file with mayapy, cached); once Maya has read a file,
  every pick in it uses Maya's result. Rigs (skinning, blend shapes…) always get Maya's evaluation
- Pick the Outliner heading (Maya) or a scene (Blender) to see everything visible at once
- Fixed: Maya meshes moved or sculpted with vertex tweaks were drawn without them (bodies too small, parts
  in the wrong place)
- Instances: Maya instanced shapes and transforms show under every parent; Blender collection instances
  show in place, including collections linked from other .blend files
- World positions checked against the files' own data: Blender objects parented to bones follow the bone;
  Maya transforms honour inheritsTransform
- Maya object previews place rigged / grouped meshes correctly: rotate and scale pivots, shear, rotate axis,
  duplicate short names resolved by DAG path, hidden children left out; big scenes are parsed once and
  then each pick is quick
- Blender 5 files: data that shares an address across data-blocks is now read from the right block (stored
  material previews could show the wrong picture)

**Shaders, materials and lights**
- Shader and material previews: MaterialX, OSL (.osl/.oso), Unity .mat / .shader / .shadergraph on a material
  ball (GGX, clearcoat, normal maps, transmission, textures incl. UDIM); live Shadertoy / glslsandbox GLSL on
  the GPU with compile errors on the right line; GLSL / HLSL breakdown and highlighted code view
- IES photometric files (LM-63-1995/2002/2019): light pattern on a wall, polar candela plot, beam / field
  angles, lumens and wattage

**Other**
- Maya (`mayapy`) as a fallback importer for FBX, Alembic and USD when Blender isn't available
- Batch rename: frame-number offsets (padding kept, overlapping ranges safe), repathing into another
  folder (created if missing, works across drives), and a much faster live preview
- Home folder listed first under This PC in the navigation pane; Browse… buttons use Shotrover's own folder
  picker instead of the GTK/Nautilus chooser
- Animated GIFs (and animated WebP) play in the preview pane; click to pause. Frame count, length and
  loop setting in the details
- Address bar keeps a faint outline (matching the search box) so it's clear where to click to type a path
- Fixed: a double-click right after opening a folder was ignored, and Shift-click after going back or
  reloading selected only one item

## 1.0 — 2026-10-25

First public release. Licensed under PolyForm Noncommercial 1.0.0 (free for individuals and
nonprofits; commercial licences available — see COMMERCIAL-LICENSE.md).

- Windows-Explorer layout: menus, command bar, tabs, split view, navigation / preview / details panes,
  all icon and list views, grouping, column chooser
- Background file operations with progress, conflicts, pause, undo; freedesktop trash; batch rename
- System clipboard: copied files paste into other apps — browsers (Teams, Gmail, web chat), Discord,
  Slack, Nautilus; a single copied picture also pastes as an image
- Archives: zip/tar natively, 7z/rar/cab/iso via 7-Zip; extract on double-click
- Preview: images incl. EXR/HDR/IFF/PSD decoders, text with quick editor, PDF, folder contents,
  video/audio (GStreamer), 3D models (OBJ/STL/PLY/FBX/glTF/Alembic incl. HDF5/USD/.blend) with a
  multi-process software rasteriser or OpenGL; ⅛ s crossfades; resizable, remembered panes
- Removable drives: live detection, USB badge, eject, format (UDisks2), physical-disk grouping,
  dual-boot partitions hidden until mounted; Windows-style This PC tile view
- Optional encrypted file index (AES-256 + HMAC, keyring-backed) for navigation and search head start
- CPU parking, stall watchdog with freeze dumps, `--selftest`, `--preview-bench`, `--stress`,
  `--nav-bench`, `--profile`, `--probe-gl`, `--probe-model`
- OpenRV integration (Ctrl+Shift+R)
- Crash and error reporting: exceptions, hard crashes and freezes become reports you can review,
  edit and file as a GitHub issue (Help → Report a problem…)
- Preferences dialog with General / View / Search / Optional tabs and dependency diagnostics

Known issues

- Video → video preview switches can still cut instead of crossfading on some setups.
