"""Build a no-overwrite FLAC from integer recording audio and matching metadata."""

import argparse
import base64
from decimal import Decimal, ROUND_HALF_UP
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=True, timeout=600)


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)]).stdout)


def pcm_hash(path):
    return run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0",
                "-c:a", "pcm_s32le", "-f", "hash", "-hash", "sha256", "-"]).stdout.strip()


def serial(value):
    if isinstance(value, bytes):
        result = {"type": type(value).__name__, "base64": base64.b64encode(value).decode("ascii")}
        if hasattr(value, "dataformat"):
            result["dataformat"] = int(value.dataformat)
        return result
    if isinstance(value, tuple):
        return {"type": "tuple", "value": [serial(item) for item in value]}
    if isinstance(value, list):
        return [serial(item) for item in value]
    return value


def strings(value):
    values = value if isinstance(value, list) else [value]
    result = []
    for item in values:
        if item is None or item == "":
            continue
        if isinstance(item, bytes):
            try:
                result.append(item.decode("utf-8"))
            except UnicodeDecodeError:
                result.append("base64:" + base64.b64encode(item).decode("ascii"))
        elif isinstance(item, bool):
            result.append("1" if item else "0")
        elif isinstance(item, tuple):
            result.append("/".join(map(str, item)))
        else:
            result.append(str(item))
    return result


def shift_lrc(text, offset):
    def change(match):
        start, minute, second, end = match.groups()
        value = max(Decimal(0), Decimal(minute) * 60 + Decimal(second) + Decimal(str(offset)))
        cs = int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))
        minute, rem = divmod(cs, 6000)
        second, fraction = divmod(rem, 100)
        return f"{start}{minute:02d}:{second:02d}.{fraction:02d}{end}"
    return re.sub(r"(\[|<)(\d+):(\d+(?:\.\d+)?)(\]|>)", change, text)


def tag(candidate, args, alignment):
    audio = FLAC(candidate)
    audio.tags.clear()
    audio.clear_pictures()

    def put(key, value):
        values = strings(value)
        if values:
            audio[key] = values

    if args.donor:
        donor = MP4(args.donor)
        if donor.tags.get("cnID") != [int(args.song_id)]:
            raise ValueError("Donor does not match the expected catalog song ID")
        mapping = {
            "©nam": "TITLE", "©ART": "ARTIST", "©alb": "ALBUM", "aART": "ALBUMARTIST",
            "©gen": "GENRE", "©wrt": "COMPOSER", "cprt": "COPYRIGHT", "©cmt": "COMMENT",
            "sonm": "TITLESORT", "soar": "ARTISTSORT", "soal": "ALBUMSORT",
            "soaa": "ALBUMARTISTSORT", "soco": "COMPOSERSORT", "cpil": "COMPILATION",
            "pgap": "GAPLESS_ALBUM", "xid ": "XID", "desc": "DESCRIPTION",
            "ldes": "LONGDESCRIPTION", "rtng": "CONTENT_RATING",
            "cnID": "APPLE_MUSIC_SONG_ID", "atID": "APPLE_MUSIC_ARTIST_ID",
            "plID": "APPLE_MUSIC_ALBUM_ID", "geID": "APPLE_MUSIC_GENRE_ID",
            "sfID": "APPLE_MUSIC_STOREFRONT_ID", "stik": "APPLE_MUSIC_MEDIA_TYPE",
        }
        raw = {}
        for key, value in donor.tags.items():
            if key == "covr":
                continue
            raw[key] = serial(value)
            put("APPLE_MP4_" + key.encode("utf-8").hex().upper(), value)
            if key in mapping:
                put(mapping[key], value)
        put("APPLE_MP4_METADATA_JSON", json.dumps(raw, ensure_ascii=False, sort_keys=True))
        for atom, key, totals in (("trkn", "TRACKNUMBER", ("TRACKTOTAL", "TOTALTRACKS")),
                                  ("disk", "DISCNUMBER", ("DISCTOTAL", "TOTALDISCS"))):
            if atom in donor.tags:
                number, total = donor.tags[atom][0]
                put(key, number)
                for total_key in totals:
                    put(total_key, total)
        if donor.tags.get("©day"):
            put("DATE", donor.tags["©day"][0][:10])
            put("RELEASE_DATE", donor.tags["©day"])

    if args.catalog:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        if catalog["song"]["id"] != args.song_id:
            raise ValueError("Catalog does not match the expected song ID")
        song = catalog["song"].get("attributes", {})
        album = catalog.get("album", {}).get("attributes", {})
        put("APPLE_MUSIC_CATALOG_METADATA_JSON", json.dumps(catalog, ensure_ascii=False, sort_keys=True))
        common = {"TITLE": song.get("name"), "ARTIST": song.get("artistName"),
                  "ALBUM": song.get("albumName"), "ALBUMARTIST": album.get("artistName"),
                  "GENRE": song.get("genreNames"), "DATE": song.get("releaseDate"),
                  "COMPOSER": song.get("composerName"), "COPYRIGHT": album.get("copyright"),
                  "TRACKNUMBER": song.get("trackNumber"), "DISCNUMBER": song.get("discNumber")}
        for key, value in common.items():
            if key not in audio:
                put(key, value)
        for key, value in {"ISRC": song.get("isrc"), "LABEL": album.get("recordLabel"),
                           "RECORD_LABEL": album.get("recordLabel"), "APPLE_MUSIC_URL": song.get("url"),
                           "APPLE_MUSIC_ALBUM_ID": catalog.get("album", {}).get("id"),
                           "APPLE_MUSIC_ALBUM_URL": album.get("url"),
                           "APPLE_MUSIC_SOURCE_DURATION_MS": song.get("durationInMillis")}.items():
            put(key, value)
    put("APPLE_MUSIC_SONG_ID", args.song_id)
    if "ISRC" not in audio:
        match = re.search(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", audio.get("XID", [""])[0])
        if match:
            put("ISRC", match.group())

    lyric_lines = 0
    if args.lyrics_dir:
        root = args.lyrics_dir
        selected = "lyrics-" + args.lyrics_language
        if not (root / (selected + ".lrc")).exists():
            selected = "lyrics"
        summary_path = root / "lyrics.summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        put("SONGWRITER", summary.get("songwriters"))
        lrc_path = root / (selected + ".lrc")
        if lrc_path.exists():
            lrc = lrc_path.read_text(encoding="utf-8")
            lyric_lines = len(lrc.splitlines())
            put("LYRICS", shift_lrc(lrc, alignment["offset_seconds"]))
            put("SYNCEDLYRICS", shift_lrc(lrc, alignment["offset_seconds"]))
            put("UNSYNCEDLYRICS", (root / (selected + ".txt")).read_text(encoding="utf-8"))
            put("LYRICS_LANGUAGE", args.lyrics_language if selected != "lyrics" else summary.get("language"))
            enhanced = root / (selected + "-enhanced.lrc")
            enhanced_language = args.lyrics_language if selected != "lyrics" else summary.get("language")
            if not enhanced.exists():
                enhanced = root / "lyrics-enhanced.lrc"
                enhanced_summary = root / "lyrics-enhanced.summary.json"
                if enhanced_summary.exists():
                    enhanced_language = json.loads(enhanced_summary.read_text(encoding="utf-8")).get("language")
            if enhanced.exists():
                put("ENHANCED_LYRICS", shift_lrc(enhanced.read_text(encoding="utf-8"), alignment["offset_seconds"]))
                put("ENHANCED_LYRICS_LANGUAGE", enhanced_language)
            put("LYRICS_TIME_OFFSET_MS", round(alignment["offset_seconds"] * 1000))
            put("LYRICS_ALIGNMENT_JSON", json.dumps(alignment, sort_keys=True))
        for path in root.iterdir():
            if path.name.startswith("lyrics") and path.suffix in (".ttml", ".txt", ".lrc"):
                key = "SOURCE_" + path.name.upper().replace("-", "_").replace(".", "_")
                put(key, path.read_text(encoding="utf-8"))

    if args.cover:
        cover = args.cover.read_bytes()
        stream = probe(args.cover)["streams"][0]
        if stream["codec_name"] not in ("mjpeg", "png"):
            raise ValueError("Use JPEG or PNG artwork")
        picture = Picture()
        picture.type, picture.desc = 3, "Front cover"
        picture.mime = "image/jpeg" if stream["codec_name"] == "mjpeg" else "image/png"
        picture.width, picture.height, picture.depth = stream["width"], stream["height"], 24
        picture.data = cover
        audio.add_picture(picture)
    put("AUDIO_SOURCE", args.audio_source)
    put("METADATA_SOURCE", "Gamdl / Apple Music catalog")
    put("CONVERSION_NOTE", "FLAC preserves the decoded PCM of the supplied recording; no source-extraction claim.")
    if not audio.get("TITLE") or not audio.get("ARTIST"):
        raise ValueError("Required title/artist metadata missing")
    audio.save()
    check = FLAC(candidate)
    if any(check.get(key) != audio.get(key) for key in audio.tags.keys()):
        raise ValueError("Tag round-trip mismatch")
    if [p.data for p in check.pictures] != [p.data for p in audio.pictures]:
        raise ValueError("Cover round-trip mismatch")
    return {"tags": len(check.tags), "lyrics_lines": lyric_lines,
            "cover": [{"width": p.width, "height": p.height} for p in check.pictures],
            "duration": check.info.length, "artist": check.get("ARTIST"),
            "album_artist": check.get("ALBUMARTIST"), "bits": check.info.bits_per_sample,
            "sample_rate": check.info.sample_rate, "channels": check.info.channels}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--donor", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--song-id", required=True)
    parser.add_argument("--lyrics-dir", type=Path)
    parser.add_argument("--lyrics-language", default="zh-Hans")
    parser.add_argument("--cover", type=Path)
    parser.add_argument("--audio-source", default="User-supplied recording")
    parser.add_argument("--output", type=Path, required=True)
    offsets = parser.add_mutually_exclusive_group()
    offsets.add_argument("--alignment", type=Path)
    offsets.add_argument("--offset", type=float)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.suffix.lower() != ".flac":
        parser.error("Use a new FLAC output path")
    if not args.song_id.isdecimal() or not (args.donor or args.catalog):
        parser.error("A catalog song ID and matching donor or catalog JSON are required")
    alignment = {"offset_seconds": args.offset or 0, "method": "manual" if args.offset is not None else "unaligned"}
    if args.alignment:
        alignment = json.loads(args.alignment.read_text(encoding="utf-8"))
        if alignment.get("reliable") is not True:
            parser.error("Unreliable alignment must not be applied automatically")
    if not math.isfinite(alignment["offset_seconds"]):
        parser.error("Invalid lyric offset")
    stream = next(s for s in probe(args.source)["streams"] if s["codec_type"] == "audio")
    bits = int(stream.get("bits_per_raw_sample") or stream.get("bits_per_sample") or 0)
    if stream.get("sample_fmt") not in ("s16", "s16p", "s32", "s32p") or bits not in (16, 24):
        parser.error("Use 16/24-bit integer recording audio; floating PCM needs separately approved quantization")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".flac-package-", dir=args.output.parent) as stage:
        candidate = Path(stage) / "audio.flac"
        run(["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", str(args.source),
             "-map", "0:a:0", "-map_metadata", "-1", "-c:a", "flac", "-compression_level", "8",
             "-sample_fmt", "s16" if bits == 16 else "s32", "-bits_per_raw_sample", str(bits), str(candidate)])
        result = tag(candidate, args, alignment)
        if (result["sample_rate"], result["channels"], result["bits"]) != (int(stream["sample_rate"]), stream["channels"], bits):
            raise ValueError("Audio format changed")
        before, after = pcm_hash(args.source), pcm_hash(candidate)
        if before != after:
            raise ValueError("Decoded PCM mismatch; final file was not published")
        # A same-filesystem hard link publishes atomically without replacing any file.
        os.link(candidate, args.output)
    result.update({"output": str(args.output), "pcm_sha256": after.split("=", 1)[1],
                   "offset_seconds": alignment["offset_seconds"]})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
