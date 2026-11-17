

# --------------------------------------------------------------------------- input diagnostics
DEBUG_INPUT = bool(os.environ.get("SHOTROVER_DEBUG_INPUT"))
_INPUT_T0 = time.monotonic()


def input_log(msg: str):
    """SHOTROVER_DEBUG_INPUT=1: one line per click / selection event on stderr (and in error reports)."""
    line = f"[input {time.monotonic() - _INPUT_T0:8.3f}] {msg}"
    print(line, file=sys.stderr, flush=True)
    RECENT_LOG.append(line)


def is_double_click(last, item: int, event) -> bool:
    """Our own double-click test: second press on the same item within the desktop's double-click time and
    distance. `last` = (item, time, x_root, y_root) of the previous press, or None after a folder change."""
    if last is None or item < 0 or last[0] != item:
        return False
    st = Gtk.Settings.get_default()
    try:
        dt, dist = st.props.gtk_double_click_time, st.props.gtk_double_click_distance
    except Exception:
        dt, dist = 400, 5
    return (0 <= event.time - last[1] <= dt and abs(event.x_root - last[2]) <= dist and abs(event.y_root - last[3]) <= dist)


# --------------------------------------------------------------------------- row hover for tree views
def clip_width(widget: Gtk.Widget) -> Gtk.Widget:
    """Wrap a horizontal toolbar so it never dictates the pane's minimum width: a ScrolledWindow with an
    external horizontal policy reports a tiny minimum and simply clips what doesn't fit. Without this the
    preview pane grew whenever a wide toolbar (text editor, model bar, video controls) became visible."""
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
    sw.set_propagate_natural_height(True)
    set_child(sw, widget)
    return sw


class FitImage(Gtk.DrawingArea):
    """A picture that scales DOWN to whatever space it is given (never up), centred, with a minimum size of
    zero — unlike Gtk.Image, whose minimum is the pixbuf's full size and therefore stops a pane from being
    made smaller than the picture. Used for the preview image and the big fallback icon."""

    def __init__(self, max_size: int = 0):
        super().__init__()
        self.pixbuf = None
        self.max_size = max_size              # 0 = natural size cap is the pixbuf itself
        self.set_size_request(1, 1)
        on_draw(self, self._draw)
        # animated GIF / WebP: a GdkPixbufAnimation iterator advanced on its own frame delays
        self._anim_iter = None
        self._anim_timer = 0
        self.anim_paused = False
        self.connect("map", lambda w: self._anim_schedule())
        self.connect("unmap", lambda w: self._anim_cancel())

    def set_from_pixbuf(self, pb):
        self._anim_stop()
        self.pixbuf = pb
        self.queue_draw()

    def set_animation(self, anim):
        """Play a GdkPixbuf.PixbufAnimation (falls back to its still image when it has one frame).
        Frames advance only while the widget is mapped and the window is active."""
        self._anim_stop()
        if anim is None:
            image_set_pixbuf(self, None)
            return
        if anim.is_static_image():
            image_set_pixbuf(self, anim.get_static_image())
            return
        self._anim_iter = anim.get_iter(None)
        self.anim_paused = False
        self.pixbuf = self._anim_iter.get_pixbuf()
        self.queue_draw()
        self._anim_schedule()

    @property
    def animating(self) -> bool:
        return self._anim_iter is not None

    def toggle_animation(self):
        if self._anim_iter is None:
            return
        self.anim_paused = not self.anim_paused
        if self.anim_paused:
            self._anim_cancel()
        else:
            self._anim_iter.advance(None)          # restart timing from now, not from when we paused
            self._anim_schedule()

    def _anim_stop(self):
        self._anim_cancel()
        self._anim_iter = None

    def _anim_cancel(self):
        if self._anim_timer:
            GLib.source_remove(self._anim_timer)
            self._anim_timer = 0

    def _anim_schedule(self):
        if self._anim_iter is None or self._anim_timer or self.anim_paused or not self.get_mapped():
            return
        delay = self._anim_iter.get_delay_time()
        if delay < 0:
            return                                  # last frame of a GIF that doesn't loop
        self._anim_timer = GLib.timeout_add(max(20, delay), self._anim_tick)

    def _anim_tick(self):
        self._anim_timer = 0
        it = self._anim_iter
        if it is None:
            return False
        top = toplevel(self)
        if isinstance(top, Gtk.Window) and not top.is_active():
            self._anim_timer = GLib.timeout_add(250, self._anim_tick)     # window in the background: idle
            return False
        if it.advance(None):
            self.pixbuf = it.get_pixbuf()
            self.queue_draw()
        self._anim_schedule()
        return False

    def _draw(self, w, cr):
        pb = self.pixbuf
        if pb is None:
            return False
        a = self.get_allocation()
        pw, ph = pb.get_width(), pb.get_height()
        cap = self.max_size or max(pw, ph)
        s = min(1.0, a.width / pw, a.height / ph, cap / max(pw, ph))
        dw, dh = pw * s, ph * s
        x, y = (a.width - dw) / 2, (a.height - dh) / 2
        cr.save()
        cr.translate(x, y)
        cr.scale(s, s)
        Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        cr.get_source().set_filter(cairo_filter_good())
        cr.paint()
        cr.restore()
        return False


def cairo_filter_good():
    try:
        import cairo
        return cairo.FILTER_GOOD
    except Exception:
        return 0


def enable_row_hover(tv: Gtk.TreeView):
    """Track the row under the pointer in tv.hover_path and repaint; cell data funcs read it via hover_bg()."""
    tv.hover_path = None
    add_event_mask(tv, EVMASK.POINTER_MOTION_MASK | EVMASK.LEAVE_NOTIFY_MASK)

    def motion(w, event):
        hit = w.get_path_at_pos(int(event.x), int(event.y))
        p = hit[0] if hit else None
        old = w.hover_path
        if (p is None) != (old is None) or (p is not None and old is not None and p.compare(old) != 0):
            w.hover_path = p
            w.queue_draw()
        return False

    def leave(w, event):
        if w.hover_path is not None:
            w.hover_path = None
            w.queue_draw()
        return False
    on_event(tv, "motion-notify-event", motion)
    on_event(tv, "leave-notify-event", leave)


def hover_bg(tv: Gtk.TreeView, cell, path_or_iter_model, it):
    """Apply/clear the subtle hover background on a renderer for the row being drawn.
    Runs for every visible cell of every frame, so it talks to GTK only when the renderer's state changes."""
    hp = getattr(tv, "hover_path", None)
    on = hp is not None and path_or_iter_model.get_path(it).compare(hp) == 0 and not tv.get_selection().iter_is_selected(it)
    if on:
        fg = style_fg(tv.get_style_context(), Gtk.StateFlags.NORMAL)
        cell.set_property("cell-background-rgba", rgba(fg.red, fg.green, fg.blue, 0.07))
    if on or getattr(cell, "_sr_hover", True):
        cell.set_property("cell-background-set", on)
        cell._sr_hover = on


# --------------------------------------------------------------------------- soft grid lines for tree views
def enable_soft_grid(tv: Gtk.TreeView, columns: bool = True):
    """Draw our own separators after the rows: faint horizontal rules, and (optionally) vertical rules that
    fade out as they approach each horizontal rule so the crossings never form a visible '+'."""
    # GTK 4: nothing can be painted over a tree view (on_draw_over does nothing there), and GTK's own grid
    # lines make every row a pixel taller than under GTK 3, so the lists go without these faint rules.
    tv.set_grid_lines(Gtk.TreeViewGridLines.NONE)

    def draw(w, cr):
        model = w.get_model()
        if model is None:
            return False
        rng = w.get_visible_range()
        if not rng or rng[0] is None:
            return False
        start, end = rng
        cols = [c for c in w.get_columns() if c.get_visible()]
        if not cols:
            return False
        fg = style_fg(w.get_style_context(), Gtk.StateFlags.NORMAL)
        alloc = w.get_allocation()
        rows = []
        it = model.get_iter(start)
        while it is not None:
            p = model.get_path(it)
            r = w.get_background_area(p, cols[0])
            _, y = w.convert_bin_window_to_widget_coords(0, r.y)
            v = model[it][0]
            if not (getattr(v, "kind", "") == "spacer"):
                rows.append((y, r.height))
            if p.compare(end) == 0:
                break
            it = model.iter_next(it)
            if it is None:
                break
        cr.save()
        cr.set_line_width(1)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.055)
        for y, h in rows:
            cr.move_to(0, y + h - 0.5)
            cr.line_to(alloc.width, y + h - 0.5)
        cr.stroke()
        if columns and rows:
            xs = []
            for c in cols[:-1]:
                r = w.get_background_area(start, c)
                x, _ = w.convert_bin_window_to_widget_coords(r.x + r.width, 0)
                xs.append(x - 0.5)
            fade = 7
            # Rows of one height that follow each other share one repeating gradient and one stroke per
            # column, instead of a gradient and a stroke for every cell on every frame.
            runs = []
            for y, h in rows:
                if runs and runs[-1][1] == h and runs[-1][0] + runs[-1][1] * runs[-1][2] == y:
                    runs[-1][2] += 1
                else:
                    runs.append([y, h, 1])
            import cairo
            for y, h, n in runs:
                if h <= 2 * fade + 2:
                    continue
                pat = cairo_linear(0, y, 0, y + h, fg, fade / h)
                pat.set_extend(cairo.EXTEND_REPEAT)
                cr.set_source(pat)
                for x in xs:
                    cr.move_to(x, y)
                    cr.line_to(x, y + h * n)
                cr.stroke()
        cr.restore()
        return False
    on_draw_over(tv, draw)


def cairo_linear(x0, y0, x1, y1, fg, frac):
    import cairo
    pat = cairo.LinearGradient(x0, y0, x1, y1)
    pat.add_color_stop_rgba(0.0, fg.red, fg.green, fg.blue, 0.0)
    pat.add_color_stop_rgba(frac, fg.red, fg.green, fg.blue, 0.055)
    pat.add_color_stop_rgba(1.0 - frac, fg.red, fg.green, fg.blue, 0.055)
    pat.add_color_stop_rgba(1.0, fg.red, fg.green, fg.blue, 0.0)
    return pat


# --------------------------------------------------------------------------- virtualized icon grid
class IconGrid(ScrollCanvas):
    """A Nautilus-style icon view: only the tiles inside the viewport are laid out and painted, so a
    folder with 100k entries costs the same per frame as one with 100. Reads rows straight from the
    FolderView ListStore (col 0 Entry, col 2 pixbuf, col 3 markup). API mirrors the bits of
    Gtk.IconView that FolderView used: paths are Gtk.TreePath, signals item-activated / selection-changed."""

    __gsignals__ = {
        "item-activated": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "selection-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, model: Gtk.ListStore):
        super().__init__()
        self.model: Optional[Gtk.ListStore] = None
        takes_keys(self)
        add_event_mask(self, EVMASK.BUTTON_PRESS_MASK | EVMASK.BUTTON_RELEASE_MASK |
                        EVMASK.POINTER_MOTION_MASK | EVMASK.KEY_PRESS_MASK |
                        EVMASK.SCROLL_MASK | EVMASK.LEAVE_NOTIFY_MASK)
        css_class(self, "icongrid")
        # geometry
        self.icon_size = 48
        self.horizontal = False
        self.tile_w, self.tile_h = 96, 90
        self.margin = 8
        self.cols = 1
        self.text_lines = 2
        # state
        self.selected: set = set()
        self.cursor = -1
        self.anchor = -1
        self.prelight = -1
        self.single_click = False
        self.press_index = -1
        self.press_pos = None
        self.press_was_selected = False
        self.rubber: Optional[Tuple[float, float, float, float]] = None
        self.rubber_base: set = set()
        self.drag_targets = None
        self.drag_actions = 0
        self.provider: Optional[Callable] = None     # entry -> (pixbuf, markup); used when model cols 2/3 are None
        self.muted = False                           # inactive split pane: grey icons, dimmer text
        self._cache: Dict[int, Tuple[object, str]] = {}
        # Shaped text and converted icons are kept between frames: while the window is being resized the same
        # tiles are redrawn on every frame, and wrapping each name and converting each pixbuf again took
        # more than half of the frame.
        self._layout_cache: dict = {}
        self._surf_cache: dict = {}
        self._surf_bytes = 0
        if GTK4:
            self.set_draw_func(lambda a, cr, w, h, *_: self._draw(a, cr))
            for prop in ("gtk-font-name", "gtk-theme-name", "gtk-xft-dpi"):      # shaped text is cached
                Gtk.Settings.get_default().connect("notify::" + prop, lambda *a: self.invalidate())
        else:
            self.connect("style-updated", lambda w: self._layout_cache.clear())      # font or theme changed
            self.connect("draw", self._draw)
        on_resize(self, self._relayout)
        on_event(self, "button-press-event", self._press)
        on_event(self, "button-release-event", self._release)
        on_event(self, "motion-notify-event", self._motion)
        on_event(self, "leave-notify-event", lambda w, e: self._set_prelight(-1))
        on_event(self, "key-press-event", self._key)
        on_event(self, "focus-in-event", lambda w, e: self.queue_draw() or False)
        on_event(self, "focus-out-event", lambda w, e: self.queue_draw() or False)
        if not GTK4:                       # GTK 4: file_drag_source() puts a Gtk.DragSource on the grid instead
            self.connect("drag-begin", self._drag_begin)
        if not GTK4:
            on_event(self, "grab-broken-event", lambda w, e: self._reset_press())
            self.connect("grab-notify", lambda w, was_grabbed: None if was_grabbed else self._reset_press())
        self.set_model(model)

    def _reset_press(self):
        """A dialog or drag grab interrupted a click: forget the pending press/rubber band."""
        if DEBUG_INPUT:
            input_log("grid: press reset by a grab")
        self.press_index, self.press_pos = -1, None
        if self.rubber is not None:
            self.rubber = None
            self.queue_draw()
        return False

    def _drag_begin(self, w, ctx):
        if self.cursor >= 0 and self.model is not None:
            try:
                pb = self._tile_data(self.cursor, self.model[self.cursor])[0]
                if pb is not None:
                    Gtk.drag_set_icon_pixbuf(ctx, pb, pb.get_width() // 2, pb.get_height() // 2)
            except (IndexError, ValueError):
                pass

    # ---- model
    def set_model(self, model):
        if self.model is not None:
            for h in getattr(self, "_mh", []):
                self.model.disconnect(h)
        self.model = model
        self._mh = []
        if model is not None:
            self._mh = [model.connect("row-changed", self._row_changed),
                        model.connect("row-inserted", lambda m, p, it: self._model_resized()),
                        model.connect("row-deleted", lambda m, p: self._model_resized())]
        if DEBUG_INPUT:
            input_log(f"grid: set_model({'None' if model is None else len(model)}) — selection, cursor and shift-anchor reset")
        self.selected.clear()
        self.cursor = self.anchor = -1
        self._last_click = None          # a click in the previous folder never pairs with one in this folder
        self._model_resized()

    def get_model(self):
        return self.model

    def _row_changed(self, m, p, it):
        self._cache.pop(p.get_indices()[0], None)
        self.queue_draw()

    def _drop_surfaces(self):
        self._surf_cache.clear()
        self._surf_bytes = 0

    def _icon_surface(self, pb):
        surf = self._surf_cache.get(pb)
        if surf is None:
            size = pb.get_width() * pb.get_height() * 4
            if self._surf_bytes + size > (48 << 20):
                self._drop_surfaces()
            surf = pixbuf_surface(pb)
            self._surf_cache[pb] = surf
            self._surf_bytes += size
        return surf

    def invalidate(self):
        self._drop_surfaces()
        self._cache.clear()
        self.queue_draw()

    def _tile_data(self, i, row):
        """(pixbuf, markup) for a row: model columns if filled, else computed once via provider and cached."""
        pb, mk = row[2], row[3]
        if pb is not None and mk is not None:
            return pb, mk
        hit = self._cache.get(i)
        if hit is None:
            hit = self.provider(row[0]) if self.provider else (None, "")
            self._cache[i] = hit
        return hit

    def _n(self) -> int:
        return len(self.model) if self.model is not None else 0

    def _model_resized(self):
        n = self._n()
        self.selected = {i for i in self.selected if i < n}
        if self.cursor >= n:
            self.cursor = n - 1
        self._drop_surfaces()
        self._cache.clear()
        self._relayout()

    # ---- layout
    def configure(self, icon_size: int, horizontal: bool, item_width: int, single_click: bool, extra_lines: int = 0):
        """extra_lines: more text rows than the layout normally has (search results add where the file is)."""
        self.icon_size, self.horizontal, self.single_click = icon_size, horizontal, single_click
        probe = self.create_pango_layout("Xg")
        line = probe.get_pixel_size()[1] + 1
        self.line_h, self.extra_lines = line, extra_lines
        if horizontal:
            self.text_lines = (3 + extra_lines) if icon_size >= 48 else 1
            self.tile_w = item_width
            self.tile_h = max(icon_size, self.text_lines * line) + 12
        else:
            self.text_lines = 2 + extra_lines
            self.tile_w = max(90, item_width)
            self.tile_h = icon_size + 10 + self.text_lines * line + 10
        self._layout_cache.clear()
        self._drop_surfaces()
        self._cache.clear()
        self._relayout()

    def _relayout(self):
        w = max(1, self.get_allocated_width() - 2 * self.margin)
        self.cols = max(1, w // self.tile_w)
        rows = (self._n() + self.cols - 1) // self.cols
        self.set_size(self.get_allocated_width(), rows * self.tile_h + 2 * self.margin)
        self.queue_draw()

    def _tile_rect(self, i: int) -> Tuple[int, int, int, int]:
        r, c = divmod(i, self.cols)
        return self.margin + c * self.tile_w, self.margin + r * self.tile_h, self.tile_w, self.tile_h

    def _index_at(self, x: float, y: float) -> int:
        """Index of the tile under canvas coords, or -1 (empty space counts as -1 only outside the tile box)."""
        c = int((x - self.margin) // self.tile_w)
        r = int((y - self.margin) // self.tile_h)
        if x < self.margin or y < self.margin or c < 0 or c >= self.cols or r < 0:
            return -1
        i = r * self.cols + c
        return i if i < self._n() else -1

    def _visible_range(self) -> Tuple[int, int]:
        v = Gtk.Scrollable.get_vadjustment(self)
        top = int(v.get_value()) if v else 0
        h = self.get_allocated_height()
        r0 = max(0, (top - self.margin) // self.tile_h)
        r1 = (top + h - self.margin) // self.tile_h + 1
        return int(r0 * self.cols), int(min(self._n(), (r1 + 1) * self.cols))

    # ---- drawing
    def _draw(self, w, cr):
        n = self._n()
        # Gtk.Layout paints no backdrop of its own: without this the grid showed the window colour while the
        # list layouts showed the theme's base colour, so the file area changed shade with the layout.
        Gtk.render_background(self.get_style_context(), cr, 0, 0, self.get_allocated_width(), self.get_allocated_height())
        if n == 0:
            return False
        # GTK 3.24 hands us a widget-relative cairo context; the scrolled canvas lives in the bin window,
        # which sits at (-hadj, -vadj). Translate so we can draw in canvas coordinates.
        cr.save()
        cr.translate(-self._hoff(), -self._voff())
        try:
            self._draw_tiles(cr)
        finally:
            cr.restore()
        return False

    def _draw_tiles(self, cr):
        n = self._n()
        sc = self.get_style_context()
        fg = style_fg(sc, Gtk.StateFlags.NORMAL)
        ok, sel = sc.lookup_color("theme_selected_bg_color")
        sel = sel if ok else rgba(0.2, 0.5, 0.9, 1)
        ok, selfg = sc.lookup_color("theme_selected_fg_color")
        selfg = selfg if ok else rgba(1, 1, 1, 1)
        focused = self.has_focus()
        a, b = self._visible_range()
        pad = 6
        if self.horizontal:
            cr.save()
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.055)
            cr.set_line_width(1)
            for i in range(a, b, self.cols):
                x, y, tw, th = self._tile_rect(i)
                cr.move_to(self.margin, y + th - 0.5)
                cr.line_to(self.margin + self.cols * self.tile_w, y + th - 0.5)
            cr.stroke()
            cr.restore()
        for i in range(a, b):
            try:
                row = self.model[i]
            except (IndexError, ValueError):
                break
            x, y, tw, th = self._tile_rect(i)
            is_sel = i in self.selected
            if is_sel or i == self.prelight:
                cr.save()
                _rounded(cr, x + 2, y + 2, tw - 4, th - 4, 6)
                if is_sel:
                    g_ = 0.2126 * sel.red + 0.7152 * sel.green + 0.0722 * sel.blue
                    if self.muted:
                        cr.set_source_rgba(g_, g_, g_, 0.35)
                    else:
                        cr.set_source_rgba(sel.red, sel.green, sel.blue, 0.85 if focused else 0.5)
                else:
                    cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.08)
                cr.fill()
                cr.restore()
            pb, markup = self._tile_data(i, row)
            size = self.icon_size
            if self.horizontal:
                ix, iy = x + pad, y + (th - size) // 2
                tx, ty, tw_text = x + pad + size + 8, y + 6, tw - size - 3 * pad - 8
            else:
                ix, iy = x + (tw - size) // 2, y + pad
                tx, ty, tw_text = x + 4, y + pad + size + 6, tw - 8
            if pb is not None:
                if self.muted:
                    pb = ICONS.desaturated(pb)
                ox, oy = (size - pb.get_width()) // 2, (size - pb.get_height()) // 2
                cr.set_source_surface(self._icon_surface(pb), ix + ox, iy + oy)
                cr.paint()
            lay = self._text_layout(cr, i, markup, tw_text)
            if is_sel:
                cr.set_source_rgba(selfg.red, selfg.green, selfg.blue, 1)
            else:
                cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.6 if self.muted else 1)
            cr.move_to(tx, ty if self.horizontal else ty)
            PangoCairo.show_layout(cr, lay)
            if i == self.cursor and focused:
                cr.save()
                _rounded(cr, x + 2, y + 2, tw - 4, th - 4, 6)
                cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.5)
                cr.set_line_width(1)
                cr.set_dash([2, 2])
                cr.stroke()
                cr.restore()
        if self.rubber:
            x0, y0, x1, y1 = self.rubber
            cr.rectangle(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            cr.set_source_rgba(sel.red, sel.green, sel.blue, 0.2)
            cr.fill_preserve()
            cr.set_source_rgba(sel.red, sel.green, sel.blue, 0.8)
            cr.set_line_width(1)
            cr.stroke()
        return False

    def _text_layout(self, cr, i, markup, width):
        key = (markup, width, self.text_lines, self.horizontal)
        lay = self._layout_cache.get(key)
        if lay is not None:
            return lay
        if len(self._layout_cache) > 4000:
            self._layout_cache.clear()
        lay = self.create_pango_layout("")        # widget's own Pango context: same font as the rest of the UI
        lay.set_markup(markup or "", -1)
        lay.set_width(max(10, int(width * Pango.SCALE)))
        lay.set_wrap(Pango.WrapMode.WORD_CHAR)
        lay.set_ellipsize(Pango.EllipsizeMode.END)
        # A negative height is a line limit for EACH paragraph, and a tile with a second paragraph (where the
        # file is) would get twice the lines the tile has room for and run into the tile below. So: the name
        # keeps its usual lines, and if the whole text is still too tall, cut it at the tile's text height.
        lay.set_height(-max(1, self.text_lines - getattr(self, "extra_lines", 0)))
        if lay.get_line_count() > self.text_lines:
            lay.set_height(self.text_lines * getattr(self, "line_h", 18) * Pango.SCALE)
        lay.set_alignment(Pango.Alignment.LEFT if self.horizontal else Pango.Alignment.CENTER)
        self._layout_cache[key] = lay
        return lay

    # ---- selection API (Gtk.IconView-compatible subset)
    def _emit_sel(self):
        self.emit("selection-changed")
        self.queue_draw()

    def get_selected_items(self):
        return [Gtk.TreePath.new_from_indices([i]) for i in sorted(self.selected)]

    def path_is_selected(self, path) -> bool:
        return path.get_indices()[0] in self.selected

    def select_path(self, path):
        i = path.get_indices()[0]
        self.selected.add(i)
        if self.anchor < 0:                  # programmatic selection (after a reload / going up) anchors shift-click
            self.anchor = self.cursor = i
        self._emit_sel()

    def unselect_path(self, path):
        self.selected.discard(path.get_indices()[0])
        self._emit_sel()

    def select_all(self):
        self.selected = set(range(self._n()))
        self._emit_sel()

    def unselect_all(self):
        if self.selected:
            self.selected.clear()
            self._emit_sel()

    def set_cursor(self, path, cell=None, start_editing=False):
        self.cursor = path.get_indices()[0]
        self.anchor = self.cursor
        self.queue_draw()

    def get_cursor(self):
        return (Gtk.TreePath.new_from_indices([self.cursor]) if self.cursor >= 0 else None, None)

    def scroll_to_path(self, path, use_align=False, row_align=0.0, col_align=0.0):
        i = path.get_indices()[0]
        x, y, tw, th = self._tile_rect(i)
        v = Gtk.Scrollable.get_vadjustment(self)
        if v is None:
            return
        top, page = v.get_value(), v.get_page_size()
        if y < top:
            v.set_value(y - self.margin)
        elif y + th > top + page:
            v.set_value(y + th - page + self.margin)

    def get_path_at_pos(self, x, y):
        """x, y in bin-window (canvas) coordinates, which is what button events on a Gtk.Layout carry."""
        i = self._index_at(x, y)
        return Gtk.TreePath.new_from_indices([i]) if i >= 0 else None

    def get_dest_item_at_pos(self, x, y):
        """x, y in widget coordinates (what drag-data-received gives)."""
        p = self.get_path_at_pos(x + self._hoff(), y + self._voff())
        return (p, Gtk.IconViewDropPosition.DROP_INTO) if p is not None else None

    def set_activate_on_single_click(self, v):
        self.single_click = v

    def enable_model_drag_source(self, start_button_mask, targets, actions):
        self.drag_targets = Gtk.TargetList.new(targets)
        self.drag_actions = actions

    def _voff(self):
        v = Gtk.Scrollable.get_vadjustment(self)          # (Gtk.Layout's own getter is deprecated)
        return v.get_value() if v else 0

    def _hoff(self):
        h = Gtk.Scrollable.get_hadjustment(self)
        return h.get_value() if h else 0

    # ---- mouse
    def _set_prelight(self, i):
        if i != self.prelight:
            self.prelight = i
            self.queue_draw()

    def _press(self, w, event):
        self.grab_focus()
        x, y = event.x, event.y          # bin-window coordinates
        i = self._index_at(x, y)
        mods = event.state & Gtk.accelerator_get_default_mod_mask()
        ctrl, shift = bool(mods & Gdk.ModifierType.CONTROL_MASK), bool(mods & Gdk.ModifierType.SHIFT_MASK)
        if DEBUG_INPUT:
            input_log(f"grid: {event.type.value_nick} button={event.button} item={i} shift={shift} ctrl={ctrl} "
                      f"anchor={self.anchor} cursor={self.cursor} selected={len(self.selected)} t={event.time}")
        if event.type != EV_PRESS:
            # GDK's own 2/3-click events are ignored: GDK keeps counting clicks across a folder change, so the
            # first click of a quick double-click right after opening a folder became the THIRD click of the
            # double-click that opened it, and the real double-click was lost. We pair clicks ourselves below.
            return True
        if event.button == 1:
            if is_double_click(getattr(self, "_last_click", None), i, event):
                self._last_click = None
                if i >= 0 and not self.single_click:
                    self.cursor = i
                    self.emit("item-activated", Gtk.TreePath.new_from_indices([i]))
                return True
            self._last_click = (i, event.time, event.x_root, event.y_root)
            self.press_index, self.press_pos = i, (event.x, event.y)
            self.press_was_selected = i in self.selected
            if i < 0:
                if not (ctrl or shift):
                    self.unselect_all()
                self.rubber = (x, y, x, y)
                self.rubber_base = set(self.selected) if ctrl else set()
                return True
            if ctrl:
                (self.selected.discard if i in self.selected else self.selected.add)(i)
                self.cursor = self.anchor = i
                self._emit_sel()
            elif shift and (self.anchor >= 0 or self.cursor >= 0 or self.selected):
                if self.anchor < 0:
                    self.anchor = self.cursor if self.cursor >= 0 else min(self.selected)
                lo, hi = min(self.anchor, i), max(self.anchor, i)
                self.selected = set(range(lo, hi + 1))
                self.cursor = i
                self._emit_sel()
            elif i not in self.selected:
                self.selected = {i}
                self.cursor = self.anchor = i
                self._emit_sel()
            else:
                self.cursor = i
                self.queue_draw()
            return True
        if event.button == 3:
            return False     # FolderView handles the context menu (it reads get_path_at_pos)
        return False

    def _motion(self, w, event):
        x, y = event.x, event.y
        if self.rubber is not None:
            self.rubber = (self.rubber[0], self.rubber[1], x, y)
            x0, y0, x1, y1 = self.rubber
            rx0, ry0, rx1, ry1 = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
            hit = set()
            r0, r1 = max(0, int((ry0 - self.margin) // self.tile_h)), int((ry1 - self.margin) // self.tile_h)
            for r in range(r0, r1 + 1):
                for c in range(self.cols):
                    i = r * self.cols + c
                    if i >= self._n():
                        break
                    tx, ty, tw, th = self._tile_rect(i)
                    if tx < rx1 and tx + tw > rx0 and ty < ry1 and ty + th > ry0:
                        hit.add(i)
            new = self.rubber_base ^ hit if self.rubber_base else hit
            if new != self.selected:
                self.selected = new
                self.emit("selection-changed")
            self.queue_draw()
            # autoscroll near edges
            v = Gtk.Scrollable.get_vadjustment(self)
            if v:
                vy = event.y - v.get_value()
                if vy < 12:
                    v.set_value(max(v.get_lower(), v.get_value() - 10))
                elif vy > self.get_allocated_height() - 12:
                    v.set_value(min(v.get_upper() - v.get_page_size(), v.get_value() + 10))
            return True
        if self.press_index >= 0 and self.press_pos is not None and self.drag_targets is not None and (event.state & Gdk.ModifierType.BUTTON1_MASK):
            if self.drag_check_threshold(int(self.press_pos[0]), int(self.press_pos[1]), int(event.x), int(event.y)):
                if self.press_index not in self.selected:
                    self.selected = {self.press_index}
                    self._emit_sel()
                self.drag_begin_with_coordinates(self.drag_targets, self.drag_actions, 1, event, int(event.x), int(event.y))
                self.press_index, self.press_pos = -1, None
                return True
        self._set_prelight(self._index_at(x, y))
        return False

    def _release(self, w, event):
        if event.button != 1:
            return False
        if self.rubber is not None:
            self.rubber = None
            self.queue_draw()
            return True
        i = self.press_index
        if i >= 0 and self.press_pos is not None:
            mods = event.state & Gtk.accelerator_get_default_mod_mask()
            moved = self.drag_check_threshold(int(self.press_pos[0]), int(self.press_pos[1]), int(event.x), int(event.y))
            if not moved and not mods:
                if self.single_click:
                    self.emit("item-activated", Gtk.TreePath.new_from_indices([i]))
                elif self.press_was_selected and self.selected != {i}:
                    self.selected = {i}     # click on one of several selected items selects just it
                    self._emit_sel()
        self.press_index, self.press_pos = -1, None
        return True

    # ---- keyboard
    def _key(self, w, event):
        n = self._n()
        if n == 0:
            return False
        key = event.keyval
        mods = event.state & Gtk.accelerator_get_default_mod_mask()
        ctrl, shift = bool(mods & Gdk.ModifierType.CONTROL_MASK), bool(mods & Gdk.ModifierType.SHIFT_MASK)
        cur = self.cursor if self.cursor >= 0 else 0
        page_rows = max(1, int(self.get_allocated_height() // self.tile_h))
        moves = {Gdk.KEY_Left: -1, Gdk.KEY_Right: 1, Gdk.KEY_Up: -self.cols, Gdk.KEY_Down: self.cols,
                 Gdk.KEY_Page_Up: -self.cols * page_rows, Gdk.KEY_Page_Down: self.cols * page_rows,
                 Gdk.KEY_KP_Left: -1, Gdk.KEY_KP_Right: 1, Gdk.KEY_KP_Up: -self.cols, Gdk.KEY_KP_Down: self.cols}
        if key in moves or key in (Gdk.KEY_Home, Gdk.KEY_End):
            new = 0 if key == Gdk.KEY_Home else (n - 1 if key == Gdk.KEY_End else cur + moves[key])
            new = max(0, min(n - 1, new))
            self.cursor = new
            if shift:
                a = self.anchor if self.anchor >= 0 else cur
                self.selected = set(range(min(a, new), max(a, new) + 1))
            elif not ctrl:
                self.selected = {new}
                self.anchor = new
            self.scroll_to_path(Gtk.TreePath.new_from_indices([new]))
            self._emit_sel()
            return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not mods and self.cursor >= 0:
            self.emit("item-activated", Gtk.TreePath.new_from_indices([self.cursor]))
            return True
        if key == Gdk.KEY_a and ctrl:
            self.select_all()
            return True
        return False


def _rounded(cr, x, y, w, h, r):
    import math
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def draw_capacity_bar(cr, sc: Gtk.StyleContext, x: float, y: float, w: float, h: float, frac: Optional[float]):
    """A used-space pill: faint track, fill in the theme's accent (the danger colour past 90 %). The fill is
    never narrower than the bar is tall, so a nearly empty drive shows a round dot rather than a sliver."""
    fg = style_fg(sc, Gtk.StateFlags.NORMAL)
    r = h / 2.0
    _rounded(cr, x, y, w, h, r)
    cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.14)
    cr.fill()
    if frac is None:
        return
    f = max(0.0, min(1.0, frac))
    if f <= 0:
        return
    _rounded(cr, x, y, max(h, w * f), h, r)
    if f > 0.9:
        d = Gdk.RGBA()
        d.parse(COL_DANGER)
        cr.set_source_rgb(d.red, d.green, d.blue)
    else:
        ok, sel = sc.lookup_color("theme_selected_bg_color")
        if ok:
            cr.set_source_rgb(sel.red, sel.green, sel.blue)
        else:
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.6)
    cr.fill()


class UsageRenderer(Gtk.CellRenderer):
    """'Space used' cell in the list layouts: the same pill as the This PC tiles, with the percentage beside
    it. (Gtk.CellRendererProgress drew a fat trough with the text on top of the fill, and a blob at 13 %.)"""

    fraction = GObject.Property(type=float, default=0.0)
    text = GObject.Property(type=str, default="")

    def do_get_preferred_width(self, widget):
        return 120, 170

    def do_get_preferred_height(self, widget):
        return 14, 14

    def do_render(self, cr, widget, background_area, cell_area, flags):
        sc = widget.get_style_context()
        pad = 6
        bar_w = max(40, min(96, cell_area.width - 2 * pad - 70))
        bar_h = 6
        y = cell_area.y + (cell_area.height - bar_h) / 2.0
        draw_capacity_bar(cr, sc, cell_area.x + pad, y, bar_w, bar_h, self.fraction)
        lay = widget.create_pango_layout(self.text or "")
        tw, th = lay.get_pixel_size()
        if cell_area.width - bar_w - 3 * pad >= tw:
            fg = style_fg(sc, Gtk.StateFlags.SELECTED if flags & Gtk.CellRendererState.SELECTED else Gtk.StateFlags.NORMAL)
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.75)
            cr.move_to(cell_area.x + pad + bar_w + pad + 2, cell_area.y + (cell_area.height - th) / 2.0)
            PangoCairo.show_layout(cr, lay)


    def do_snapshot(self, snapshot, widget, background_area, cell_area, flags):
        """GTK 4 draws cells through a snapshot, not a cairo context: paint the same picture into a cairo
        node covering the cell."""
        from gi.repository import Graphene
        r = Graphene.Rect()
        r.init(cell_area.x, cell_area.y, cell_area.width, cell_area.height)
        self.do_render(snapshot.append_cairo(r), widget, background_area, cell_area, flags)


# --------------------------------------------------------------------------- This PC: Windows-style tile view
class DriveBar(Gtk.DrawingArea):
    """The thin capacity bar under a drive's name: used/total, red past 90 % like Explorer."""

    def __init__(self):
        super().__init__()
        self.frac = None
        self.set_size_request(120, 10)
        on_draw(self, self._draw)

    def set_fraction(self, frac):
        self.frac = frac
        self.queue_draw()

    def _draw(self, w, cr):
        a = self.get_allocation()
        draw_capacity_bar(cr, self.get_style_context(), 0, 2, a.width, a.height - 4, self.frac)
        return False


class PCView(Gtk.ScrolledWindow):
    """Explorer-style 'This PC': collapsible sections (Folders, one per physical disk, Network locations) of
    tiles. Folder tiles are icon + name; drive tiles are icon, name, capacity bar and 'x free of y'.
    Built from ordinary GTK widgets (FlowBox per section) so selection, keyboard navigation, hover and
    activation behave like the rest of the desktop. Emits 'selection-changed', 'item-activated' (Entry) and
    'context-menu' (Entry or None, event)."""

    __gsignals__ = {"selection-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
                    "item-activated": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
                    "context-menu": (GObject.SignalFlags.RUN_FIRST, None, (object, object))}

    def __init__(self):
        super().__init__(hexpand=True, vexpand=True)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.box = with_margins(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4), 12)
        set_child(self, self.box)
        self.flows: List[Gtk.FlowBox] = []
        self.tiles: Dict[int, Tuple[Gtk.FlowBoxChild, Entry, Optional[DriveBar], Optional[Gtk.Label]]] = {}
        self.single_click = False
        self._suppress = False
        self.collapsed: set = set()

    # ---- build
    def set_entries(self, ents: List[Entry], single_click: bool):
        self.single_click = single_click
        for c in child_widgets(self.box):
            take_out(self.box, c)
        self.flows, self.tiles = [], {}
        sections: List[Tuple[str, List[Entry]]] = []
        for e in ents:
            if sections and sections[-1][0] == e.section:
                sections[-1][1].append(e)
            else:
                sections.append((e.section, [e]))
        for title, items in sections:
            exp = Gtk.Expander(expanded=title not in self.collapsed)
            lab = Gtk.Label(xalign=0)
            lab.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>  <span alpha='55%'>({len(items)})</span>")
            exp.set_label_widget(lab)
            exp.connect("notify::expanded", lambda ex, p, t=title: (self.collapsed.discard(t) if ex.get_expanded() else self.collapsed.add(t)))
            fb = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.MULTIPLE, homogeneous=True, max_children_per_line=12, min_children_per_line=1,
                             row_spacing=4, column_spacing=4, margin_top=4, margin_bottom=8, margin_start=16, valign=Gtk.Align.START)
            fb.set_activate_on_single_click(single_click)
            fb.connect("selected-children-changed", self._sel_changed)
            fb.connect("child-activated", lambda f, ch: self.emit("item-activated", self.tiles[id(ch)][1]))
            on_event(fb, "button-press-event", self._press)
            for e in items:
                ch = Gtk.FlowBoxChild()
                tile, bar, info = self._make_tile(e)
                set_child(ch, tile)
                fb.insert(ch, -1)
                self.tiles[id(ch)] = (ch, e, bar, info)
            set_child(exp, fb)
            self.flows.append(fb)
            put(self.box, exp, False, False, 0)
            sep = Gtk.Separator()
            put(self.box, sep, False, False, 2)
        show_all(self.box)
        self.refresh()

    def _make_tile(self, e: Entry):
        is_drive = e.section not in ("Folders",) and (getattr(e, "drive_kind", "") or e.usage is not None)
        h = with_margins(Gtk.Box(spacing=10), 6)
        img = image_from_pixbuf(ICONS.pixbuf(e.icon, 48, e)) if e.icon else icon_image("folder", "dialog")
        img.set_valign(Gtk.Align.START)
        put(h, img, False, False, 0)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name = Gtk.Label(label=e.name, xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=26)
        put(v, name, False, False, 0)
        bar = info = None
        if is_drive:
            bar = DriveBar()
            put(v, bar, False, False, 2)
            info = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=28)
            css_class(info, "dim-label")
            put(v, info, False, False, 0)
            h.set_size_request(250, -1)
        else:
            sub = Gtk.Label(label=pretty_path(e.location or ""), xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE, max_width_chars=26)
            css_class(sub, "dim-label")
            put(v, sub, False, False, 0)
            h.set_size_request(200, -1)
        put(h, v, True, True, 0)
        if getattr(e, "drive_kind", "") == "unmounted":
            h.set_opacity(0.55)
        return h, bar, info

    def refresh(self):
        """Re-read usage/type on the entries (the free-space thread fills them in after the first paint)."""
        for ch, e, bar, info in self.tiles.values():
            if bar is not None:
                used, total = (e.usage or (0, 0))
                bar.set_fraction((used / total) if total else None)
            if info is not None:
                info.set_text(e.type or "")

    # ---- selection
    def _sel_changed(self, fb):
        if self._suppress:
            return
        self._suppress = True
        for other in self.flows:            # one selection across all sections (plain click only)
            if other is not fb and not (current_modifiers() & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)):
                other.unselect_all()
        self._suppress = False
        self.emit("selection-changed")

    def selected_entries(self) -> List[Entry]:
        out = []
        for fb in self.flows:
            for ch in fb.get_selected_children():
                out.append(self.tiles[id(ch)][1])
        return out

    def select_none(self):
        self._suppress = True
        for fb in self.flows:
            fb.unselect_all()
        self._suppress = False
        self.emit("selection-changed")

    def select_all(self):
        self._suppress = True
        for fb in self.flows:
            fb.select_all()
        self._suppress = False
        self.emit("selection-changed")

    def select_names(self, names: List[str]):
        self._suppress = True
        for fb in self.flows:
            fb.unselect_all()
            for ch in child_widgets(fb):
                if self.tiles[id(ch)][1].name in names:
                    fb.select_child(ch)
        self._suppress = False
        self.emit("selection-changed")

    def _press(self, fb, event):
        if event.button == 3:
            ch = fb.get_child_at_pos(int(event.x), int(event.y))
            if ch is not None:
                if not ch.is_selected():
                    self.select_none()
                    fb.select_child(ch)
                self.emit("context-menu", self.tiles[id(ch)][1], event)
            else:
                self.select_none()
                self.emit("context-menu", None, event)
            return True
        if event.button == 1 and fb.get_child_at_pos(int(event.x), int(event.y)) is None:
            self.select_none()
        return False


# --------------------------------------------------------------------------- system clipboard: files
class FileClipboard:
    """Puts copied/cut files on the system clipboard in every form other applications look for.

    Gtk.Clipboard.set_with_data() - the usual way to offer custom formats - is not callable from PyGObject
    (it is marked non-introspectable), so Shotrover owns the CLIPBOARD selection through a hidden widget and
    answers format requests itself. Offered, in order of preference:
      image/png (+ the file's own image type)  a single picture: pastes as an image in any chat / web app
      x-special/gnome-copied-files             Nautilus and other GTK file managers (copy vs cut)
      text/uri-list                            Chromium, Firefox, Electron apps (Teams, Discord, Slack), KDE:
                                               web pages receive these as real files on paste
      UTF8_STRING / text/plain                 the paths, for terminals and text fields
    The files stay on the clipboard while Shotrover runs (as with every X11/Wayland app)."""
    IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                   ".webp": "image/webp", ".bmp": "image/bmp"}
    MAX_IMAGE = 40 << 20             # bigger pictures are offered as files only

    def __init__(self):
        if not GTK4:                       # GTK 3 owns the selection through an invisible widget
            self.w = Gtk.Invisible()
            self.w.connect("selection-get", self._get)
            on_event(self.w, "selection-clear-event", self._lost)
            self.sel = Gdk.SELECTION_CLIPBOARD
        self.mode, self.paths, self.uris = "copy", [], []
        self.image_path: Optional[str] = None
        self._png: Optional[bytes] = None

    def targets_for(self, paths: List[str]) -> List[str]:
        targets = []
        self.image_path = None
        if len(paths) == 1:
            ext = os.path.splitext(paths[0])[1].lower()
            try:
                small = os.path.getsize(paths[0]) <= self.MAX_IMAGE
            except OSError:
                small = False
            if ext in self.IMAGE_TYPES and small:
                self.image_path = paths[0]
                targets.append("image/png")
                if self.IMAGE_TYPES[ext] != "image/png":
                    targets.append(self.IMAGE_TYPES[ext])
        return targets + ["x-special/gnome-copied-files", "text/uri-list", "UTF8_STRING", "text/plain;charset=utf-8",
                          "text/plain", "STRING", "TEXT"]

    def set_files(self, mode: str, paths: List[str]) -> bool:
        self.mode, self.paths = mode, list(paths)
        self.uris = [Gio.File.new_for_path(p).get_uri() for p in paths]
        self._png = None
        targets = self.targets_for(paths)
        if GTK4:                           # one content provider per format, offered together
            try:
                provs = [Gdk.ContentProvider.new_for_bytes(t, GLib.Bytes.new(self.payload(t) or b"")) for t in targets]
                Gdk.Display.get_default().get_clipboard().set_content(Gdk.ContentProvider.new_union(provs))
                return True
            except Exception as ex:
                bench(f"clipboard: offering the files failed: {ex}")
                return False
        try:
            Gtk.selection_clear_targets(self.w, self.sel)
            for i, t in enumerate(targets):
                Gtk.selection_add_target(self.w, self.sel, Gdk.Atom.intern(t, False), i)
            t0 = Gtk.get_current_event_time() or Gdk.CURRENT_TIME
            return bool(Gtk.selection_owner_set(self.w, self.sel, t0))
        except Exception as ex:
            bench(f"clipboard: owning the selection failed: {ex}")
            return False

    def _lost(self, *a):
        self.paths, self.uris, self.image_path, self._png = [], [], None, None
        return False

    def payload(self, name: str) -> Optional[bytes]:
        """The bytes for one clipboard format (None: nothing to offer)."""
        if name.startswith("image/"):
            p = self.image_path
            if not p:
                return None
            ext = os.path.splitext(p)[1].lower()
            try:
                if name == self.IMAGE_TYPES.get(ext):
                    with open(p, "rb") as f:
                        return f.read()
                if name == "image/png":
                    if self._png is None:
                        pb = GdkPixbuf.Pixbuf.new_from_file(p)
                        ok, buf = pb.save_to_bufferv("png", [], [])
                        self._png = bytes(buf) if ok else b""
                    return self._png or None
            except Exception as ex:
                bench(f"clipboard: image conversion failed: {ex}")
            return None
        if name == "x-special/gnome-copied-files":
            return (self.mode + "\n" + "\n".join(self.uris)).encode()
        if name == "text/uri-list":
            return ("\r\n".join(self.uris) + "\r\n").encode()          # RFC 2483: CRLF-separated
        return "\n".join(self.paths).encode()

    def _get(self, widget, sd, info, time_):
        name = sd.get_target().name()
        if name in ("UTF8_STRING", "STRING", "TEXT", "text/plain", "text/plain;charset=utf-8"):
            sd.set_text("\n".join(self.paths), -1)
            return
        data = self.payload(name)
        if data:
            sd.set(sd.get_target(), 8, data)


_FILE_CLIPBOARD: Optional[FileClipboard] = None


def file_clipboard() -> FileClipboard:
    global _FILE_CLIPBOARD
    if _FILE_CLIPBOARD is None:
        _FILE_CLIPBOARD = FileClipboard()
    return _FILE_CLIPBOARD


# --------------------------------------------------------------------------- the Details list under GTK 4
# Gtk.TreeView repaints every visible cell from scratch on every frame, through a Python call per cell, and
# builds a new text layout each time: about twice the cost of Gtk.ColumnView, which keeps one small widget per
# visible cell and only fills it in when a row scrolls into view. DetailsList wraps a ColumnView and answers
# the handful of TreeView calls FolderView makes (selection, cursor, row under a point, columns), in tree
# paths, so the folder view is the same code under both toolkits. It mirrors the rows of the Gtk.ListStore
# the icon layouts also read.
if GTK4:
    class _DRow(GObject.Object):
        """One row: an Entry, or the text of a group heading."""

        def __init__(self, v):
            super().__init__()
            self.v = v

    def _tpath(i: int):
        return Gtk.TreePath.new_from_indices([i])

    class _DSelection:
        """The part of Gtk.TreeSelection the folder view uses, over the list's Gtk.MultiSelection."""

        def __init__(self, owner):
            self.o = owner
            self._cbs: dict = {}
            self._next = 1

        def set_mode(self, mode):
            pass

        def connect(self, name, cb, *args):
            self._next += 1
            self._cbs[self._next] = (cb, args)
            return self._next

        def disconnect(self, hid):
            self._cbs.pop(hid, None)

        def handler_is_connected(self, hid) -> bool:
            return hid in self._cbs

        def changed(self):
            for cb, args in list(self._cbs.values()):
                cb(self, *args)

        def select_path(self, path):
            i = path.get_indices()[0]
            if self.o.is_entry(i):                       # group headings are never selected
                self.o.sel.select_item(i, False)

        def unselect_path(self, path):
            self.o.sel.unselect_item(path.get_indices()[0])

        def path_is_selected(self, path) -> bool:
            return self.o.sel.is_selected(path.get_indices()[0])

        def select_all(self):
            o = self.o
            o.sel.select_all()
            if o._heads:                                 # group headings stay out of it
                for i in range(o.rows.get_n_items()):
                    if not isinstance(o.rows.get_item(i).v, Entry):
                        o.sel.unselect_item(i)

        def unselect_all(self):
            self.o.sel.unselect_all()

        def get_selected_rows(self):
            return self.o.store, [_tpath(i) for i in self.o.selected_indices()]

        def count_selected_rows(self) -> int:
            return len(self.o.selected_indices())

    class DetailsList:
        """See the comment above. `fv` is the FolderView: it makes and fills the cells (_cell_make4,
        _cell_fill4), because what a cell shows is the folder view's business."""

        def __init__(self, fv):
            self.cv = None                               # first: __getattr__ falls back on it
            self.fv = fv
            self.rows = Gio.ListStore(item_type=_DRow)
            self.sel = Gtk.MultiSelection(model=self.rows)
            self.cv = Gtk.ColumnView(model=self.sel)
            self.cv.set_enable_rubberband(True)
            css_class(self.cv, "sr-details")
            self.selection = _DSelection(self)
            self.store = None                            # the Gtk.ListStore being mirrored, None while detached
            self._store_ids: list = []
            self.active = True                           # False while an icon layout shows: nothing is mirrored
            self._stale = False
            self._cells: dict = {}                       # cell -> column key, for the cells showing a row right now
            self._of_child: dict = {}                    # a cell's widget -> the cell (to find the row under a point)
            self._columns: list = []
            self._cursor: Optional[int] = None
            self._on_activate: list = []
            self._last_act = (None, 0.0)
            self._refresh_id = None
            self._sorting = False
            self._sort_key = None
            self._typed = ("", 0.0)
            self._heads = False                          # some rows are group headings
            self._specs = None                           # what set_columns was last asked for
            self._columns_id = None
            self.sel.connect("selection-changed", self._sel_changed)
            self.cv.connect("activate", lambda v, pos: self._activated(pos))
            rows = Gtk.SignalListItemFactory()
            rows.connect("bind", self._row_bind)
            self.cv.set_row_factory(rows)
            self.cv.get_sorter().connect("changed", self._sorter_changed)

        def __getattr__(self, name):                     # everything else is the widget's own
            cv = self.__dict__.get("cv")
            if cv is None:
                raise AttributeError(name)
            return getattr(cv, name)

        # ---- controllers: ours must see a click or a key before the rows do. A row takes Space and Enter for
        # itself and selects on any press; the folder view decides first (quick look, the context menu, its own
        # pairing of double clicks) and lets the rest through.
        def add_controller(self, controller):
            # (the drag source too: a row claims the press, and a claimed press never reaches a later phase)
            if isinstance(controller, (Gtk.GestureClick, Gtk.EventControllerKey, Gtk.DragSource)):
                controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            self.cv.add_controller(controller)

        # ---- rows
        def is_entry(self, i: int) -> bool:
            row = self.rows.get_item(i) if 0 <= i < self.rows.get_n_items() else None
            return row is not None and isinstance(row.v, Entry)

        def _row_bind(self, factory, row):
            item = row.get_item()
            real = item is not None and isinstance(item.v, Entry)
            row.set_selectable(real)
            row.set_activatable(real)

        def get_model(self):
            return self.store

        def set_model(self, store):
            if self.store is not None:
                for h in self._store_ids:
                    self.store.disconnect(h)
            self._store_ids = []
            self.store = store
            if store is None:
                return                                   # what is shown stays until the new rows are attached
            self._store_ids = [store.connect("row-inserted", self._inserted)]
            self._resync()

        def set_active(self, on: bool):
            was, self.active = self.active, bool(on)
            if self.active and not was and self._stale and self.store is not None:
                self._resync()

        def _resync(self):
            if not self.active:
                self._stale = True
                return
            self._stale = False
            store, items = self.store, []
            it = store.get_iter_first()
            while it is not None:
                items.append(_DRow(store.get_value(it, 0)))
                it = store.iter_next(it)
            self._heads = any(not isinstance(r.v, Entry) for r in items)
            had = self.sel.get_selection().get_size() > 0
            self.rows.splice(0, self.rows.get_n_items(), items)
            self._cursor = None
            if had:
                self.selection.changed()

        def _inserted(self, store, path, it):
            if not self.active:
                self._stale = True
                return
            row = _DRow(store.get_value(it, 0))
            if not isinstance(row.v, Entry):
                self._heads = True
            self.rows.insert(path.get_indices()[0], row)

        # ---- selection and cursor
        def get_selection(self):
            return self.selection

        def selected_indices(self) -> List[int]:
            bits = self.sel.get_selection()
            out = []
            for k in range(bits.get_size()):
                i = bits.get_nth(k)
                if self.is_entry(i):
                    out.append(i)
            return out

        @property
        def selected(self):                              # what file_drag_source asks a list for
            return set(self.selected_indices())

        def _sel_changed(self, model, position, n_items):
            self.selection.changed()
            if any(key == "_chk" for key in self._cells.values()):
                self.refresh()

        def _has_focus(self) -> bool:
            root = self.cv.get_root()
            f = root.get_focus() if root is not None else None
            return f is not None and (f is self.cv or f.is_ancestor(self.cv))

        def contains(self, widget) -> bool:
            return widget is not None and (widget is self.cv or widget.is_ancestor(self.cv))

        def set_cursor(self, path, column=None, start_editing=False):
            """Like the tree view: the row becomes the only selected one and is scrolled into view."""
            i = path.get_indices()[0]
            if not 0 <= i < self.rows.get_n_items():
                return
            self._cursor = i
            flags = Gtk.ListScrollFlags.SELECT
            if self._has_focus():                        # never take the keyboard from the address bar or a dialog
                flags |= Gtk.ListScrollFlags.FOCUS
            self.cv.scroll_to(i, None, flags, None)

        def get_cursor(self):
            root = self.cv.get_root()
            f = root.get_focus() if root is not None else None
            if f is not None and f is not self.cv and f.is_ancestor(self.cv):
                pos = self._pos_of(f)
                if pos is not None:
                    self._cursor = pos
            ok = self._cursor is not None and 0 <= self._cursor < self.rows.get_n_items()
            return (_tpath(self._cursor) if ok else None), None

        def scroll_to_cell(self, path, *a):
            i = path.get_indices()[0]
            if 0 <= i < self.rows.get_n_items():
                self.cv.scroll_to(i, None, Gtk.ListScrollFlags.NONE, None)

        def grab_focus(self):
            if self._cursor is not None and 0 <= self._cursor < self.rows.get_n_items():
                self.cv.scroll_to(self._cursor, None, Gtk.ListScrollFlags.FOCUS, None)
                return True
            return self.cv.grab_focus()

        # ---- the row under a point (coordinates relative to the list widget, header included)
        def _pos_of(self, widget) -> Optional[int]:
            w = widget
            while w is not None and w is not self.cv:
                for cand in (w, w.get_first_child()):
                    if cand is None:
                        continue
                    cell = self._of_child.get(cand)
                    if cell is None and cand is not w:
                        inner = cand.get_first_child()
                        cell = self._of_child.get(inner) if inner is not None else None
                    if cell is not None:
                        pos = cell.get_position()
                        return pos if 0 <= pos < self.rows.get_n_items() else None
                w = w.get_parent()
            return None

        def _index_at(self, x, y) -> Optional[int]:
            hit = self.cv.pick(x, y, Gtk.PickFlags.DEFAULT)
            return self._pos_of(hit) if hit is not None else None

        def get_path_at_pos(self, x, y):
            i = self._index_at(x, y)
            if i is None:
                return None
            self._cursor = i
            return _tpath(i), None, 0, 0

        def get_dest_row_at_pos(self, x, y):
            i = self._index_at(x, y)
            return (_tpath(i), None) if i is not None else None

        # ---- activation (double click, Enter)
        def connect(self, name, cb, *args):
            if name == "row-activated":
                self._on_activate.append((cb, args))
                return 0
            return self.cv.connect(name, cb, *args)

        def set_activate_on_single_click(self, on):
            self.cv.set_single_click_activate(bool(on))

        def row_activated(self, path, column=None):
            self._activated(path.get_indices()[0])

        def _activated(self, pos: int):
            now = time.monotonic()
            if self._last_act[0] == pos and now - self._last_act[1] < 0.15:
                return                                   # the list's own double click on top of ours
            self._last_act = (pos, now)
            self._cursor = pos

            def run():                                   # not inside the click or key that asked for it: opening
                for cb, args in self._on_activate:       # a folder can rebuild the columns, and GTK hangs when a
                    cb(self, _tpath(pos), None, *args)   # column is removed while one of its cells handles an event
                return False
            GLib.idle_add(run)

        # ---- columns
        def get_columns(self):
            return list(self._columns)

        def set_columns(self, specs, sort_key, sort_desc):
            """specs: [(key, title, width or 0, expand, clickable)]. Replaces every column, unless they are
            the ones already there (nearly every folder change): widths the user set then stay too.
            Columns that exist are replaced a moment later, never inside the caller: GTK hangs when a column
            is removed while one of its cells is handling the click or key that led here."""
            want = (tuple(specs), sort_key, bool(sort_desc))
            if want == self._specs:
                return
            self._specs = want
            if not self._columns:
                self._apply_columns()
            elif self._columns_id is None:
                self._columns_id = GLib.idle_add(self._apply_columns, priority=GLib.PRIORITY_HIGH)

        def _apply_columns(self):
            self._columns_id = None
            specs, sort_key, sort_desc = self._specs
            self._sorting = True
            try:
                for c in self._columns:
                    self.cv.remove_column(c)
                self._columns = []
                marked = None
                for key, title, width, expand, clickable in specs:
                    fac = Gtk.SignalListItemFactory()
                    fac.connect("setup", self._cell_setup, key)
                    fac.connect("bind", self._cell_bind, key)
                    fac.connect("unbind", self._cell_unbind)
                    fac.connect("teardown", self._cell_teardown)
                    col = Gtk.ColumnViewColumn(title=title, factory=fac)
                    col.key = key
                    col.set_resizable(key != "_chk")
                    col.set_expand(bool(expand))
                    if width and not expand:
                        col.set_fixed_width(width)
                    if clickable:
                        col.set_sorter(Gtk.StringSorter.new(None))      # sorts nothing: it makes the header a button
                        if key == sort_key:
                            marked = col
                    self.cv.append_column(col)
                    self._columns.append(col)
                self._sort_key = sort_key if marked is not None else None
                self.cv.sort_by_column(marked, Gtk.SortType.DESCENDING if sort_desc else Gtk.SortType.ASCENDING)
            finally:
                self._sorting = False
            return False

        def _sorter_changed(self, sorter, change):
            """A header was clicked. The folder view sorts (off the main thread) and rebuilds the columns, which
            puts the arrow where it belongs; that must not happen inside the click."""
            if self._sorting:
                return
            col = sorter.get_primary_sort_column()
            key = getattr(col, "key", None) if col is not None else self._sort_key
            if key:
                GLib.idle_add(lambda: (self.fv.win.sort_by(key), False)[1])

        def fit_columns(self):
            for c in self._columns:
                if not c.get_expand() and c.key != "_chk":
                    c.set_fixed_width(-1)

        # ---- cells
        def _cell_setup(self, factory, cell, key):
            child = self.fv._cell_make4(key)
            cell.set_child(child)
            self._of_child[child] = cell

        def _cell_bind(self, factory, cell, key):
            self._cells[cell] = key
            self.fv._cell_fill4(cell, key)

        def _cell_unbind(self, factory, cell):
            self._cells.pop(cell, None)

        def _cell_teardown(self, factory, cell):
            self._cells.pop(cell, None)
            child = cell.get_child()
            if child is not None:
                self._of_child.pop(child, None)

        def cell_of(self, child):
            return self._of_child.get(child)

        def refresh(self):
            """Fill in every visible cell again, once, after whatever is going on (the tree view's queue_draw)."""
            if self._refresh_id is None:
                def run():
                    self._refresh_id = None
                    for cell, key in list(self._cells.items()):
                        self.fv._cell_fill4(cell, key)
                    return False
                self._refresh_id = GLib.idle_add(run)

        def queue_draw(self):
            self.refresh()

        # ---- renaming in place
        def edit_name(self, path, text: str, select_len: int, on_done, retry: bool = True):
            i = path.get_indices()[0]
            for cell, key in self._cells.items():
                if key == "name" and cell.get_position() == i:
                    label = cell.get_child().get_last_child()
                    ok, r = label.compute_bounds(self.cv)
                    if ok:
                        return edit_over4(self.cv, r.get_x(), r.get_y(), r.get_width(), r.get_height(), text, select_len,
                                          on_done, self.selection)
            if retry:                                    # the row is not on screen: bring it there, then once more
                self.scroll_to_cell(path)
                GLib.timeout_add(60, lambda: (self.edit_name(path, text, select_len, on_done, False), False)[1])
            else:
                on_done(None)

        # ---- typing a name jumps to it (the tree view's interactive search)
        def typeahead(self, ch: str):
            now = time.monotonic()
            text = (self._typed[0] if now - self._typed[1] < 1.0 else "") + ch.lower()
            self._typed = (text, now)
            n = self.rows.get_n_items()
            start = (self._cursor or 0) + (1 if len(text) == 1 else 0)
            for k in range(n):
                i = (start + k) % n
                v = self.rows.get_item(i).v
                if isinstance(v, Entry) and v.name.lower().startswith(text):
                    self.set_cursor(_tpath(i))
                    return

