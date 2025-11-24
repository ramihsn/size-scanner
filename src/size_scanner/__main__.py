try:
    # Normal installed/frozen case: import by package name
    from size_scanner import main  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    # Fallback when running from the source tree with `python -m size_scanner`
    from . import main  # type: ignore[no-redef]


if __name__ == "__main__":
    main()
