from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from . import helpers, core


class Args(Namespace):
    root: Path
    reverse: bool
    threshold: int  # min size in bytes


def _parse_args() -> Args:
    parser = ArgumentParser(description="Fast tree-size viewer (cross-platform).")
    parser.set_defaults(reverse=False)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    # fmt: off
    parser.add_argument("-t", "--threshold", default=0, type=helpers.parse_size,
                        help="Minimum size threshold (e.g. 10M, 500K). Default: 0")  # fmt: on

    sort = parser.add_mutually_exclusive_group()
    sort.add_argument("-a", "--asc", dest="reverse", action="store_false", help="Ascending order")
    sort.add_argument("-d", "--desc", dest="reverse", action="store_true", help="Descending order")

    args = parser.parse_args(namespace=Args())
    if not args.root.exists():
        parser.error(f"Cannot find path '{args.root.absolute()}' because it does not exist.")
    return args


def _print_tree(node: core.Node, threshold: int, /, *, reverse: bool = False, indent: int = 0) -> None:
    for node in sorted(node, key=lambda x: x.size, reverse=reverse):
        if node.size >= threshold:
            _type = "F" if node.is_file else "D"
            print(f"[{node.file_count:<7,}][{_type}]", helpers.format_size(node.size), node.path)


def main() -> None:
    args = _parse_args()

    try:
        print(f"Building tree for {args.root.resolve()}...")
        results = core.build_tree(args.root)
        sort_dir = "desc" if args.reverse else "asc"
        print(f"\rPrinting tree in {sort_dir} order...")
        _print_tree(results, args.threshold, reverse=args.reverse)
    except KeyboardInterrupt:
        helpers.warning("Keyboard interrupt, aborting.")
        return
