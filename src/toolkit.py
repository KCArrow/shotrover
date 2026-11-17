

# =========================================================================== toolkit compatibility layer
# Small functions the rest of the code calls in place of GTK 3 calls that GTK 4 removed or changed. The
# interface is being ported in stages (docs/internal/GTK4-PORT.md): first every caller moves to these while
# the application still runs on GTK 3, then each function gets its GTK 4 body. Keep them few and small, and
# keep the GTK 3 behaviour exactly what the replaced call did.

def put(box, child, expand: bool = True, fill: bool = True, padding: int = 0):
    """box.pack_start(child, expand, fill, padding). The defaults are PyGObject's (expand and fill on).
    Anything that is not a Gtk.Box (a tree-view column, a header bar…) keeps its own pack_start."""
    if not isinstance(box, Gtk.Box):
        if isinstance(box, Gtk.CellLayout):
            return box.pack_start(child, expand)
        return box.pack_start(child)
    if not GTK4:
        return box.pack_start(child, expand, fill, padding)
    _pack4(box, child, expand, fill, padding, False)


def put_end(box, child, expand: bool = True, fill: bool = True, padding: int = 0):
    """box.pack_end(child, expand, fill, padding): packed from the far end, the first one outermost."""
    if not isinstance(box, Gtk.Box):
        return box.pack_end(child, expand) if isinstance(box, Gtk.CellLayout) else box.pack_end(child)
    if not GTK4:
        return box.pack_end(child, expand, fill, padding)
    _pack4(box, child, expand, fill, padding, True)


def _pack4(box, child, expand, fill, padding, at_end):
    """GTK 4 has only append(): expand and padding become properties of the child, and children packed
    from the end are inserted after the last start child, so the first end child stays outermost. While no
    child expands, the innermost end child is given the spare room and aligned to the end, which is what
    keeps the end group at the far side."""
    # children may have been taken out since the last call (a bar that is rebuilt): forget those
    ends = [c for c in (getattr(box, "_sr_ends", None) or []) if c.get_parent() is box]
    box._sr_ends = ends
    last_start = getattr(box, "_sr_last_start", None)
    if last_start is not None and last_start.get_parent() is not box:
        starts = [c for c in child_widgets(box) if not any(c is e for e in ends)]
        last_start = box._sr_last_start = starts[-1] if starts else None
    pusher = getattr(box, "_sr_pusher", None)
    if pusher is not None and pusher.get_parent() is not box:
        box._sr_pusher = None
    if not child_widgets(box):
        box._sr_expands = False
    horiz = box.get_orientation() == Gtk.Orientation.HORIZONTAL
    set_expand = child.set_hexpand if horiz else child.set_vexpand
    set_align = child.set_halign if horiz else child.set_valign
    if expand:
        set_expand(True)
        if not fill:
            set_align(Gtk.Align.CENTER)
        box._sr_expands = True
    if padding:
        for side in (("start", "end") if horiz else ("top", "bottom")):
            getattr(child, "set_margin_" + side)(getattr(child, "get_margin_" + side)() + padding)
    if not at_end:
        if getattr(box, "_sr_ends", None):
            box.insert_child_after(child, last_start)
        else:
            box.append(child)
        box._sr_last_start = child
    else:
        box.insert_child_after(child, last_start)            # None puts it first: right when nothing starts
        box._sr_ends = (getattr(box, "_sr_ends", None) or []) + [child]
    pusher = getattr(box, "_sr_pusher", None)
    if pusher is not None:                                   # undo the previous stand-in for spare room
        (pusher.set_hexpand if horiz else pusher.set_vexpand)(False)
        (pusher.set_halign if horiz else pusher.set_valign)(Gtk.Align.FILL)
        box._sr_pusher = None
    ends = getattr(box, "_sr_ends", None)
    if ends and not getattr(box, "_sr_expands", False):
        inner = ends[-1]
        (inner.set_hexpand if horiz else inner.set_vexpand)(True)
        (inner.set_halign if horiz else inner.set_valign)(Gtk.Align.END)
        box._sr_pusher = inner


def show_all(widget):
    """widget.show_all(). GTK 4 widgets are visible unless hidden, so there it only has to show the widget."""
    if not GTK4:
        return widget.show_all()
    widget.set_visible(True)


def child_widgets(widget) -> list:
    """widget.get_children(): the direct children, in order."""
    if not GTK4:
        return widget.get_children()
    out, c = [], widget.get_first_child()
    while c is not None:
        out.append(c)
        c = c.get_next_sibling()
    return out


def set_child(container, child):
    """container.add(child) for a container that holds one child: a window, scrolled window, frame, button,
    expander, overlay, event box."""
    if not GTK4:
        return container.add(child)
    if hasattr(container, "set_child"):
        return container.set_child(child)
    container.append(child)                      # event_box() is a plain Gtk.Box there


def take_out(container, child):
    """container.remove(child) for a widget container (box, grid, stack, pane, menu, single-child holder)."""
    if not GTK4:
        return container.remove(child)
    if isinstance(container, Gtk.Paned):
        if container.get_start_child() is child:
            return container.set_start_child(None)
        return container.set_end_child(None)
    if hasattr(container, "remove"):
        return container.remove(child)
    container.set_child(None)


def pane_first(paned, child, resize: bool = False, shrink: bool = True):
    """paned.pack1(child, resize, shrink): the left or top side."""
    if not GTK4:
        return paned.pack1(child, resize, shrink)
    paned.set_start_child(child)
    paned.set_resize_start_child(resize)
    paned.set_shrink_start_child(shrink)


def pane_second(paned, child, resize: bool = True, shrink: bool = True):
    """paned.pack2(child, resize, shrink): the right or bottom side."""
    if not GTK4:
        return paned.pack2(child, resize, shrink)
    paned.set_end_child(child)
    paned.set_resize_end_child(resize)
    paned.set_shrink_end_child(shrink)


def event_box():
    """A holder that exists only so its child can receive mouse events. GTK 4 has no Gtk.EventBox (every
    widget takes input there), so it is a plain box."""
    return Gtk.Box() if GTK4 else Gtk.EventBox()


def on_draw(area, handler):
    """area.connect("draw", handler) for a Gtk.DrawingArea: handler(widget, cr) paints it."""
    if not GTK4:
        return area.connect("draw", handler)
    area.set_draw_func(lambda a, cr, w, h, *_: handler(a, cr))


def on_draw_over(widget, handler, under: bool = False):
    """Extra painting on a widget that also draws itself: rules over a list, an outline round a bar.
    handler(widget, cr) runs after the widget's own drawing, or before it with under=True.
    GTK 4 has no draw signal on ordinary widgets, so nothing extra is painted there yet (cosmetic only)."""
    if not GTK4:
        return widget.connect("draw", handler) if under else widget.connect_after("draw", handler)
    return 0


def start_hidden(widget, on: bool = True):
    """widget.set_no_show_all(on): the widget stays hidden when its window is shown, until code shows it.
    GTK 4 widgets are visible unless hidden, so there the widget is hidden now."""
    if not GTK4:
        return widget.set_no_show_all(on)
    if on:
        widget.set_visible(False)


def css_class(widget, name: str, on: bool = True):
    """Add (or with on=False remove) a CSS class on a widget."""
    if GTK4:
        return widget.add_css_class(name) if on else widget.remove_css_class(name)
    sc = widget.get_style_context()
    return sc.add_class(name) if on else sc.remove_class(name)


def style_fg(style_context, state=None):
    """style_context.get_color(state): the text colour (Gdk.RGBA) for a widget state; NORMAL when not given.
    GTK 4's style context has one colour, for the widget's current state.

    The other style-context calls the code uses (lookup_color, add_class / remove_class on a context held in
    a variable, get_state, Gtk.render_background) still exist in GTK 4.12, where they are deprecated. They
    are left as they are for now; replace them when GTK 3 is dropped."""
    if GTK4:
        return style_context.get_color()
    return style_context.get_color(Gtk.StateFlags.NORMAL if state is None else state)


# Extra rules for GTK 4 only: its menus are popovers of buttons and its menu bar a row of menu buttons (see
# menu4 and menu_bar), and buttons are far taller than GTK 3 menu items unless told otherwise.
CSS_GTK4 = """
.sr-menubar > menubutton > button { min-height: 0; padding: 3px 8px; border-radius: 0; font-weight: normal; }
popover.menu > contents { padding: 4px 0; }
popover.menu button, popover.menu menubutton > button { min-height: 0; padding: 4px 10px; border-radius: 0; font-weight: normal; }
popover.menu checkbutton { min-height: 0; padding: 0; }
/* GTK 3 draws no focus ring round a list; GTK 4 outlined the whole file area and the navigation pane */
treeview:focus-visible, treeview.view:focus-visible, .icongrid:focus-visible { outline: none; }
popover.menu separator { margin: 4px 0; }
/* painted in code under GTK 3 (on_draw_over), which GTK 4 cannot do: the same lines through CSS */
.pathbar { border: 1px solid alpha(@theme_fg_color, 0.16); }
.pathbar:hover, .pathbar:focus-within { border-color: alpha(@theme_fg_color, 0.34); }
.pane-header button { min-height: 0; min-width: 0; padding: 0 2px; }
popover.sr-rename > contents { padding: 0; border-radius: 0; box-shadow: none; border: none; }
popover.sr-rename entry { min-height: 0; border-radius: 0; }
/* the Details list (Gtk.ColumnView): rows as tight as the tree view's were, no outline round the list */
columnview.sr-details > listview > row > cell { padding: 3px 6px; }
columnview.sr-details:focus-visible, columnview.sr-details > listview:focus-visible { outline: none; }
columnview.sr-details > listview > row:focus-visible { outline-offset: -1px; }
columnview.sr-details .sr-group { font-weight: bold; opacity: 0.72; }
"""


def load_app_css(css: bytes):
    """Install the application's stylesheet for every window. Raises GLib.Error if it does not parse."""
    prov = Gtk.CssProvider()
    if GTK4:
        # GTK 4 drops a rule it cannot parse and says nothing unless asked; while the port is in progress, say it
        def bad(provider, section, error):      # do not touch `section`: reading it hangs PyGObject 3.40
            print("shotrover[gtk4]: stylesheet:", error.message, file=sys.stderr)
        prov.connect("parsing-error", bad)
        prov.load_from_data((css.decode() if isinstance(css, bytes) else css) + CSS_GTK4, -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    else:
        prov.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def run_dialog(dialog) -> int:
    """dialog.run(): show a modal dialog, wait for an answer and return the response id. The caller still
    destroys the dialog. GTK 4 has no run(); there a nested main loop waits for the response signal."""
    if not GTK4:
        return dialog.run()
    out = {"r": int(Gtk.ResponseType.DELETE_EVENT)}
    loop = GLib.MainLoop()

    def answered(d, r):
        out["r"] = r
        loop.quit()
    # Gtk.AboutDialog is a plain window in GTK 4: it has no response signal and ends only by being closed
    h1 = dialog.connect("response", answered) if GObject.signal_lookup("response", type(dialog)) else 0
    h2 = dialog.connect("close-request", lambda d: (loop.quit(), False)[1])
    dialog.set_modal(True)
    dialog.present()
    loop.run()
    for h in (h1, h2):
        if h:
            dialog.disconnect(h)
    return out["r"]


# ---- input events
# Handlers keep the GTK 3 form handler(widget, event) and read event.button, .x, .y, .state, .keyval, .type…
# Under GTK 3 on_event is a plain signal connection. Under GTK 4, which has no event signals, it will attach
# the matching controller and hand the handler an object with the same fields.
EV_PRESS = Gdk.EventType.BUTTON_PRESS if not GTK4 else "press"
EV_PRESS2 = Gdk.EventType._2BUTTON_PRESS if not GTK4 else "press2"           # double click
EV_PRESS3 = Gdk.EventType._3BUTTON_PRESS if not GTK4 else "press3"           # triple click


class Ev:
    """GTK 4 only: what a GTK 3 handler reads from its event. Controllers have no event structure, so
    on_event() fills one of these in and passes it instead."""

    def __init__(self, type_=None, **kw):
        self.type = type_
        self.button = 0
        self.x = self.y = self.x_root = self.y_root = 0.0
        self.state = Gdk.ModifierType(0)
        self.keyval = 0
        self.hardware_keycode = 0
        self.time = 0
        self.direction = None
        self.delta_x = self.delta_y = 0.0
        self.string = ""
        self.detail = None                  # crossing events: GTK 4's leave already ignores moves onto a child
        self.__dict__.update(kw)

    def __getattr__(self, name):            # a field no handler was known to read: say so once, answer None
        if name.startswith("__"):
            raise AttributeError(name)
        port_todo("event field ." + name)
        return None

    def triggers_context_menu(self) -> bool:
        return self.button == 3

    def get_scroll_deltas(self):
        return True, self.delta_x, self.delta_y

    def get_state(self):
        return True, self.state


def _ev_from(controller, type_=None, **kw):
    ev = Ev(type_, **kw)
    try:
        ev.state = controller.get_current_event_state()
        ev.time = controller.get_current_event_time()
    except Exception:
        pass
    ev.x_root, ev.y_root = ev.x, ev.y
    return ev


def _ev_xy(widget, x, y):
    """GTK 4 only: pointer coordinates as the GTK 3 handlers expect them. A controller reports them relative
    to the widget; GTK 3 reported a tree view's relative to its rows (below the header, scrolled) and the
    icon canvas's relative to the whole scrolled canvas."""
    if isinstance(widget, Gtk.TreeView):
        return widget.convert_widget_to_bin_window_coords(int(x), int(y))
    if isinstance(widget, ScrollCanvas):
        h, v = widget.hadjustment, widget.vadjustment
        return x + (h.get_value() if h is not None else 0), y + (v.get_value() if v is not None else 0)
    return x, y


def current_modifiers():
    """The modifier keys held right now (Ctrl, Shift…), for code that runs inside a signal with no event."""
    if not GTK4:
        return Gtk.get_current_event_state()[1]
    try:
        return Gdk.Display.get_default().get_default_seat().get_keyboard().get_modifier_state()
    except Exception:
        return Gdk.ModifierType(0)


def _one_group(widget, gesture):
    """GTK 4 only: add a gesture to a widget, in one group with every other gesture we attach to it. Gestures that are not grouped cancel
    each other: a second click handler, or the drag gesture that reports releases, went dead the moment
    another one claimed the press (seen with a real pointer: drag-end arrived at once with 0, 0)."""
    widget.add_controller(gesture)          # first: GTK only groups gestures that are already on the same widget
    first = getattr(widget, "_sr_gesture", None)
    if first is None:
        widget._sr_gesture = gesture
    else:
        gesture.group(first)


def on_event(widget, name: str, handler, *args):
    """widget.connect("<name>-event", handler, *args). A handler returns True to stop the event there.
    GTK 4: attaches the matching controller and calls handler(widget, Ev, *args)."""
    if not GTK4:
        return widget.connect(name, handler, *args)
    if name == "button-release-event":
        # Not Gtk.GestureClick: it gives up as soon as the pointer moves a few pixels, so the release that ends
        # a rubber band never arrived. A drag gesture follows the button until it is let go. It is put in one
        # group with the click gesture, or it would be cancelled the moment a press handler claims the click.
        # While the button is held, a claimed sequence no longer reaches the motion controller either, so the
        # drag gesture also feeds the widget's motion handlers.
        # (The raw-event controller, Gtk.EventControllerLegacy, is no use: PyGObject 3.40 hands it None.)
        g = Gtk.GestureDrag()
        g.set_button(0)

        def where(gesture, dx, dy):
            start = gesture.get_start_point()
            x, y = (start[-2] + dx, start[-1] + dy) if start and start[0] else (dx, dy)
            return _ev_xy(widget, x, y)

        def dragging(gesture, dx, dy):
            ex, ey = where(gesture, dx, dy)
            button = gesture.get_current_button()
            mask = {1: Gdk.ModifierType.BUTTON1_MASK, 2: Gdk.ModifierType.BUTTON2_MASK, 3: Gdk.ModifierType.BUTTON3_MASK}.get(button)
            for mh, margs in getattr(widget, "_sr_motion", ()):
                ev = _ev_from(gesture, None, x=ex, y=ey, button=button)
                if mask is not None:
                    ev.state = ev.state | mask
                mh(widget, ev, *margs)

        def let_go(gesture, dx, dy):
            ex, ey = where(gesture, dx, dy)
            handler(widget, _ev_from(gesture, None, x=ex, y=ey, button=gesture.get_current_button()), *args)
        g.connect("drag-update", dragging)
        g.connect("drag-end", let_go)
        _one_group(widget, g)
    elif name == "button-press-event":
        g = Gtk.GestureClick()
        g.set_button(0)                                     # every button; the handler looks at event.button

        def click(gesture, n_press, x, y):
            def send(type_):
                ex, ey = _ev_xy(widget, x, y)
                ev = _ev_from(gesture, type_, x=ex, y=ey, button=gesture.get_current_button())
                if handler(widget, ev, *args):
                    gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            send(EV_PRESS)                                  # GTK 3 sends the plain press first, then the
            if n_press == 2:                                # double- or triple-click event on top of it
                send(EV_PRESS2)
            elif n_press >= 3:
                send(EV_PRESS3)
        g.connect("pressed", click)
        _one_group(widget, g)
    elif name in ("motion-notify-event", "enter-notify-event", "leave-notify-event"):
        c = Gtk.EventControllerMotion()
        if name == "leave-notify-event":
            c.connect("leave", lambda ctl: handler(widget, _ev_from(ctl), *args))
        else:
            if name == "motion-notify-event":           # also called by the drag gesture, see above
                widget._sr_motion = list(getattr(widget, "_sr_motion", ())) + [(handler, args)]

            def moved(ctl, x, y):
                ex, ey = _ev_xy(widget, x, y)
                return handler(widget, _ev_from(ctl, x=ex, y=ey), *args)
            c.connect("motion" if name == "motion-notify-event" else "enter", moved)
        widget.add_controller(c)
    elif name == "scroll-event":
        c = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)

        def scrolled(ctl, dx, dy):
            d = Gdk.ScrollDirection
            direction = (d.UP if dy < 0 else d.DOWN) if dy else (d.LEFT if dx < 0 else d.RIGHT)
            return bool(handler(widget, _ev_from(ctl, delta_x=dx, delta_y=dy, direction=direction), *args))
        c.connect("scroll", scrolled)
        widget.add_controller(c)
    elif name == "key-press-event":
        c = Gtk.EventControllerKey()
        if isinstance(widget, Gtk.Window):                  # a window's handler ran before the focused widget's
            c.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def pressed(ctl, keyval, keycode, state):
            uni = Gdk.keyval_to_unicode(keyval)
            ev = Ev(keyval=keyval, hardware_keycode=keycode, state=state, string=chr(uni) if uni else "")
            try:
                ev.time = ctl.get_current_event_time()
            except Exception:
                pass
            return bool(handler(widget, ev, *args))
        c.connect("key-pressed", pressed)
        widget.add_controller(c)
    elif name in ("focus-in-event", "focus-out-event"):
        c = Gtk.EventControllerFocus()
        c.connect("enter" if name == "focus-in-event" else "leave", lambda ctl: handler(widget, Ev(), *args))
        widget.add_controller(c)
    elif name == "delete-event":
        return widget.connect("close-request", lambda w: bool(handler(w, None, *args)))
    elif name == "unmap-event":
        return widget.connect("unmap", lambda w: handler(w, None, *args))
    else:
        port_todo("on_event " + name)
    return 0


# ---- small differences in widget construction and properties
_ICON_SIZES = {"menu": "MENU", "button": "BUTTON", "dialog": "DIALOG"}


def icon_image(icon, size: str = "button"):
    """A Gtk.Image for an icon name or a Gio.Icon. size: "menu" and "button" are 16 px, "dialog" is 48 px."""
    by_name = isinstance(icon, str)
    if not GTK4:
        sz = getattr(Gtk.IconSize, _ICON_SIZES[size])
        return Gtk.Image.new_from_icon_name(icon, sz) if by_name else Gtk.Image.new_from_gicon(icon, sz)
    img = Gtk.Image.new_from_icon_name(icon) if by_name else Gtk.Image.new_from_gicon(icon)
    if size == "dialog":
        img.set_pixel_size(48)
    return img


def icon_button(icon_name: str, size: str = "button"):
    """A button showing only an icon."""
    if not GTK4:
        return Gtk.Button.new_from_icon_name(icon_name, getattr(Gtk.IconSize, _ICON_SIZES[size]))
    return Gtk.Button.new_from_icon_name(icon_name)


def button_image(button, image):
    """button.set_image(image): replace the picture on an icon-only button."""
    if not GTK4:
        return button.set_image(image)
    button.set_child(image)


def flat_button(button):
    """button.set_relief(Gtk.ReliefStyle.NONE): no frame until the pointer is over it."""
    if not GTK4:
        return button.set_relief(Gtk.ReliefStyle.NONE)
    button.set_has_frame(False)


def set_margins(widget, n: int):
    """container.set_border_width(n): n pixels of space round the contents."""
    if not GTK4:
        return widget.set_border_width(n)
    for side in ("top", "bottom", "start", "end"):
        getattr(widget, "set_margin_" + side)(n)


def label_wrap(label, on: bool = True):
    """label.set_line_wrap(on)."""
    return label.set_wrap(on) if GTK4 else label.set_line_wrap(on)


def label_wrap_mode(label, mode):
    """label.set_line_wrap_mode(mode)."""
    return label.set_wrap_mode(mode) if GTK4 else label.set_line_wrap_mode(mode)


def set_frame(widget, on: bool):
    """set_shadow_type(IN or NONE) on a scrolled window or frame: a thin frame round it, or none."""
    if not GTK4:
        return widget.set_shadow_type(Gtk.ShadowType.IN if on else Gtk.ShadowType.NONE)
    if hasattr(widget, "set_has_frame"):
        widget.set_has_frame(on)


def toplevel(widget):
    """widget.get_toplevel(): the window a widget is in."""
    return widget.get_root() if GTK4 else widget.get_toplevel()


def dialog_secondary(dialog, text: str):
    """message_dialog.format_secondary_text(text): the smaller text under the heading."""
    dialog.props.secondary_use_markup = False
    dialog.props.secondary_text = text


def center_on_parent(window):
    """window.set_position(CENTER_ON_PARENT). GTK 4 leaves placement to the window manager."""
    if not GTK4:
        window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)


class _NoMask:
    def __getattr__(self, name):
        return 0


EVMASK = _NoMask() if GTK4 else Gdk.EventMask      # GTK 4 widgets receive every event; there are no masks


def add_event_mask(widget, mask):
    """widget.add_events(mask). Nothing to do under GTK 4."""
    if not GTK4:
        widget.add_events(mask)


def with_margins(widget, n: int, inner: bool = False):
    """Give a new widget n pixels of space on every side and return it. Stands in for the constructor
    properties margin=n (space outside the widget) and, with inner=True, border_width=n (space inside a
    container); GTK 4 has neither property, and there both become the four margins."""
    if not GTK4 and inner:
        widget.set_border_width(n)
    else:
        for side in ("top", "bottom", "start", "end"):
            getattr(widget, "set_margin_" + side)(n)
    return widget


# ---- bookkeeping for the port
_TODO_SEEN: set = set()


def port_todo(what: str):
    """Mark a place that does nothing under GTK 4 yet. Each one is printed once, so a GTK 4 run lists what is
    still missing. Never called under GTK 3."""
    if what not in _TODO_SEEN:
        _TODO_SEEN.add(what)
        print("shotrover[gtk4]: not ported yet:", what, file=sys.stderr)


def on_resize(widget, handler):
    """Call handler() whenever the widget gets a new size (GTK 3: size-allocate)."""
    if not GTK4:
        return widget.connect("size-allocate", lambda w, a: handler())
    if isinstance(widget, Gtk.DrawingArea):
        return widget.connect("resize", lambda w, width, height: handler())
    if isinstance(widget, Gtk.Window):
        widget.connect("map", lambda w: GLib.idle_add(lambda: (handler(), False)[1]))      # its first real size
        widget.connect("notify::default-width", lambda *a: handler())
        return widget.connect("notify::default-height", lambda *a: handler())
    if isinstance(widget, Gtk.Paned):                   # its furthest divider position changes with its size
        return widget.connect("notify::max-position", lambda *a: handler())
    port_todo("on_resize for " + type(widget).__name__)
    return widget.connect("map", lambda w: GLib.idle_add(lambda: (handler(), False)[1]))


# ---- a scrollable canvas that draws only what is visible (the icon layouts)
if GTK4:
    class ScrollCanvas(Gtk.DrawingArea, Gtk.Scrollable):
        """What IconGrid used Gtk.Layout for: a canvas far larger than the widget, scrolled by the adjustments
        of the Gtk.ScrolledWindow it sits in. The subclass draws in canvas coordinates after translating by
        the adjustment values, exactly as it did with Gtk.Layout."""
        hadjustment = GObject.Property(type=Gtk.Adjustment)
        vadjustment = GObject.Property(type=Gtk.Adjustment)
        hscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
        vscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)

        def __init__(self):
            super().__init__()
            self._sr_canvas = (1, 1)
            self._sr_watch: dict = {}
            self.set_hexpand(True)
            self.set_vexpand(True)
            self.connect("notify::vadjustment", lambda *a: self._sr_adopt("v"))
            self.connect("notify::hadjustment", lambda *a: self._sr_adopt("h"))
            self.connect("resize", lambda *a: self._sr_sync())

        def _sr_adopt(self, which: str):
            adj = self.vadjustment if which == "v" else self.hadjustment
            old = self._sr_watch.pop(which, None)
            if old is not None:
                old[0].disconnect(old[1])
            if adj is not None:
                self._sr_watch[which] = (adj, adj.connect("value-changed", lambda a: self.queue_draw()))
            self._sr_sync()

        def _sr_sync(self):
            for adj, total, page in ((self.vadjustment, self._sr_canvas[1], self.get_height()),
                                     (self.hadjustment, self._sr_canvas[0], self.get_width())):
                if adj is None:
                    continue
                upper = max(total, page)
                adj.configure(max(0, min(adj.get_value(), upper - page)), 0, upper, max(1, page * 0.1), max(1, page * 0.9), page)

        def set_size(self, width: int, height: int):
            """The size of the whole canvas, as Gtk.Layout.set_size."""
            self._sr_canvas = (int(width), int(height))
            self._sr_sync()
else:
    ScrollCanvas = Gtk.Layout


def theme_icon_pixbuf(icon, size: int):
    """The desktop icon theme's picture for a Gio.Icon at size px (GdkPixbuf), or the generic file icon when
    the theme has none, or None when even that is missing. icon may be None."""
    if not GTK4:
        theme = Gtk.IconTheme.get_default()
        try:
            info = theme.lookup_by_gicon(icon, size, Gtk.IconLookupFlags.FORCE_SIZE) if icon else None
            if info is None:
                info = theme.lookup_icon("text-x-generic", size, Gtk.IconLookupFlags.FORCE_SIZE)
            pb = info.load_icon() if info else None
        except GLib.Error:
            pb = None
        if pb is None:
            try:
                pb = theme.load_icon("text-x-generic", size, Gtk.IconLookupFlags.FORCE_SIZE)
            except GLib.Error:
                pb = None
        return pb
    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    for candidate in (icon, Gio.ThemedIcon.new("text-x-generic")):
        if candidate is None:
            continue
        try:
            paintable = theme.lookup_by_gicon(candidate, size, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags(0))
            f = paintable.get_file() if paintable is not None else None
            path = f.get_path() if f is not None else None
            if path:
                return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        except (GLib.Error, TypeError):
            pass
    return None


# ---- dragging files
def _uri_targets():
    return [Gtk.TargetEntry.new("text/uri-list", 0, 0)]


class _Sel4:
    """GTK 4 only: stands in for the Gtk.SelectionData the GTK 3 drag handlers read and fill."""

    def __init__(self, uris=None):
        self.uris = list(uris or [])

    def set_uris(self, uris):
        self.uris = list(uris or [])
        return True

    def get_uris(self):
        return self.uris


def read_files4(clipboard, done):
    """GTK 4 only: ask the clipboard for files without blocking, then call done(paths) (an empty list when
    it holds none).

    Do NOT read the clipboard or a drop as a stream (read_async / read_finish) from Python for a format
    that may be missing: with PyGObject 3.40 the finish call then corrupts memory and the process aborts
    with "free(): invalid pointer". Asking for a Gdk.FileList value is safe on both paths. The one stream
    read there is, read_cut_files4, checks that the format is on offer first."""
    def got(clip, res):
        try:
            files = clip.read_value_finish(res).get_files()
            paths = [p for p in (f.get_path() for f in files) if p]
        except Exception:
            paths = []
        done(paths)
    try:
        clipboard.read_value_async(Gdk.FileList, GLib.PRIORITY_DEFAULT, None, got)
    except Exception:
        done([])


def read_cut_files4(clipboard, done):
    """GTK 4 only: files on the clipboard with whether they were cut or copied; calls done(mode, paths) with
    mode "cut", "copy" or "" (no files).

    Cut or copy is the first line of x-special/gnome-copied-files, which can only be read as a stream. That
    is the read read_files4 warns about, so it is done ONLY when the clipboard lists that format (asking for
    the list reads nothing): with the format present the read is sound, tested 30 times in a row against a
    GTK 3 owner. Anything else, and any failure, falls back to the plain file list, as a copy."""
    mime = "x-special/gnome-copied-files"

    def plain():
        read_files4(clipboard, lambda paths: done("copy" if paths else "", paths))

    def got_bytes(stream, res):
        try:
            raw = stream.read_bytes_finish(res).get_data() or b""
            stream.close(None)
            lines = bytes(raw).decode("utf-8", "replace").split("\n")
            paths = [p for p in (Gio.File.new_for_uri(u.strip()).get_path() for u in lines[1:] if u.strip()) if p]
        except Exception:
            paths = []
        if not paths:
            return plain()
        done("cut" if lines[0].strip() == "cut" else "copy", paths)

    def got(clip, res):
        try:
            stream = clip.read_finish(res)[0]
            stream.read_bytes_async(1 << 20, GLib.PRIORITY_DEFAULT, None, got_bytes)
        except Exception:
            plain()
    try:
        if not clipboard.get_formats().contain_mime_type(mime):
            return plain()
        clipboard.read_async([mime], GLib.PRIORITY_DEFAULT, None, got)
    except Exception:
        plain()


def file_drag_source(widget, on_get):
    """Let the user drag the selected files out of a list. on_get(widget, context, selection_data, info, time)
    fills in the file URIs, as GTK 3's drag-data-get."""
    if not GTK4:
        widget.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, _uri_targets(),
                                        Gdk.DragAction.COPY | Gdk.DragAction.MOVE | Gdk.DragAction.ASK)
        return widget.connect("drag-data-get", on_get)
    src = Gtk.DragSource()
    src.set_actions(Gdk.DragAction.COPY | Gdk.DragAction.MOVE)

    def prepare(source, x, y):
        # only a drag that starts on a selected item moves files; anywhere else it is a rubber band or nothing
        ex, ey = _ev_xy(widget, x, y)
        if isinstance(widget, Gtk.TreeView):
            hit = widget.get_path_at_pos(int(ex), int(ey))
            if not hit or not widget.get_selection().path_is_selected(hit[0]):
                return None
        elif hasattr(widget, "_index_at"):
            if widget._index_at(ex, ey) not in widget.selected:
                return None
        if hasattr(widget, "_reset_press"):
            widget._reset_press()               # the grid's own press tracking ends where the drag starts
        sel = _Sel4()
        on_get(widget, None, sel, 0, 0)
        if not sel.uris:
            return None
        body = ("\r\n".join(sel.uris) + "\r\n").encode("utf-8")
        return Gdk.ContentProvider.new_for_bytes("text/uri-list", GLib.Bytes.new(body))
    src.connect("prepare", prepare)
    _one_group(widget, src)


def file_drop_target(widget, on_received, *args):
    """Let files be dropped on a widget. on_received(widget, context, x, y, selection_data, info, time, *args),
    as GTK 3's drag-data-received; x and y are relative to the widget."""
    if not GTK4:
        widget.drag_dest_set(Gtk.DestDefaults.ALL, _uri_targets(), Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        return widget.connect("drag-data-received", on_received, *args)
    target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)

    def dropped(tgt, value, x, y):                      # GTK turns a dropped text/uri-list into a file list
        try:
            uris = [f.get_uri() for f in value.get_files()]
        except Exception:
            uris = []
        if uris:
            on_received(widget, None, int(x), int(y), _Sel4(uris), 0, 0, *args)
        return bool(uris)
    target.connect("drop", dropped)
    widget.add_controller(target)


def drag_finish(context, ok: bool, time_):
    """Gtk.drag_finish(context, ok, False, time). GTK 4 finishes the drop in file_drop_target itself."""
    if not GTK4:
        Gtk.drag_finish(context, ok, False, time_)


# ---- keyboard shortcuts
def accel_parse(accel: str):
    """(keyval, modifiers) for an accelerator string such as "<Control>l"; (0, 0) when it does not parse."""
    r = Gtk.accelerator_parse(accel or "")
    if GTK4:                                    # GTK 4 returns (parsed, keyval, modifiers)
        return (r[1], r[2]) if r[0] else (0, Gdk.ModifierType(0))
    return r


class Shortcuts:
    """The window's keyboard shortcuts: bind(accel, callback) and unbind(handle).
    GTK 3: an accelerator group. GTK 4: a shortcut controller on the window."""

    def __init__(self, window):
        if GTK4:
            self.ctl = Gtk.ShortcutController()
            self.ctl.set_scope(Gtk.ShortcutScope.GLOBAL)
            window.add_controller(self.ctl)
        else:
            self.group = Gtk.AccelGroup()
            window.add_accel_group(self.group)

    def bind(self, accel: str, callback):
        """Run callback() when the accelerator is pressed. Returns a handle for unbind, or None."""
        key, mods = accel_parse(accel)
        if not key:
            return None
        if GTK4:
            sc = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string(accel),
                                  Gtk.CallbackAction.new(lambda widget, args: (callback(), True)[1]))
            self.ctl.add_shortcut(sc)
            return sc
        self.group.connect(key, mods, Gtk.AccelFlags.VISIBLE, lambda g, o, k, m: (callback(), True)[1])
        return (key, int(mods))

    def unbind(self, handle):
        if handle is None:
            return
        if GTK4:
            self.ctl.remove_shortcut(handle)
        else:
            self.group.disconnect_key(handle[0], Gdk.ModifierType(handle[1]))


# ---- menus
# Menus are described by specs (see build_menu in mainwindow.py): "-" for a separator, (label, callback, accel) tuples,
# or dicts with label / cb / accel / check / radio / sensitive / sub. GTK 3 builds Gtk.Menu from them.
# GTK 4 has no Gtk.Menu; there a menu is a popover holding a column of flat buttons.
def _close_menus(pop):
    while pop is not None:
        pop.popdown()
        parent = pop.get_parent()
        pop = parent.get_ancestor(Gtk.Popover) if parent is not None else None


def menu4(spec):
    """GTK 4 only: a popover menu for a spec."""
    pop = Gtk.Popover()
    pop.set_has_arrow(False)
    pop.add_css_class("menu")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    pop.set_child(box)
    for s in spec:
        if s == "-":
            box.append(Gtk.Separator())
            continue
        if isinstance(s, tuple):
            s = {"label": s[0], "cb": s[1] if len(s) > 1 else None, "accel": s[2] if len(s) > 2 else ""}
        label, cb, radio = s["label"], s.get("cb"), s.get("radio")
        if label == "-":
            box.append(Gtk.Separator())
            continue
        if "sub" in s:
            b = Gtk.MenuButton()
            b.set_direction(Gtk.ArrowType.RIGHT)
            b.set_has_frame(False)
            row = Gtk.Box(spacing=24)                # our own child: the label at the left, like the items
            text = Gtk.Label.new_with_mnemonic(label)
            text.set_xalign(0)
            text.set_hexpand(True)
            row.append(text)
            row.append(Gtk.Image.new_from_icon_name("pan-end-symbolic"))
            b.set_child(row)
            b.set_popover(menu4(s["sub"]))
        elif radio is not None or s.get("check") is not None:
            # a flat button like the plain items, with a box (or, in a radio group, a round mark) in front
            # that only shows the state; the item's shortcut is listed at the right like everywhere else
            b = Gtk.Button()
            b.set_has_frame(False)
            row = Gtk.Box(spacing=8)
            mark = Gtk.CheckButton()
            mark.set_can_target(False)
            mark.set_focusable(False)
            if radio is not None:
                pair = Gtk.CheckButton()                 # a second button in the group makes GTK draw it round
                mark.set_group(pair)
                mark._sr_pair = pair
                radio.append(mark)
            mark.set_active(bool(s.get("check")))
            row.append(mark)
            text = Gtk.Label.new_with_mnemonic(label)
            text.set_xalign(0)
            text.set_hexpand(True)
            text.set_mnemonic_widget(b)
            row.append(text)
            if s.get("accel"):
                key = Gtk.Label(label=shortcut_label(s["accel"]))
                key.add_css_class("dim-label")
                key.set_margin_start(16)
                row.append(key)
            b.set_child(row)
            if cb is not None:              # a radio item reports only when it becomes the chosen one
                b.connect("clicked", lambda w, cb=cb, mark=mark, is_radio=radio is not None:
                          None if (is_radio and mark.get_active()) else (_close_menus(pop), cb()))
        else:
            b = Gtk.Button()
            b.set_has_frame(False)
            row = Gtk.Box(spacing=24)
            text = Gtk.Label.new_with_mnemonic(label)
            text.set_xalign(0)
            text.set_hexpand(True)
            text.set_mnemonic_widget(b)
            row.append(text)
            if s.get("accel"):
                key = Gtk.Label(label=shortcut_label(s["accel"]))
                key.add_css_class("dim-label")
                row.append(key)
            b.set_child(row)
            if cb is not None:
                b.connect("clicked", lambda w, cb=cb: (_close_menus(pop), cb()))
        b.set_sensitive(s.get("sensitive", True))
        box.append(b)
    return pop


def popup_menu(menu, widget, event=None, where: str = "pointer"):
    """Show a menu made by build_menu() for a widget: at the pointer (pass the button event), "under" the
    widget's left edge, or at its "center"."""
    if not GTK4:
        menu.attach_to_widget(widget, None)
        if where == "pointer" and event is not None:
            return menu.popup_at_pointer(event)
        if where == "under":
            return menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)
        return menu.popup_at_widget(widget, Gdk.Gravity.CENTER, Gdk.Gravity.NORTH_WEST, None)
    # A popover has to be the child of the widget it points at. The previous menu is let go only now, when the
    # next one opens: unparenting one from its own "closed" signal crashed GTK now and then (a segfault inside
    # the main loop, seen with real clicks on a test display).
    old = getattr(widget, "_sr_menu", None)
    if old is not None and old is not menu and old.get_parent() is widget:
        old.unparent()
    if not hasattr(widget, "_sr_menu"):
        widget.connect("unrealize", lambda w: (w._sr_menu.unparent() if getattr(w, "_sr_menu", None) is not None
                                               and w._sr_menu.get_parent() is w else None, setattr(w, "_sr_menu", None))[1])
    widget._sr_menu = menu
    if menu.get_parent() is not widget:
        if menu.get_parent() is not None:
            menu.unparent()
        menu.set_parent(widget)
    if where == "pointer" and event is not None:
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(event.x), int(event.y), 1, 1
        menu.set_pointing_to(rect)
    elif where == "under":
        menu.set_position(Gtk.PositionType.BOTTOM)
        menu.set_halign(Gtk.Align.START)
    else:                                   # "center", or a pointer menu asked for from the keyboard
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = widget.get_width() // 2, widget.get_height() // 3, 1, 1
        menu.set_pointing_to(rect)
    menu.popup()


def menu_bar():
    """The row of menus at the top of a window (GTK 3: Gtk.MenuBar; GTK 4: a row of menu buttons)."""
    if not GTK4:
        return Gtk.MenuBar()
    bar = Gtk.Box()
    bar.add_css_class("sr-menubar")
    return bar


def menu_bar_add4(bar, title: str, spec_fn):
    """GTK 4 only: add a menu to the bar. spec_fn() is asked for the spec each time the menu opens."""
    b = Gtk.MenuButton()
    b.set_child(Gtk.Label.new_with_mnemonic(title))      # a child of our own: set_label() would add an arrow
    b.set_has_frame(False)
    b.set_create_popup_func(lambda button: button.set_popover(menu4(spec_fn())))
    bar.append(b)


def info_bar_content(bar, widget):
    """Put a widget in an info bar's content area, taking the spare width."""
    if not GTK4:
        return bar.get_content_area().pack_start(widget, True, True, 0)
    widget.set_hexpand(True)
    bar.add_child(widget)


def see_through(area):
    """Make a drawing area that is laid over other widgets ignore the mouse and keyboard, so input reaches
    what is underneath."""
    area.set_can_focus(False)
    if GTK4:
        area.set_can_target(False)
    else:
        area.set_has_window(False)              # no GdkWindow of its own, so it can never intercept input
        area.set_app_paintable(True)


def move_child(box, child, position: int):
    """box.reorder_child(child, position): move a child to the given place among its siblings."""
    if not GTK4:
        return box.reorder_child(child, position)
    others = [c for c in child_widgets(box) if c is not child]
    box.reorder_child_after(child, others[position - 1] if position > 0 and others else None)


def takes_keys(widget):
    """Let a custom widget hold the keyboard focus. GTK 3: can-focus. GTK 4 renamed that property to
    "focusable" and kept the name can-focus for something else (may focus pass into this widget at all,
    true by default), so set_can_focus(True) there changes nothing and the widget never receives a key."""
    if GTK4:
        widget.set_focusable(True)
    else:
        widget.set_can_focus(True)


def on_menu_key(widget, callback):
    """Run callback() when the keyboard asks for the widget's context menu (the Menu key, Shift+F10)."""
    if not GTK4:
        return widget.connect("popup-menu", lambda w: callback() or True)
    ctl = Gtk.ShortcutController()
    ctl.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Menu|<Shift>F10"),
                                      Gtk.CallbackAction.new(lambda w, a: (callback(), True)[1])))
    widget.add_controller(ctl)


# ---- list rows as tall as under GTK 3
# GTK 3 put 2 px between the rows of every tree view (its "vertical-separator" style property); GTK 4 has no
# such thing, so every list came out tighter. Each cell gets 1 px more above and below instead, once: columns
# are rebuilt with the same renderers when the layout changes.
if GTK4:
    _append_column3 = Gtk.TreeView.append_column

    def _append_column4(tree, column):
        for cell in column.get_cells():
            if not getattr(cell, "_sr_padded", False):
                xpad, ypad = cell.get_padding()
                cell.set_padding(xpad, ypad + 1)
                cell._sr_padded = True
        return _append_column3(tree, column)
    Gtk.TreeView.append_column = _append_column4


# ---- PyGObject older than 3.42 with GTK 4 (RHEL 9 ships 3.40)
# Its Python overrides for list and tree stores still call insert_with_valuesv, which GTK 4 exposes as
# insert_with_values. Without this, every store.append(row) raises AttributeError.
if GTK4:
    for _store in (Gtk.ListStore, Gtk.TreeStore):
        if not hasattr(_store, "insert_with_valuesv") and hasattr(_store, "insert_with_values"):
            _store.insert_with_valuesv = _store.insert_with_values


def radio_button(group, label: Optional[str] = None):
    """A radio button in the same group as `group` (another radio button, or None to start a group).
    Without a label the caller gives it a child. GTK 4 has no Gtk.RadioButton: check buttons are grouped."""
    if not GTK4:
        if label is None:
            return Gtk.RadioButton.new_from_widget(group)
        return Gtk.RadioButton.new_with_label_from_widget(group, label)
    b = Gtk.CheckButton(label=label) if label is not None else Gtk.CheckButton()
    if group is not None:
        b.set_group(group)
    return b


def window_size(window):
    """(width, height) of a window, as Gtk.Window.get_size()."""
    if not GTK4:
        return tuple(window.get_size())
    return window.get_width(), window.get_height()


def resize_window(window, width: int, height: int):
    """window.resize(width, height)."""
    if not GTK4:
        return window.resize(width, height)
    window.set_default_size(width, height)


def about_logo(dialog, pixbuf):
    """Set an about dialog's logo from a pixbuf."""
    if not GTK4:
        return dialog.set_logo(pixbuf)
    dialog.set_logo(Gdk.Texture.new_for_pixbuf(pixbuf))


def pixbuf_surface(pixbuf):
    """A cairo surface holding a pixbuf's picture, for drawing it many times without converting it again."""
    if not GTK4:
        return Gdk.cairo_surface_create_from_pixbuf(pixbuf, 1, None)
    import cairo
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, pixbuf.get_width(), pixbuf.get_height())
    cr = cairo.Context(surf)
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
    cr.paint()
    return surf


def image_set_pixbuf(image, pixbuf):
    """image.set_from_pixbuf(pixbuf), shown at the pixbuf's own size. (A GTK 4 Gtk.Image draws every picture
    at icon size, 16 px, unless told otherwise.) Also accepts Shotrover's FitImage."""
    image.set_from_pixbuf(pixbuf)
    if GTK4 and pixbuf is not None and isinstance(image, Gtk.Image):
        image.set_pixel_size(max(pixbuf.get_width(), pixbuf.get_height()))


def image_from_pixbuf(pixbuf):
    """Gtk.Image.new_from_pixbuf(pixbuf), shown at the pixbuf's own size."""
    img = Gtk.Image()
    image_set_pixbuf(img, pixbuf)
    return img


def clip_wide(child):
    """A holder for a row that may be wider than the room it gets (the breadcrumbs of a deep path).
    GTK 3 lets such a row be cut off. GTK 4 would instead make the whole window as wide as the row, so there
    the row sits in a scroller without scroll bars, which clips it."""
    if not GTK4:
        return child
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
    sw.set_propagate_natural_height(True)
    sw.set_hexpand(True)                    # or it is given its minimum width, which is nothing
    sw.set_child(child)
    adj = sw.get_hadjustment()              # keep the END in view: the folder you are in matters most
    adj.connect("changed", lambda a: a.set_value(max(0, a.get_upper() - a.get_page_size())))
    return sw


def edit_cell4(tree, path, column, renderer, text: str, select_len: int, on_done):
    """GTK 4 only: edit one cell of a tree view in place, then call on_done(new_text) (not called when the
    edit is cancelled).

    GTK 4.12 puts its own cell editor one row too high when the list has headers (seen in a ten-line test
    program, so it is GTK's bug, not ours). This shows an entry in a borderless popover laid exactly over the
    cell instead."""
    area = tree.get_cell_area(path, column)
    pos = column.cell_get_position(renderer)
    xoff, width = (pos[0], pos[1]) if pos else (0, area.width)
    x, y = tree.convert_bin_window_to_widget_coords(area.x + xoff, area.y)
    edit_over4(tree, x, y, width, area.height, text, select_len, on_done, tree.get_selection())


def edit_over4(parent, x, y, width, height, text: str, select_len: int, on_done, selection):
    """GTK 4 only: an entry in a borderless popover laid over the rectangle (x, y, width, height) of `parent`;
    on_done(new_text) when Enter is pressed, on_done(None) when the edit is cancelled or `selection` changes."""
    old = getattr(parent, "_sr_edit_pop", None)
    if old is not None and old.get_parent() is parent:
        old.unparent()
    pop = Gtk.Popover()
    parent._sr_edit_pop = pop
    pop.set_has_arrow(False)
    pop.add_css_class("sr-rename")
    pop.set_parent(parent)
    rect = Gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = int(x), int(y), max(1, int(width)), int(height)
    pop.set_pointing_to(rect)
    pop.set_position(Gtk.PositionType.BOTTOM)
    pop.set_halign(Gtk.Align.START)
    pop.set_offset(0, -int(height))                      # down from the cell's bottom edge, so back up over it
    entry = Gtk.Entry()
    entry.set_text(text)
    entry.set_size_request(max(160, int(width)), int(height))
    pop.set_child(entry)
    state = {"done": False}

    def finish(ok):
        if state["done"]:
            return
        state["done"] = True
        new = entry.get_text()
        pop.popdown()
        on_done(new if ok else None)
    entry.connect("activate", lambda e: finish(True))
    pop.connect("closed", lambda p: finish(False))
    # GTK 3's editor ends when the selection moves on (navigation, a reload, another click); so does this one
    watch = selection.connect("changed", lambda *a: finish(False))
    pop.connect("closed", lambda p: selection.disconnect(watch) if selection.handler_is_connected(watch) else None)
    pop.popup()
    entry.grab_focus()
    GLib.idle_add(lambda: (entry.select_region(0, select_len), False)[1])


_TEXTURES4: dict = {}


def texture4(pixbuf):
    """GTK 4 only: the pixbuf as a texture for a Gtk.Image, made once per pixbuf (the icon cache hands out the
    same pixbuf for the same icon, so a list of a thousand rows needs a few dozen)."""
    hit = _TEXTURES4.get(id(pixbuf))
    if hit is None or hit[0] is not pixbuf:
        if len(_TEXTURES4) > 6000:
            _TEXTURES4.clear()
        hit = _TEXTURES4[id(pixbuf)] = (pixbuf, Gdk.Texture.new_for_pixbuf(pixbuf))      # keeps the pixbuf, so its id stays its own
    return hit[1]


def fixed_width(widget):
    """Stop a widget from taking spare width although something inside it would like to. Under GTK 4 a
    child that expands makes every parent expand too (a tab label made its tab fill the tab bar)."""
    if GTK4:
        widget.set_hexpand(False)
    return widget
