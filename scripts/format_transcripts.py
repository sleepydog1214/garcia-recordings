# E:\garcia-recordings\scripts\format_transcripts.py

from pathlib import Path
import re
import textwrap

INPUT_DIR = Path(r"E:\garcia-recordings\transcripts")
OUTPUT_DIR = Path(r"E:\garcia-recordings\formatted-transcripts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_LINE_WIDTH = 95
SENTENCE_BREAK = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'])')


def format_text(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    sentences = SENTENCE_BREAK.split(text)

    paragraphs = []
    current = []

    for sentence in sentences:
        current.append(sentence.strip())

        # New paragraph every 4-ish sentences
        if len(current) >= 4:
            paragraph = " ".join(current)
            paragraphs.append(textwrap.fill(paragraph, width=MAX_LINE_WIDTH))
            current = []

    if current:
        paragraph = " ".join(current)
        paragraphs.append(textwrap.fill(paragraph, width=MAX_LINE_WIDTH))

    return "\n\n".join(paragraphs) + "\n"


def main():
    txt_files = sorted(INPUT_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {INPUT_DIR}")
        return

    for txt_file in txt_files:
        raw = txt_file.read_text(encoding="utf-8", errors="replace")
        formatted = format_text(raw)

        out_file = OUTPUT_DIR / txt_file.name
        out_file.write_text(formatted, encoding="utf-8")

        print(f"Formatted: {out_file}")

    print("\nDone.")


if __name__ == "__main__":
    main()
