import io
import os
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, abort, render_template, send_file, request, Response


def _env_first(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


B2_BUCKET = _env_first("B2_BUCKET", "B2_BUCKETNAME", default="GarciaRecordings")
B2_ENDPOINT_URL = _env_first("B2_ENDPOINT_URL", default="https://s3.us-west-001.backblazeb2.com")
B2_KEY_ID = _env_first("B2_KEY_ID", "B2_KEYID")
B2_APPLICATION_KEY = _env_first("B2_APPLICATION_KEY", "B2_APPKEY")

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FORMATTED_TRANSCRIPTS_PREFIX = "formatted-transcripts/"
CLIPS_PREFIX = "clips/"
NOTES_PREFIX = "notes/"
SUMMARY_PREFIX = "summary/"

app = Flask(__name__)


def _require_b2_credentials() -> None:
    if not B2_KEY_ID or not B2_APPLICATION_KEY:
        raise RuntimeError(
            "Missing Backblaze B2 credentials. Set B2_KEY_ID/B2_KEYID and B2_APPLICATION_KEY/B2_APPKEY environment variables."
        )


@lru_cache(maxsize=1)
def _b2_client():
    _require_b2_credentials()
    return boto3.client(
        "s3",
        endpoint_url=B2_ENDPOINT_URL,
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APPLICATION_KEY,
    )


def _list_keys(prefix: str) -> list[str]:
    try:
        paginator = _b2_client().get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=B2_BUCKET, Prefix=prefix)
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Error listing keys with prefix {prefix}: {e}")
        return []

    keys: list[str] = []
    for page in pages:
        for item in page.get("Contents", []):
            key = item.get("Key")
            if key:
                keys.append(key)
    return keys


def _fetch_object_bytes(key: str) -> bytes | None:
    try:
        response = _b2_client().get_object(Bucket=B2_BUCKET, Key=key)
        return response["Body"].read()
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Error fetching object {key}: {e}")
        return None


def _find_key_by_suffix(expected_suffix: str) -> str | None:
    suffix = expected_suffix.replace("\\", "/")
    for key in _list_keys(""):
        if key == suffix or key.endswith(f"/{suffix}"):
            return key
    return None


def _fetch_object_bytes_by_suffix(expected_suffix: str) -> bytes | None:
    exact = _fetch_object_bytes(expected_suffix)
    if exact is not None:
        return exact
    resolved_key = _find_key_by_suffix(expected_suffix)
    if resolved_key is None:
        return None
    return _fetch_object_bytes(resolved_key)


def _fetch_object_range(key: str, start: int, end: int) -> bytes | None:
    try:
        range_header = f"bytes={start}-{end}"
        response = _b2_client().get_object(Bucket=B2_BUCKET, Key=key, Range=range_header)
        return response["Body"].read()
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Error fetching range {start}-{end} for {key}: {e}")
        return None


def _get_object_metadata(key: str):
    try:
        return _b2_client().head_object(Bucket=B2_BUCKET, Key=key)
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Error getting metadata for {key}: {e}")
        return None


def _safe_name(name: str) -> str:
    if "/" in name or "\\" in name or ".." in name:
        abort(404)
    return name


def _transcript_path(name: str) -> Path:
    return Path(f"{FORMATTED_TRANSCRIPTS_PREFIX}{name}.txt")


def _audio_path(name: str) -> str | None:
    target = f"{name}.wav"
    for key in _list_keys(CLIPS_PREFIX):
        # Normalize key to use forward slashes for comparison
        normalized_key = key.replace("\\", "/")
        if normalized_key.endswith(target):
            return normalized_key
    # Also check without prefix just in case it's in the root or has another prefix
    for key in _list_keys(""):
        normalized_key = key.replace("\\", "/")
        if normalized_key.endswith(target):
            return normalized_key
    return None


def _notes_path(name: str) -> Path:
    return Path(f"{NOTES_PREFIX}{name}.md")


def _summary_path(name: str) -> Path:
    return Path(f"{SUMMARY_PREFIX}{name}.txt")


def _available_names() -> list[str]:
    names: set[str] = set()
    for key in _list_keys(""):
        normalized = key.replace("\\", "/")
        if "/formatted-transcripts/" not in f"/{normalized}" and not normalized.startswith(FORMATTED_TRANSCRIPTS_PREFIX):
            continue
        if not normalized.endswith(".txt"):
            continue
        names.add(Path(normalized).stem)
    return sorted(names)


@app.route("/")
def index():
    names = _available_names()
    return render_template("index.html", names=names)


@app.route("/transcript/<name>")
def transcript(name: str):
    name = _safe_name(name)
    transcript_key = str(_transcript_path(name))
    if _fetch_object_bytes_by_suffix(transcript_key) is None:
        abort(404)

    summary_bytes = _fetch_object_bytes_by_suffix(str(_summary_path(name)))
    if summary_bytes is not None:
        transcript_text = summary_bytes.decode("utf-8")
    else:
        transcript_text = "No summary found yet for this clip."
    has_audio = _audio_path(name) is not None
    has_notes = _fetch_object_bytes_by_suffix(str(_notes_path(name))) is not None
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
    note_bytes = _fetch_object_bytes_by_suffix(str(_notes_path(name)))
    if note_bytes is not None:
        note_text = note_bytes.decode("utf-8")
    else:
        note_text = "No family notes/corrections yet for this clip."
    return render_template("notes.html", name=name, note_text=note_text)


@app.route("/download/transcript/<name>")
def download_transcript(name: str):
    name = _safe_name(name)
    transcript_bytes = _fetch_object_bytes_by_suffix(str(_transcript_path(name)))
    if transcript_bytes is None:
        abort(404)
    return send_file(
        io.BytesIO(transcript_bytes),
        as_attachment=True,
        download_name=f"{name}.txt",
        mimetype="text/plain",
    )


@app.route("/audio/<name>")
def audio(name: str):
    name = _safe_name(name)
    audio_key = _audio_path(name)
    if audio_key is None:
        abort(404)

    metadata = _get_object_metadata(audio_key)
    if metadata is None:
        abort(404)

    file_size = metadata["ContentLength"]
    range_header = request.headers.get("Range", None)

    if not range_header:
        audio_bytes = _fetch_object_bytes(audio_key)
        if audio_bytes is None:
            abort(404)
        return send_file(io.BytesIO(audio_bytes), mimetype="audio/wav")

    try:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
    except (ValueError, IndexError):
        abort(416)

    if start >= file_size or end >= file_size or start > end:
        abort(416)

    chunk = _fetch_object_range(audio_key, start, end)
    if chunk is None:
        abort(404)

    rv = Response(
        chunk,
        206,
        mimetype="audio/wav",
        content_type="audio/wav",
        direct_passthrough=True,
    )
    rv.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
    rv.headers.add("Accept-Ranges", "bytes")
    return rv


@app.route("/download/audio/<name>")
def download_audio(name: str):
    name = _safe_name(name)
    audio_key = _audio_path(name)
    if audio_key is None:
        abort(404)
    audio_bytes = _fetch_object_bytes(audio_key)
    if audio_bytes is None:
        abort(404)
    return send_file(
        io.BytesIO(audio_bytes),
        as_attachment=True,
        download_name=f"{name}.wav",
        mimetype="audio/wav",
    )


if __name__ == "__main__":
    app.run(debug=True)
