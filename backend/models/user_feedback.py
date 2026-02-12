"""User feedback model — tracks user interactions for network effect learning.

Captures every meaningful user interaction with signals, briefs, and
recommendations to build the feedback loop that makes intelligence
better over time. This is the foundation of the network effect moat.
"""

from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class UserFeedback(Base, UUIDMixin, TimestampMixin):
    """User feedback / interaction event for intelligence improvement.

    feedback_type values:
      - signal_useful: User marked signal as useful
      - signal_not_useful: User marked signal as not useful
      - signal_saved: User bookmarked/saved a signal
      - signal_shared: User shared a signal
      - signal_dismissed: User dismissed an alert
      - brief_useful: Brief marked as helpful
      - brief_shared: Brief shared externally
      - recommendation_clicked: User clicked on a recommendation
      - recommendation_dismissed: User dismissed recommendation
      - search_clicked: User clicked a search result
      - chat_followup: User asked follow-up in chat (interest signal)
      - causal_annotation: User annotated causal relationship
      - expert_correction: User corrected system output

    target_type / target_id: Polymorphic reference to the content
    (signal, brief, recommendation, entity, etc.)
    """

    __tablename__ = "user_feedback"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What kind of feedback
    feedback_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )

    # What was the feedback about (polymorphic)
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # signal, brief, recommendation, entity, causal_chain
    target_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )

    # Sentiment/score (optional numeric rating)
    sentiment: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # -1.0 (negative) to 1.0 (positive)

    # Free-form user comment or annotation
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Context at time of feedback (user's current query, page, etc.)
    context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    def __repr__(self) -> str:
        return (
            f"<UserFeedback {self.feedback_type} on {self.target_type}={self.target_id} "
            f"by user={self.user_id}>"
        )
