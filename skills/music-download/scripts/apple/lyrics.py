"""Preserve TTML and render complete official lyric translations and timing."""

import argparse
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

XML = "{http://www.w3.org/XML/1998/namespace}"
APPLE = "{http://music.apple.com/lyric-ttml-internal}"
TTML = "{http://www.w3.org/ns/ttml}"


def timed_lines(text):
    return len(re.findall(r"^\[\d+:\d{2}(?:\.\d+)?\].*\S", text, re.MULTILINE))


def select_bundle(output, language="zh-Hans"):
    output = Path(output)
    names = ["lyrics-" + language, "lyrics-" + language + "-enhanced",
             "lyrics", "lyrics-enhanced"]
    candidates = []
    for name in names:
        lrc_path, text_path = output / (name + ".lrc"), output / (name + ".txt")
        if not lrc_path.exists() or not text_path.exists():
            continue
        text, lrc = text_path.read_text(encoding="utf-8"), lrc_path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        summary_name = "lyrics-enhanced" if name.endswith("-enhanced") else "lyrics"
        summary_path = output / (summary_name + ".summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        candidates.append({"name": name, "text": text, "lrc": lrc,
                           "timed_lines": timed_lines(lrc), "summary": summary,
                           "language": language if name.startswith("lyrics-" + language) else summary.get("language")})
    # A file extension does not establish timing; an original timed variant beats plain translation.
    return next((item for item in candidates if item["timed_lines"]), candidates[0] if candidates else None)


def local(tag):
    return tag.rsplit("}", 1)[-1]


def seconds(value):
    if value.endswith("ms"):
        return Decimal(value[:-2]) / 1000
    if value.endswith("s"):
        return Decimal(value[:-1])
    return sum(Decimal(part) * 60**i for i, part in enumerate(reversed(value.split(":"))))


def stamp(value):
    cs = int((seconds(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    minute, rem = divmod(cs, 6000)
    second, fraction = divmod(rem, 100)
    return f"{minute:02d}:{second:02d}.{fraction:02d}"


def body_lines(tree):
    body = next((e for e in tree if local(e.tag) == "body"), None)
    if body is None:
        raise ValueError("TTML body missing")
    return [e for e in body.iter() if local(e.tag) == "p"]


def render(tree, enhanced):
    lines = body_lines(tree)
    plain, timed = [], []
    for p in lines:
        text = "".join(p.itertext()).strip()
        plain.append(text)
        parts = []

        def collect(element):
            if element.text:
                begin = element.get("begin") if local(element.tag) == "span" else None
                parts.append((f"<{stamp(begin)}>" if enhanced and begin else "") + element.text)
            for child in element:
                collect(child)
                if child.tail:
                    parts.append(child.tail)

        collect(p)
        prefix = f"[{stamp(p.get('begin'))}]" if p.get("begin") else ""
        timed.append(prefix + ("".join(parts).strip() if enhanced else text))
    return "\n".join(plain), "\n".join(timed)


def translated_tree(tree, translation):
    result = deepcopy(tree)
    replacements = {e.get("for"): e for e in translation if local(e.tag) == "text"}
    paragraphs = body_lines(result)
    keys = [p.get(APPLE + "key") or p.get(XML + "id") for p in paragraphs]
    if not all(keys) or not all(key in replacements for key in keys):
        raise ValueError("Incomplete official translation; keep the original language")
    for p, key in zip(paragraphs, keys):
        source = replacements[key]
        for child in list(p):
            p.remove(child)
        p.text = source.text
        for child in source:
            copied = deepcopy(child)
            for element in copied.iter():
                if local(element.tag) == "span":
                    element.tag = TTML + "span"
            p.append(copied)
        if "".join(p.itertext()) != "".join(source.itertext()):
            raise ValueError("Translation text mismatch")
    result.set(XML + "lang", translation.get(XML + "lang"))
    return result


def write_bundle(xml, output, enhanced=False):
    tree = ET.fromstring(xml)
    if local(tree.tag) != "tt":
        raise ValueError("Expected TTML")
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    prefix = "lyrics-enhanced" if enhanced else "lyrics"
    variants = [(prefix, tree, xml)]
    languages, issues = [], []
    for translation in tree.iter():
        if local(translation.tag) != "translation":
            continue
        language = translation.get(XML + "lang", "")
        if not language or not all(c.isalnum() or c == "-" for c in language):
            continue
        if language in languages:
            continue
        try:
            converted = translated_tree(tree, translation)
        except ValueError:
            issues.append({"language": language, "error": "incomplete_translation"})
            continue
        name = "lyrics-" + language + ("-enhanced" if enhanced else "")
        variants.append((name, converted, ET.tostring(converted, encoding="unicode")))
        languages.append(language)
    for name, variant, raw in variants:
        text, lrc = render(variant, enhanced)
        for extension, content in (("ttml", raw), ("txt", text), ("lrc", lrc)):
            with (output / f"{name}.{extension}").open("x", encoding="utf-8") as handle:
                handle.write(content)
    writers = list(dict.fromkeys(
        "".join(e.itertext()).strip() for e in tree.iter()
        if local(e.tag) == "songwriter" and "".join(e.itertext()).strip()
    ))
    word_timing = any(local(e.tag) == "span" and e.get("begin")
                      for p in body_lines(tree) for e in p.iter())
    summary = {"language": tree.get(XML + "lang"), "lines": len(body_lines(tree)),
               "enhanced": enhanced, "syllable_synced": word_timing,
               "timed_lines": timed_lines(render(tree, enhanced)[1]),
               "official_translations": languages,
               "songwriters": writers, "issues": issues}
    with (output / f"{prefix}.summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--enhanced", action="store_true")
    args = parser.parse_args()
    print(json.dumps(write_bundle(args.input.read_text(encoding="utf-8"),
                                  args.output_dir, args.enhanced)))
