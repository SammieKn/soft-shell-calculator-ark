# VIKTOR Parametrization — Input Fields Reference

All fields are assigned as **class attributes** on a `vkt.Parametrization` subclass.
Every field takes a human-readable `label` as its first positional argument.

---

## Numeric input

```python
# Decimal number — optional kwargs: default, min, max, step, suffix, num_decimals, description
vkt.NumberField("Width", default=1.0, min=0.0, max=100.0, suffix="m")

# Whole number only
vkt.IntegerField("Count", default=5, min=1)

# Visual slider (equivalent to NumberField with a slider widget)
vkt.Slider("Factor", min=0, max=10, default=5, step=0.5)
```

---

## Text input

```python
# Single-line short text
vkt.TextField("Name", default="John")

# Multi-line long text
vkt.TextAreaField("Description")
```

---

## Options and selections

```python
# Single selection — renders as a dropdown by default
vkt.OptionField("Material", options=["Steel", "Concrete", "Wood"], default="Steel")

# Variant: radio buttons
vkt.OptionField("Side", options=["Left", "Right"], variant="radio-button")

# Multiple selections from a list
vkt.MultiSelectField("Features", options=["A", "B", "C"])

# Autocomplete (typed filtering over a large options list)
vkt.AutocompleteField("City", options=["Amsterdam", "Rotterdam", "Utrecht"])
```

---

## Boolean / toggle

```python
vkt.BooleanField("Enable calculation", default=True)
```

---

## Date

```python
vkt.DateField("Inspection date")
```

---

## Color

```python
vkt.ColorField("Line color")
```

---

## File upload

```python
# Single file — file_types restricts accepted extensions
vkt.FileField("Upload data file", file_types=[".csv", ".xlsx"])

# Multiple files at once
vkt.MultiFileField("Upload measurements", file_types=[".dat", ".txt"])
```

See `references/files.md` for how to read uploaded files in a view method.

---

## Tables and dynamic arrays

```python
# Fixed-column table — users add rows
vkt.Table("Data table") \
    .with_field(vkt.TextField("Label")) \
    .with_field(vkt.NumberField("Value", suffix="kN"))

# Dynamic array — similar to Table but rendered as stacked form groups
vkt.DynamicArray("Load cases") \
    .with_field(vkt.TextField("Name")) \
    .with_field(vkt.NumberField("Load", suffix="kN")) \
    .with_field(vkt.OptionField("Type", options=["Dead", "Live"]))
```

Accessing table rows in a view method:
```python
for row in (params.my_table or []):
    label = row.label
    value = row.value
```

---

## Read-only display fields (no user input)

```python
# Static markdown text block — useful for instructions or section headings
vkt.Text("## Instructions\nFill in all required fields before calculating.")

# Dynamic computed output shown inline in the parametrization panel
# value accepts a Lookup (reads another field) or a callback method name
vkt.OutputField("Computed area", value=vkt.Lookup("width"), suffix="m²")

# Static image in the parametrization panel (requires assets_path in config)
vkt.Image("diagram.png")

# Manual line break to control field layout
vkt.LineBreak()
```

---

## Action buttons

```python
# Triggers a Controller method that returns nothing (side-effect only)
vkt.ActionButton("Run simulation", method="run_simulation")

# Triggers a Controller method that returns a file download
vkt.DownloadButton("Download report", method="generate_report")

# Triggers a Controller method that returns updated params values
vkt.SetParamsButton("Fill defaults", method="fill_defaults")
```

See `references/files.md` for the `DownloadButton` handler pattern.

---

## Hidden field (JSON storage)

```python
# Stores arbitrary JSON data on the entity — not visible to the user
vkt.HiddenField("cached_result")
```

---

## Field visibility (conditional fields)

Any field can be conditionally shown/hidden:

```python
# Using a Lookup — field is visible when another field equals a value
vkt.NumberField(
    "Wall thickness",
    visible=vkt.Lookup("material") == "Concrete"
)

# Using a callback — method on Controller returns True/False
vkt.NumberField("Advanced setting", visible="get_show_advanced")
```

---

## Common field arguments (available on most fields)

| Argument | Description |
|----------|-------------|
| `default` | Pre-filled value |
| `description` | Tooltip text shown to the user |
| `visible` | `True` / `False` / `Lookup` / callback name |
| `flex` | Width as a fraction of the row (e.g. `50` = half width) |
| `name` | Override the attribute key used in `params` |
