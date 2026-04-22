---
name: viktor-sdk
description: >
  Expert guidance for building VIKTOR applications using the VIKTOR Python SDK.
  Covers the full development loop: defining Parametrization with input fields,
  structuring views and results, wiring params to calculation logic, organising
  the parametrization with Tabs and Sections, uploading and processing files,
  and configuring the app via viktor.config.toml and requirements.txt.
  Use this skill whenever the user is working on a VIKTOR app, adding input
  fields or views, wiring user input to output, handling file uploads, building
  a Controller or Parametrization class, asking about PlotlyView, ImageView,
  DataView, TableView, DownloadButton, or any other VIKTOR SDK concept — even
  if they don't say "VIKTOR" explicitly but the file context is a VIKTOR app.
---

# VIKTOR SDK

## Reference files in this skill

Read these when you need full API detail — don't load them all upfront, only
the ones relevant to the current task:

| File | Contents |
|------|----------|
| `references/parametrization.md` | Every input field type with signatures and examples |
| `references/views.md` | Every view/result type with decorator patterns and examples |
| `references/layout.md` | Tabs, Sections, hiding, conditional visibility |
| `references/files.md` | File upload reading, DownloadButton, file type handling |
| `references/config.md` | `viktor.config.toml` keys and `requirements.txt` format |

---

## Minimal app structure

Three files are required in the app root:

```
my-app/
├── app.py             # Controller + Parametrization
├── requirements.txt   # Python deps — must include viktor==<version>
└── viktor.config.toml # App type, Python version, registered name
```

Everything is imported from the top-level `viktor` package:

```python
import viktor as vkt
```

---

## The Controller / Parametrization pattern

The **Parametrization** defines what the user can fill in (left panel).
The **Controller** defines what is computed and shown (right panel).
They are linked via `Controller.parametrization = Parametrization`.

```python
import viktor as vkt


class Parametrization(vkt.Parametrization):
    width = vkt.NumberField("Width", suffix="m", default=1.0)
    height = vkt.NumberField("Height", suffix="m", default=2.0)


class Controller(vkt.Controller):
    parametrization = Parametrization

    @vkt.DataView("Results")
    def show_results(self, params, **kwargs):
        area = params.width * params.height
        data = vkt.DataGroup(vkt.DataItem("Area", area, suffix="m²"))
        return vkt.DataResult(data)
```

### Wiring params to output

`params` mirrors the Parametrization class hierarchy exactly.
`Parametrization.tab_a.section_b.my_field` → `params.tab_a.section_b.my_field`.

Every view method signature must be `(self, params, **kwargs)`.

---

## Building an app — typical workflow

1. **Define the Parametrization** with the fields users need to fill in.
   → See `references/parametrization.md` for the full field catalogue.

2. **Organise with Tabs and Sections** if there are many fields.
   → See `references/layout.md`.

3. **Add view methods** to the Controller for each output panel.
   → See `references/views.md` for all view types and their result objects.

4. **Handle file upload** if users need to supply data files.
   → See `references/files.md`.

5. **Wire calculation logic** between `params` values and view return values.
   Keep heavy computation in separate modules; the Controller just calls them.

6. **Configure the app** in `viktor.config.toml` and list deps in `requirements.txt`.
   → See `references/config.md`.

---

## Common pitfalls

- View methods must always accept `**kwargs` — the platform may inject extra
  arguments in future SDK versions.
- `params.some_file` is `None` when no file has been uploaded — always guard.
- `import viktor as vkt` goes at the top of the file, never inside a method.
- `DataGroup` keyword argument names become the attribute path for `Summary` —
  use meaningful names when nesting.
- The `packages` key in `viktor.config.toml` is for Linux system packages
  (apt-get), **not** Python packages — Python deps go in `requirements.txt`.
- Internal helper packages that live as folders inside the app root do **not**
  need to be added to `requirements.txt`.
