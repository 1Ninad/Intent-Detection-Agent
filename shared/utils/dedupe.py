def dedupe_signals(signals):
    seen = set()
    deduped = []
    for s in signals:
        if s.id not in seen:
            deduped.append(s)
            seen.add(s.id)
    return deduped
