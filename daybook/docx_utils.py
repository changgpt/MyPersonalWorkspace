"""Convert an uploaded .docx file to Markdown.

This is a pragmatic subset, not a full converter: headings, bold/italic
runs, bullet/numbered lists, and plain paragraphs. Tables and images are
not handled -- if you need those, paste the text in manually instead.
"""
import io

import docx


def _runs_to_markdown(paragraph):
    parts = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        if run.bold and run.italic:
            text = f"***{text}***"
        elif run.bold:
            text = f"**{text}**"
        elif run.italic:
            text = f"*{text}*"
        parts.append(text)
    return "".join(parts) or paragraph.text


def _heading_level(style_name):
    if style_name and style_name.startswith("Heading "):
        suffix = style_name.rsplit(" ", 1)[-1]
        if suffix.isdigit():
            return min(int(suffix), 6)
    return None


def _is_list_item(style_name):
    return bool(style_name) and "List" in style_name


def docx_bytes_to_markdown(file_bytes):
    document = docx.Document(io.BytesIO(file_bytes))
    lines = []
    for paragraph in document.paragraphs:
        text = _runs_to_markdown(paragraph).strip()
        if not text:
            lines.append("")
            continue
        style_name = paragraph.style.name if paragraph.style else ""
        level = _heading_level(style_name)
        if level:
            lines.append(f"{'#' * level} {text}")
        elif _is_list_item(style_name):
            lines.append(f"- {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines).strip() + "\n"
