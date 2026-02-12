"""Data Classification System - Tag data sensitivity for compliance.

Classifies data as PUBLIC, INTERNAL, PII, or PHI with appropriate
storage, retention, and access control policies.
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class DataClassification(str, Enum):
    """Data sensitivity classification levels."""

    PUBLIC = "public"  # Can be shared publicly
    INTERNAL = "internal"  # Internal use only
    PII = "pii"  # Personally Identifiable Information (GDPR/NDPR)
    PHI = "phi"  # Protected Health Information (HIPAA)


class DataPolicy:
    """Storage and retention policies per classification."""

    POLICIES = {
        DataClassification.PUBLIC: {
            "encryption_required": False,
            "retention_days": 730,  # 2 years
            "audit_access": False,
            "allow_export": True,
            "redact_in_logs": False,
        },
        DataClassification.INTERNAL: {
            "encryption_required": True,
            "retention_days": 365,  # 1 year
            "audit_access": True,
            "allow_export": False,
            "redact_in_logs": False,
        },
        DataClassification.PII: {
            "encryption_required": True,
            "retention_days": 90,  # 90 days (GDPR default)
            "audit_access": True,
            "allow_export": True,  # For GDPR export requests
            "redact_in_logs": True,
        },
        DataClassification.PHI: {
            "encryption_required": True,
            "retention_days": 90,  # 90 days (HIPAA minimum)
            "audit_access": True,
            "allow_export": False,  # Restricted
            "redact_in_logs": True,
        },
    }

    @staticmethod
    def get_policy(classification: DataClassification) -> dict:
        """Get policy for data classification."""
        return DataPolicy.POLICIES[classification]

    @staticmethod
    def should_encrypt(classification: DataClassification) -> bool:
        """Check if data requires encryption."""
        return DataPolicy.POLICIES[classification]["encryption_required"]

    @staticmethod
    def get_retention_days(classification: DataClassification) -> int:
        """Get retention period in days."""
        return DataPolicy.POLICIES[classification]["retention_days"]

    @staticmethod
    def should_audit(classification: DataClassification) -> bool:
        """Check if access should be audited."""
        return DataPolicy.POLICIES[classification]["audit_access"]


# Model-level classification mapping
MODEL_CLASSIFICATIONS = {
    "Signal": DataClassification.INTERNAL,  # May contain business intel
    "SignalEntity": DataClassification.INTERNAL,
    "IntelligenceBrief": DataClassification.INTERNAL,
    "ChatMessage": DataClassification.PII,  # User queries may contain PII
    "SearchQuery": DataClassification.PII,  # User search history
    "User": DataClassification.PII,  # User data
    "Organization": DataClassification.INTERNAL,
    "AuditLog": DataClassification.INTERNAL,
    "AIUsageLog": DataClassification.INTERNAL,
}


def classify_field(model_name: str, field_name: str) -> DataClassification:
    """Classify a specific field.

    Args:
        model_name: Model class name
        field_name: Field name

    Returns:
        Data classification level
    """
    # PHI detection rules
    phi_fields = {"diagnosis", "treatment", "medical_history", "prescription"}
    if field_name.lower() in phi_fields:
        return DataClassification.PHI

    # PII detection rules
    pii_fields = {"email", "phone", "address", "ssn", "passport", "ip_address"}
    if field_name.lower() in pii_fields:
        return DataClassification.PII

    # Default to model-level classification
    return MODEL_CLASSIFICATIONS.get(model_name, DataClassification.INTERNAL)
