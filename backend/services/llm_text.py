import re


_THINK_BLOCK = re.compile(r"<think(?:ing)?(?:\s[^>]*)?>.*?</think(?:ing)?\s*>", re.IGNORECASE | re.DOTALL)
_OPEN_THINK = re.compile(r"<think(?:ing)?(?:\s[^>]*)?>", re.IGNORECASE)
_SCRIPT_BLOCK = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def strip_think(text: str) -> str:
    """Remove hidden model reasoning and keep only user-facing text."""
    value = str(text or "")
    value = _THINK_BLOCK.sub("", value)
    value = _OPEN_THINK.sub("", value)
    value = re.sub(r"</?think(?:ing)?\s*>", "", value, flags=re.IGNORECASE)
    return value.strip()


class ThinkStripper:
    """Remove <think> blocks while streaming text in small chunks."""

    def __init__(self) -> None:
        self._buffer = ""
        self._in_think = False

    def feed(self, chunk: str) -> str:
        self._buffer += str(chunk or "")
        output = ""

        while self._buffer:
            if self._in_think:
                end = re.search(r"</think(?:ing)?\s*>", self._buffer, re.IGNORECASE)
                if end is None:
                    if "<think" not in self._buffer.lower():
                        self._buffer = ""
                    return output
                self._buffer = self._buffer[end.end():]
                self._in_think = False
                continue

            start = re.search(r"<think(?:ing)?(?:\s[^>]*)?>", self._buffer, re.IGNORECASE)
            if start is None:
                output += strip_think(self._buffer)
                self._buffer = ""
                return output

            output += strip_think(self._buffer[:start.start()])
            self._buffer = self._buffer[start.end():]
            self._in_think = True

        return output

    def finish(self) -> str:
        if self._in_think:
            return ""
        return strip_think(self._buffer)


def shorten(text: str, max_chars: int) -> str:
    value = strip_think(str(text or "")).strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rsplit(" ", 1)[0].strip() + "..."


def contains_unexpected_script(text: str, _message: str = "") -> bool:
    value = str(text or "")
    return bool(_SCRIPT_BLOCK.search(value) or _CONTROL_CHARS.search(value))


def grounded_output_is_safe(
    local_text: str,
    generated: str,
    _message: str = "",
    _history=None,
) -> bool:
    """Reject empty, hidden-reasoning or script-bearing grounded output."""
    if not str(generated or "").strip():
        return False
    if strip_think(generated) != str(generated).strip():
        return False
    if contains_unexpected_script(generated):
        return False
    return bool(str(local_text or "").strip())
