from __future__ import annotations


def _to_float(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def comma(v):
    n = _to_float(v)
    return "-" if n is None else f"{n:,.0f}"


def comma1(v):
    n = _to_float(v)
    return "-" if n is None else f"{n:,.1f}"


def comma2(v):
    n = _to_float(v)
    return "-" if n is None else f"{n:,.2f}"


def pct(v):
    n = _to_float(v)
    return "-" if n is None else f"{n:.0f}%"


def pct1(v):
    n = _to_float(v)
    return "-" if n is None else f"{n:.1f}%"


def default_dash(v):
    return "-" if v is None or v == "" else v


def colorize_negative(v):
    n = _to_float(v)
    if n is None:
        return "-"
    text = f"{n:,.2f}" if abs(n) < 100 and n % 1 else f"{n:,.0f}"
    return f"<span style='color:red'>{text}</span>" if n < 0 else text


FILTERS = {
    "comma": comma,
    "comma1": comma1,
    "comma2": comma2,
    "pct": pct,
    "pct1": pct1,
    "default_dash": default_dash,
    "colorize_negative": colorize_negative,
}
