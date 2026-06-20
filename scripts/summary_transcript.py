from pathlib import Path

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
FORMATTED_TRANSCRIPTS_DIR = BASE_DIR / "formatted-transcripts"
SUMMARY_DIR = BASE_DIR / "summary"
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI()

PROMPT_TEMPLATE = """
You are helping summarize a family-history transcript.

Write a concise summary focused on Grandpa Garcia:
- Emphasize what Grandpa Garcia says directly.
- Emphasize things he did (work, moves, decisions, actions, events).
- Preserve uncertainty when the transcript is unclear. Do not invent details.

Use this format:
1) Key points (3-6 bullets)
2) Things Grandpa Garcia did (bulleted)
3) Notable dates/places mentioned (bulleted)

Transcript file name: {name}
""".strip()


def summarize_transcript(name: str, transcript_text: str) -> str:
    prompt = PROMPT_TEMPLATE.format(name=name)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"{prompt}\n\nTranscript:\n{transcript_text}",
    )
    return response.output_text.strip()


def main() -> None:
    transcript_files = sorted(FORMATTED_TRANSCRIPTS_DIR.glob("*.txt"))

    if not transcript_files:
        print("No formatted transcript files found.")
        return

    for transcript_file in transcript_files:
        name = transcript_file.stem
        summary_file = SUMMARY_DIR / f"{name}.txt"

        transcript_text = transcript_file.read_text(encoding="utf-8")
        print(f"Summarizing {transcript_file.name}")
        summary_text = summarize_transcript(name=name, transcript_text=transcript_text)
        summary_file.write_text(summary_text + "\n", encoding="utf-8")
        print(f"Wrote {summary_file}")

    print("Done.")


if __name__ == "__main__":
    main()
