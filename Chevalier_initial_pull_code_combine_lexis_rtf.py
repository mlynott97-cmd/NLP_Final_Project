from __future__ import annotations

from pathlib import Path
import argparse
import csv
import re
import shutil
import subprocess
import tempfile

DATE_PATTERN = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s+\d{4}\b"
)
BODY_PATTERN = re.compile(r"^Body(?:_\d+)?(?:Body)?$")
PICTURE_PATTERN = re.compile(r"pict\d+\.jpg", flags=re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://\S+")


def convert_rtf_to_text(rtf_path: Path) -> str:
    """Convert an RTF export to plain text on macOS, Linux, or Windows."""
    if shutil.which("textutil"):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            txt_path = Path(tmp.name)
        try:
            subprocess.run(
                ["textutil", "-convert", "txt", "-output", str(txt_path), str(rtf_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return txt_path.read_text(encoding="utf-8", errors="ignore")
        finally:
            txt_path.unlink(missing_ok=True)

    if shutil.which("unrtf"):
        result = subprocess.run(
            ["unrtf", "--text", str(rtf_path)],
            check=True,
            capture_output=True,
        )
        return result.stdout.decode("utf-8", errors="ignore")

    raise RuntimeError(
        "No RTF converter found. On macOS, textutil is built in. "
        "On Linux, install unrtf."
    )


def clean_line(line: str) -> str:
    line = PICTURE_PATTERN.sub("", line)
    line = line.replace("\xa0", " ")
    return re.sub(r"\s+", " ", line).strip()


def parse_lexis_text(text: str, source_file: str) -> list[dict[str, str]]:
    lines = [clean_line(line) for line in text.splitlines()]
    articles: list[dict[str, str]] = []

    for body_index, line in enumerate(lines):
        # Lexis may render the label as Body, Body_0, or Body_0Body.
        if not BODY_PATTERN.fullmatch(line):
            continue

        date_index = None
        for i in range(body_index - 1, max(-1, body_index - 35), -1):
            if DATE_PATTERN.match(lines[i]):
                date_index = i
                break
        if date_index is None:
            continue

        date_match = DATE_PATTERN.match(lines[date_index])
        if not date_match:
            continue
        date_of_publication = date_match.group(0)

        # Work backward from the date. The closest useful line is normally outlet;
        # the next useful line is normally title. Skip URLs and Lexis category labels.
        candidates: list[str] = []
        for i in range(date_index - 1, max(-1, date_index - 25), -1):
            value = lines[i]
            if not value:
                continue
            if URL_PATTERN.fullmatch(value) or value.startswith("http"):
                continue
            if value in {"WebNews - Academic", "WebNews - English", "WebNews - Spanish"}:
                continue
            if value.startswith("Page of") or value.startswith("Bookmark_"):
                continue
            candidates.append(value)
            if len(candidates) == 2:
                break

        if len(candidates) < 2:
            continue

        media_outlet = candidates[0]
        title = candidates[1]

        body_lines: list[str] = []
        i = body_index + 1
        while i < len(lines):
            value = lines[i]
            if value.startswith("Classification") or value.startswith("End of Document"):
                break
            if value and not value.startswith("###"):
                body_lines.append(value)
            i += 1

        body = re.sub(r"\s+", " ", " ".join(body_lines)).strip()
        articles.append(
            {
                "date_of_publication": date_of_publication,
                "media_outlet": media_outlet,
                "title": title,
                "body": body,
                "source_file": source_file,
            }
        )

    return articles


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Combine LexisNexis RTF exports into one CSV file."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="RTF files to combine")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("lexis_articles_624.csv")
    )
    parser.add_argument(
        "--expected-rows", type=int, default=None,
        help="Fail if the parsed row count does not match this number."
    )
    args = parser.parse_args()

    all_articles: list[dict[str, str]] = []
    for rtf_path in args.inputs:
        text = convert_rtf_to_text(rtf_path)
        parsed = parse_lexis_text(text, rtf_path.name)
        print(f"{rtf_path.name}: {len(parsed)} articles")
        all_articles.extend(parsed)

    # The two exports are expected to contain distinct sets. Keep all rows,
    # because the requested total is the sum of the export counts.
    if args.expected_rows is not None and len(all_articles) != args.expected_rows:
        raise ValueError(
            f"Expected {args.expected_rows} rows, but parsed {len(all_articles)}."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date_of_publication", "media_outlet", "title", "body"],
        )
        writer.writeheader()
        for article in all_articles:
            writer.writerow({key: article[key] for key in writer.fieldnames})

    print(f"Created {args.output} with {len(all_articles)} rows.")


if __name__ == "__main__":
    main()
