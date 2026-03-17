"""Moat metrics snapshot model — tracks intelligence moat health over time.

Stores periodic snapshots of the five core success metrics defined in the
Technical Implementation Moat Strategy. Each snapshot captures the full
state at a point in time, enabling trend analysis and target tracking.
"""

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class MoatMetricSnapshot(Base, UUIDMixin, TimestampMixin):
    """Point-in-time snapshot of all intelligence moat success metrics.

    Captured on a schedule (daily) and on-demand via API.

    Core metrics (from the strategy doc):
      1. Entity Graph Coverage — # of entities, verified count, relationships
      2. Causal Chains Discovered — validated chains with high confidence
      3. Prediction Accuracy — % of predictions validated as accurate
      4. Replicability Score — % of outputs ChatGPT could replicate
      5. User Retention (DAU/MAU) — daily/monthly active user ratio

    Additional operational metrics are stored in the details JSONB.
    """

    __tablename__ = "moat_metric_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_date", name="uq_moat_metric_snapshots_date"),
    )

    # Timing
    snapshot_date: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # YYYY-MM-DD

    # ── Metric 1: Entity Graph Coverage ──────────────────────────────
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entity_verified_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    entity_relationship_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    entity_source_profile_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # ── Metric 2: Causal Chains Discovered ───────────────────────────
    causal_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    causal_edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    causal_chain_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # validated chains with confidence >= 0.6

    # ── Metric 3: Prediction Accuracy ────────────────────────────────
    prediction_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prediction_accurate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prediction_inaccurate: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    prediction_accuracy_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0..100

    # ── Metric 4: Replicability Score ────────────────────────────────
    replicability_tests_run: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    replicability_score_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0..100, lower is better

    # ── Metric 5: User Retention (DAU/MAU) ───────────────────────────
    dau: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Daily active users
    mau: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Monthly active users
    dau_mau_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1

    # ── Overall Health ───────────────────────────────────────────────
    moat_health_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Composite 0..100

    # Full detail breakdown (for drill-down)
    details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    def __repr__(self) -> str:
        return (
            f"<MoatMetricSnapshot {self.snapshot_date} "
            f"health={self.moat_health_score}>"
        )
