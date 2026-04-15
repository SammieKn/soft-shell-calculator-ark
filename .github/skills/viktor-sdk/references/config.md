# VIKTOR App Configuration Reference

## viktor.config.toml

Placed at the app root alongside `app.py`. Written in TOML.

```toml
# Required
app_type = 'editor'        # 'editor' | 'simple' | 'tree'

# Strongly recommended
python_version = '3.12'    # '3.10' | '3.11' | '3.12' | '3.13' | '3.14'
registered_name = 'my-app' # name used when publishing

# Optional
assets_path = 'assets'     # relative path to folder with static assets (images etc.)
# packages = ["libgdal-dev", "tesseract-ocr"]  # Linux apt-get system packages ONLY
# welcome_text = 'welcome.md'                  # tree apps only
# enable_privileged_api = true                 # bypass user access restrictions
```

### app_type options

| Value | Description |
|-------|-------------|
| `'editor'` | Single entity per user session; each user works in isolation |
| `'simple'` | Single entity type; entities are shared among users |
| `'tree'` | Multiple entity types arranged in a hierarchy; entities shared |

Most calculation apps use `'editor'`.

### packages

Only for Linux system-level dependencies (e.g., image processing libs, OCR engines).
**Do not list Python packages here** — those go in `requirements.txt`.

---

## requirements.txt

Standard pip-format file. Must include `viktor` pinned to the version you develop against.

```
viktor==14.29.0
numpy>=1.26.0
pandas>=3.0.0
scipy>=1.11.0
matplotlib>=3.10.0
plotly>=5.0.0
openpyxl>=3.1.0
```

### Notes

- Always pin `viktor` to an exact version to avoid surprise breakage on deployment.
- Other packages can use `>=` version constraints.
- Python packages that live as local folders inside the app root (e.g., an internal
  library package) do **not** need to be listed here — Python finds them automatically
  because the app root is on the path.
- The `viktor-cli` tool respects this file when building the virtual environment
  for local development.

---

## Local development commands

```bash
# First-time setup of the local VIKTOR environment
viktor-cli clean-start

# Start the app connected to the VIKTOR platform
viktor-cli start

# Publish the app to the platform
viktor-cli publish --registered-name my-app
```

`clean-start` rebuilds the virtual environment from scratch and reconnects.
`start` reconnects using the existing environment (faster).
