from core.brain.insight_engine import generate_insights
from core.brain.experiment_engine import generate_experiments
from core.brain.report_engine import build_creator_brain_report


def build_stratify_brain(patterns, category=None, benchmark=None):
    insights = generate_insights(patterns)
    experiments = generate_experiments(insights)

    return build_creator_brain_report(
        insights=insights,
        experiments=experiments,
        category=category or {},
        benchmark=benchmark or {},
    )