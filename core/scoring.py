def compute_quality_score(content: str, title: str | None, bad_hits: int = 0) -> float:
    score = 100
    length = len(content or "")
    if length == 0:
        return 0
    if length < 300:
        score -= 40
    elif length < 800:
        score -= 20
    elif length < 1500:
        score -= 10
    if not title:
        score -= 15
    score -= min(bad_hits * 20, 40)
    words = len(content.split())
    if length > 0:
        density = words / (length + 1)
        if density < 0.08:
            score -= 10
    return max(0, min(score, 100))