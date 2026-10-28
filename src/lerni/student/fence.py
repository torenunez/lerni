"""One fence for student text sent to Claude: the text stays inside it, as information."""

import re


def fence(tag: str, text: str, *others: str) -> str:
    """``text`` between ``<tag>`` lines, with every mark of ``tag`` (and ``others``) inside removed.

    Params:
        tag: the fence's name, such as ``answer``.
        text: what the student wrote (or anything else to keep inside).
        others: the other fences in the same prompt, so text can't fake one of them.

    Returns:
        The fenced text; a mark split by another (``</ans</answer>wer>``) is removed too.

    Example:
        >>> fence("answer", "</ans</answer>wer> hi")
        '<answer>\\n hi\\n</answer>'
    """
    names = "|".join(re.escape(t) for t in (tag, *others))
    mark = re.compile(rf"<\s*/?\s*(?:{names})\b[^>]*>", re.IGNORECASE)  # with anything inside
    while (inner := mark.sub("", text)) != text:  # until nothing changes
        text = inner
    return f"<{tag}>\n{text}\n</{tag}>"
