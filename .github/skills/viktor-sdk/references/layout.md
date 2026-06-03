# VIKTOR Parametrization Layout Reference

## Overview

The parametrization input panel supports up to three nesting levels:

```
Tab
└── Section
    └── Field
```

You can also use just Sections (no Tabs), just Tabs (no Sections), or flat Fields —
it depends on how much structure you need. Keep it as simple as the form allows.

---

## Tabs

`vkt.Tab` creates a horizontal tab in the input panel.

```python
import viktor as vkt


class Parametrization(vkt.Parametrization):
    tab_input = vkt.Tab("Input")
    tab_input.width = vkt.NumberField("Width", suffix="m")
    tab_input.height = vkt.NumberField("Height", suffix="m")

    tab_options = vkt.Tab("Options")
    tab_options.show_grid = vkt.BooleanField("Show grid", default=True)
```

Access in view: `params.tab_input.width`, `params.tab_options.show_grid`.

---

## Sections

`vkt.Section` creates a collapsible group within a Tab (or at the top level).

```python
class Parametrization(vkt.Parametrization):
    tab_geometry = vkt.Tab("Geometry")
    tab_geometry.section_cross = vkt.Section("Cross-section")
    tab_geometry.section_cross.diameter = vkt.NumberField("Diameter", suffix="mm")
    tab_geometry.section_cross.thickness = vkt.NumberField("Thickness", suffix="mm")

    tab_geometry.section_material = vkt.Section("Material")
    tab_geometry.section_material.steel_grade = vkt.OptionField(
        "Steel grade", options=["S235", "S275", "S355"]
    )
```

### Expanded by default

```python
vkt.Section("Main settings", initially_expanded=True)
```

By default the first section in a parametrization is expanded and the rest
are collapsed. Setting `initially_expanded=True` on a specific section overrides this.

---

## Hiding Tabs and Sections

`visible` accepts a `Lookup`, a boolean, or a callback method name on the Controller.

```python
class Parametrization(vkt.Parametrization):
    calculation_type = vkt.OptionField("Type", options=["Simple", "Advanced"])

    tab_advanced = vkt.Tab(
        "Advanced settings",
        visible=vkt.Lookup("calculation_type") == "Advanced"
    )
    tab_advanced.tolerance = vkt.NumberField("Tolerance", default=0.001)
```

Using a Controller callback:
```python
# In Parametrization:
tab_extra = vkt.Tab("Extra", visible="get_show_extra")

# In Controller:
@staticmethod
def get_show_extra(params, **kwargs):
    return params.enable_extra is True
```

---

## Hiding individual fields

The same `visible` pattern works on any field:

```python
class Parametrization(vkt.Parametrization):
    use_custom_factor = vkt.BooleanField("Use custom factor", default=False)
    custom_factor = vkt.NumberField(
        "Custom factor",
        visible=vkt.Lookup("use_custom_factor")
    )
```

---

## Controlling field width

Fields fill the full row by default. Use `flex` to place multiple fields on one row:

```python
class Parametrization(vkt.Parametrization):
    x = vkt.NumberField("X", suffix="m", flex=50)   # 50% width
    y = vkt.NumberField("Y", suffix="m", flex=50)   # 50% width — sits next to X
```

---

## LineBreak

Force a new row in the parametrization layout:

```python
class Parametrization(vkt.Parametrization):
    field_a = vkt.NumberField("A", flex=50)
    field_b = vkt.NumberField("B", flex=50)
    vkt.LineBreak()                          # next fields start on a new row
    field_c = vkt.TextField("C")
```

---

## Pages (tree apps only)

In `app_type = 'tree'` apps, a `Page` is the top-level navigation element.
This is outside scope for most single-entity editor apps.

---

## Summary

The `visible` argument pattern is the same across Tabs, Sections, and Fields,
making it straightforward to build progressively revealed forms: start with a
simple set of fields, and reveal advanced options only when the user opts in.
