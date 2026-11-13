# ai-generated: 100% - Copilot implemented the matching rules and command line from the course specification.
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-14..P-24)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote

CLASS_CWES = {
    "secret": (259, 260, 321, 798),
    "injection": (74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336),
    "deserialization": (502,),
    "weak-crypto": (261, 326, 327, 328, 330, 331, 338, 759, 760, 916),
    "insecure-transport": (295, 297, 319, 322, 757),
    "path-traversal": (22, 23, 35, 36, 73),
    "ssrf": (918,),
    "vulnerable-dependency": (937, 1035, 1104, 1395),
    "misconfiguration": (16, 215, 250, 489, 668, 732, 1188),
    "access-control": (284, 285, 639, 862, 863),
}
CWE_TO_CLASSES: dict[str, set[str]] = {}
for _cls, _nums in CLASS_CWES.items():
    for _n in _nums:
        CWE_TO_CLASSES.setdefault(str(_n), set()).add(_cls)

SEMGREP_NAMES = {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}
FIXED_TOOLS = {"trivy", "grype", "osv-scanner", "gitleaks"}
CWE_RE = re.compile(r"(?<![A-Za-z0-9])CWE-([0-9]+)", re.IGNORECASE | re.ASCII)
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")
TRIVY_TAGS = {"vulnerability": "vulnerable-dependency", "secret": "secret", "misconfiguration": "misconfiguration"}


def obj(value, key):
    """A dict member that is itself a dict, else an empty dict (null counts as absent)."""
    if isinstance(value, dict):
        member = value.get(key)
        if isinstance(member, dict):
            return member
    return {}


def items(value, key):
    if isinstance(value, dict):
        member = value.get(key)
        if isinstance(member, list):
            return member
    return []


def is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def tool_id(run: dict) -> str:
    name = obj(obj(run, "tool"), "driver").get("name")
    if not isinstance(name, str):
        return "unknown"
    folded = name.strip().lower()
    if folded in SEMGREP_NAMES:
        return "semgrep"
    if folded in FIXED_TOOLS:
        return folded
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return slug or "unknown"


def result_path(uri: str) -> str:
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    return path


def in_set(path: str, root: str):
    parts = path.split("/")
    if root not in parts:
        return None
    last = len(parts) - 1 - parts[::-1].index(root)
    return "/".join(parts[last:])


def lines_of(location_region: dict):
    start = location_region.get("startLine")
    if not is_int(start) or start < 1:
        return None
    end = location_region.get("endLine")
    if not is_int(end) or end < start:
        end = start
    return start, end


def string_tags(holder: dict) -> list[str]:
    return [t for t in items(obj(holder, "properties"), "tags") if isinstance(t, str)]


def result_classes(tool: str, result: dict, rule: dict) -> set[str]:
    own = obj(result, "properties").get("class")
    if isinstance(own, str) and own in CLASS_CWES:
        return {own}
    rule_tags = string_tags(rule)
    if tool == "gitleaks":
        return {"secret"}
    if tool in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    if tool == "trivy":
        found = {TRIVY_TAGS[t.lower()] for t in rule_tags if t.lower() in TRIVY_TAGS}
        if found:
            return found
    found = set()
    for tag in string_tags(result) + rule_tags:
        for match in CWE_RE.finditer(tag):
            found |= CWE_TO_CLASSES.get(match.group(1).lstrip("0"), set())
    return found or {"other"}


def pep503(text: str) -> str:
    return re.sub(r"[-_.]+", "-", text.lower())


def names_package(result: dict, package) -> bool:
    text = obj(result, "message").get("text")
    if not isinstance(text, str) or not isinstance(package, str):
        return False
    wanted = pep503(package)
    for token in TOKEN_RE.findall(text):
        token = token.strip("._-")
        if token and pep503(token) == wanted:
            return True
    return False


def matches(defect: dict, file: str, classes: set[str], lines, result: dict) -> bool:
    if defect.get("file") != file or defect.get("class") not in classes:
        return False
    if defect["class"] == "vulnerable-dependency":
        return names_package(result, defect.get("package"))
    if lines is None:
        return False
    start, end = lines
    return start <= defect["end_line"] and defect["start_line"] <= end


def ratio(num, den):
    return None if den == 0 else round(num / den, 4)


def confusion_matrix(labels: dict, sarif_documents: list) -> dict:
    root = labels["set"]
    defects = labels["defects"]
    found: dict[str, set[int]] = {}
    false_pos: dict[str, set] = {}
    for document in sarif_documents:
        for run in items(document, "runs"):
            if not isinstance(run, dict):
                continue
            tool = tool_id(run)
            found.setdefault(tool, set())
            false_pos.setdefault(tool, set())
            rules = items(obj(obj(run, "tool"), "driver"), "rules")
            for result in items(run, "results"):
                if not isinstance(result, dict):
                    continue
                kind = result.get("kind")
                if kind is not None and kind != "fail":
                    continue
                if result.get("suppressions"):
                    continue
                locations = items(result, "locations")
                if not locations:
                    continue
                physical = obj(locations[0], "physicalLocation")
                uri = obj(physical, "artifactLocation").get("uri")
                if not isinstance(uri, str) or not uri:
                    continue
                file = in_set(result_path(uri), root)
                if file is None:
                    continue
                lines = lines_of(obj(physical, "region"))
                rule_id = result.get("ruleId")
                rule_id = rule_id if isinstance(rule_id, str) else None
                rule = {}
                if rule_id is not None:
                    for candidate in rules:
                        if isinstance(candidate, dict) and candidate.get("id") == rule_id:
                            rule = candidate
                            break
                classes = result_classes(tool, result, rule)
                hit = [i for i, d in enumerate(defects) if matches(d, file, classes, lines, result)]
                if hit:
                    found[tool].update(hit)
                else:
                    start, end = lines if lines else (None, None)
                    false_pos[tool].add((rule_id, file, start, end))
    tools = {}
    total = len(defects)
    for tool in found:
        tp = len(found[tool])
        fp = len(false_pos[tool])
        fn = total - tp
        tools[tool] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": root, "defects": total, "tools": tools}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8-sig") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8-sig") as fh:
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())