"""Configurable product boundaries without billing or destructive locking."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductAccess:
    tier: str = "beta"
    visible_experiments: int = 3
    benchmark_details: bool = True
    report_export: bool = False
    project_history: bool = False
    builder_diagnostics: bool = False

    def to_dict(self):
        return asdict(self)


FREE_PREVIEW = ProductAccess(
    tier="free_preview", visible_experiments=1, benchmark_details=False,
    report_export=False, project_history=False, builder_diagnostics=False,
)

BETA_ACCESS = ProductAccess()


def access_for_mode(product_mode="creator"):
    """Beta keeps current features available; Builder remains mode-gated."""
    return ProductAccess(**{
        **BETA_ACCESS.to_dict(),
        "builder_diagnostics": str(product_mode).lower() == "builder",
    })
