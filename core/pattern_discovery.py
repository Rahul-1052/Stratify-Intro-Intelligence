"""
Generic Benchmark Pattern Discovery for Stratify 2.0.

Design principle:
    This module must not know what any feature means.

It does not contain predefined fields such as:
    - visual_energy
    - scene_type
    - payoff_teased
    - first_frame_strength
    - pacing_level

Instead, it discovers every available feature dynamically from the
user, stronger benchmark, and lower benchmark evidence.

The same comparison logic therefore works automatically when new
observation fields are added elsewhere in Stratify.
"""

from collections import Counter
import json
import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence


# These values represent unavailable evidence.
#
# This is not a content rule or feature taxonomy. It simply prevents missing
# values from being treated as real benchmark observations.
UNKNOWN_VALUES = {
    None,
    "",
    "unknown",
    "unavailable",
    "not_available",
    "not_detected",
    "unclear",
    "null",
    "none",
}


def _normalize_value(value: Any) -> Any:
    """
    Normalize a raw feature value before comparison.

    Strings are cleaned so values such as:

        "High"
        " high "
        "HIGH"

    are treated as the same observation.

    Numeric and Boolean values are preserved.
    """

    if isinstance(value, str):
        cleaned = " ".join(value.strip().lower().split())

        if cleaned in UNKNOWN_VALUES:
            return None

        return cleaned

    if isinstance(value, float) and not math.isfinite(value):
        return None

    # Keep structured provider evidence deterministic and hashable so a single
    # malformed field cannot abort learning from every other valid field.
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)

    if isinstance(value, (list, tuple, set)):
        sequence = list(value)
        if isinstance(value, set):
            sequence = sorted(sequence, key=repr)
        return json.dumps(sequence, ensure_ascii=False, default=str)

    try:
        if value in UNKNOWN_VALUES:
            return None
    except TypeError:
        return str(value)

    return value


def _display_value(value: Any) -> str:
    """
    Convert a normalized value into readable report text.
    """

    if value is None:
        return "unknown"

    if isinstance(value, bool):
        return "present" if value else "not present"

    return str(value)


def _humanize_feature_name(feature: str) -> str:
    """
    Convert backend field names into readable labels.

    Example:

        hook_visible_in_first_3_seconds
        becomes
        Hook Visible In First 3 Seconds

    This does not attach meaning to the feature. It only formats its name.
    """

    return str(feature or "feature").replace("_", " ").strip().title()


def _extract_summary(item: Any) -> Dict[str, Any]:
    """
    Extract a feature summary from any supported Stratify result shape.

    Current benchmark objects may contain features as:

        {
            "feature_summary": {...}
        }

    or:

        {
            "features": {
                "feature_summary": {...}
            }
        }

    A direct feature dictionary is also accepted to keep the function
    resilient as the architecture evolves.
    """

    if not isinstance(item, Mapping):
        return {}

    direct_summary = item.get("feature_summary")

    if isinstance(direct_summary, Mapping):
        return dict(direct_summary)

    features = item.get("features")

    if isinstance(features, Mapping):
        nested_summary = features.get("feature_summary")

        if isinstance(nested_summary, Mapping):
            return dict(nested_summary)

    # A direct dictionary can be used when it does not look like a wrapper.
    wrapper_keys = {
        "video",
        "video_id",
        "title",
        "features",
        "feature_summary",
        "status",
        "warnings",
    }

    if not wrapper_keys.intersection(item.keys()):
        return dict(item)

    return {}


def _discover_feature_keys(
    top_features: Sequence[Any],
    lower_features: Sequence[Any],
    user_features: Any,
) -> List[str]:
    """
    Discover all comparable feature fields dynamically.

    No feature names are declared inside this module.

    Whenever another part of Stratify adds a new observation field, this
    function automatically includes it in comparison.
    """

    discovered = set()

    for item in list(top_features or []) + list(lower_features or []):
        discovered.update(_extract_summary(item).keys())

    discovered.update(_extract_summary(user_features).keys())

    return sorted(str(key) for key in discovered)


def _collect_feature_values(
    items: Sequence[Any],
    feature: str,
) -> List[Any]:
    """
    Collect every usable value observed for one feature in a benchmark group.
    """

    values = []

    for item in items or []:
        summary = _extract_summary(item)
        value = _normalize_value(summary.get(feature))

        if value is not None:
            values.append(value)

    return values


def _distribution(values: Iterable[Any]) -> Dict[Any, int]:
    """
    Build the observed value distribution for one feature.
    """

    return dict(Counter(values))


def _dominant_observation(values: Sequence[Any], min_support: int = 2) -> Dict[str, Any]:
    """
    Summarize the most frequent value in an observed group.

    Stability is derived from the current sample itself.

    No feature-specific rule is used.

    A value is considered stable when:
        - it occurs at least three times, and
        - it is not tied with another value.

    The share is retained as evidence rather than being hidden behind
    a feature-specific heuristic.
    """

    values = list(values or [])

    if not values:
        return {
            "value": None,
            "count": 0,
            "total": 0,
            "share": 0.0,
            "stable": False,
            "distribution": {},
        }

    ranked = Counter(values).most_common()

    dominant_value, dominant_count = ranked[0]
    total = len(values)

    tied = (
        len(ranked) > 1
        and ranked[1][1] == dominant_count
    )

    return {
        "value": dominant_value,
        "count": dominant_count,
        "total": total,
        "share": round(dominant_count / total, 4),
        "stable": dominant_count >= max(int(min_support), 2) and not tied,
        "distribution": dict(ranked),
    }


def _classify_position(
    user_value: Any,
    top: Mapping[str, Any],
    lower: Mapping[str, Any],
) -> str:
    """
    Position the user using only observed group relationships.

    Possible results:

    insufficient_evidence
        One or both benchmark groups do not contain a stable pattern.

    non_discriminative
        Stronger and lower benchmark groups share the same dominant value.

    aligned_with_top
        User matches the stronger group and differs from the lower group.

    aligned_with_lower
        User matches the lower group and differs from the stronger group.

    outside_both_groups
        User differs from both observed group values.

    user_value_unavailable
        The current intro did not produce a usable value.

    Importantly, a user who differs from both groups does not receive a
    directional recommendation.
    """

    if user_value is None:
        return "user_value_unavailable"

    if not top.get("stable") or not lower.get("stable"):
        return "insufficient_evidence"

    top_value = top.get("value")
    lower_value = lower.get("value")

    if top_value == lower_value:
        return "non_discriminative"

    if user_value == top_value:
        return "aligned_with_top"

    if user_value == lower_value:
        return "aligned_with_lower"

    return "outside_both_groups"


def _build_explanation(
    feature_label: str,
    user_value: Any,
    top: Mapping[str, Any],
    lower: Mapping[str, Any],
    status: str,
) -> str:
    """
    Generate a neutral explanation from the observed values.

    No feature-specific interpretation is introduced.
    """

    user_text = _display_value(user_value)
    top_text = _display_value(top.get("value"))
    lower_text = _display_value(lower.get("value"))

    if status == "user_value_unavailable":
        return (
            f"{feature_label}: the current intro did not produce a usable "
            "value, so Stratify could not position this feature."
        )

    if status == "insufficient_evidence":
        return (
            f"{feature_label}: one or both benchmark groups did not show a "
            "stable dominant value, so no directional conclusion was made."
        )

    if status == "non_discriminative":
        return (
            f"{feature_label}: both benchmark groups were dominated by "
            f"'{top_text}', so this feature did not distinguish stronger "
            "and lower-performing intros."
        )

    if status == "aligned_with_top":
        return (
            f"{feature_label}: the current value '{user_text}' matches the "
            f"stronger benchmark value '{top_text}' and differs from the "
            f"lower benchmark value '{lower_text}'."
        )

    if status == "aligned_with_lower":
        return (
            f"{feature_label}: the current value '{user_text}' matches the "
            f"lower benchmark value '{lower_text}' and differs from the "
            f"stronger benchmark value '{top_text}'."
        )

    return (
        f"{feature_label}: the current value '{user_text}' differs from both "
        f"the stronger benchmark value '{top_text}' and the lower benchmark "
        f"value '{lower_text}'. The current sample does not establish which "
        "alternative should be tested."
    )


def _build_evidence_text(
    group_name: str,
    dominant: Mapping[str, Any],
) -> str:
    """
    Describe the observed benchmark distribution.
    """

    if dominant.get("total", 0) == 0:
        return f"{group_name}: no usable values were observed."

    if not dominant.get("stable"):
        return (
            f"{group_name}: no stable dominant value was found across "
            f"{dominant.get('total', 0)} observed intro(s)."
        )

    return (
        f"{group_name}: '{_display_value(dominant.get('value'))}' appeared "
        f"in {dominant.get('count', 0)} of "
        f"{dominant.get('total', 0)} observed intro(s)."
    )


def _build_generic_test(
    feature: str,
    user_value: Any,
    top_value: Any,
) -> Dict[str, Any]:
    """
    Build a schema-agnostic experiment.

    The test does not assume whether a feature represents energy, pacing,
    conflict, text, motion, or any other concept.

    It simply compares the stronger observed value against the current value.
    """

    feature_label = _humanize_feature_name(feature)
    user_text = _display_value(user_value)
    top_text = _display_value(top_value)

    return {
        "title": f"Test the observed {feature_label.lower()} difference",
        "suggested_test": (
            f"Create one intro version using the stronger benchmark value "
            f"'{top_text}' for {feature_label.lower()}, and compare it with "
            f"the current value '{user_text}'. Keep the remaining intro "
            "elements as consistent as possible."
        ),
    }


def _evidence_confidence(
    top: Mapping[str, Any],
    lower: Mapping[str, Any],
) -> str:
    """
    Derive recommendation confidence from observed evidence coverage.

    Confidence is not tied to a particular feature.

    The function uses:
        - whether both groups contain stable patterns,
        - how many examples support each group,
        - and the dominant share in each group.
    """

    if not top.get("stable") or not lower.get("stable"):
        return "low"

    minimum_group_size = min(
        top.get("total", 0),
        lower.get("total", 0),
    )

    minimum_share = min(
        top.get("share", 0.0),
        lower.get("share", 0.0),
    )

    if minimum_group_size >= 3 and minimum_share >= (2 / 3):
        return "moderate"

    return "limited"


def _build_recommendation(
    comparison: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Create an experiment only for a directionally supported difference.

    This function is called only when the user matches the lower benchmark
    group and the stronger group has a different stable value.
    """

    feature = comparison["feature"]
    user_value = comparison["user_value"]
    top = comparison["top"]
    lower = comparison["lower"]

    test = _build_generic_test(
        feature=feature,
        user_value=user_value,
        top_value=top.get("value"),
    )

    return {
        "feature": feature,
        "title": test["title"],
        "evidence": (
            f"{_build_evidence_text('Stronger benchmarks', top)} "
            f"{_build_evidence_text('Lower benchmarks', lower)} "
            f"The current intro matched the lower benchmark value "
            f"'{_display_value(user_value)}'."
        ),
        "why_it_matters": (
            "The current intro matches the dominant value observed in the "
            "lower-performing benchmark group while the stronger group shows "
            "a different stable value. This is correlational evidence and "
            "should be tested rather than treated as a guaranteed cause."
        ),
        "suggested_test": test["suggested_test"],
        "confidence": _evidence_confidence(top, lower),
    }


def _overall_confidence(
    top_features: Sequence[Any],
    lower_features: Sequence[Any],
    comparisons: Sequence[Mapping[str, Any]],
) -> Dict[str, str]:
    """
    Summarize confidence across the full benchmark comparison.

    No specific feature count is required by name.

    Confidence depends on:
        - how many benchmark intros produced evidence,
        - and how many dynamically discovered features produced a usable
          directional comparison.
    """

    top_count = sum(
        bool(_extract_summary(item))
        for item in top_features or []
    )

    lower_count = sum(
        bool(_extract_summary(item))
        for item in lower_features or []
    )

    directional_count = sum(
        item.get("status")
        in {
            "aligned_with_top",
            "aligned_with_lower",
        }
        for item in comparisons
    )

    if (
        top_count >= 3
        and lower_count >= 3
        and directional_count >= 2
    ):
        return {
            "level": "moderate",
            "reason": (
                "Three stronger and three lower benchmark intros produced "
                "usable evidence, with multiple dynamically discovered "
                "features showing directional group contrast."
            ),
        }

    if (
        top_count >= 2
        and lower_count >= 2
        and directional_count >= 1
    ):
        return {
            "level": "limited",
            "reason": (
                "Both benchmark groups produced usable evidence, but the "
                "sample or number of directional contrasts remains small."
            ),
        }

    return {
        "level": "low",
        "reason": (
            "The current benchmark sample did not produce enough stable, "
            "directional evidence."
        ),
    }


def _build_final_verdict(
    comparisons: Sequence[Mapping[str, Any]],
    confidence: str,
) -> str:
    """
    Build a verdict only from generic comparison statuses.
    """

    aligned_top = sum(
        item.get("status") == "aligned_with_top"
        for item in comparisons
    )

    aligned_lower = sum(
        item.get("status") == "aligned_with_lower"
        for item in comparisons
    )

    outside_both = sum(
        item.get("status") == "outside_both_groups"
        for item in comparisons
    )

    if confidence == "low":
        return (
            "The available benchmark evidence is too limited for a reliable "
            "directional position."
        )

    if aligned_lower:
        return (
            f"The current intro matches {aligned_lower} dynamically discovered "
            f"lower-benchmark pattern(s) and {aligned_top} stronger-benchmark "
            f"pattern(s). {outside_both} additional difference(s) were not "
            "used because the user matched neither benchmark group."
        )

    if aligned_top:
        return (
            f"The current intro matches {aligned_top} dynamically discovered "
            "stronger-benchmark pattern(s), with no supported lower-group "
            f"match. {outside_both} unmatched difference(s) were withheld."
        )

    if outside_both:
        return (
            f"{outside_both} difference(s) were observed, but the current "
            "intro matched neither benchmark group. Stratify does not have a "
            "supported direction for those differences."
        )

    return (
        "No dynamically discovered feature produced a stable directional "
        "contrast for the current intro."
    )


def discover_patterns(
    top_features,
    lower_features,
    user_features,
    min_support=2,
):
    """
    Main schema-agnostic pattern-discovery entry point.

    Every output is derived from the feature fields present in the current
    evidence. Adding a new feature elsewhere in Stratify does not require a
    code change here.
    """

    feature_keys = _discover_feature_keys(
        top_features=top_features,
        lower_features=lower_features,
        user_features=user_features,
    )

    user_summary = _extract_summary(user_features)

    comparisons = []
    risk_signals = []
    alignments = []
    ambiguous_differences = []
    recommendations = []

    for feature in feature_keys:
        # Collect all observed values for this dynamically discovered field.
        top_values = _collect_feature_values(
            top_features,
            feature,
        )

        lower_values = _collect_feature_values(
            lower_features,
            feature,
        )

        user_value = _normalize_value(
            user_summary.get(feature)
        )

        # Determine each group's dominant observation.
        top = _dominant_observation(top_values, min_support=min_support)
        lower = _dominant_observation(lower_values, min_support=min_support)

        # Position the user only from relationships in the current sample.
        status = _classify_position(
            user_value=user_value,
            top=top,
            lower=lower,
        )

        label = _humanize_feature_name(feature)

        comparison = {
            "feature": feature,
            "label": label,
            "actionable": status in {
                "aligned_with_top",
                "aligned_with_lower",
            },
            "user_value": _display_value(user_value),
            "top_dominant_value": _display_value(
                top.get("value")
            ),
            "top_evidence_count": top.get("count", 0),
            "top_evidence_total": top.get("total", 0),
            "top_evidence_share": top.get("share", 0.0),
            "top_evidence": _build_evidence_text(
                "Top benchmarks",
                top,
            ),
            "lower_dominant_value": _display_value(
                lower.get("value")
            ),
            "lower_evidence_count": lower.get("count", 0),
            "lower_evidence_total": lower.get("total", 0),
            "lower_evidence_share": lower.get("share", 0.0),
            "lower_evidence": _build_evidence_text(
                "Lower benchmarks",
                lower,
            ),
            "status": status,
            "explanation": _build_explanation(
                feature_label=label,
                user_value=user_value,
                top=top,
                lower=lower,
                status=status,
            ),

            # Internal evidence objects are retained so recommendation
            # generation does not need to reconstruct the distributions.
            "top": top,
            "lower": lower,
            "raw_user_value": user_value,
        }

        comparisons.append(comparison)

        signal = {
            "feature": feature,
            "label": label,
            "user_value": comparison["user_value"],
            "top_dominant_value": (
                comparison["top_dominant_value"]
            ),
            "lower_dominant_value": (
                comparison["lower_dominant_value"]
            ),
            "evidence": (
                f"{comparison['top_evidence']} "
                f"{comparison['lower_evidence']}"
            ),
            "explanation": comparison["explanation"],
        }

        if status == "aligned_with_top":
            alignments.append(signal)

        elif status == "aligned_with_lower":
            # A recommendation is allowed only in this state.
            risk_signals.append(signal)
            recommendations.append(
                _build_recommendation(
                    comparison={
                        "feature": feature,
                        "user_value": user_value,
                        "top": top,
                        "lower": lower,
                    }
                )
            )

        elif status == "outside_both_groups":
            ambiguous_differences.append(signal)

    confidence = _overall_confidence(
        top_features=top_features,
        lower_features=lower_features,
        comparisons=comparisons,
    )

    # Remove internal comparison objects before sending data to the UI.
    public_comparisons = []

    for comparison in comparisons:
        public_item = {
            key: value
            for key, value in comparison.items()
            if key not in {
                "top",
                "lower",
                "raw_user_value",
            }
        }

        public_comparisons.append(public_item)

    return {
        "feature_comparison": public_comparisons,

        # These compatibility keys remain because the current Streamlit
        # interface expects them. They contain dynamically discovered fields.
        "visual_comparisons": public_comparisons,
        "storytelling_comparisons": [],

        "user_position": [
            item["explanation"]
            for item in public_comparisons
            if item["status"]
            in {
                "aligned_with_top",
                "aligned_with_lower",
            }
        ],

        # The previous concept of a "missing winning feature" is intentionally
        # removed because differing from both groups does not establish a
        # supported direction.
        "missing_winning_features": [],

        "aligned_features": alignments,
        "risk_signals": risk_signals,
        "ambiguous_differences": ambiguous_differences,

        # Recommendations are generated only when the current intro matches
        # the lower benchmark group and differs from a stable stronger group.
        "recommendations": recommendations,
        "strongest_opportunities": risk_signals,
        "top_creator_experiments": recommendations[:3],

        "final_verdict": _build_final_verdict(
            comparisons=public_comparisons,
            confidence=confidence["level"],
        ),

        "confidence": confidence["level"],
        "confidence_reason": confidence["reason"],

        # Helpful Builder Mode metadata.
        "discovered_feature_count": len(feature_keys),
        "discovered_features": feature_keys,
    }
