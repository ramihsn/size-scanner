def parse_size(text: str) -> int:
    """
    Parse size like: 123, 10K, 20M, 3G (case-insensitive) into bytes.
    """
    text = text.strip().upper()
    if not text:
        return 0

    multipliers = {
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }

    if text[-1] in multipliers:
        num = float(text[:-1])
        return int(num * multipliers[text[-1]])
    return int(text)


def format_size(num_bytes: int) -> str | None:
    """
    Human-readable size (B, KiB, MiB, GiB, TiB).
    """
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:<5.1f} {unit:>3}"
        size /= 1024
    return f"{size:<5.1f} {unit:>3}"


def warning(message: str) -> None:
    """
    Print a warning message.
    """
    print(f"\033[93m{message}\033[0m")
