"""Extract guide prose without treating frontmatter or fenced samples as headings."""

from __future__ import annotations

import re


def markdown_prose(text: str) -> tuple[str, bool]:
    text = re.sub(r"\A---\n.*?\n---(?:\n|$)", "", text, count=1, flags=re.DOTALL)
    output: list[str] = []
    fence = ""
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        if fence:
            closing = re.fullmatch(r" {0,3}([`~]+)[ \t]*", bare)
            if closing and set(closing[1]) == {fence[0]} and len(closing[1]) >= len(fence):
                fence = ""
            continue
        opening = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", bare)
        if opening and not (opening[1][0] == "`" and "`" in opening[2]):
            fence = opening[1]
        else:
            output.append(line)
    return "".join(output), bool(fence)
