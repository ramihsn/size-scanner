# size-scanner

[![CI](https://github.com/ramihsn/size-scanner/actions/workflows/ci.yml/badge.svg)](https://github.com/ramihsn/size-scanner/actions/workflows/ci.yml)

A small, fast, cross-platform CLI tool to scan a directory tree and show
sizes of files and folders, with optional size threshold filtering and sorting.

Under the hood it uses:

- `os.scandir()` + `stat()` for efficient filesystem traversal
- A lightweight `Node` tree structure
- A top-level `ThreadPoolExecutor` to parallelize scanning of immediate subdirectories
- A simple spinner to show progress on large trees

Tested on:

- Python 3.10, 3.11, 3.12, 3.13, 3.14
- Linux, macOS, Windows

---

## Quick download (prebuilt binaries)

You don’t need Python installed to run `size-scanner`. Just grab a binary from
the latest GitHub Release:

- **Windows**  
  - [`size-scanner-windows.zip`](https://github.com/ramihsn/size-scanner/releases/latest/download/size-scanner-windows.zip)
  - [`size-scanner-windows-x86_64.zip`](https://github.com/ramihsn/size-scanner/releases/latest/download/size-scanner-windows-x86_64.zip)

- **Linux**  
  - [`size-scanner-linux.tar.gz`](https://github.com/ramihsn/size-scanner/releases/latest/download/size-scanner-linux.tar.gz)
  - [`size-scanner-linux-x86_64.tar.gz`](https://github.com/ramihsn/size-scanner/releases/latest/download/size-scanner-linux-x86_64.tar.gz)

- **macOS**  
  - [`size-scanner-macos.tar.gz`](https://github.com/ramihsn/size-scanner/releases/latest/download/size-scanner-macos.tar.gz)
  - [`size-scanner-macos-x86_64.tar.gz`](https://github.com/ramihsn/size-scanner/releases/latest/download/size-scanner-macos-x86_64.tar.gz)

Then:

```bash
# Linux / macOS
tar -xzf size-scanner-*-x86_64.tar.gz
./size-scanner -h
````

```powershell
# Windows (PowerShell)
Expand-Archive .\size-scanner-windows-x86_64.zip
.\size-scanner.exe -h
```

You can also browse all releases here:
[https://github.com/ramihsn/size-scanner/releases](https://github.com/ramihsn/size-scanner/releases)

---

## Installation (from source)

### Using `uv` (recommended for development)

Clone the repo:

```bash
git clone https://github.com/ramihsn/size-scanner.git
cd size-scanner
```

Run directly with `uv`:

```bash
uv run size-scanner --help
```

Or install as a tool (editable):

```bash
uv tool install -e .
size-scanner --help
```

### Using plain `pip`

Build and install from source:

```bash
python -m pip install --upgrade pip build
python -m build
python -m pip install dist/*.whl
size-scanner --help
```

---

## Usage

Basic syntax:

```bash
size-scanner [ROOT] [-t THRESHOLD] [-a | -d]
```

**Positional arguments**

* `ROOT`
  Optional. Root path to scan. Defaults to the current working directory.

**Options**

* `-t`, `--threshold`
  Minimum size to **show** (files/dirs smaller than this are hidden in the output).
  Accepts plain bytes or IEC suffixes (powers of 1024):

  * `10K` → 10 × 1024 bytes
  * `20M` → 20 × 1024² bytes
  * `3G` → 3 × 1024³ bytes
  * `1T` → 1 × 1024⁴ bytes

  Example: `-t 100M`

* `-a`, `--asc`
  Sort ascending by size (default).

* `-d`, `--desc`
  Sort descending by size.

---

## Examples

### Scan the current directory

```bash
size-scanner
```

### Scan a specific directory

```bash
size-scanner /path/to/project
```

### Show only items ≥ 500 MB, largest first

```bash
size-scanner . -t 500M -d
```

Example output:

```text
Building tree for /home/user/projects...
Printing tree in desc order...
[     123][D] 12.3 GiB /home/user/projects/big_dataset
[      45][D]  4.7 GiB /home/user/projects/logs
[       1][F]  3.2 GiB /home/user/projects/big_file.bin
...
```

Legend:

* First column: number of files in the subtree
* `[D]` = directory, `[F]` = file
* Size is **total aggregate size** of the subtree (for directories) or the file itself.

---

## How it works (short version)

### Data model

`core.Node` represents a file or directory:

```python
@dataclasses.dataclass(slots=True)
class Node:
    path: Path
    size: int          # total size of this file / subtree
    file_count: int    # number of files in this subtree
    is_file: bool
    children: dict[str, "Node"]
```

### Tree building

`core.build_tree(root)`:

* Uses a `ThreadPoolExecutor` to process **immediate subdirectories** of `root` in parallel.
* Each worker calls a single-threaded `_build_tree_single()` for its subtree.
* This keeps the threading model simple:

  * No nested executors.
  * No deadlocks / waiting on futures from inside workers.
* Sizes are **always real subtree sizes** (no thresholding at build time).

### CLI flow

* Parse CLI arguments (`root`, `threshold`, `--asc` / `--desc`).

* Build the full tree once.

* Flatten via iteration over the `Node` tree:

  ```python
  sorted(node, key=lambda x: x.size, reverse=reverse)
  ```

* Apply the `threshold` only at **print time**.

---

## Development

Install dev dependencies with `uv`:

```bash
uv sync --group dev
```

Then you can use tools like `ipython` from the environment:

```bash
uv run ipython
```

Run a local smoke test:

```bash
uv run size-scanner . -t 10M -d
```

Linting / formatting / type checking (if configured in `pyproject.toml`):

```bash
uv run --group dev black src
uv run --group dev flake8 src
uv run --group dev mypy src
```

---

## CI

GitHub Actions CI is configured to:

* Run on Linux, Windows, and macOS
* Use Python 3.10–3.14
* Build the package (`sdist` + wheel) with `uv build`
* Install the built wheel
* Run `size-scanner --help` as a smoke test

See [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) for details.

There is also a `release.yml` workflow that:

* Triggers on tags matching `v*.*.*` (e.g. `v0.1.0`)
* Builds standalone binaries for Linux, macOS, and Windows using PyInstaller
* Uploads them as assets to the GitHub Release
* Lets you download the latest binaries via the links in this README

---

## Future ideas

* Exclude patterns (e.g. `.git`, `.venv`, `node_modules`) via CLI flags
* Tree-style output (`├──`, `└──`) with indentation
* JSON output mode for scripting / integration
* “Top N heaviest paths” view
* Optional colorized output (sizes / types)
