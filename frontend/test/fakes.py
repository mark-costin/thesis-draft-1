"""Stand-ins for streamlit and plotly so the frontend can be tested without them installed.

FakeStreamlit records what a page draws and lets a test decide which buttons are
"clicked" (by label or key) and what values inputs hold. st.rerun()/st.stop()
raise exceptions, like the real ones, so a page run ends where Streamlit's would.
"""
import datetime
import sys
import types


class SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


class StopScript(Exception):
    pass


class RerunScript(Exception):
    pass


class _Block:
    """A container (column, tab, form, expander...). Usable with `with` and as `col.button(...)`."""

    def __init__(self, st):
        self._st = st

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getattr__(self, name):
        return getattr(self._st, name)


class _Selection:
    def __init__(self):
        self.rows = []


class _DataframeState:
    def __init__(self):
        self.selection = _Selection()


class _Anything:
    """Accepts any call or attribute (used for st.column_config.*)."""

    def __getattr__(self, name):
        return _Anything()

    def __call__(self, *a, **k):
        return None


class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.column_config = _Anything()
        self.reset()

    # ------------------------------------------------------------------ control
    def reset(self):
        self.session_state = SessionState()
        self.calls = []        # (kind, text) for everything drawn
        self.clicks = set()    # button labels or keys that count as clicked
        self.inputs = {}       # key or label -> value returned by an input widget
        self.new_run()

    def new_run(self):
        """Start a script run: real Streamlit refuses two widgets with the same ID in one run."""
        self._ids = set()

    def _register(self, kind, label, key):
        wid = ("key", key) if key is not None else (kind, label)
        if wid in self._ids:
            raise AssertionError(f"Duplicate widget ID {wid}: Streamlit would raise DuplicateWidgetID")
        self._ids.add(wid)

    def drawn(self, kind=None):
        return [t for k, t in self.calls if kind is None or k == kind]

    def _rec(self, kind, text=""):
        self.calls.append((kind, str(text)))

    def _value(self, label, key, default):
        self._register("input", label, key)
        if key is not None and key in self.inputs:
            value = self.inputs[key]
        elif label in self.inputs:
            value = self.inputs[label]
        elif key is not None and key in self.session_state:
            value = self.session_state[key]
        else:
            value = default
        if key is not None:
            self.session_state[key] = value
        return value

    def _clicked(self, label, key, kwargs):
        if kwargs.get("disabled"):
            return False
        return label in self.clicks or (key is not None and key in self.clicks)

    # ------------------------------------------------------------------ layout
    def set_page_config(self, *a, **k):
        pass

    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Block(self) for _ in range(n)]

    def tabs(self, labels):
        return [_Block(self) for _ in labels]

    def container(self, *a, **k):
        return _Block(self)

    def expander(self, label="", *a, **k):
        self._rec("expander", label)
        return _Block(self)

    def form(self, *a, **k):
        return _Block(self)

    def popover(self, *a, **k):
        return _Block(self)

    def spinner(self, *a, **k):
        return _Block(self)

    def empty(self):
        return _Block(self)

    @property
    def sidebar(self):
        return _Block(self)

    # ------------------------------------------------------------------ output
    def _out(kind):
        def draw(self, body="", *a, **k):
            self._rec(kind, body)
            return _Block(self)
        return draw

    markdown = _out("markdown")
    write = _out("write")
    caption = _out("caption")
    info = _out("info")
    success = _out("success")
    warning = _out("warning")
    error = _out("error")
    json = _out("json")
    title = _out("title")
    header = _out("header")
    subheader = _out("subheader")
    code = _out("code")
    toast = _out("toast")
    text = _out("text")
    del _out

    def metric(self, label, value=None, *a, **k):
        self._rec("metric", f"{label}={value}")

    def divider(self, *a, **k):
        pass

    def plotly_chart(self, fig, *a, **k):
        self._rec("plotly_chart", "")

    def line_chart(self, *a, **k):
        self._rec("chart", "")

    bar_chart = line_chart

    def dataframe(self, data=None, *a, **k):
        self._rec("dataframe", "" if data is None else len(data))
        return _DataframeState()

    def table(self, data=None, *a, **k):
        self._rec("table", "" if data is None else len(data))

    # ------------------------------------------------------------------ widgets
    def button(self, label, key=None, **k):
        self._register("button", label, key)
        self._rec("button", label)
        return self._clicked(label, key, k)

    def form_submit_button(self, label="Submit", key=None, **k):
        self._rec("submit", label)
        return self._clicked(label, key, k)

    def text_input(self, label, value="", key=None, **k):
        return self._value(label, key, value if value is not None else "")

    def text_area(self, label, value="", key=None, **k):
        return self._value(label, key, value if value is not None else "")

    def number_input(self, label, min_value=None, max_value=None, value="min", step=None, key=None, **k):
        default = (min_value if min_value is not None else 0.0) if value == "min" else value
        return self._value(label, key, default)

    def selectbox(self, label, options, index=0, key=None, format_func=None, **k):
        options = list(options)
        default = options[index] if (index is not None and options) else None
        return self._value(label, key, default)

    def radio(self, label, options, index=0, key=None, **k):
        options = list(options)
        default = options[index] if (index is not None and options) else None
        return self._value(label, key, default)

    def multiselect(self, label, options, default=None, key=None, **k):
        return self._value(label, key, list(default or []))

    def checkbox(self, label, value=False, key=None, **k):
        return self._value(label, key, value)

    toggle = checkbox

    def slider(self, label, min_value=None, max_value=None, value=None, key=None, **k):
        return self._value(label, key, value)

    def date_input(self, label, value=None, key=None, **k):
        return self._value(label, key, value or datetime.date(1990, 1, 1))

    def data_editor(self, data, key=None, **k):
        return data

    # ------------------------------------------------------------------ control flow
    def dialog(self, *a, **k):
        return lambda fn: fn

    def fragment(self, *a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda fn: fn

    def cache_data(self, *a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda fn: fn

    def rerun(self, *a, **k):
        raise RerunScript()

    def stop(self):
        raise StopScript()


class _PlotlyObj:
    def __init__(self, *a, **k):
        self.args, self.kwargs = a, k

    def update_layout(self, *a, **k):
        pass

    def add_trace(self, *a, **k):
        pass

    def add_vline(self, *a, **k):
        pass


def _make_plotly():
    plotly = types.ModuleType("plotly")
    go = types.ModuleType("plotly.graph_objects")
    for name in ("Figure", "Indicator", "Bar", "Pie", "Scatter"):
        setattr(go, name, _PlotlyObj)
    plotly.graph_objects = go
    return plotly, go


ST = FakeStreamlit()


def install():
    """Put the fakes in sys.modules (once) and return the fake streamlit."""
    sys.modules["streamlit"] = ST
    if "plotly" not in sys.modules or not hasattr(sys.modules["plotly"], "graph_objects"):
        plotly, go = _make_plotly()
        sys.modules["plotly"] = plotly
        sys.modules["plotly.graph_objects"] = go
    # Modules imported earlier against another fake must use this one.
    for name in ("frontend.docpage_api", "docpage_api"):
        mod = sys.modules.get(name)
        if mod is not None:
            mod.st = ST
    return ST
