from pathlib import Path

from flask import Flask, abort, render_template, send_file


BASE_DIR = Path(__file__).parent
FORMATTED_TRANSCRIPTS_DIR = BASE_DIR / "formatted-transcripts"
CLIPS_DIR = BASE_DIR / "clips"
NOTES_DIR = BASE_DIR / "notes"
SUMMARY_DIR = BASE_DIR / "summary"

app = Flask(__name__)


def _safe_name(name: str) -> str:
    if "/" in name or "\\" in name or ".." in name:
        abort(404)
    return name


def _transcript_path(name: str) -> Path:
    return FORMATTED_TRANSCRIPTS_DIR / f"{name}.txt"


def _audio_path(name: str) -> Path | None:
    matches = list(CLIPS_DIR.rglob(f"{name}.wav"))
    if not matches:
        return None
    return matches[0]


def _notes_path(name: str) -> Path:
    return NOTES_DIR / f"{name}.md"


def _summary_path(name: str) -> Path:
    return SUMMARY_DIR / f"{name}.txt"


def _available_names() -> list[str]:
    if not FORMATTED_TRANSCRIPTS_DIR.exists():
        return []
    return sorted(path.stem for path in FORMATTED_TRANSCRIPTS_DIR.glob("*.txt"))


@app.route("/")
def index():
    names = _available_names()
    return render_template("index.html", names=names)


@app.route("/transcript/<name>")
def transcript(name: str):
    name = _safe_name(name)
    transcript_file = _transcript_path(name)
    if not transcript_file.exists():
        abort(404)

    summary_file = _summary_path(name)
    if summary_file.exists():
        transcript_text = summary_file.read_text(encoding="utf-8")
    else:
        transcript_text = "No summary found yet for this clip."
    has_audio = _audio_path(name) is not None
    has_notes = _notes_path(name).exists()
    return render_template(
        "transcript.html",
        name=name,
        transcript_text=transcript_text,
        has_audio=has_audio,
        has_notes=has_notes,
    )


@app.route("/notes/<name>")
def notes(name: str):
    name = _safe_name(name)
    note_file = _notes_path(name)
    if note_file.exists():
        note_text = note_file.read_text(encoding="utf-8")
    else:
        note_text = "No family notes/corrections yet for this clip."
    return render_template("notes.html", name=name, note_text=note_text)


@app.route("/download/transcript/<name>")
def download_transcript(name: str):
    name = _safe_name(name)
    transcript_file = _transcript_path(name)
    if not transcript_file.exists():
        abort(404)
    return send_file(transcript_file, as_attachment=True)


@app.route("/audio/<name>")
def audio(name: str):
    name = _safe_name(name)
    audio_file = _audio_path(name)
    if audio_file is None:
        abort(404)
    return send_file(audio_file)


@app.route("/download/audio/<name>")
def download_audio(name: str):
    name = _safe_name(name)
    audio_file = _audio_path(name)
    if audio_file is None:
        abort(404)
    return send_file(audio_file, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
