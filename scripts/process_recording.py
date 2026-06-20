from pathlib import Path
import subprocess

INPUT_DIR = Path(r"E:\garcia-recordings\original")
OUTPUT_DIR = Path(r"E:\garcia-recordings\clips")

CHUNK_SECONDS = 15 * 60  # 15 minutes

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}


def run(cmd: list[str]) -> None:
    print("Running:")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def process_file(input_file: Path) -> None:
    base_name = input_file.stem
    file_output_dir = OUTPUT_DIR / base_name
    file_output_dir.mkdir(parents=True, exist_ok=True)

    output_pattern = file_output_dir / f"{base_name}_clip_%03d.wav"

    audio_filter = (
        "highpass=f=80,"
        "lowpass=f=8000,"
        "afftdn=nf=-25,"
        "loudnorm=I=-18:TP=-2:LRA=11"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),
        "-ac", "1",              # mono
        "-ar", "16000",          # 16 kHz, good for speech transcription
        "-af", audio_filter,
        "-f", "segment",
        "-segment_time", str(CHUNK_SECONDS),
        "-reset_timestamps", "1",
        str(output_pattern),
    ]

    run(cmd)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    audio_files = [
        p for p in INPUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]

    if not audio_files:
        print(f"No audio files found in {INPUT_DIR}")
        return

    for audio_file in audio_files:
        print(f"\nProcessing {audio_file.name}")
        process_file(audio_file)

    print("\nDone.")


if __name__ == "__main__":
    main()
