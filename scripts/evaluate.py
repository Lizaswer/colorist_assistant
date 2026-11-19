from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from colorist.cases import evaluate_case, load_cases


def _mark(value: bool | None) -> str:
    if value is None:
        return "SKIP"
    return "OK" if value else "FAIL"


def main() -> int:
    cases = load_cases()
    lines = ["# Evaluation report", "", "| Case | Verified | Formula | Risks |", "|---|---:|---:|---:|"]
    failures = 0
    skipped = 0
    for case in cases:
        result = evaluate_case(case)
        if result.formula_match is None and result.risk_match is None:
            skipped += 1
        elif not ((result.formula_match is not False) and (result.risk_match is not False)):
            failures += 1
        lines.append(
            f"| {result.case_id} | {'yes' if result.verified else 'no'} | "
            f"{_mark(result.formula_match)} | {_mark(result.risk_match)} |"
        )
        if result.error:
            lines.extend(["", f"> Calculator error: {result.error}", ""])
        if result.skipped_reason:
            lines.extend(["", f"> Skipped: {result.skipped_reason}", ""])
        if result.known_gap:
            lines.extend(["", f"> Known gap: {result.known_gap}", ""])
    lines.extend(["", f"Итого: {len(cases)} кейсов, {failures} с расхождением, {skipped} пропущено движком."])
    out = Path("docs/evaluation/report.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
