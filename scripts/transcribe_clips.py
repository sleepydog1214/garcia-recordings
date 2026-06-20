from pathlib import Path
from openai import OpenAI

CLIPS_DIR = Path(r"E:\garcia-recordings\clips")
TRANSCRIPTS_DIR = Path(r"E:\garcia-recordings\transcripts")
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI()

PROMPT = """
This is a 1986 family-history interview.
The speaker is my grandfather, born in Mexico around 1900.
He later moved to Michigan, lived around River Rouge, married a Hungarian woman,
had 9 children, and worked on the railroads.
Please preserve uncertain words with [unclear] rather than guessing.
"""

def transcribe_clip(audio_path: Path) -> str:
    print(f"Transcribing {audio_path.name}")

    with audio_path.open("rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            response_format="text",
            prompt=PROMPT,
        )

    return transcript


def main():
    wav_files = sorted(CLIPS_DIR.rglob("*.wav"))

    if not wav_files:
        print("No WAV clips found.")
        return

    full_transcript_parts = []

    for wav_file in wav_files:
        out_file = TRANSCRIPTS_DIR / f"{wav_file.stem}.txt"

        if out_file.exists():
            print(f"Skipping existing transcript: {out_file.name}")
            text = out_file.read_text(encoding="utf-8")
        else:
            text = transcribe_clip(wav_file)
            out_file.write_text(text, encoding="utf-8")

        full_transcript_parts.append(f"\n\n## {wav_file.stem}\n\n{text}")

    combined = TRANSCRIPTS_DIR / "grandpa_garcia_combined_transcript.md"
    combined.write_text("\n".join(full_transcript_parts), encoding="utf-8")

    print(f"\nDone. Combined transcript written to:\n{combined}")


if __name__ == "__main__":
    main()
