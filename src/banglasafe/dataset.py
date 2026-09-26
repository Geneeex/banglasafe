"""Load the BanglaSafe prompt set from Hugging Face, with filtering and resume support."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import httpx

from .config import HF_DATASET

# The prompt set is a public JSONL file, so a plain GET is enough. Pulling in the
# datasets library for 879 rows would cost pyarrow, pandas, and a slow cold start.
FILE_URL = "https://huggingface.co/datasets/{repo}/resolve/{rev}/prompts.jsonl"

CACHE_DIR = Path(os.environ.get("BANGLASAFE_CACHE", Path.home() / ".cache" / "banglasafe"))


def fetch_prompts(revision: str = "main", *, refresh: bool = False) -> list[dict]:
    """Download prompts.jsonl, cached on disk after the first call."""
    cache = CACHE_DIR / f"prompts-{revision}.jsonl"
    if cache.exists() and not refresh:
        return read_jsonl(cache)

    url = FILE_URL.format(repo=HF_DATASET, rev=revision)
    try:
        r = httpx.get(url, follow_redirects=True, timeout=60.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(
            f"Could not download the prompt set from {url}\n  {e}\n"
            "  Check your connection, or pass --revision to pin a different version."
        ) from e

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(r.text)
    return read_jsonl(cache)


def load_prompts(
    *,
    conditions: tuple[str, ...] | None = None,
    categories: tuple[str, ...] | None = None,
    limit: int | None = None,
    revision: str = "main",
) -> list[dict]:
    """Fetch the 879 prompts. Public dataset, no token required.

    `limit` selects whole harm instances rather than the first N rows, so every
    selected instance keeps all five of its conditions. Comparing registers on a
    partial instance would be meaningless.
    """
    rows = fetch_prompts(revision)

    if conditions:
        rows = [r for r in rows if r["condition"] in conditions]
    if categories:
        rows = [r for r in rows if r["category"] in categories]

    if limit is not None:
        rows = _sample_instances(rows, limit)

    rows.sort(key=lambda r: r["prompt_id"])
    return rows


def _instance_of(prompt_id: str) -> str:
    """`bm-A-EN-1` -> `bm-A`. The harm instance shared across the five conditions."""
    return "-".join(prompt_id.split("-")[:2])


def _sample_instances(rows: list[dict], limit: int) -> list[dict]:
    """Take `limit` whole instances, spread evenly across harm categories."""
    by_cat: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for r in rows:
        inst = _instance_of(r["prompt_id"])
        if inst not in seen:
            seen.add(inst)
            by_cat[r["category"]].append(inst)

    keep: list[str] = []
    cats = sorted(by_cat)
    i = 0
    while len(keep) < limit and any(by_cat.values()):
        c = cats[i % len(cats)]
        if by_cat[c]:
            keep.append(by_cat[c].pop(0))
        i += 1
    keep_set = set(keep)
    return [r for r in rows if _instance_of(r["prompt_id"]) in keep_set]


def load_done(path: Path, key: str = "response_id") -> set[str]:
    """Ids already written, so an interrupted run resumes instead of restarting."""
    done: set[str] = set()
    if not path.exists():
        return done
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not rec.get("error") and rec.get(key):
                done.add(rec[key])
    return done


def read_jsonl(path: Path) -> list[dict]:
    with Path(path).open() as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
