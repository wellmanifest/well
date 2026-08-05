from __future__ import annotations

from pathlib import Path

from wellmanifest.dialects.policy import PolicyDialect
from wellmanifest.governance import lint_policy_document
from wellmanifest.models import Severity
from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "tests" / "fixtures" / "governance-current"


def test_bash_fenced_policy_is_imported_with_warning() -> None:
    source = (CURRENT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    document = WellManifestRuntime().parse(source, dialect="policy", source_name="CONTRIBUTING.md")
    ids = {rule["id"] for rule in document.ir["rules"]}
    assert "C-CONTEXT-001" in ids
    assert "C-CONTEXT-002" in ids
    assert any(item.code == "WM-POLICY-101" and item.severity == Severity.WARNING for item in document.diagnostics)


def test_policy_lint_finds_undeclared_transition_target() -> None:
    source = (CURRENT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    document = WellManifestRuntime().parse(source, dialect="policy", source_name="CONTRIBUTING.md")
    diagnostics = lint_policy_document(document)
    item = next(item for item in diagnostics if item.code == "WM-POLICY-204")
    assert "IN_PROGRESS" in item.message
    assert item.range is not None and item.range.start.line > 300


def test_policy_formatter_rewrites_only_policy_shaped_bash_fences() -> None:
    source = '''# Example

```bash
RULE C-ONE
WHEN TRUE
DO RUN
```

```bash
echo "ordinary shell"
```
'''
    rewritten, count = PolicyDialect.rewrite_fences(source)
    assert count == 1
    assert "```wellm-policy\nRULE C-ONE" in rewritten
    assert '```bash\necho "ordinary shell"' in rewritten


def test_policy_lint_rejects_duplicate_rule_ids() -> None:
    source = '''RULE C-DUP
WHEN A
DO X

RULE C-DUP
WHEN B
DO Y
'''
    document = WellManifestRuntime().parse(source, dialect="policy")
    diagnostics = lint_policy_document(document)
    assert any(item.code == "WM-POLICY-201" and item.severity == Severity.ERROR for item in diagnostics)


def test_policy_document_header_is_not_overwritten_by_legend_placeholders() -> None:
    contributing = CURRENT / "CONTRIBUTING.md"
    source = contributing.read_text(encoding="utf-8")
    document = PolicyDialect().parse(source, source_name=str(contributing))

    assert document.ir["metadata"] == {
        "document": "CONTRIBUTING",
        "version": 7,
        "language": "PL",
        "mode": "PROCEDURAL",
        "purpose": "proces pracy nad repozytorium",
        "policy": "POLICY.md",
    }
