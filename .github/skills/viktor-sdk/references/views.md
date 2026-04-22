# VIKTOR Views Reference

Views are defined as methods on the `Controller` class decorated with a view class.
Every view decorator requires a `label` (the tab name shown in the output panel).
Every view method signature must be `(self, params, **kwargs)`.

---

## PlotlyView — interactive plots and charts

Best for line charts, scatter plots, bar charts, and any interactive graph.
Requires `plotly` in `requirements.txt`.

```python
import plotly.graph_objects as go
import viktor as vkt


class Controller(vkt.Controller):

    @vkt.PlotlyView("Signal plot")
    def plot_signal(self, params, **kwargs):
        x = list(range(100))
        y = [v ** 2 for v in x]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Signal"))
        fig.update_layout(xaxis_title="Sample", yaxis_title="Value")
        return vkt.PlotlyResult(fig)
```

Pass a `go.Figure` object or a valid Plotly dict to `PlotlyResult`.

### Combined: PlotlyAndDataView

```python
    @vkt.PlotlyAndDataView("Plot + summary")
    def plot_and_data(self, params, **kwargs):
        fig = go.Figure(...)
        data = vkt.DataGroup(vkt.DataItem("Peak value", 42.1, suffix="kN"))
        return vkt.PlotlyAndDataResult(fig, data=data)
```

---

## ImageView — static images (matplotlib, PNG, SVG, JPG, GIF)

Best for matplotlib figures or pre-rendered images.

```python
from io import StringIO
import matplotlib.pyplot as plt
import viktor as vkt


class Controller(vkt.Controller):

    @vkt.ImageView("Chart")
    def show_chart(self, params, **kwargs):
        fig, ax = plt.subplots()
        ax.bar(["A", "B", "C"], [3, 7, 5])
        ax.set_ylabel("Value")
        svg_data = StringIO()
        fig.savefig(svg_data, format="svg")
        plt.close()
        return vkt.ImageResult(svg_data)
```

For PNG/JPG images from bytes:
```python
from io import BytesIO
return vkt.ImageResult(BytesIO(image_bytes))
```

### Combined: ImageAndDataView

```python
    @vkt.ImageAndDataView("Chart + data")
    def chart_and_data(self, params, **kwargs):
        svg_data = ...  # StringIO with SVG content
        data = vkt.DataGroup(vkt.DataItem("Max", 99, suffix="kN"))
        return vkt.ImageAndDataResult(svg_data, data=data)
```

---

## DataView — grouped key-value results

Best for showing structured calculation results with labels, units, and statuses.
Data is nested up to three levels deep using `DataGroup` and `DataItem`.

```python
import viktor as vkt


class Controller(vkt.Controller):

    @vkt.DataView("Results")
    def show_results(self, params, **kwargs):
        data = vkt.DataGroup(
            # keyword names become the attribute path for Summary references
            total_force=vkt.DataItem("Total force", 123.4, suffix="kN"),
            status=vkt.DataItem(
                "Status",
                "OK",
                status=vkt.DataStatus.SUCCESS,
                status_message="Within limits",
            ),
            breakdown=vkt.DataItem(
                "Breakdown",
                "",
                subgroup=vkt.DataGroup(
                    dead=vkt.DataItem("Dead load", 80.0, suffix="kN"),
                    live=vkt.DataItem("Live load", 43.4, suffix="kN"),
                ),
            ),
        )
        return vkt.DataResult(data)
```

### DataItem arguments

| Argument | Type | Description |
|----------|------|-------------|
| `label` | str | Display name |
| `value` | any | The value to display |
| `suffix` | str | Unit appended after value |
| `prefix` | str | Symbol prepended before value |
| `explanation_label` | str | Tooltip / explanation text |
| `status` | `vkt.DataStatus` | `SUCCESS`, `WARNING`, or `ERROR` |
| `status_message` | str | Text shown alongside the status icon |
| `subgroup` | `DataGroup` | Nested group of items |
| `number_of_decimals` | int | Rounding for numeric values |

### Dynamic DataGroups (variable number of items)

```python
items = [vkt.DataItem(name, val, suffix="kN") for name, val in results.items()]
data = vkt.DataGroup(*items)
return vkt.DataResult(data)
```

---

## TableView — tabular data

Best for presenting rows of results. Supports pandas DataFrames directly.

```python
import viktor as vkt


class Controller(vkt.Controller):

    @vkt.TableView("Overview")
    def show_table(self, params, **kwargs):
        data = [
            ["Item A", 1.5, True],
            ["Item B", 2.3, False],
        ]
        return vkt.TableResult(
            data,
            column_headers=["Name", "Value (m)", "Pass"],
        )
```

### Using a pandas DataFrame

```python
import pandas as pd
import viktor as vkt

    @vkt.TableView("Results")
    def show_table(self, params, **kwargs):
        df = pd.DataFrame({"Name": ["A", "B"], "Value": [1.5, 2.3]})
        return vkt.TableResult(df)
```

### TableResult arguments

| Argument | Description |
|----------|-------------|
| `data` | 2D list, DataFrame, or Styler |
| `row_headers` | List of row labels or `TableHeader` objects |
| `column_headers` | List of column labels or `TableHeader` objects |
| `enable_sorting_and_filtering` | Default `True`; set `False` to disable |

Per-cell styling: wrap values in `vkt.TableCell(value, background_color=vkt.Color.green())`.
Per-column styling: use `vkt.TableHeader("Label", num_decimals=2, align="right")`.

---

## SVGView — custom SVG drawings

```python
import viktor as vkt


class Controller(vkt.Controller):

    @vkt.SVGView("Diagram")
    def show_svg(self, params, **kwargs):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">' \
              '<rect width="200" height="100" fill="lightblue"/></svg>'
        return vkt.SVGResult(svg)
```

---

## PDFView — inline PDF report

```python
import viktor as vkt


class Controller(vkt.Controller):

    @vkt.PDFView("Report")
    def show_pdf(self, params, **kwargs):
        pdf_bytes = ...  # bytes of a PDF file
        return vkt.PDFResult(file=vkt.File.from_data(pdf_bytes))
```

---

## WebView — arbitrary HTML

```python
import viktor as vkt


class Controller(vkt.Controller):

    @vkt.WebView("Dashboard")
    def show_html(self, params, **kwargs):
        html = "<h1>Hello</h1><p>Custom HTML output.</p>"
        return vkt.WebResult(html)
```

---

## View decorator optional arguments

All view decorators accept additional arguments beyond `label`:

| Argument | Description |
|----------|-------------|
| `duration_guess` | `DurationGuess.SHORT / MEDIUM / LONG` — sets loading indicator |
| `update_label` | Label shown on the "update" button in the panel |

Example:
```python
@vkt.PlotlyView("Analysis", duration_guess=vkt.DurationGuess.LONG)
def run_analysis(self, params, **kwargs):
    ...
```

---

## Memoize — caching expensive function calls

Use `@vkt.memoize` to cache the result of a slow function. The cached result is
reused for up to **24 hours** as long as the arguments do not change. This avoids
re-running the same calculation when the user switches between views or triggers
a download without changing the input.

**Rules:**
- Must be a **module-level** function, not a method on `Controller`.
- All arguments must be **keyword-only** (defined after a bare `*`).
- Call sites must pass arguments by keyword.
- In development the local cache is limited to 50 entries (FIFO eviction).
  In production the storage is unlimited.

**IMPORTANT limitation:** `@vkt.memoize` hashes the arguments to detect changes.
VIKTOR `FileResource` objects from `params` are **new instances on every render**
even when the user hasn't changed any files. This means `@vkt.memoize` will
**always** be a cache miss when the arguments include `FileResource` objects.
Use `vkt.Storage(scope='session')` instead for file-based inputs (see below).

```python
import viktor as vkt


@vkt.memoize
def run_heavy_analysis(*, param_a, param_b):
    # only re-runs when param_a or param_b changes
    return _do_work(param_a, param_b)


class Controller(vkt.Controller):

    @vkt.DataView("Results")
    def show_results(self, params, **kwargs):
        result = run_heavy_analysis(param_a=params.a, param_b=params.b)
        data = vkt.DataGroup(vkt.DataItem("Count", len(result)))
        return vkt.DataResult(data)
```

---

## Session Storage — caching file-based results

When uploads (`FileResource` objects) are the input to a long-running analysis,
use `vkt.Storage(scope='session')` to cache the serialized result. The session
scope persists for the lifetime of the user's browser tab and is unique per user.

**Pattern — fingerprint → check storage → compute if miss → store → return:**

```python
import hashlib
import json
import viktor as vkt

_FP_KEY   = "analysis_fingerprint"
_DATA_KEY = "analysis_result"


def _fingerprint(files: list) -> str:
    names = sorted(getattr(f, "filename", "") for f in files)
    return hashlib.sha256(":".join(names).encode()).hexdigest()


def get_or_compute(files: list) -> dict:
    fp = _fingerprint(files)
    try:
        stored_fp = vkt.Storage().get(_FP_KEY, scope="session")
        if stored_fp.getvalue().decode() == fp:
            stored = vkt.Storage().get(_DATA_KEY, scope="session")
            return json.loads(stored.getvalue().decode())
    except Exception:
        pass  # cache miss

    result = _run_analysis(files)   # the expensive call

    try:
        vkt.Storage().set(_FP_KEY,   data=vkt.File.from_data(fp),                  scope="session")
        vkt.Storage().set(_DATA_KEY, data=vkt.File.from_data(json.dumps(result)),   scope="session")
    except Exception:
        pass

    return result
```

**Key notes:**
- `vkt.Storage().get(key, scope="session")` raises an exception when the key
  does not exist — always wrap in `try/except`.
- `vkt.Storage().set(key, data=vkt.File.from_data(str_or_bytes), scope="session")`
- Session data is deleted automatically when the browser tab is closed.
- Requires SDK >= 14.28.0. The `scope='session'` option is only available for
  `editor` app type and higher.
- The fingerprint should be based on something stable (filenames, not object
  identity). Including file sizes adds robustness but requires reading bytes.


