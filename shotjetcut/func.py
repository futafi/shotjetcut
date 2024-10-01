def aspect_ratio(width: int, height: int) -> tuple[int, int]:
    if height == 0:
        return (0, 0)

    def gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    c = gcd(width, height)
    return width // c, height // c


def to_timecode(secs: float) -> str:
    sign = ""
    if secs < 0:
        sign = "-"
        secs = -secs

    _m, _s = divmod(secs, 60)
    _h, _m = divmod(_m, 60)
    s, m, h = float(_s), int(_m), int(_h)

    return f"{sign}{h:02d}:{m:02d}:{s:06.3f}"


def parse_timecode(timecode: str) -> float:
    sign = -1 if timecode[0] == '-' else 1
    h, m, s = map(float, timecode.strip('-').split(':'))
    return sign * (h * 3600 + m * 60 + s)
