"""Fetch public catalog metadata and TTML through an existing Gamdl environment."""

import argparse
import asyncio
import json
from pathlib import Path
import sys

from gamdl import __version__
from gamdl.api import AppleMusicApi
from gamdl.media import Song

from lyrics import write_bundle


def public_metadata(value):
    if isinstance(value, list):
        return [public_metadata(item) for item in value]
    if isinstance(value, dict):
        return {key: public_metadata(item) for key, item in value.items()
                if key not in {"extendedAssetUrls", "assetUrls", "assets", "previews",
                               "licenseServerUrl", "drmInfo"}
                and "token" not in key.lower()}
    return value


async def fetch(args):
    options = {"storefront": args.storefront, "language": args.language}
    api = (await AppleMusicApi.from_cookies(str(args.cookies), **options) if args.cookies
           else await AppleMusicApi.create(**options))
    async with api:
        resource, album = {}, {}
        if args.song_id:
            resource = (await api.get_song(args.song_id, extend="", include="albums,artists"))["data"][0]
            if resource["id"] != args.song_id:
                raise ValueError("Unexpected catalog song")
            albums = resource.get("relationships", {}).get("albums", {}).get("data", [])
            album = (await api.get_album(albums[0]["id"], extend=""))["data"][0] if albums else {}
        else:
            album = (await api.get_album(args.album_id, extend=""))["data"][0]
            if album["id"] != args.album_id:
                raise ValueError("Unexpected catalog album")
        result = {"gamdl_version": __version__, "song": public_metadata(resource),
                  "album": public_metadata(album), "lyrics": {}, "lyrics_requested": not args.metadata_only, "issues": []}
        args.output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        song = Song.from_metadata(resource, api=api) if not args.metadata_only else None
        for enhanced in (() if args.metadata_only else (False, True)):
            mode = "enhanced" if enhanced else "standard"
            try:
                lyrics = await song.get_lyrics(syllable=enhanced, language=args.language)
                if lyrics and lyrics.source_ttml:
                    result["lyrics"][mode] = write_bundle(lyrics.source_ttml, args.output_dir, enhanced)
                else:
                    result["issues"].append({"operation": mode + "_lyrics", "error_type": "UnavailableLyrics",
                                             "status": None})
            except Exception as exc:
                result["issues"].append({"operation": mode + "_lyrics", "error_type": type(exc).__name__,
                                         "status": getattr(exc, "status_code", None)})
                if getattr(exc, "status_code", None) in (401, 403) or "Authentication" in type(exc).__name__:
                    break
        with (args.output_dir / "catalog.json").open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        if not args.metadata_only:
            mode = "standard" if "standard" in result["lyrics"] else "enhanced"
            prefix = "lyrics" if mode == "standard" else "lyrics-enhanced"
            available = bool(result["lyrics"])
            text = (args.output_dir / (prefix + ".txt")).read_text(encoding="utf-8") if available else ""
            lrc = (args.output_dir / (prefix + ".lrc")).read_text(encoding="utf-8") if available else ""
            attributes = resource.get("attributes", {})
            failed = any(issue["error_type"] != "UnavailableLyrics" for issue in result["issues"])
            lyric_result = {"status": "available" if available else "request_failed" if failed else "unavailable", "provider": "apple", "origin": "official",
                            "sourceId": args.song_id, "track": {"id": args.song_id, "title": attributes.get("name"),
                            "artists": [{"name": attributes.get("artistName")}], "album": {"id": album.get("id"),
                            "name": attributes.get("albumName")}, "durationMs": attributes.get("durationInMillis"),
                            "isrc": attributes.get("isrc")}, "text": text, "lrc": lrc,
                            "language": result["lyrics"].get(mode, {}).get("language"),
                            "alignment": "source_timestamps_unmeasured", "issues": result["issues"],
                            "variants": result["lyrics"]}
            with (args.output_dir / "lyrics.json").open("x", encoding="utf-8") as handle:
                json.dump(lyric_result, handle, ensure_ascii=False, indent=2)
        print(json.dumps({"song_id": resource.get("id"), "album_id": album.get("id"), "lyrics_requested": not args.metadata_only,
                          "lyrics": result["lyrics"], "issues": result["issues"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--song-id")
    identity.add_argument("--album-id")
    parser.add_argument("--cookies", type=Path)
    parser.add_argument("--metadata-only", action="store_true", help="Fetch catalog without lyric or audio requests; cookies are optional")
    parser.add_argument("--storefront", required=True)
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not (args.song_id or args.album_id).isdecimal() or args.output_dir.exists():
        parser.error("Use a catalog song/album ID and a new output directory")
    if not args.metadata_only and (not args.cookies or not args.song_id):
        parser.error("Lyrics require a song ID and already authorized cookies; album mode requires --metadata-only")
    try:
        asyncio.run(asyncio.wait_for(fetch(args), timeout=120))
    except Exception as exc:
        # API exceptions can contain credential-bearing URLs; do not print them.
        print(json.dumps({"error_type": type(exc).__name__,
                          "status": getattr(exc, "status_code", None)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
