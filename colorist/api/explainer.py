from colorist.rules.models import Formula


def explain(formula: Formula) -> str:
    lines = ["Объяснение:"]
    for step in formula.steps:
        lines.append(f"- [{step.rule_id}] {step.text}")
    lines.append(
        f"- Итог: {formula.total_grams:g} г красителя, оксид {formula.oxide_percent:g}%, "
        f"{formula.mix_ratio}, {formula.time_min} мин."
    )
    return "\n".join(lines)
