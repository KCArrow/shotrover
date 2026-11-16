
# --------------------------------------------------------------------------- error report dialog
class ReportDialog(Gtk.Dialog):
    """Shows a report (editable, so the user can remove anything private) and opens it as a pre-filled
    GitHub issue. Nothing leaves the machine unless the user presses that button."""
    COPY, ISSUE, DISMISS = 1, 2, 4

    def __init__(self, parent, path: str):
        super().__init__(title="Error report", transient_for=parent, modal=True)
        self.path = path
        self.set_default_size(760, 560)
        box = self.get_content_area()
        box.set_spacing(8)
        set_margins(box, 12)
        head = Gtk.Label(xalign=0)
        head.set_markup(f"<b>{GLib.markup_escape_text(CRASH.summary_of(path))}</b>")
        label_wrap(head, True)
        put(box, head, False, False, 0)
        sub = Gtk.Label(xalign=0, label="Review before reporting. Your home folder and user name are already replaced; "
                                        "edit out anything else you'd rather not share. Reporting opens a pre-filled "
                                        "issue on GitHub (a free GitHub account is needed).")
        label_wrap(sub, True)
        css_class(sub, "dim-label")
        put(box, sub, False, False, 0)
        try:
            with open(path) as f:
                text = f.read()
        except OSError as ex:
            text = f"(report unreadable: {ex})"
        self.buf = Gtk.TextBuffer()
        self.buf.set_text(text)
        tv = Gtk.TextView(buffer=self.buf, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        tv.set_left_margin(6)
        tv.set_right_margin(6)
        sw = Gtk.ScrolledWindow()
        set_frame(sw, True)
        set_child(sw, tv)
        put(box, sw, True, True, 0)
        self.note = Gtk.Label(xalign=0)
        label_wrap(self.note, True)
        put(box, self.note, False, False, 0)
        self.add_button("Don't send", self.DISMISS)
        self.add_button("Copy", self.COPY)
        b = self.add_button("Report on GitHub…", self.ISSUE)
        css_class(b, "suggested-action")
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        show_all(self)

    def text(self) -> str:
        return self.buf.get_text(self.buf.get_start_iter(), self.buf.get_end_iter(), False)

    def _save(self):
        try:
            with open(self.path, "w") as f:
                f.write(self.text())
        except OSError:
            pass

    def run_report(self):
        while True:
            r = run_dialog(self)
            if r == self.COPY:
                set_clipboard_text(self.text())
                self.note.set_text("Copied.")
                continue
            if r == self.ISSUE:
                self._save()
                err = CRASH.github_issue(self.path, self.text())
                if err:
                    self.note.set_text(err)
                    continue
                CRASH.archive(self.path, "sent")
                break
            if r == self.DISMISS:
                CRASH.archive(self.path, "dismissed")
            else:
                self._save()               # Close: keep it pending (offered again at the next start)
            break
        self.destroy()


def open_report(parent, path: Optional[str] = None):
    """Show the report at `path`, or build a fresh manual one (Help → Report a problem; built in a thread
    because listing the optional tools runs a few quick subprocesses)."""
    if path is not None:
        ReportDialog(parent, path).run_report()
        return

    def work():
        p = CRASH.manual_report()
        GLib.idle_add(lambda: (ReportDialog(parent, p).run_report(), False)[1])
    bg(work)
