#!/usr/bin/env python3
"""kb.py: helper for an llm-learning knowledge base (Jonhvmp/llm-learning layout).

The agent writes the content of a knowledge unit; this script does the
bookkeeping that agents get wrong by hand: the id and the path agree, the
manifest matches the unit's frontmatter, the domain map and the vocabulary
know the domain, and the journal stays valid YAML.

Root: --root, else $AGENT_LEARNING_KB, else ~/.agent-learning/knowledge.
Needs python3 >= 3.9 and PyYAML. Any agent with a shell can run it.

Commands (run `kb.py <command> --help` for flags):
  init DEST --owner NAME   instantiate a base from the template
  new                      scaffold a unit whose id and path agree
  register PATH...         upsert manifest entries and domain-map rows
  journal                  append a recognition event
  validate                 check units, manifest, journal and inbox
  index                    one line per active unit, for long manifests
  --selftest               run the built-in tests in a throwaway directory
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("kb.py needs PyYAML: python3 -m pip install --user pyyaml")

DEFAULT_ROOT = Path.home() / ".agent-learning" / "knowledge"
REPO_TEMPLATE = Path(__file__).resolve().parents[3] / "knowledge-template"

# Fallbacks when the base has no schema file; the schema in the base wins.
DEFAULT_REQUIRED = ["id", "kind", "domain", "title", "summary", "triggers", "confidence",
                    "evidence", "created", "updated", "status"]
DEFAULT_KINDS = ["playbook", "pattern", "pitfall-set", "meta-skill", "reference", "protocol"]
DEFAULT_SECTIONS = {
    "playbook": ["Context", "Outcome", "Procedure", "Parameters", "Invariants", "Pitfalls",
                 "Verification", "Related"],
    "pattern": ["Context", "Problem", "Solution", "Structure", "Parameters", "Invariants",
                "Trade-offs", "Related"],
    "pitfall-set": ["Context", "Pitfalls", "Related"],
    "meta-skill": ["Context", "Principle", "Procedure", "Signals", "Anti-patterns", "Related"],
    "reference": ["Context", "Table", "Related"],
}
HAS_PINS = {"playbook", "pattern", "pitfall-set", "reference"}
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ENTRY_KEYS = ["id", "path", "kind", "domain", "confidence", "status", "tags", "triggers"]
DASHES = "—–"


class KBError(Exception):
    pass


def today() -> str:
    return os.environ.get("KB_TODAY") or dt.date.today().isoformat()


def read_text(p: Path) -> str:
    # BOM and CRLF are normalised away on every read.
    return p.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def dump(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=None,
                          width=4096)


def split_fm(text: str):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return None, text


def load_fm(p: Path):
    fm, body = split_fm(read_text(p))
    if fm is None:
        raise KBError(f"{p.name}: no YAML frontmatter between two '---' lines")
    try:
        data = yaml.safe_load(fm) or {}
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" (line {mark.line + 2})" if mark else ""
        raise KBError(f"{p.name}: frontmatter is not valid YAML{where}; quote values that "
                      "start with {, [ or contain ': '")
    if not isinstance(data, dict):
        raise KBError(f"{p.name}: frontmatter is not a mapping")
    for k, v in list(data.items()):
        if isinstance(v, (dt.date, dt.datetime)):
            data[k] = v.isoformat()[:10]
    return data, body


def rel(root: Path, p: Path) -> str:
    return p.resolve().relative_to(root.resolve()).as_posix()


# ---------------------------------------------------------------- base files

def load_schema(root: Path):
    p = root / "schema" / "knowledge-unit.schema.yaml"
    required, kinds, sections, id_re = DEFAULT_REQUIRED, DEFAULT_KINDS, DEFAULT_SECTIONS, None
    if p.exists():
        s = yaml.safe_load(read_text(p)) or {}
        required = s.get("required", required)
        props = s.get("properties", {})
        kinds = props.get("kind", {}).get("enum", kinds)
        id_re = props.get("id", {}).get("pattern")
        sections = s.get("body_sections_required_order", sections)
    return {"required": required, "kinds": kinds, "sections": sections,
            "id_re": re.compile(id_re or r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")}


def load_vocab(root: Path) -> dict:
    p = root / "schema" / "vocabulary.yaml"
    return (yaml.safe_load(read_text(p)) or {}) if p.exists() else {}


def load_manifest(root: Path):
    p = root / "manifest.yaml"
    if not p.exists():
        raise KBError(f"no manifest.yaml under {root}; is this a knowledge base?")
    text = read_text(p)
    data = yaml.safe_load(text) or {}
    data.setdefault("units", [])
    data["units"] = data["units"] or []
    return p, text, data


def save_manifest(p: Path, text: str, units: list) -> None:
    lines = text.split("\n")
    idx = next((i for i, l in enumerate(lines) if re.match(r"^units:", l)), None)
    head = lines if idx is None else lines[:idx]
    head = [re.sub(r"^updated:.*$", f"updated: {today()}", l) for l in head]
    units = sorted(units, key=lambda u: u["id"])
    if units:
        body = "units:\n" + "".join("  " + l + "\n" for l in dump(units).splitlines())
    else:
        body = "units: []\n"
    out = "\n".join(head).rstrip("\n") + "\n\n" + body
    yaml.safe_load(out)  # never leave a manifest that does not parse
    write_text(p, out)


def domain_short(root: Path, domain: str):
    if domain == "meta":
        return "meta"
    p = root / "domains" / domain / "_domain.md"
    if not p.exists():
        return None
    data, _ = load_fm(p)
    return str(data.get("id", "")).split(".")[0] or None


def add_vocab_domain(root: Path, domain: str, scope: str) -> None:
    p = root / "schema" / "vocabulary.yaml"
    lines = read_text(p).split("\n")
    i = next((n for n, l in enumerate(lines) if re.match(r"^domains:", l)), None)
    entry = f"  {domain}: {json.dumps(scope, ensure_ascii=False)}"
    if i is None:
        lines += ["domains:", entry]
    else:
        m = re.match(r"^domains:\s*\{\}\s*(#.*)?$", lines[i])
        if m:
            lines[i] = "domains:" + (f"   {m.group(1)}" if m.group(1) else "")
            lines.insert(i + 1, entry)
        else:
            j = i + 1
            while j < len(lines) and lines[j].startswith((" ", "\t")):
                j += 1
            lines.insert(j, entry)
    out = "\n".join(lines)
    if domain not in ((yaml.safe_load(out) or {}).get("domains") or {}):
        raise KBError("could not add the domain to schema/vocabulary.yaml; add it by hand")
    write_text(p, out)


def create_domain_map(root: Path, domain: str, short: str, scope: str) -> None:
    write_text(root / "domains" / domain / "_domain.md", f"""---
id: {short}._domain
kind: reference
domain: {domain}
title: {domain} domain map
summary: scope, units and gaps of {domain}
updated: {today()}
---

# {domain}

## Scope
- In: {scope}
- Out: not defined yet

## Units
| id | kind | confidence | path |
|---|---|---|---|

## Topics

## Open gaps
- none recorded
""")


def upsert_domain_row(root: Path, entry: dict, topic) -> None:
    p = root / "domains" / entry["domain"] / "_domain.md"
    if entry["domain"] == "meta" or not p.exists():
        return
    text = read_text(p)
    lines = text.split("\n")
    hdr = next((i for i, l in enumerate(lines) if re.match(r"^\|\s*id\s*\|\s*kind\s*\|", l)), None)
    if hdr is not None:
        start = end = hdr + 2
        while end < len(lines) and lines[end].startswith("|"):
            end += 1
        rows = {}
        for l in lines[start:end]:
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if cells and cells[0]:
                rows[cells[0]] = l
        rows[entry["id"]] = (f"| {entry['id']} | {entry['kind']} | {entry['confidence']} | "
                             f"{entry['path']} |")
        lines[start:end] = [rows[k] for k in sorted(rows)]
    if topic:
        t = next((i for i, l in enumerate(lines) if l.strip() == "## Topics"), None)
        if t is not None and not any(l.startswith(f"- `{topic}/`") for l in lines):
            j = t + 1
            while j < len(lines) and (lines[j].startswith("- ") or not lines[j].strip()):
                if lines[j].startswith("- "):
                    j += 1
                    continue
                if j + 1 < len(lines) and lines[j + 1].startswith("- "):
                    j += 1
                    continue
                break
            lines.insert(j if lines[j - 1].startswith("- ") else t + 1, f"- `{topic}/`")
    out = "\n".join(lines)
    out = re.sub(r"^updated:.*$", f"updated: {today()}", out, count=1, flags=re.M)
    write_text(p, out)


def unit_files(root: Path):
    out = []
    for base in ("domains", "meta-skills"):
        d = root / base
        if d.is_dir():
            out += [p for p in sorted(d.rglob("*.md"))
                    if p.name != "_domain.md" and p.name.lower() != "readme.md"]
    return out


def entry_from(root: Path, p: Path, data: dict) -> dict:
    e = {k: data.get(k) for k in ENTRY_KEYS if k != "path"}
    e["path"] = rel(root, p)
    e["tags"] = data.get("tags") or []
    return {k: e[k] for k in ENTRY_KEYS}


def expected_path(data: dict, short):
    parts = str(data.get("id", "")).split(".")
    if data.get("kind") == "meta-skill" or data.get("domain") == "meta":
        return f"meta-skills/{parts[-1]}.md", "meta"
    if len(parts) != 3:
        return None, short
    return f"domains/{data.get('domain')}/{parts[1]}/{parts[2]}.md", short


# ------------------------------------------------------------------ commands

def cmd_init(a) -> int:
    src = Path(a.template).expanduser() if a.template else REPO_TEMPLATE
    dest = Path(a.dest).expanduser()
    if not (src / "manifest.yaml").exists():
        raise KBError(f"template not found at {src}")
    if dest.exists() and any(dest.iterdir()):
        raise KBError(f"{dest} exists and is not empty; refusing to overwrite a knowledge base")
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    for p in sorted(dest.rglob("*")):
        if p.is_file() and p.suffix in (".md", ".yaml", ".yml"):
            write_text(p, normalise_dashes(read_text(p), p.suffix))
    m = dest / "manifest.yaml"
    write_text(m, re.sub(r'^owner:\s*"\{owner_name\}"', f"owner: {json.dumps(a.owner, ensure_ascii=False)}",
                         read_text(m), count=1, flags=re.M))
    for p in [m, dest / "schema" / "vocabulary.yaml", dest / "journal" / "recognitions.yaml"]:
        if p.exists():
            yaml.safe_load(read_text(p))
    for p in dest.rglob("*.md"):
        fm, _ = split_fm(read_text(p))
        if fm is not None and "{" not in fm:
            yaml.safe_load(fm)
    print(f"initialised {dest} (owner: {a.owner})")
    return 0


def normalise_dashes(text: str, suffix: str) -> str:
    # The owner's house style bans em and en dashes. Frontmatter and YAML get a
    # comma (a colon would break a plain YAML scalar); Markdown bodies get a colon.
    text = re.sub(r"(\d)–(\d)", r"\1-\2", text)
    if suffix in (".yaml", ".yml"):
        return text.replace(" — ", ": ").replace("—", ", ").replace("–", "-")
    fm, body = split_fm(text)
    if fm is not None:
        fm = fm.replace(" — ", ", ").replace("—", ", ").replace("–", "-")
        text = "---\n" + fm + "\n---\n" + body
    return text.replace(" — ", ": ").replace("—", ", ").replace("–", "-")


def cmd_new(root: Path, a) -> int:
    schema = load_schema(root)
    kind = a.kind
    if kind not in schema["kinds"] or kind == "protocol":
        raise KBError(f"kind must be one of {[k for k in schema['kinds'] if k != 'protocol']}")
    slug = a.slug or ("pitfalls" if kind == "pitfall-set" else None)
    if not slug or not SLUG_RE.match(slug):
        raise KBError("--slug is required: lowercase words joined by '-'")
    topic = None
    if kind == "meta-skill":
        domain, uid, path = "meta", f"meta.{slug}", f"meta-skills/{slug}.md"
    else:
        domain, topic = a.domain, a.topic
        if not domain or not SLUG_RE.match(domain) or not topic or not SLUG_RE.match(topic):
            raise KBError("--domain and --topic are required: lowercase words joined by '-'")
        short = domain_short(root, domain)
        if short is None:
            if not a.scope:
                raise KBError(f"domain '{domain}' is new: pass --scope \"<what it covers>\" "
                              "(and --short if its ids should use an abbreviation)")
            short = a.short or domain
            add_vocab_domain(root, domain, a.scope)
            create_domain_map(root, domain, short, a.scope)
            print(f"created domain {domain} (ids start with '{short}.')")
        uid, path = f"{short}.{topic}.{slug}", f"domains/{domain}/{topic}/{slug}.md"
    if not schema["id_re"].match(uid):
        raise KBError(f"id {uid} does not match the schema pattern")
    _, _, man = load_manifest(root)
    clash = next((u for u in man["units"] if u.get("id") == uid), None)
    if (root / path).exists() or clash:
        raise KBError(f"{uid} already exists ({path}): update it in place (PROTOCOL.md section 5), "
                      "never create a duplicate")
    tpl = root / "templates" / f"{kind}.md"
    if not tpl.exists():
        raise KBError(f"no template for kind {kind} at {tpl}")
    _, body = split_fm(read_text(tpl))
    body = re.sub(r"^# .*$", f"# {a.title}", body, count=1, flags=re.M)
    fm = {"id": uid, "kind": kind, "domain": domain, "title": a.title, "summary": a.summary,
          "triggers": a.trigger, "tags": a.tag or [], "confidence": a.confidence,
          "evidence": a.evidence}
    if kind in HAS_PINS:
        fm["version_pins"] = dict(x.split("=", 1) for x in (a.pin or []))
    if kind == "playbook":
        fm["prerequisites"] = []
    fm.update({"related": [], "status": "active", "created": today(), "updated": today(),
               "changelog": []})
    write_text(root / path, "---\n" + dump(fm) + "---\n" + body)
    print(path)
    print(f"next: fill every section of {path}, then run: kb.py register {path} && kb.py validate")
    return 0


def cmd_register(root: Path, a) -> int:
    mp, mtext, man = load_manifest(root)
    units = [u for u in man["units"] if isinstance(u, dict)]
    for raw in a.paths:
        p = Path(raw)
        p = p if p.is_absolute() else root / p
        if not p.exists():
            raise KBError(f"{raw}: no such unit")
        data, _ = load_fm(p)
        e = entry_from(root, p, data)
        units = [u for u in units if u.get("id") != e["id"] and u.get("path") != e["path"]]
        units.append(e)
        parts = e["id"].split(".")
        upsert_domain_row(root, e, parts[1] if len(parts) == 3 and e["domain"] != "meta" else None)
        print(f"registered {e['id']} -> {e['path']}")
    save_manifest(mp, mtext, units)
    return 0


def cmd_journal(root: Path, a) -> int:
    p = root / "journal" / "recognitions.yaml"
    _, _, man = load_manifest(root)
    known = {u.get("id") for u in man["units"] if isinstance(u, dict)}
    created, updated = csv(a.created), csv(a.updated)
    for uid in created + updated:
        if uid not in known:
            print(f"WARN {uid} is not in the manifest; register it first", file=sys.stderr)
    entry = {"date": today(), "signal": a.signal,
             "work": {"summary": a.summary, "artifacts": csv(a.artifacts)},
             "units_created": created, "units_updated": updated}
    if a.notes:
        entry["notes"] = a.notes
    text = read_text(p) if p.exists() else ""
    out = text.rstrip("\n") + "\n\n" + dump([entry])
    parsed = yaml.safe_load(out)
    if not isinstance(parsed, list):
        raise KBError("journal/recognitions.yaml would not be a YAML list; fix it by hand first")
    write_text(p, out)
    print(f"journal: {len(parsed)} events")
    return 0


def csv(v) -> list:
    out = []
    for x in v or []:
        out += [s.strip() for s in str(x).split(",") if s.strip()]
    return out


def check(root: Path):
    errors, warns = [], []
    err = lambda w, m: errors.append(f"ERROR {w}: {m}")
    warn = lambda w, m: warns.append(f"WARN {w}: {m}")
    schema = load_schema(root)
    vocab = load_vocab(root)
    domains = set((vocab.get("domains") or {}).keys()) | {"meta"}
    evidence_types = set(vocab.get("evidence_types") or [])
    try:
        _, _, man = load_manifest(root)
    except (KBError, yaml.YAMLError) as e:
        return [f"ERROR manifest.yaml: {e}"], []
    if "{" in str(man.get("owner", "")) or not man.get("owner"):
        err("manifest.yaml", "owner is not set; the capture trigger reads the owner from here")
    entries = {}
    for u in man["units"]:
        if not isinstance(u, dict) or not u.get("id"):
            err("manifest.yaml", f"malformed entry {u!r}")
            continue
        if u["id"] in entries:
            err("manifest.yaml", f"duplicate entry {u['id']}")
        entries[u["id"]] = u
    seen = {}
    for p in unit_files(root):
        w = rel(root, p)
        try:
            data, body = load_fm(p)
        except KBError as e:
            err(w, str(e))
            continue
        missing = [k for k in schema["required"] if data.get(k) in (None, "", [])]
        if missing:
            err(w, f"missing required fields: {', '.join(missing)}")
        uid, kind = str(data.get("id", "")), data.get("kind")
        if uid in seen:
            err(w, f"id {uid} also used by {seen[uid]}")
        seen[uid] = w
        if not schema["id_re"].match(uid):
            err(w, f"id '{uid}' does not match the schema pattern")
        if kind not in schema["kinds"]:
            err(w, f"kind '{kind}' is not one of {schema['kinds']}")
        if data.get("confidence") not in ("high", "medium", "low"):
            err(w, f"confidence '{data.get('confidence')}' must be high, medium or low")
        if data.get("status") not in ("active", "draft", "deprecated"):
            err(w, f"status '{data.get('status')}' must be active, draft or deprecated")
        if len(str(data.get("title", ""))) > 90:
            err(w, "title longer than 90 characters")
        if len(str(data.get("summary", ""))) > 200:
            err(w, "summary longer than 200 characters")
        trig = data.get("triggers") or []
        if not isinstance(trig, list) or any("{task_condition}" in str(t) for t in trig):
            err(w, "triggers must be a list of real task conditions")
        for ev in data.get("evidence") or []:
            if evidence_types and ev not in evidence_types:
                warn(w, f"evidence '{ev}' is not in vocabulary.yaml#evidence_types")
        if str(data.get("updated", "")) < str(data.get("created", "")):
            err(w, "updated is earlier than created")
        dom = data.get("domain")
        if dom not in domains:
            err(w, f"domain '{dom}' is not in schema/vocabulary.yaml#domains")
        short = domain_short(root, dom) if dom else None
        if dom and dom != "meta" and short is None:
            err(w, f"domains/{dom}/_domain.md is missing")
        exp, short = expected_path(data, short)
        if exp is None:
            err(w, f"id '{uid}' must be <domain_short>.<topic>.<slug>")
        elif exp != w and not w.startswith("archive/"):
            err(w, f"id {uid} belongs at {exp}; rename the file or fix the id")
        if short and uid.split(".")[0] != short:
            err(w, f"ids in domain '{dom}' start with '{short}.'")
        want = schema["sections"].get(kind)
        if want:
            heads = [h.strip() for h in re.findall(r"^## (.+)$", body, flags=re.M)]
            order = [h for h in heads if h in want]
            absent = [s for s in want if s not in heads]
            if absent:
                err(w, f"missing sections for {kind}: {', '.join(absent)}")
            elif order != want:
                err(w, f"sections out of order; expected {' > '.join(want)}")
        tpl = root / "templates" / f"{kind}.md"
        if tpl.exists():
            _, tbody = split_fm(read_text(tpl))
            stubs = {l.strip() for l in tbody.split("\n")
                     if "{" in l and not l.startswith("#") and len(l.strip()) > 3}
            left = [l.strip() for l in body.split("\n") if l.strip() in stubs]
            if left:
                err(w, f"template text left unfilled: {left[0]!r}")
        if re.search(r"[à-ÿ]", body + str(data.get("title", ""))):
            warn(w, "non-ASCII letters found; units are English only")
        if re.search(f"[{DASHES}]", body):
            warn(w, "em or en dash found; the owner's house style bans them")
        e = entries.get(uid)
        if e is None:
            err(w, f"not in manifest.yaml; run: kb.py register {w}")
        else:
            fresh = entry_from(root, p, data)
            stale = [k for k in ENTRY_KEYS if e.get(k) != fresh.get(k)]
            if stale:
                err(w, f"manifest entry is stale ({', '.join(stale)}); run: kb.py register {w}")
    for uid, e in entries.items():
        if uid not in seen:
            err("manifest.yaml", f"{uid} points to {e.get('path')}, which is not a unit file")
    j = root / "journal" / "recognitions.yaml"
    if j.exists():
        try:
            if not isinstance(yaml.safe_load(read_text(j)), (list, type(None))):
                err("journal/recognitions.yaml", "must be a YAML list")
        except yaml.YAMLError:
            err("journal/recognitions.yaml", "not valid YAML")
    cutoff = (dt.date.fromisoformat(today()) - dt.timedelta(days=30)).isoformat()
    for p in sorted((root / "inbox").glob("*.md")) if (root / "inbox").is_dir() else []:
        m = re.match(r"(\d{4}-\d{2}-\d{2})-", p.name)
        if m and m.group(1) < cutoff:
            warn(f"inbox/{p.name}", "older than 30 days; refine it into a unit or archive it")
    return errors, warns


def cmd_validate(root: Path, a) -> int:
    errors, warns = check(root)
    for line in errors + warns:
        print(line)
    n = len(unit_files(root))
    verdict = "FAIL" if errors else "OK"
    print(f"{verdict}: {n} units, {len(errors)} errors, {len(warns)} warnings ({root})")
    return 1 if errors else 0


def cmd_index(root: Path, a) -> int:
    _, _, man = load_manifest(root)
    rank = {"high": 0, "medium": 1, "low": 2}
    units = [u for u in man["units"] if isinstance(u, dict) and u.get("status") != "deprecated"]
    for u in sorted(units, key=lambda u: (rank.get(u.get("confidence"), 3), u["id"])):
        print(f"{u['id']} | {u.get('kind')} | {u.get('confidence')} | "
              + " ; ".join(map(str, u.get("triggers") or [])))
    if not units:
        print("(no units yet)")
    return 0


# ------------------------------------------------------------------ selftest

def selftest() -> int:
    fails = []

    def expect(name, cond):
        if not cond:
            fails.append(name)
        print(("ok   " if cond else "FAIL ") + name)

    def run(argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = main(argv)
            except KBError as e:
                print(e)
                code = 2
        return code, out.getvalue()

    with tempfile.TemporaryDirectory(prefix="kb selftest ") as tmp:
        t = Path(tmp) / "tpl"
        (t / "schema").mkdir(parents=True)
        for d in ("templates", "journal", "inbox", "domains", "meta-skills", "archive"):
            (t / d).mkdir()
        write_text(t / "manifest.yaml", '# registry\nversion: 1\nowner: "{owner_name}"   # set once\n'
                   "updated: 2026-01-01\n\n# entry := {id, path}\nunits: []\n")
        write_text(t / "PROTOCOL.md", "---\nid: root.protocol\ntitle: Rules — all\n---\n"
                   "1. **Extract** — list. See steps 2–7.\n")
        write_text(t / "schema" / "vocabulary.yaml", "version: 1\nevidence_types:\n  - runtime-verified\n"
                   "  - owner-recognized\ndomains: {}   # add when creating — see PROTOCOL\ntags: []\n")
        if (REPO_TEMPLATE / "schema" / "knowledge-unit.schema.yaml").exists():
            shutil.copy(REPO_TEMPLATE / "schema" / "knowledge-unit.schema.yaml", t / "schema")
        write_text(t / "templates" / "pitfall-set.md", "---\nid: {x}\n---\n\n# {topic} pitfalls\n\n"
                   "## Context\n{scope}\n\n## Pitfalls\n| ID | Symptom | Root cause | Fix | Pin |\n"
                   "|---|---|---|---|---|\n| P1 | {symptom} | {cause} | {fix} | {pkg}@{version} |\n\n"
                   "## Related\n- @{unit_id}\n")
        write_text(t / "templates" / "meta-skill.md", "---\nid: meta.{slug}\n---\n\n# {title}\n\n"
                   "## Context\n{when_relevant}\n\n## Principle\n{one_sentence_rule}\n\n## Procedure\n"
                   "1. {step}\n\n## Signals\n- Use when: {signal}\n\n## Anti-patterns\n- {bad}\n\n"
                   "## Related\n- none\n")
        write_text(t / "journal" / "recognitions.yaml", "# Append-only.\n")
        kb = Path(tmp) / "base with space"

        code, out = run(["validate", "--root", str(t)])
        expect("raw template fails validation on the unset owner", code == 1 and "owner" in out)
        code, out = run(["init", str(kb), "--owner", "Ana Tester", "--template", str(t)])
        expect("init succeeds into a path with a space", code == 0)
        prot = read_text(kb / "PROTOCOL.md")
        expect("init strips em and en dashes", not re.search(f"[{DASHES}]", prot)
               and "2-7" in prot and "**Extract**: list" in prot)
        expect("init sets the owner", 'owner: "Ana Tester"' in read_text(kb / "manifest.yaml"))
        code, out = run(["init", str(kb), "--owner", "X", "--template", str(t)])
        expect("init refuses a non-empty destination", code == 2)
        code, out = run(["validate", "--root", str(kb)])
        expect("fresh base validates", code == 0 and "OK: 0 units" in out)

        new = ["new", "--root", str(kb), "--kind", "pitfall-set", "--domain", "ops", "--topic",
               "systemd-timers", "--title", "systemd user timer missed runs",
               "--summary", "why {job} skipped a run", "--trigger", "{job} did not run after suspend",
               "--confidence", "high", "--evidence", "runtime-verified", "--evidence",
               "owner-recognized", "--pin", "systemd=257", "--tag", "systemd"]
        code, out = run(new)
        expect("new without --scope on a new domain is refused", code == 2 and "--scope" in out)
        code, out = run(new + ["--scope", "host operations"])
        unit = kb / "domains" / "ops" / "systemd-timers" / "pitfalls.md"
        expect("new puts a pitfall-set at <topic>/pitfalls.md", code == 0 and unit.exists())
        voc = yaml.safe_load(read_text(kb / "schema" / "vocabulary.yaml"))
        expect("new registers the domain in the vocabulary", "ops" in (voc.get("domains") or {}))
        expect("new creates the domain map", (kb / "domains" / "ops" / "_domain.md").exists())
        code, out = run(["validate", "--root", str(kb)])
        expect("unfilled, unregistered unit fails", code == 1 and "unfilled" in out
               and "not in manifest" in out)
        filled = read_text(unit).replace("{scope}", "user timers").replace(
            "| P1 | {symptom} | {cause} | {fix} | {pkg}@{version} |",
            "| P1 | LAST n/a | no Persistent=true | add it | systemd@257 |").replace(
            "- @{unit_id}", "- none")
        write_text(unit, filled)
        code, out = run(["register", "--root", str(kb), str(unit)])
        code, out = run(["validate", "--root", str(kb)])
        expect("filled and registered unit validates", code == 0)
        dmap = read_text(kb / "domains" / "ops" / "_domain.md")
        expect("register adds the domain-map row and topic",
               "| ops.systemd-timers.pitfalls | pitfall-set | high |" in dmap
               and "- `systemd-timers/`" in dmap)
        code, out = run(new + ["--scope", "host operations"])
        expect("a second new with the same id is refused", code == 2 and "in place" in out)

        write_text(unit, "﻿" + read_text(unit).replace("\n", "\r\n"))
        code, out = run(["validate", "--root", str(kb)])
        expect("BOM and CRLF unit still validates", code == 0)
        write_text(unit, read_text(unit).replace("{job} did not run after suspend",
                                                 "{job} skipped while suspended"))
        code, out = run(["validate", "--root", str(kb)])
        expect("trigger edited without register is caught as stale", code == 1 and "stale" in out)
        run(["register", "--root", str(kb), str(unit)])
        moved = unit.with_name("missed-runs.md")
        unit.rename(moved)
        code, out = run(["validate", "--root", str(kb)])
        expect("id and file name disagreeing is caught", code == 1 and "belongs at" in out)
        moved.rename(unit)

        code, out = run(["new", "--root", str(kb), "--kind", "meta-skill", "--slug", "verify-first",
                         "--title", "verify first", "--summary", "check {x}", "--trigger",
                         "about to report {task} done", "--confidence", "medium", "--evidence",
                         "owner-recognized"])
        expect("meta-skill lands in meta-skills/<slug>.md",
               code == 0 and (kb / "meta-skills" / "verify-first.md").exists())
        code, out = run(["new", "--root", str(kb), "--kind", "pitfall-set", "--domain", "web",
                         "--topic", "e2e", "--title", "e2e waits", "--summary", "s", "--trigger",
                         "{t} flaky", "--confidence", "low", "--evidence", "runtime-verified",
                         "--scope", "web apps", "--short", "w"])
        voc = yaml.safe_load(read_text(kb / "schema" / "vocabulary.yaml"))
        expect("a second domain is appended to the vocabulary",
               {"ops", "web"} <= set(voc.get("domains") or {}))
        expect("--short sets the id prefix",
               "id: w.e2e.pitfalls" in read_text(kb / "domains" / "web" / "e2e" / "pitfalls.md"))

        code, out = run(["journal", "--root", str(kb), "--signal", "owner: 'guarda isso'",
                         "--summary", "timer fix", "--created", "ops.systemd-timers.pitfalls",
                         "--updated", "nope.x.y"])
        j = yaml.safe_load(read_text(kb / "journal" / "recognitions.yaml"))
        expect("journal appends a parseable event", code == 0 and isinstance(j, list) and len(j) == 1)
        expect("journal warns on an unknown id", "nope.x.y" in out)
        old = (dt.date.fromisoformat(today()) - dt.timedelta(days=40)).isoformat()
        write_text(kb / "inbox" / f"{old}-stale.md", "- raw\n")
        _, warns = check(kb)
        expect("inbox item older than 30 days warns", any("older than 30 days" in w for w in warns))
        code, out = run(["index", "--root", str(kb)])
        expect("index lists the high-confidence unit first",
               out.splitlines()[0].startswith("ops.systemd-timers.pitfalls"))

        if (REPO_TEMPLATE / "manifest.yaml").exists():
            real = Path(tmp) / "real"
            code, out = run(["init", str(real), "--owner", "Ana Tester"])
            code2, out2 = run(["validate", "--root", str(real)])
            expect("the vendored knowledge-template initialises and validates",
                   code == 0 and code2 == 0)
            left = [str(p) for p in real.rglob("*") if p.is_file()
                    and re.search(f"[{DASHES}]", read_text(p))]
            expect("no dash survives init of the vendored template", not left)

    print(f"{'FAIL' if fails else 'OK'}: {len(fails)} failed")
    return 1 if fails else 0


# ---------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="kb.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--selftest", action="store_true", help="run the built-in tests and exit")
    sub = ap.add_subparsers(dest="cmd")

    def with_root(p):
        p.add_argument("--root", help="knowledge base root (default: $AGENT_LEARNING_KB or "
                                      "~/.agent-learning/knowledge)")
        return p

    p = sub.add_parser("init", help="instantiate a base from the template")
    p.add_argument("dest")
    p.add_argument("--owner", required=True)
    p.add_argument("--template", help=f"template dir (default: {REPO_TEMPLATE})")
    p = with_root(sub.add_parser("new", help="scaffold a unit whose id and path agree"))
    p.add_argument("--kind", required=True)
    p.add_argument("--domain")
    p.add_argument("--topic")
    p.add_argument("--slug", help="file name without .md (pitfall-set defaults to 'pitfalls')")
    p.add_argument("--title", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--trigger", action="append", required=True,
                   help="task condition with placeholders; repeat for several")
    p.add_argument("--tag", action="append")
    p.add_argument("--confidence", required=True, choices=["high", "medium", "low"])
    p.add_argument("--evidence", action="append", required=True)
    p.add_argument("--pin", action="append", help="package=version; repeat for several")
    p.add_argument("--scope", help="required when the domain is new")
    p.add_argument("--short", help="id prefix for a new domain (default: the domain name)")
    p = with_root(sub.add_parser("register", help="upsert manifest entries and domain-map rows"))
    p.add_argument("paths", nargs="+")
    p = with_root(sub.add_parser("journal", help="append a recognition event"))
    p.add_argument("--signal", required=True, help="the owner's words, quoted")
    p.add_argument("--summary", required=True)
    p.add_argument("--created", action="append")
    p.add_argument("--updated", action="append")
    p.add_argument("--artifacts", action="append")
    p.add_argument("--notes")
    with_root(sub.add_parser("validate", help="check units, manifest, journal and inbox"))
    with_root(sub.add_parser("index", help="one line per active unit"))

    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help()
        return 2
    if a.cmd == "init":
        return cmd_init(a)
    root = Path(a.root or os.environ.get("AGENT_LEARNING_KB") or DEFAULT_ROOT).expanduser()
    return {"new": cmd_new, "register": cmd_register, "journal": cmd_journal,
            "validate": cmd_validate, "index": cmd_index}[a.cmd](root, a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KBError as e:
        print(f"kb.py: {e}", file=sys.stderr)
        sys.exit(2)
