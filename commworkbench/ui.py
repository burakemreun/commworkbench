import json
import logging
import os
import queue
import tempfile
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from commworkbench.config_loader import CONFIGS_DIR
from commworkbench.constants import UI_POLL_INTERVAL_MS

log = logging.getLogger(__name__)

# error-label key for the raw send row; not a message name, so it never collides
RAW_KEY = "__raw__"


class _Tooltip:
    """Hover text for a widget - tkinter ships no tooltip of its own."""

    def __init__(self, widget, text_fn):
        self._widget = widget
        self._text_fn = text_fn
        self._win = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None):
        text = self._text_fn()
        if not text or self._win is not None:
            return
        self._win = tk.Toplevel(self._widget)
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(
            f"+{self._widget.winfo_rootx() + 12}"
            f"+{self._widget.winfo_rooty() + self._widget.winfo_height() + 4}"
        )
        tk.Label(
            self._win, text=text, justify="left", bg="#ffffe0",
            relief="solid", bd=1, padx=5, pady=3,
        ).pack()

    def _hide(self, _event=None):
        if self._win is not None:
            self._win.destroy()
            self._win = None


def _save_json_atomic(path, data: dict, what: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except OSError as e:
        log.error("failed to save %s: %s", what, e)


def _fmt_value(val) -> str:
    if isinstance(val, (bytes, bytearray)):
        return val.hex(" ")
    return str(val)


class CommWorkbenchUI:
    def __init__(
        self,
        configs: dict[str, dict],
        project_name: str = "_current",
        protocol_config: dict | None = None,
        frame_queue: queue.Queue | None = None,
        parser=None,
        connection_manager=None,
        close_callback=None,
        traffic_logger=None,
    ):
        self.ui_cfg = configs.get("ui.json", {})
        self._cfg_path = CONFIGS_DIR / project_name / "ui.json"
        self._ratios: dict[str, float] = dict(self.ui_cfg.get("panes", {"main_display": 0.5}))
        self._max_log_entries = self.ui_cfg.get("max_log_entries", 1000)

        self._conn_cfg = configs.get("connection.json", {})
        self._conn_path = CONFIGS_DIR / project_name / "connection.json"
        self._conn_requested = connection_manager is not None
        self._port_info: dict[str, str] = {}

        self._protocol_config = protocol_config or {}
        self._protocol_codec = None
        self._queue = frame_queue
        self._parser = parser
        self._conn_mgr = connection_manager
        self._close_callback = close_callback
        self._traffic_logger = traffic_logger

        self._poll_after_id = None
        self._log_entries: list[tuple[str, tuple]] = []
        self._field_labels: dict[str, dict[str, tk.Label]] = {}

        self._send_entries: dict[str, dict[str, tk.Entry]] = {}
        self._send_errors: dict[str, tk.Label] = {}
        self._periodic: dict[str, dict] = {}

        self.root = tk.Tk()
        self.root.title("CommWorkbench")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        geo = self.ui_cfg.get("geometry", {"width": 1200, "height": 800})
        w, h = geo["width"], geo["height"]
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self._build_connection_bar()
        self._build_status_bar()
        self._build_send_area()
        self._build_panes()

        if self._queue is not None:
            self._poll_queue()

    def set_connection_manager(self, conn_mgr):
        self._conn_mgr = conn_mgr
        self._conn_requested = conn_mgr is not None
        self._refresh_connect_button()

    def apply_connection_config(self, conn_cfg: dict, project_name: str):
        """Adopt another project's connection.json - the bar edits that project's
        settings from then on, and saves back into its own file."""
        self._conn_cfg = conn_cfg
        self._conn_path = CONFIGS_DIR / project_name / "connection.json"
        self._load_conn_fields()

    def set_protocol_codec(self, codec):
        self._protocol_codec = codec


    # ---- connection bar -------------------------------------------------

    def _build_connection_bar(self):
        box = ttk.LabelFrame(self.root, text="Connection")
        box.pack(fill="x", side="top", padx=4, pady=(4, 0))

        self._connect_btn = ttk.Button(box, text="Connect", command=self._on_connect_click)
        self._connect_btn.pack(side="right", padx=6, pady=4)

        row = tk.Frame(box)
        row.pack(side="left", fill="x", padx=4, pady=4)

        self._type_var = tk.StringVar()
        tk.Label(row, text="Type:").pack(side="left")
        type_combo = ttk.Combobox(
            row, textvariable=self._type_var, state="readonly", width=7,
            values=("tcp", "serial"),
        )
        type_combo.pack(side="left", padx=(2, 10))
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._show_type_fields())

        self._tcp_frame = tk.Frame(row)
        self._host_var = tk.StringVar()
        tk.Label(self._tcp_frame, text="Host:").pack(side="left")
        tk.Entry(self._tcp_frame, textvariable=self._host_var, width=15).pack(side="left", padx=(2, 10))
        self._tcp_port_var = tk.StringVar()
        tk.Label(self._tcp_frame, text="Port:").pack(side="left")
        tk.Entry(self._tcp_frame, textvariable=self._tcp_port_var, width=7).pack(side="left", padx=(2, 10))
        self._mode_var = tk.StringVar()
        tk.Label(self._tcp_frame, text="Mode:").pack(side="left")
        ttk.Combobox(
            self._tcp_frame, textvariable=self._mode_var, state="readonly", width=8,
            values=("client", "server"),
        ).pack(side="left", padx=2)

        self._serial_frame = tk.Frame(row)
        self._com_var = tk.StringVar()
        tk.Label(self._serial_frame, text="Port:").pack(side="left")
        # editable on purpose: a port the scan cannot see (driver not up yet, a
        # remote/virtual port) still has to be typeable
        self._com_combo = ttk.Combobox(
            self._serial_frame, textvariable=self._com_var, width=12,
            postcommand=self._refresh_ports,
        )
        self._com_combo.pack(side="left", padx=(2, 10))
        _Tooltip(self._com_combo, self._port_tooltip)
        self._refresh_ports()
        self._baud_var = tk.StringVar()
        tk.Label(self._serial_frame, text="Baud:").pack(side="left")
        # not readonly: the list is a shortcut, any rate can be typed in
        self._baud_combo = ttk.Combobox(
            self._serial_frame, textvariable=self._baud_var, width=9,
            values=("9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"),
        )
        self._baud_combo.pack(side="left", padx=2)

        self._load_conn_fields()

    def _scan_serial_ports(self) -> dict[str, str]:
        """Port name -> what is behind it. Empty when pyserial is not installed."""
        try:
            from serial.tools import list_ports
        except ImportError:
            log.warning("pyserial not installed - serial ports cannot be listed")
            return {}
        try:
            ports = list_ports.comports()
        except OSError as e:
            log.warning("serial port scan failed: %s", e)
            return {}
        found = {}
        for port in ports:
            detail = [port.description or port.device]
            if port.manufacturer:
                detail.append(port.manufacturer)
            if port.hwid:
                detail.append(port.hwid)
            found[port.device] = "\n".join(detail)
        return found

    def _refresh_ports(self):
        # rescanned every time the list drops down, so hot-plugged adapters show up
        self._port_info = self._scan_serial_ports()
        self._com_combo["values"] = tuple(self._port_info)

    def _port_tooltip(self) -> str:
        selected = self._com_var.get().strip()
        if selected in self._port_info:
            return f"{selected}\n{self._port_info[selected]}"
        if not self._port_info:
            return "No serial ports detected on this PC"
        return f"{selected or '(empty)'} - not detected on this PC"

    def _load_conn_fields(self):
        mode = self._conn_cfg.get("mode", "tcp_client")
        tcp = self._conn_cfg.get("tcp", {})
        serial = self._conn_cfg.get("serial", {})
        self._type_var.set("serial" if mode == "serial" else "tcp")
        self._mode_var.set("server" if mode == "tcp_server" else "client")
        self._host_var.set(str(tcp.get("host", "127.0.0.1")))
        self._tcp_port_var.set(str(tcp.get("port", 8080)))
        self._com_var.set(str(serial.get("port", "COM1")))
        self._baud_var.set(str(serial.get("baud_rate", 115200)))
        self._show_type_fields()
        self._refresh_connect_button()

    def _show_type_fields(self):
        serial = self._type_var.get() == "serial"
        self._tcp_frame.pack_forget()
        self._serial_frame.pack_forget()
        (self._serial_frame if serial else self._tcp_frame).pack(side="left")

    def _refresh_connect_button(self):
        self._connect_btn.config(text="Disconnect" if self._conn_requested else "Connect")

    def _apply_conn_fields(self) -> str | None:
        """Push the bar into the live connection config. Returns an error to show."""
        if self._type_var.get() == "serial":
            try:
                baud = int(self._baud_var.get())
            except ValueError:
                return f"Invalid baud rate: {self._baud_var.get()!r}"
            self._conn_cfg["mode"] = "serial"
            self._conn_cfg.setdefault("serial", {}).update(
                {"port": self._com_var.get().strip(), "baud_rate": baud}
            )
            return None
        try:
            port = int(self._tcp_port_var.get())
        except ValueError:
            return f"Invalid port: {self._tcp_port_var.get()!r}"
        self._conn_cfg["mode"] = (
            "tcp_server" if self._mode_var.get() == "server" else "tcp_client"
        )
        self._conn_cfg.setdefault("tcp", {}).update(
            {"host": self._host_var.get().strip(), "port": port}
        )
        return None

    def _on_connect_click(self):
        if self._conn_mgr is None:
            self.update_status("No connection manager — open a project first")
            return
        if self._conn_requested:
            self._conn_mgr.disconnect()
            self._conn_requested = False
        else:
            error = self._apply_conn_fields()
            if error:
                self.update_status(error)
                return
            self._conn_mgr.connect()
            self._conn_requested = True
        self._refresh_connect_button()

    def _build_status_bar(self):
        bar = tk.Frame(self.root, relief="sunken", bd=1)
        bar.pack(fill="x", side="top")

        self._project_var = tk.StringVar()
        self._project_combo = ttk.Combobox(
            bar, textvariable=self._project_var, state="readonly", width=20,
        )
        self._project_combo.pack(side="right", padx=6, pady=2)
        self._project_combo.bind("<<ComboboxSelected>>", self._on_project_change)

        self._log_view_var = tk.StringVar(value=self.ui_cfg.get("log_view", "mixed"))
        self._log_view_combo = ttk.Combobox(
            bar, textvariable=self._log_view_var, state="readonly", width=6,
            values=("mixed", "split"),
        )
        self._log_view_combo.pack(side="right", padx=6, pady=2)
        self._log_view_combo.bind("<<ComboboxSelected>>", self._on_log_view_change)

        self._status_label = tk.Label(bar, text="Disconnected", anchor="w", padx=6)
        self._status_label.pack(side="left", fill="x", expand=True)

        self._led_canvas = tk.Canvas(bar, width=20, height=20, highlightthickness=0)
        self._led_canvas.pack(side="right", padx=6, pady=2)
        self._set_led(False)

    def _set_led(self, connected: bool):
        c = self._led_canvas
        c.delete("all")
        color = "green" if connected else "red"
        c.create_oval(2, 2, 18, 18, fill=color, outline="")

    def set_project_list(self, projects: list[str]):
        self._project_combo["values"] = projects
        if projects and self._project_var.get() not in projects:
            self._project_var.set(projects[0])

    def _on_project_change(self, _event=None):
        if self._close_callback:
            self._close_callback("project_switch", self._project_var.get())

    def _build_panes(self):
        self._paned = tk.PanedWindow(self.root, orient="horizontal", sashwidth=5)
        self._paned.pack(fill="both", expand=True)

        self._build_main_display()
        self._build_traffic_log()

        # panes are stored as a ratio: re-apply it on every resize, and re-read it
        # whenever the user lets go of the sash
        self._sash_pending = False
        self._paned.bind("<Configure>", self._schedule_sash_ratio)
        self._paned.bind("<ButtonRelease-1>", self._record_sash_ratio)

    def _schedule_sash_ratio(self, _event=None):
        # placing the sash inside the <Configure> handler loses to the paned
        # window's own relayout, so wait for it to finish first
        if self._sash_pending:
            return
        self._sash_pending = True
        self.root.after_idle(self._apply_sash_ratio)

    def _apply_sash_ratio(self):
        self._sash_pending = False
        pw = self._paned.winfo_width()
        if pw > 1:
            self._paned.sash_place(0, int(pw * self._ratios.get("main_display", 0.5)), 0)

    def _record_sash_ratio(self, _event=None):
        try:
            pw = self._paned.winfo_width()
            if pw > 1:
                self._ratios["main_display"] = self._paned.sash_coord(0)[0] / pw
        except (tk.TclError, IndexError):
            pass

    def _build_main_display(self):
        self._notebook = ttk.Notebook(self._paned)
        self._paned.add(self._notebook, stretch="always")

        messages = self._protocol_config.get("messages", {})
        for msg_name, msg_def in messages.items():
            if msg_def.get("direction", "rx") != "rx":
                continue
            frame = ttk.Frame(self._notebook)
            self._notebook.add(frame, text=msg_def.get("name", msg_name))
            self._field_labels[msg_name] = {}
            for i, field in enumerate(msg_def.get("fields", [])):
                fname = field["name"]
                lbl_name = tk.Label(frame, text=f"{fname}:", anchor="e", padx=6)
                lbl_name.grid(row=i, column=0, sticky="e", padx=4, pady=2)
                lbl_val = tk.Label(frame, text="\u2014", anchor="w", padx=6, relief="sunken", width=30)
                lbl_val.grid(row=i, column=1, sticky="w", padx=4, pady=2)
                self._field_labels[msg_name][fname] = lbl_val

    def _build_traffic_log(self):
        container = ttk.Frame(self._paned)
        self._paned.add(container, stretch="always")

        if self.ui_cfg.get("log_view") == "split":
            splitter = tk.PanedWindow(container, orient="vertical", sashwidth=5)
            splitter.pack(fill="both", expand=True)
            self._trees = {}
            for direction in ("TX", "RX"):
                box = ttk.LabelFrame(splitter, text=direction)
                splitter.add(box, stretch="always")
                self._trees[direction] = self._make_tree(box)
        else:
            tree = self._make_tree(container)
            self._trees = {"TX": tree, "RX": tree}

        self._replay_log_entries()

    def _make_tree(self, parent) -> ttk.Treeview:
        columns = ("time", "direction", "message", "raw_hex")
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        tree.heading("time", text="Time")
        tree.heading("direction", text="Dir")
        tree.heading("message", text="Message")
        tree.heading("raw_hex", text="Raw Hex")
        tree.column("time", width=80, stretch=False)
        tree.column("direction", width=40, stretch=False)
        tree.column("message", width=180)
        tree.column("raw_hex", width=200)

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

    def _replay_log_entries(self):
        # the rows outlive the widgets, so toggling the view keeps the history
        for direction, values in self._log_entries:
            self._insert_row(direction, values)

    def _on_log_view_change(self, _event=None):
        if self._log_view_var.get() == self.ui_cfg.get("log_view", "mixed"):
            return
        self.ui_cfg["log_view"] = self._log_view_var.get()
        self.rebuild_panes()

    def _poll_queue(self):
        if self._queue is None:
            return
        try:
            while True:
                event = self._queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self._poll_after_id = self.root.after(UI_POLL_INTERVAL_MS, self._poll_queue)

    def _handle_event(self, event: dict):
        etype = event.get("type")
        if etype == "status":
            self.update_status(event.get("text", ""), event.get("connected", False))
            if self._traffic_logger:
                self._traffic_logger.log_status(event.get("text", ""))
        elif etype == "data" and self._parser is not None:
            self._parser.feed(event.get("raw", b""))
            for frame in self._parser.get_frames():
                self._process_frame(frame)
        elif etype == "frame":
            self._process_frame(event)

    def _process_frame(self, frame: dict):
        ftype = frame.get("type")
        if ftype == "frame":
            self._update_display(frame)
            self._add_log_entry(frame)
            if self._traffic_logger:
                self._traffic_logger.log_event(
                    frame.get("direction", "rx"),
                    frame.get("msg_name", ""),
                    frame.get("fields", {}),
                    frame.get("raw_hex", ""),
                )
        elif ftype == "unknown":
            self._add_log_entry({
                "type": "frame",
                "msg_name": "[UNKNOWN]",
                "raw_hex": frame.get("raw_hex", ""),
                "direction": frame.get("direction", "rx"),
                "fields": {},
            })
            if self._traffic_logger:
                self._traffic_logger.log_event(
                    frame.get("direction", "rx"), "[UNKNOWN]", {}, frame.get("raw_hex", ""),
                )
        elif ftype == "error":
            self._add_log_entry({
                "type": "error",
                "msg_name": "ERROR",
                "raw_hex": frame.get("raw_hex", ""),
                "direction": "rx",
                "fields": {"message": frame.get("message", "")},
            })
            if self._traffic_logger:
                self._traffic_logger.log_error(
                    frame.get("message", ""),
                    frame.get("raw_hex", ""),
                )

    def _update_display(self, frame: dict):
        msg_name = frame.get("msg_name", "")
        fields = frame.get("fields", {})
        if msg_name in self._field_labels:
            for fname, val in fields.items():
                if fname in self._field_labels[msg_name]:
                    self._field_labels[msg_name][fname].config(text=_fmt_value(val))

    def _add_log_entry(self, frame: dict):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        direction = frame.get("direction", "rx").upper()
        msg_name = frame.get("msg_name", "")
        raw_hex = frame.get("raw_hex", "")

        fields = frame.get("fields", {})
        summary = " ".join(f"{k}={_fmt_value(v)}" for k, v in fields.items()) if fields else ""

        values = (now, direction, f"{msg_name} {summary}", raw_hex)
        self._log_entries.append((direction, values))
        if len(self._log_entries) > self._max_log_entries:
            del self._log_entries[:-self._max_log_entries]
        self._insert_row(direction, values)

    def _insert_row(self, direction: str, values: tuple):
        tree = self._trees.get(direction) or self._trees["RX"]
        tree.insert("", "end", values=values)
        if len(tree.get_children()) > self._max_log_entries:
            tree.delete(tree.get_children()[0])
        tree.yview_moveto(1.0)

    def _build_send_area(self):
        self._send_outer = tk.Frame(self.root, relief="sunken", bd=1)
        self._send_outer.pack(fill="x", side="bottom")

        header = tk.Label(self._send_outer, text="Send Area", anchor="w", padx=6, pady=2)
        header.pack(fill="x")

        canvas = tk.Canvas(self._send_outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._send_outer, orient="vertical", command=canvas.yview)
        self._send_inner = tk.Frame(canvas)

        self._send_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._send_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._canvas = canvas
        self._send_inner.bind("<Enter>", lambda e: self._bind_mousewheel(canvas))
        self._send_inner.bind("<Leave>", lambda e: self._unbind_mousewheel(canvas))

        self._build_raw_form()

        messages = self._protocol_config.get("messages", {})
        for msg_name, msg_def in messages.items():
            if msg_def.get("direction", "tx") != "tx":
                continue
            self._build_message_form(msg_name, msg_def)

    def _build_raw_form(self):
        frame = tk.LabelFrame(self._send_inner, text="Raw Bytes", padx=4, pady=4)
        frame.pack(fill="x", padx=4, pady=2)

        tk.Label(frame, text="hex:", anchor="e", padx=4).grid(row=0, column=0, sticky="e")
        self._raw_entry = tk.Entry(frame, width=48)
        self._raw_entry.grid(row=0, column=1, sticky="w", padx=2, pady=1)
        self._raw_entry.bind("<Return>", lambda e: self._send_raw())
        tk.Button(frame, text="Send", command=self._send_raw).grid(
            row=0, column=2, sticky="w", padx=4
        )

        err_label = tk.Label(frame, text="", fg="red", anchor="w")
        err_label.grid(row=1, column=0, columnspan=3, sticky="w", padx=4)
        self._send_errors[RAW_KEY] = err_label

    def _send_raw(self):
        self._clear_send_error(RAW_KEY)
        text = self._raw_entry.get().strip()
        if not text:
            return
        # accept what people actually paste: "01 02", "0102", "0x01,0x02"
        cleaned = text.replace("0x", "").replace(",", " ").replace("-", " ").replace(" ", "")
        try:
            data = bytes.fromhex(cleaned)
        except ValueError as e:
            self._show_send_error(RAW_KEY, f"Not hex: {e}")
            return

        if self._queue is not None:
            self._queue.put({
                "type": "frame",
                "msg_name": "[RAW]",
                "fields": {},
                "raw_hex": data.hex(" "),
                "direction": "tx",
            })

        if self._conn_mgr and self._conn_mgr.is_connected():
            self._conn_mgr.send(data)
        else:
            self._show_send_error(RAW_KEY, "Not connected")

    def _bind_mousewheel(self, canvas):
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _unbind_mousewheel(self, canvas):
        canvas.unbind_all("<MouseWheel>")

    def _build_message_form(self, msg_name: str, msg_def: dict):
        frame = tk.LabelFrame(self._send_inner, text=msg_def.get("name", msg_name), padx=4, pady=4)
        frame.pack(fill="x", padx=4, pady=2)

        self._send_entries[msg_name] = {}
        editable = [f for f in msg_def.get("fields", []) if "constant" not in f]
        for i, field in enumerate(editable):
            fname = field["name"]
            ftype = field.get("type", "")
            tk.Label(frame, text=f"{fname} ({ftype}):", anchor="e", padx=4).grid(row=i, column=0, sticky="e", padx=2, pady=1)
            entry = tk.Entry(frame, width=20)
            entry.grid(row=i, column=1, sticky="w", padx=2, pady=1)
            self._send_entries[msg_name][fname] = entry

        btn_row = len(editable)

        send_btn = tk.Button(frame, text="Send", command=lambda mn=msg_name: self._send_message(mn))
        send_btn.grid(row=btn_row, column=0, columnspan=2, sticky="w", padx=4, pady=2)

        tk.Label(frame, text="Periodic (ms):", anchor="e", padx=4).grid(row=btn_row, column=2, sticky="e", padx=2, pady=1)
        interval_entry = tk.Entry(frame, width=8)
        interval_entry.insert(0, "1000")
        interval_entry.grid(row=btn_row, column=3, sticky="w", padx=2, pady=1)

        periodic_btn = tk.Button(frame, text="Start", command=lambda mn=msg_name: self._toggle_periodic(mn))
        periodic_btn.grid(row=btn_row, column=4, sticky="w", padx=2, pady=1)

        self._periodic[msg_name] = {"interval_entry": interval_entry, "btn": periodic_btn, "after_id": None}

        err_label = tk.Label(frame, text="", fg="red", anchor="w")
        err_label.grid(row=btn_row + 1, column=0, columnspan=5, sticky="w", padx=4)
        self._send_errors[msg_name] = err_label

    def _collect_field_values(self, msg_name: str) -> dict | None:
        values = {}
        for fname, entry in self._send_entries[msg_name].items():
            raw = entry.get().strip()
            if not raw:
                values[fname] = None
                continue
            field_def = next((f for f in self._protocol_config["messages"][msg_name]["fields"] if f["name"] == fname), None)
            if not field_def:
                continue
            ftype = field_def.get("type", "")
            try:
                if ftype in ("float32", "float64"):
                    values[fname] = float(raw)
                elif ftype in ("int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64"):
                    values[fname] = int(raw, 0)
                elif ftype == "enum":
                    values[fname] = raw
                elif ftype == "bytes":
                    values[fname] = raw
                elif ftype == "bitfield":
                    values[fname] = json.loads(raw) if raw.startswith("{") else raw
                else:
                    values[fname] = raw
            except (ValueError, json.JSONDecodeError) as e:
                self._show_send_error(msg_name, f"{fname}: {e}")
                return None
        return values

    def _show_send_error(self, msg_name: str, text: str):
        self._send_errors[msg_name].config(text=text)

    def _clear_send_error(self, msg_name: str):
        self._send_errors[msg_name].config(text="")

    def _send_message(self, msg_name: str):
        self._clear_send_error(msg_name)
        values = self._collect_field_values(msg_name)
        if values is None:
            return

        if self._protocol_codec is None:
            self._show_send_error(msg_name, "No protocol loaded")
            return

        errors = self._protocol_codec.validate(msg_name, values)
        if errors:
            self._show_send_error(msg_name, "; ".join(errors))
            return

        try:
            encoded = self._protocol_codec.encode(msg_name, values)
        except Exception as e:
            self._show_send_error(msg_name, str(e))
            return

        raw_hex = encoded.hex(" ")
        # tree row + comm.log block both come from the queue round-trip below
        if self._queue is not None:
            self._queue.put({
                "type": "frame",
                "msg_name": msg_name,
                "fields": values,
                "raw_hex": raw_hex,
                "direction": "tx",
            })

        if self._conn_mgr and self._conn_mgr.is_connected():
            self._conn_mgr.send(encoded)
        else:
            self._show_send_error(msg_name, "Not connected")

    def _toggle_periodic(self, msg_name: str):
        info = self._periodic[msg_name]
        if info["after_id"] is not None:
            self.root.after_cancel(info["after_id"])
            info["after_id"] = None
            info["btn"].config(text="Start")
        else:
            try:
                interval = int(info["interval_entry"].get().strip())
            except ValueError:
                self._show_send_error(msg_name, "Invalid interval")
                return
            info["btn"].config(text="Stop")
            self._schedule_periodic(msg_name, interval)

    def _schedule_periodic(self, msg_name: str, interval_ms: int):
        def tick():
            self._send_message(msg_name)
            info = self._periodic[msg_name]
            if info["after_id"] is not None:
                info["after_id"] = self.root.after(interval_ms, tick)

        info = self._periodic[msg_name]
        info["after_id"] = self.root.after(interval_ms, tick)

    def cancel_all_periodic(self):
        for info in self._periodic.values():
            if info["after_id"] is not None:
                self.root.after_cancel(info["after_id"])
                info["after_id"] = None
                info["btn"].config(text="Start")

    def apply_ui_config(self, ui_cfg: dict):
        """Adopt another project's ui.json: layout is per-project, so the window
        follows it instead of writing the previous project's layout into it."""
        self.ui_cfg = ui_cfg
        self._ratios = dict(ui_cfg.get("panes", {"main_display": 0.5}))
        self._max_log_entries = ui_cfg.get("max_log_entries", 1000)
        self._log_view_var.set(ui_cfg.get("log_view", "mixed"))
        geo = ui_cfg.get("geometry", {})
        if "width" in geo and "height" in geo:
            self.root.geometry(f"{geo['width']}x{geo['height']}")

    def rebuild_panes(self):
        if hasattr(self, "_paned"):
            self._paned.destroy()
        self._field_labels.clear()
        self._build_panes()

    def rebuild_send_area(self):
        self.cancel_all_periodic()
        if hasattr(self, "_send_outer"):
            self._send_outer.destroy()
        self._send_entries.clear()
        self._send_errors.clear()
        self._periodic.clear()
        self._build_send_area()

    def collect_tx_state(self) -> dict[str, dict]:
        state = {}
        for msg_name, entries in self._send_entries.items():
            msg_state = {}
            for fname, entry in entries.items():
                val = entry.get().strip()
                if val:
                    msg_state[fname] = val
            if msg_state:
                state[msg_name] = msg_state
        return state

    def restore_tx_state(self, tx_state: dict[str, dict]):
        for msg_name, fields in tx_state.items():
            if msg_name in self._send_entries:
                for fname, val in fields.items():
                    if fname in self._send_entries[msg_name]:
                        self._send_entries[msg_name][fname].delete(0, "end")
                        self._send_entries[msg_name][fname].insert(0, str(val))

    def clear_display(self):
        for msg_labels in self._field_labels.values():
            for lbl in msg_labels.values():
                lbl.config(text="\u2014")

        # traffic belongs to the project it came from
        self._log_entries.clear()
        for tree in dict.fromkeys(self._trees.values()):
            tree.delete(*tree.get_children())

    def _save_layout(self):
        self._record_sash_ratio()

        self.ui_cfg["panes"] = dict(self._ratios)
        self.ui_cfg["log_view"] = self.ui_cfg.get("log_view", "mixed")
        w, h = self.root.winfo_width(), self.root.winfo_height()
        self.ui_cfg["geometry"] = {"width": w, "height": h}

        _save_json_atomic(self._cfg_path, self.ui_cfg, "layout")

    def _save_connection(self):
        # the bar edits the live config dict, so what is in memory is what to write
        if not self._conn_cfg:
            return
        self._apply_conn_fields()
        _save_json_atomic(self._conn_path, self._conn_cfg, "connection settings")

    def _on_close(self):
        self.cancel_all_periodic()
        if self._poll_after_id is not None:
            self.root.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        if self._close_callback:
            self._close_callback("close")
        self._save_layout()
        self._save_connection()
        self.root.destroy()

    def update_status(self, text: str, connected: bool = False):
        self._status_label.config(text=text)
        self._set_led(connected)

    def run(self):
        self.root.mainloop()


def run(configs: dict[str, dict], project_name: str = "_current"):
    ui = CommWorkbenchUI(configs, project_name)
    ui.run()
