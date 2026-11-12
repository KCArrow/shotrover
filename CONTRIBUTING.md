# Contributing

## Setup

```bash
git clone https://github.com/KCArrow/shotrover.git && cd shotrover
# GTK 3 + PyGObject (+ numpy): see "Get started" in the README for your distro's command
./build.sh && python3 shotrover.py
```

## Workflow

1. Edit the parts in `src/` — never `shotrover.py`, it is generated. `docs/ARCHITECTURE.md` says what
   lives where and the order the parts are concatenated in.
2. `./build.sh` (also byte-compiles as a syntax check).
3. `python3 tests/headless.py --selftest` must pass; run `python3 shotrover.py --preview-bench --quick`
   if you touched decoders or the model pipeline, and `--stress` for anything in the window code.
4. Commit `src/` **and** the rebuilt `shotrover.py` together, so the single-file download on the
   default branch always matches the source.

## Rules of the house

- The GTK main thread never touches the disk or the network. Anything that can block goes to a
  thread or the `run_heavy` pool and reports back with `GLib.idle_add` + a generation check.
- No pip dependencies for the core. New capabilities are optional, detected at runtime, listed in
  `optional_deps()` (p3d) so they show up in Preferences → Optional with an install hint, and the
  app must degrade gracefully (a message in the preview pane, never an exception dialog).
- Every GStreamer call goes through `VideoPreview._ops`. Every new preview type gets its row in
  `run_preview_bench` and a unit test in `run_selftest`.
- UI strings are terse: labels, not explanations. The baseline is Python 3.9 syntax and GTK 3.24, so it runs on
  long-term-support distros as well as rolling ones.
- Nothing distro-specific in the code: find tools on PATH or in their usual locations, and give install
  hints through `pkg_install()` / `pkg_hint()` (p3d), which pick dnf, apt, pacman or zypper names.
- Keep `--selftest` fast (< 10 s without `--bench`).

## Licensing of contributions

Shotrover is licensed under the PolyForm Noncommercial License (plus a permission that lets freelancers use it for paid work) with commercial licences sold
separately (see COMMERCIAL-LICENSE.md). So that this remains possible, by submitting a pull
request you agree that your contribution is provided under the same terms **and** that you grant
the project author a perpetual, irrevocable, royalty-free licence to use, modify and relicense it,
including under commercial terms. You keep the copyright to your work. If you can't agree to that,
please open an issue describing the change instead of a PR.

## Releasing

```bash
# bump VERSION in src/p1.py, update CHANGELOG.md
./build.sh && ./make-portable.sh         # dist/shotrover-<ver>-portable.zip
git tag v<ver> && git push --tags        # the release workflow attaches the zip
```
