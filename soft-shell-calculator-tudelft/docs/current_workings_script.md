# Current Workings of the TU Delft Soft Shell Calculator

> **Source file:** `soft-shell-calculator-tudelft/app/soft_shell_calculator.py`  
> **Version:** v1.1 (Anindya, revised by Michele Mirra)  
> **Purpose:** This document describes the workings of the original script as a reference for the refactoring effort.

---

## 1. Purpose

The Soft Shell Calculator analyzes **RPD (Resistograph Pile Drilling) measurements** of wooden utility poles to estimate the dimensions of the wood cross-section zones. These estimates help Gemeente Amsterdam assess the structural health and decay of wooden poles.

The tool produces four key outputs per measurement:

| Output | Description |
|---|---|
| **Diameter** | Estimated cross-section diameter in mm |
| **Annual ring count** | Estimated number of growth rings |
| **Sapwood width** | Estimated width of the outer sapwood layer in mm |
| **Soft shell thickness** | Estimated thickness of the degraded outer zone in mm (left and right sides) |

---

## 2. Input Data Format — `.rgp` Files

Measurements are stored as JSON files produced by an IML Resi PD device. Each file contains:

- A `header` section with measurement metadata
- A `profile` section with the raw drilling signal arrays

The fields consumed by the script are:

| Field | Description |
|---|---|
| `header.resolutionFeed` | Sampling resolution in samples per mm (e.g. `10`) |
| `header.dateYear` | Measurement year |
| `header.dateMonth` | Measurement month |
| `header.dateDay` | Measurement day |
| `profile.drill` | Array of drilling resistance values (%) sampled at each step |

The `resolutionFeed` value is central to all spatial calculations — it converts sample indices to physical depths in mm by dividing the index by the resolution.

---

## 3. Application Structure

The entire application is a single Python script. It contains one utility function and one wxPython GUI class.

```
soft_shell_calculator.py
├── pair_similar_names()          Utility: pair filenames by string similarity
└── class MainWindow (wx.Frame)   Single wxPython window
    ├── __init__()                Calls InitUI, centres and shows window
    ├── InitUI()                  Builds the widget layout
    ├── OnClickb1()               Handler: load a single .rgp file
    ├── OnClickb2()               Handler: load a directory of .rgp files
    ├── OnClickb3()               Handler: run analysis and export outputs
    └── on_close()                Handler: destroy window and exit
```

### 3.1 User Interface

The UI is built with wxPython and consists of:

- A matplotlib canvas for displaying the output plots inline
- **Button 1** — "Load single RPD measurement": opens a file dialog for one `.rgp` file
- **Button 2** — "Load multiple RPD measurements": opens a directory dialog
- **Checkbox** — "Pair RPD measurements": enabled only when a directory is loaded; triggers pairing logic
- **Button 3** — "Analyze and generate output": disabled until a file or directory is loaded; runs the full analysis pipeline

The application determines which mode to run (single file vs. directory) by comparing the status bar text string to an expected value. This is the only mechanism that distinguishes the two execution paths.

---

## 4. Signal Processing Pipeline

The core analysis is performed identically in three separate places in the script (single file, directory Excel export, directory PDF export). The steps are:

### Step 1 — Load raw signal

```python
drill_amp = np.array(data["profile"]["drill"])
resolution = data["header"]["resolutionFeed"]
depth = np.arange(0, len(drill_amp)) / resolution  # depth axis in mm
```

### Step 2 — Threshold filtering

Low values at the start of the signal (before the drill bit enters the wood) are removed by filtering out samples below 1% of the signal average:

```python
threshold1 = 0.01 * np.average(drill_amp)
filtered_signal = drill_amp[drill_amp > threshold1]
threshold_cut = np.min(np.where(drill_amp > threshold1)) / resolution
```

### Step 3 — Variance-based trimming

The filtered signal is further trimmed by scanning 25-sample windows. Windows with a variance below `0.01` (near-constant signal, indicating the lead-in or lead-out of the drill outside the wood) are skipped one sample at a time. Once a high-variance window is found, all 25 samples are accepted and the index advances by 25.

```python
while i < len(filtered_signal) - 25:
    window = filtered_signal[i:i+25]
    if np.var(window) > 0.01:
        pile_signal.extend(window)
        i += 25
    else:
        i += 1
```

The resulting `pile_signal` represents only the wood cross-section.

### Step 4 — Overlap position (used for plotting only)

For display purposes, the script finds the position in the original signal where variance first becomes significant, so the original signal can be plotted shifted to align with the trimmed signal:

```python
for p in range(len(drill_amp) - 25):
    window = drill_amp[p:p+25]
    if np.var(window) > 0.01:
        overlap_position = p / resolution
        break
depth_overlap_position = max(threshold_cut, overlap_position)
```

### Step 5 — Diameter estimation

The diameter is calculated directly from the length of the trimmed pile signal:

```python
diameter = len(pile_signal) / resolution  # mm
```

### Step 6 — Moving average

A symmetric 100-sample moving average (50 samples each side) is computed over the pile signal. At the edges, the window is shortened and the count adjusted accordingly to avoid bias:

```python
for N in range(len(pile_signal)):
    i = max(0, N - 50)
    j = min(len(pile_signal), N + 50)
    k = j - i
    movav[N] = sum(pile_signal[i:j]) / k
```

### Step 7 — Annual ring counting

The pile signal is first smoothed using a Savitzky-Golay filter (window length 15, polynomial order 11), then peaks are detected with a minimum distance of 10% of the resolution:

```python
pile_signal1 = savgol_filter(pile_signal, 15, 11)
rings = round(len(find_peaks(pile_signal1, distance=0.1 * resolution)[0]) / 2, 0)
```

The peak count is divided by 2 because the drill passes through the pith and each ring is crossed twice (once entering, once exiting).

### Step 8 — Growth rate estimation

The growth rate is estimated using only the outer 75% zone on each side (from the bark inward to 75% of the radius) to avoid the more compressed rings near the pith:

```python
rings_075_left  = peaks in pile_signal[0 : 0.75 * (diameter/2) * resolution]
rings_075_right = peaks in pile_signal[1.25 * (diameter/2) * resolution : diameter * resolution]

growth_rate = average(
    0.75 * (diameter / 2) / rings_075_left,
    0.75 * (diameter / 2) / rings_075_right
)  # mm per ring
```

### Step 9 — Sapwood width estimation

Sapwood width is estimated using an empirical biological regression formula:

$$\text{sapwood} = \frac{37.17 \cdot r_g^{0.95}}{1 + 5.58 \cdot e^{-0.054 \cdot \text{rings}}}$$

where $r_g$ is the growth rate in mm/ring and `rings` is the total estimated ring count.

```python
sapwood = round((37.17 * growth_rate ** 0.95) / (1 + 5.58 * np.exp(-0.054 * rings)), 0)
```

### Step 10 — Soft shell detection

The soft shell boundary is identified using an Incremental One-directional Moving Average (IOMA) computed separately for the left half (pith → bark) and right half (pith → bark):

```python
# Left side: iterate inward from pith, accumulate single values
for i in reversed(movav[:int(pith * resolution)]):
    array_movav.append(i)
    ioma_left.append(sum(array_movav) / len(array_movav))
    array_movav = []

# Right side: iterate outward from pith
for i in movav[int(pith * resolution):]:
    array_movav.append(i)
    ioma_right.append(sum(array_movav) / len(array_movav))
```

The soft shell boundary is where the moving average falls below 40% of the maximum IOMA value:

```python
soft_shell_left  = np.min(np.where(movav > 0.4 * np.max(ioma_left)))  / resolution
soft_shell_right = np.max(np.where(movav > 0.4 * np.max(ioma_right))) / resolution
```

The reported soft shell thicknesses are:
- **Left side:** `soft_shell_left` (mm from the left entry point)
- **Right side:** `diameter - soft_shell_right` (mm from the right entry point)

---

## 5. Visualization

Each measurement produces two matplotlib subplots rendered side-by-side:

### 5.1 Linear drilling signal plot (left panel)

Shows the full drilling profile with annotated structural boundaries:

| Element | Colour | Description |
|---|---|---|
| Original signal | Grey dotted | Raw `drill_amp` shifted to align with trimmed signal |
| Trimmed signal | Blue solid | `pile_signal` after cut-off |
| Moving average | Red solid | 100-sample symmetric moving average |
| Center line | Purple dashed | `diameter / 2` |
| Diameter markers | Black dashed | Start (0) and end (`diameter`) of pile signal |
| Sapwood markers | Orange dashed | Left (`sapwood`) and right (`diameter - sapwood`) sapwood boundary |
| Soft shell markers | Green dashed | `soft_shell_left` and `soft_shell_right` positions |
| Background spans | Pink/light green/dark green | Soft shell zone, sound cross-section, estimated heartwood |

### 5.2 Polar cross-section plot (right panel)

A polar bar chart that overlays concentric zones on a circular representation of the pole cross-section:

| Zone | Colour |
|---|---|
| Soft shell (outer) | Pink `(1, 0.7, 0.7)` |
| Sound cross-section | Light green `(0.753, 1, 0.737)` |
| Estimated heartwood | Dark green `(0.569, 0.71, 0.51)` |

Text annotations show the soft shell thickness, pile radius at the cardinal positions around the circle.

---

## 6. Measurement Pairing

When processing a directory, the optional pairing feature groups measurements that come from the same pole (drilled from two opposite sides). Pairing is based on filename similarity using `difflib.SequenceMatcher` with a threshold of 0.8:

```python
def pair_similar_names(names, threshold=0.8):
    for each unmatched name:
        find the first other name with similarity >= threshold
        add as a pair
```

For each pair, the averaged outputs are calculated:

| Output | Calculation |
|---|---|
| Average diameter | `(diameter_1 + diameter_2) / 2` |
| Average sapwood width | `(sapwood_1 + sapwood_2) / 2` |
| Average soft shell | `(avg_ss_left + avg_ss_right) / 2` |

Paired outputs are saved to `Output_grouped_RPD_files.xlsx` and `Output_grouped_RPD_files.PDF`. The PDF shows a combined polar plot with both measurements plotted in opposing quadrants (NW/SE for measurement 1, NE/SW for measurement 2).

---

## 7. Output Files

| File | Content |
|---|---|
| `Output.xlsx` | One row per measurement: ID, date, diameter, ring count, sapwood width, soft shell left, soft shell right |
| `Output.pdf` | One page per measurement with the linear signal plot and polar cross-section plot |
| `Output_grouped_RPD_files.xlsx` | One row per pair: IDs, averaged diameter, sapwood and soft shell |
| `Output_grouped_RPD_files.PDF` | One page per pair: combined polar cross-section plot |

---

## 8. Known Issues and Observations

The following issues were identified in the original code and should be addressed in the refactoring:

### 8.1 Duplicated signal processing pipeline
The entire signal processing pipeline (Steps 2–10) is copy-pasted verbatim in three separate locations: the single-file path, the batch Excel export loop, and the batch PDF export loop. Any bug fix or change must be applied in all three places.

### 8.2 Control flow via status bar text
The `OnClickb3` event handler determines whether to run in single-file or directory mode by comparing the status bar label string to hardcoded expected values. This is fragile and breaks if the status bar text changes for any reason.

### 8.3 No separation of concerns
Data loading, signal processing, numerical calculations, plot generation, and file I/O are all interleaved within a single event handler method.

### 8.4 Potential division-by-zero
If `rings_075_left` or `rings_075_right` is zero (no peaks found in that half), the growth rate calculation crashes with a `ZeroDivisionError`. This can occur on low-quality or very short signals.

### 8.5 Bug in IOMA construction
In the `ioma_right` loop, `ioma_left` is reversed on every iteration (`ioma_left = list(reversed(ioma_left))`). This is almost certainly unintentional and means `ioma_left` is re-reversed repeatedly, resulting in unpredictable ordering depending on the number of iterations.

### 8.6 No logging or error reporting
There is no structured logging. Processing failures are either swallowed silently or shown as wxPython error dialogs with minimal context.

### 8.7 No tests
There are no unit tests or integration tests for the signal processing algorithm, the empirical formula, or the pairing logic.

### 8.8 IOMA logic produces single-element averages
In the IOMA loop, `array_movav` is reset to `[]` after every single appended value, making each `ioma` value simply equal to the corresponding `movav` value. The IOMA therefore does not actually accumulate — it is equivalent to `movav` directly.
