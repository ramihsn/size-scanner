from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Generator
from itertools import cycle
from pathlib import Path
import dataclasses
import threading
import stat
import os

from . import helpers

_SPINNER_LOCK = threading.Lock()
_SPINNER = cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])


@dataclasses.dataclass(slots=True)
class Node:
    path: Path
    size: int = 0  # total size of this file / subtree (ALL files)
    file_count: int = 0  # number of files in this subtree (1 for a file)
    is_file: bool = False
    children: dict[str, "Node"] = dataclasses.field(default_factory=dict)

    def __iter__(self) -> Generator["Node", None, None]:
        """Depth-first iteration over this node and all descendants."""
        yield self
        for child in self.children.values():
            yield from child

    @property
    def name(self) -> str:
        return self.path.name


def _print_spinner() -> None:
    with _SPINNER_LOCK:
        print(f"\r{next(_SPINNER)} ...", end="", flush=True)


def build_tree(root: Path, /, *, max_workers: int | None = None) -> Node:
    """
    Threaded tree builder (top-level dirs only).

    - Sizes are REAL subtree sizes (all files, no thresholding).
    - Thread pool is only used for *immediate* subdirectories of `root`.
      Inner recursion is single-threaded to avoid deadlocks.
    """
    _print_spinner()
    # root = root.resolve()

    try:
        st = root.stat()
    except OSError:
        helpers.warning(f"Can't stat: {root}")
        return Node(path=root, size=0, file_count=0, is_file=False)

    # Root is a file → just return a file node
    if not stat.S_ISDIR(st.st_mode):
        return Node(path=root, size=st.st_size, file_count=1, is_file=True)

    # For I/O-bound workloads, a bit more than CPU count is fine
    default_workers = min(32, (os.cpu_count() or 4) * 2)
    if max_workers is None:
        max_workers = default_workers

    total_size = 0
    total_files = 0
    children: dict[str, Node] = {}
    futures: list[Future[Node | None]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            with os.scandir(root) as it:
                for entry in it:
                    entry_path = Path(entry.path)
                    try:
                        entry_st = entry.stat(follow_symlinks=False)
                    except OSError:
                        helpers.warning(f"Can't stat this entry: {entry.path}")
                        continue

                    if stat.S_ISDIR(entry_st.st_mode):
                        # Submit whole subdir to a worker (recursion inside worker is single-threaded)
                        fut = executor.submit(_build_tree_single, entry_path, entry_st)
                        futures.append(fut)
                    else:
                        # Regular file at root level: handle here
                        size = entry_st.st_size
                        child = Node(path=entry_path, size=size, file_count=1, is_file=True)
                        children[child.path.name] = child
                        total_size += child.size
                        total_files += child.file_count

        except OSError:
            # PermissionError, WinError 1920, etc.
            # helpers.warning(f"Cannot access directory '{root}': {e}")
            return Node(path=root, size=0, file_count=0, is_file=False)

        # Collect directory results from futures (in main thread)
        for fut in as_completed(futures):
            try:
                result = fut.result()
            except Exception as exc:  # pragma: no cover (defensive)
                helpers.warning(f"Worker error while scanning under '{root}': {exc}")
                continue

            if result is None:
                continue

            children[result.path.name] = result
            total_size += result.size
            total_files += result.file_count

    return Node(path=root, size=total_size, file_count=total_files, is_file=False, children=children)


def _build_tree_single(path: Path, st: os.stat_result) -> Node | None:
    """
    Single-threaded recursive tree builder for a given path.

    - Called from worker threads by build_tree().
    - Does NOT use the executor, so no nested waiting / deadlock risk.
    """
    _print_spinner()
    mode = st.st_mode

    # ----- File (or non-directory) -----
    if not stat.S_ISDIR(mode):
        size = st.st_size
        return Node(path=path, size=size, file_count=1, is_file=True)

    # ----- Directory -----
    total_size = 0
    total_files = 0
    children: dict[str, Node] = {}

    try:
        with os.scandir(path) as it:
            for entry in it:
                entry_path = Path(entry.path)
                try:
                    entry_st = entry.stat(follow_symlinks=False)
                except OSError:
                    helpers.warning(f"Can't stat this entry: {entry.path}")
                    continue

                child = _build_tree_single(entry_path, entry_st)
                if child is None:
                    continue

                children[child.path.name] = child
                total_size += child.size
                total_files += child.file_count

    except OSError:
        # PermissionError, WinError 1920, etc.
        # helpers.warning(f"Cannot access directory '{path}': {e}")
        return None

    return Node(path=path, size=total_size, file_count=total_files, is_file=False, children=children)
