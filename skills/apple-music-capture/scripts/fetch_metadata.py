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
    api = await AppleMusicApi.from_cookies(str(args.cookies),
                                          storefront=args.storefront, language=args.language)
    async with api:
        resource = (await api.get_song(args.song_id, extend="", include="albums,artists"))["data"][0]
        if resource["id"] != args.song_id:
            raise ValueError("Unexpected catalog song")
        albums = resource.get("relationships", {}).get("albums", {}).get("data", [])
        album = (await api.get_album(albums[0]["id"], extend=""))["data"][0] if albums else {}
        song = Song.from_metadata(resource, api=api)
        result = {"gamdl_version": __version__, "song": public_metadata(resource),
                  "album": public_metadata(album), "lyrics": {}, "issues": []}
        args.output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        for enhanced in (False, True):
            mode = "enhanced" if enhanced else "standard"
            try:
                lyrics = await song.get_lyrics(syllable=enhanced, language=args.language)
                if lyrics and lyrics.source_ttml:
                    result["lyrics"][mode] = write_bundle(lyrics.source_ttml, args.output_dir, enhanced)
            except Exception as exc:
                result["issues"].append({"operation": mode + "_lyrics", "error_type": type(exc).__name__,
                                         "status": getattr(exc, "status_code", None)})
        with (args.output_dir / "catalog.json").open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print(json.dumps({"song_id": resource["id"], "album_id": album.get("id"),
                          "lyrics": result["lyrics"], "issues": result["issues"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--song-id", required=True)
    parser.add_argument("--cookies", required=True, type=Path)
    parser.add_argument("--storefront", required=True)
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not args.song_id.isdecimal() or args.output_dir.exists():
        parser.error("Use a catalog song ID and a new output directory")
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
