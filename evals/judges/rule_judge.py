from __future__ import annotations
import re


SYNONYM_GROUPS = {
    "girlfriend": ["girlfriend", "gf", "ladki", "partner", "divya"],
    "boyfriend": ["boyfriend", "bf", "ladka", "partner", "aarav"],
    "captain": ["captain"],
    "hamster": ["hamster"],
    "rat": ["rat", "chuha"],
    "daredevil": ["daredevil"],
    "rocky": ["rocky"],
}


def judge_rule(
    response: str,
    expected_checks: list[str],
    disallowed_behaviors: list[str],
) -> dict:
    """Deterministic rule-based judge for 'rule' scored cases.

    Uses keyword/phrase matching against the response text. Each expected check
    and disallowed behavior is evaluated as a natural-language description, so
    this judge looks for obvious signals rather than exact substring matches.
    """
    response_lower = response.lower()
    failures: list[str] = []
    checks_passed = 0
    total_checks = len(expected_checks) + len(disallowed_behaviors)

    for check in expected_checks:
        if _check_passes(response_lower, check):
            checks_passed += 1
        else:
            failures.append(f"EXPECTED NOT MET: {check}")

    for behavior in disallowed_behaviors:
        if _behavior_absent(response_lower, behavior):
            checks_passed += 1
        else:
            failures.append(f"DISALLOWED PRESENT: {behavior}")

    passed = len(failures) == 0
    score = checks_passed / total_checks if total_checks > 0 else 1.0

    return {
        "passed": passed,
        "score": score,
        "checks_passed": checks_passed,
        "checks_total": total_checks,
        "failures": failures,
    }


_NEGATION_PREFIXES = [
    "does not ", "do not ", "should not ", "must not ",
    "doesn't ", "don't ", "shouldn't ", "mustn't ",
    "never ", "no ", "without ",
]


def _check_passes(response_lower: str, check: str) -> bool:
    """Heuristic: extract key terms from the check description and see if
    the response contains them. For terms with known synonyms, any synonym
    in the response counts as a match.

    Handles negation: if the check says "Does not X" or "without X",
    we verify the terms are ABSENT rather than present.
    """
    check_lower = check.lower()
    is_negative = any(check_lower.startswith(p) for p in _NEGATION_PREFIXES)

    key_terms = _extract_key_terms(check)
    if not key_terms:
        return True

    if is_negative:
        return not any(_term_present(response_lower, term) for term in key_terms)
    return any(_term_present(response_lower, term) for term in key_terms)


def _term_present(response_lower: str, term: str) -> bool:
    """Check if term or any of its synonyms appear in the response."""
    if term in response_lower:
        return True
    for canonical, synonyms in SYNONYM_GROUPS.items():
        if term == canonical or term in synonyms:
            return any(syn in response_lower for syn in synonyms)
    return False


def _behavior_absent(response_lower: str, behavior: str) -> bool:
    """Heuristic: extract forbidden terms from the behavior description
    and verify none appear in the response."""
    forbidden = _extract_forbidden_terms(behavior)
    if not forbidden:
        return True
    return not any(term in response_lower for term in forbidden)


def _extract_key_terms(description: str) -> list[str]:
    """Pull concrete values from check descriptions.

    Looks for quoted strings, proper nouns, numbers, and specific keywords.
    """
    terms: list[str] = []

    quoted = re.findall(r"['\"]([^'\"]+)['\"]", description)
    terms.extend(q.lower() for q in quoted)

    numbers = re.findall(r"\b\d+\b", description)
    terms.extend(numbers)

    proper_nouns = [
        "spark", "pixel", "divya", "rohan", "meera", "priya", "aarav",
        "rakesh", "arjun", "daredevil", "rocky", "nisha", "ic-14829",
        "ic14829", "dtu", "bruno", "hamster", "rat", "girlfriend",
        "boyfriend", "captain", "green tea", "makhana",
    ]
    desc_lower = description.lower()
    for noun in proper_nouns:
        if noun in desc_lower:
            terms.append(noun)

    return list(set(terms))


def _extract_forbidden_terms(description: str) -> list[str]:
    """Pull terms that should NOT appear from disallowed behavior descriptions."""
    terms: list[str] = []
    import re

    quoted = re.findall(r"['\"]([^'\"]+)['\"]", description)
    terms.extend(q.lower() for q in quoted)

    desc_lower = description.lower()

    fabrication_markers = [
        "fabricating", "inventing", "guessing", "making up",
    ]
    if any(m in desc_lower for m in fabrication_markers):
        specific_values = re.findall(r"(?:e\.g\.\s*|like\s+)['\"]?([^'\",.]+)", desc_lower)
        terms.extend(v.strip().lower() for v in specific_values if len(v.strip()) > 2)

    return list(set(terms))
