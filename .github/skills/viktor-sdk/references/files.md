# VIKTOR File Handling Reference

## Uploading a single file (FileField)

Declare in Parametrization:

```python
import viktor as vkt


class Parametrization(vkt.Parametrization):
    data_file = vkt.FileField(
        "Upload data file",
        file_types=[".csv", ".xlsx"],   # optional whitelist
        max_size=10_000_000,            # optional max bytes (10 MB)
    )
```

Read in a view method:

```python
class Controller(vkt.Controller):

    @vkt.DataView("Results")
    def show_results(self, params, **kwargs):
        file_resource = params.data_file  # FileResource | None
        if file_resource is None:
            data = vkt.DataGroup(vkt.DataItem("Status", "No file uploaded"))
            return vkt.DataResult(data)

        with file_resource.file as f:
            raw_bytes: bytes = f.getvalue()

        # Parse as needed — example: CSV via pandas
        import io
        import pandas as pd
        df = pd.read_csv(io.BytesIO(raw_bytes))

        data = vkt.DataGroup(vkt.DataItem("Rows", len(df)))
        return vkt.DataResult(data)
```

---

## Uploading multiple files (MultiFileField)

```python
class Parametrization(vkt.Parametrization):
    measurement_files = vkt.MultiFileField(
        "Upload measurements",
        file_types=[".dat", ".txt"],
    )
```

Read in a view method:

```python
    @vkt.DataView("Summary")
    def show_summary(self, params, **kwargs):
        files = params.measurement_files or []   # list of FileResource, never None
        results = []
        for file_resource in files:
            with file_resource.file as f:
                content: bytes = f.getvalue()
            # process content ...
            results.append(len(content))

        data = vkt.DataGroup(
            vkt.DataItem("Files uploaded", len(files)),
            vkt.DataItem("Total bytes", sum(results), suffix="B"),
        )
        return vkt.DataResult(data)
```

---

## File name and metadata

`FileResource` exposes the original file name:

```python
with file_resource.file as f:
    content = f.getvalue()
filename = file_resource.filename   # e.g. "measurement_01.dat"
```

---

## Downloading a file (DownloadButton)

Declare in Parametrization:

```python
class Parametrization(vkt.Parametrization):
    download_btn = vkt.DownloadButton("Download result", method="generate_download")
```

Handle in Controller — the method returns a `DownloadResult`:

```python
class Controller(vkt.Controller):

    def generate_download(self, params, **kwargs):
        # Build file content — here a simple CSV
        lines = ["name,value", "A,1", "B,2"]
        content = "\n".join(lines).encode("utf-8")
        return vkt.DownloadResult(content, "result.csv")
```

`DownloadResult(data, filename)`:
- `data` — `bytes` or a file-like object (`BytesIO`, `StringIO`)
- `filename` — the suggested filename for the browser download

---

## Creating a vkt.File for PDFView or other uses

```python
import viktor as vkt

pdf_bytes: bytes = ...
f = vkt.File.from_data(pdf_bytes)

# Use in PDFView:
return vkt.PDFResult(file=f)
```

---

## Notes

- Always guard `FileField` values against `None` before calling `.file`.
- `MultiFileField` always returns a list (possibly empty), never `None`.
- File bytes are accessed inside a context manager (`with file_resource.file as f`).
- Large files will slow down view rendering — consider validating `max_size` in
  the `FileField` to give users early feedback.
