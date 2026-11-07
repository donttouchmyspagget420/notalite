import re
import textwrap

from src.enums import PdfMetric


def build_pdf(title, content):
    raw_lines = [f"# {title}", ""] + (content or "").splitlines()
    lines = []

    for raw in raw_lines:
        line = raw.rstrip()

        if line.strip().startswith("```"):
            continue

        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "- ", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)
        line = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", line)
        line = line.replace("**", "").replace("__", "").replace("`", "")
        line = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", line)

        if not line.strip():
            lines.append("")
            continue

        wrapped = textwrap.wrap(
            line, width=PdfMetric.WRAP_WIDTH, break_long_words=True
        )
        lines.extend(wrapped or [""])

    lines = lines or [title]
    pages = [
        lines[index:index + PdfMetric.MAX_LINES]
        for index in range(0, len(lines), PdfMetric.MAX_LINES)
    ]
    pages = pages or [[""]]

    kids = [f"{6 + index * 2} 0 R" for index in range(len(pages))]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            b"<< /Type /Pages /Kids ["
            + " ".join(kids).encode("ascii")
            + b"] /Count "
            + str(len(pages)).encode("ascii")
            + b" >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]

    for index, page_lines in enumerate(pages):
        content_number = 5 + index * 2

        stream = bytearray()
        stream += b"BT\n"
        stream += f"/F1 {PdfMetric.FONT_SIZE} Tf\n".encode("ascii")
        stream += f"{PdfMetric.MARGIN} {PdfMetric.TEXT_TOP} Td\n".encode("ascii")
        stream += f"{PdfMetric.LEADING} TL\n".encode("ascii")

        for line in page_lines:
            data = line.encode("cp1252", "replace")
            data = data.replace(b"\\", b"\\\\")
            data = data.replace(b"(", b"\\(")
            data = data.replace(b")", b"\\)")
            stream += b"(" + data + b") Tj\nT*\n"

        stream += b"ET"

        objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + bytes(stream)
            + b"\nendstream"
        )
        objects.append(
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
                + str(PdfMetric.PAGE_WIDTH).encode("ascii")
                + b" "
                + str(PdfMetric.PAGE_HEIGHT).encode("ascii")
                + b"] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents "
                + str(content_number).encode("ascii")
                + b" 0 R >>"
            )
        )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (len(objects) + 1)

    for index, obj in enumerate(objects, start=1):
        offsets[index] = len(pdf)
        pdf += f"{index} 0 obj\n".encode("ascii")
        pdf += obj
        pdf += b"\nendobj\n"

    xref_position = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"

    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")

    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF\n"
    ).encode("ascii")

    return bytes(pdf)
