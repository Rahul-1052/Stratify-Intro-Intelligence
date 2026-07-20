"""Customer-facing report derived from observed intro evidence.

Benchmark findings may enrich this report, but are never required to produce it.
"""

from collections import Counter


UNKNOWN = {"", "unknown", "none", "n/a", "unavailable", "not detected"}


def _text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(filter(None, (_text(item) for item in value)))
    if isinstance(value, dict):
        return ", ".join(f"{key.replace('_', ' ')}: {_text(item)}" for key, item in value.items() if _text(item))
    value = str(value).strip()
    return "" if value.lower() in UNKNOWN else value


def _observation(report):
    intro = report.get("intro_observation") or {}
    return intro.get("observation") or intro.get("observations") or {}


def _features(report):
    return (report.get("feature_report") or {}).get("feature_summary") or {}


def _frames(report):
    vision = report.get("vision") or {}
    return vision.get("frame_observations") or []


def _first(mapping, *keys):
    for key in keys:
        value = _text(mapping.get(key))
        if value:
            return value
    return ""


def _timeline(report):
    frames = _frames(report)
    entries = []
    for index, frame in enumerate(frames[:8]):
        timestamp = frame.get("timestamp", index)
        signals = []
        for key, label in (("scene_type", "scene"), ("visual_energy", "energy"), ("dominant_lighting", "lighting")):
            value = _text(frame.get(key))
            if value:
                signals.append(f"{label}: {value}")
        if frame.get("human_presence") is True:
            signals.append("person visible")
        if frame.get("text_overlay") is True:
            signals.append("text visible")
        entries.append({"time": f"{float(timestamp):.0f}s", "observation": "; ".join(signals) or "Frame sampled; limited visual signals detected."})
    if entries:
        return entries
    observation = _observation(report)
    opening = _first(observation, "opening_summary", "first_impression")
    return [{"time": "Opening", "observation": opening or "Intro evidence was limited; no visual detail is being inferred."}]


def _observable_signals(report):
    observation, features, frames = _observation(report), _features(report), _frames(report)
    signals = []
    candidates = (
        ("Opening", _first(observation, "opening_summary", "first_impression")),
        ("Hook", _first(observation, "hook_type", "opening_action_type") or _first(features, "hook_type", "opening_mode")),
        ("Subject", _first(observation, "main_subject", "subject_clarity") or _first(features, "main_subject")),
        ("Promise", _first(observation, "story_promise", "payoff_teased")),
        ("Pacing", _first(features, "pacing", "pace", "visual_energy")),
        ("Text", _first(features, "text_overlay", "on_screen_text")),
    )
    for label, value in candidates:
        if value:
            signals.append({"label": label, "value": value, "source": "direct_intro_observation"})
    if frames:
        energies = [_text(frame.get("visual_energy")) for frame in frames]
        energies = [item for item in energies if item]
        if energies and not any(item["label"] == "Pacing" for item in signals):
            signals.append({"label": "Visual energy", "value": Counter(energies).most_common(1)[0][0], "source": "sampled_intro_frames"})
    return signals


def _experiments(signals):
    by_label = {item["label"].lower(): item for item in signals}
    templates = [
        ("Clarify the first-frame promise", "Opening", "Create a second cut that states or shows the core promise in the first visible beat. Keep the rest unchanged.", "Compare whether the promise is easier to identify from the opening frame alone."),
        ("Test an earlier visual change", "Pacing", "Create a version with one meaningful shot, subject, or composition change earlier in the opening. Keep the message unchanged.", "Compare the first seconds side by side for visible momentum; this does not claim a retention outcome."),
        ("Test a cleaner information hierarchy", "Text", "Create one version with a single concise on-screen message and one version without it. Keep imagery and timing unchanged.", "Compare which version communicates the opening idea with less visual competition."),
        ("Make the main subject unmistakable", "Subject", "Create an alternate opening where the observed main subject is visually dominant immediately.", "Compare whether a first-time viewer can identify the subject without title or audio context."),
        ("Strengthen the observable hook", "Hook", "Create an alternate first beat that makes the observed hook more explicit while preserving the same content promise.", "Compare which opening makes the intended action or question easier to describe."),
    ]
    experiments = []
    for title, preferred, action, validation in templates:
        evidence = by_label.get(preferred.lower()) or (signals[len(experiments) % len(signals)] if signals else None)
        evidence_text = f"Observed {evidence['label'].lower()}: {evidence['value']}." if evidence else "Visual intro evidence was unavailable; use an uploaded opening clip before interpreting this test."
        experiments.append({"title": title, "suggested_test": action, "why_it_matters": evidence_text, "validation": validation, "confidence": "Observation-backed" if evidence else "Needs observation", "evidence_source": evidence.get("source") if evidence else "acquisition_status", "benchmark_supported": False})
        if len(experiments) == 3:
            break
    return experiments


def build_creator_report(report):
    signals = _observable_signals(report)
    benchmark = report.get("benchmark") or {}
    quality = benchmark.get("benchmark_quality") or {}
    patterns = report.get("patterns") or {}
    benchmark_experiments = patterns.get("top_creator_experiments") or patterns.get("recommendations") or []
    experiments = []
    if quality.get("eligible_for_directional_learning"):
        for item in benchmark_experiments[:3]:
            enriched = dict(item)
            enriched["benchmark_supported"] = True
            enriched["evidence_source"] = "qualified_benchmark_comparison"
            experiments.append(enriched)
    for item in _experiments(signals):
        if len(experiments) >= 3:
            break
        if item["title"] not in {existing.get("title") for existing in experiments}:
            experiments.append(item)

    opening = signals[0]["value"] if signals else "The intro could not be visually characterized from the available frames."
    working = [f"{item['label']}: {item['value']}" for item in signals[:3]]
    if not working:
        working = ["Stratify preserved uncertainty instead of inferring unseen intro behavior."]
    opportunity = experiments[0] if experiments else {}
    return {
        "opening_snapshot": {"summary": opening, "signals": signals[:6]},
        "intro_timeline": _timeline(report),
        "whats_working": working,
        "biggest_opportunity": {"title": opportunity.get("title", "Improve observable opening clarity"), "summary": opportunity.get("why_it_matters", "Use the next controlled edit to make the opening easier to interpret.")},
        "experiments": experiments[:3],
        "evidence_validation": {"status": "validated" if quality.get("eligible_for_directional_learning") else "observation_only", "label": "Benchmark-enriched" if quality.get("eligible_for_directional_learning") else "Observation-backed; benchmark validation unavailable", "benchmark_supported": bool(quality.get("eligible_for_directional_learning")), "benchmark_quality": quality},
    }
