"""Authoritative registry of current and planned intelligence modules."""

from core.stratify_report import run_stratify_report
from stratify_platform.contracts import IntelligenceModule, IntelligenceStage, ModuleStatus


INTRO_STAGES = (
    IntelligenceStage.ACQUIRE, IntelligenceStage.OBSERVE,
    IntelligenceStage.UNDERSTAND, IntelligenceStage.REASON,
    IntelligenceStage.RECOMMEND, IntelligenceStage.VALIDATE,
    IntelligenceStage.PRESENT,
)


MODULE_REGISTRY = {
    "intro_intelligence": IntelligenceModule(
        module_id="intro_intelligence",
        name="Intro Intelligence",
        description="Observe the opening, understand its creative signals, and generate controlled experiments.",
        status=ModuleStatus.AVAILABLE,
        version="1.0",
        supported_inputs=("youtube_url", "video_upload"),
        capabilities=("intro_observation", "intro_timeline", "creator_experiments", "optional_benchmark_validation"),
        stages=INTRO_STAGES,
        runner=run_stratify_report,
    ),
    "story_intelligence": IntelligenceModule("story_intelligence", "Story Intelligence", "Understand story structure and progression across a creative asset.", ModuleStatus.PLANNED, "planned", ("video",), (), (), None),
    "editing_intelligence": IntelligenceModule("editing_intelligence", "Editing Intelligence", "Analyze editing decisions across the complete creative.", ModuleStatus.PLANNED, "planned", ("video",), (), (), None),
    "packaging_intelligence": IntelligenceModule("packaging_intelligence", "Packaging Intelligence", "Evaluate titles, thumbnails, and audience-facing presentation.", ModuleStatus.PLANNED, "planned", ("metadata", "image"), (), (), None),
    "audience_intelligence": IntelligenceModule("audience_intelligence", "Audience Intelligence", "Connect creative decisions with reliable audience evidence.", ModuleStatus.PLANNED, "planned", ("analytics",), (), (), None),
    "creator_intelligence": IntelligenceModule("creator_intelligence", "Creator Intelligence", "Build reusable learning from a creator's completed experiments.", ModuleStatus.PLANNED, "planned", ("project_history",), (), (), None),
}


def get_module(module_id):
    try:
        return MODULE_REGISTRY[module_id]
    except KeyError as exc:
        raise KeyError(f"Unknown intelligence module: {module_id}") from exc


def list_modules():
    return tuple(MODULE_REGISTRY.values())


def run_module(module_id, **kwargs):
    return get_module(module_id).run(**kwargs)
