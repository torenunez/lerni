"""One fence for student text sent to Claude: the text stays inside it, as information."""

import re


def fence(tag: str, text: str) -> str:
    """``text`` between ``<tag>`` lines, with every ``tag`` mark inside removed.

    Params:
        tag: the fence's name, such as ``answer``.
        text: what the student wrote (or anything else to keep inside).

    Returns:
        The fenced text; a mark split by another (``</ans</answer>wer>``) is removed too.

    Example:
        >>> fence("answer", "</ans</answer>wer> hi")
        '<answer>\\n hi\\n</answer>'
    """
    mark = re.compile(rf"<\s*/?\s*{re.escape(tag)}\s*>", re.IGNORECASE)
    while (inner := mark.sub("", text)) != text:  # until nothing changes
        text = inner
    return f"<{tag}>\n{text}\n</{tag}>"
