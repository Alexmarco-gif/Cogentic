"""
Feature Flags Tests

Tests for feature flag evaluation, guards, and integration.
"""

import pytest
from pathlib import Path
from uuid import uuid4

from backend.services.feature_flags import FeatureFlagService, FeatureDefinition
from backend.auth.schemas import AuthContext
from backend.auth.guards import require_feature
from backend.auth.exceptions import FeatureDisabledError
from datetime import datetime


@pytest.fixture
def temp_features_yaml(tmp_path):
    """Create temporary features.yaml for testing"""
    features_file = tmp_path / "features.yaml"
    features_file.write_text("""
features:
  test_enabled_feature:
    enabled: true
    description: "Test feature that is enabled"
  
  test_disabled_feature:
    enabled: false
    description: "Test feature that is disabled"
  
  test_pro_feature:
    enabled: true
    description: "Feature requiring Pro plan"
    required_plan: pro
  
  test_enterprise_feature:
    enabled: true
    description: "Feature requiring Enterprise plan"
    required_plan: enterprise
  
  test_user_override:
    enabled: false
    description: "Feature disabled globally but with user overrides"
    enabled_for_users:
      - "user-123"
      - "user-456"
  
  test_org_override:
    enabled: false
    description: "Feature disabled globally but with org overrides"
    enabled_for_orgs:
      - "org-abc"
      - "org-xyz"
""")
    return features_file


@pytest.fixture
def feature_service(temp_features_yaml):
    """Create FeatureFlagService with test config"""
    return FeatureFlagService(config_path=temp_features_yaml)


class TestFeatureFlagService:
    """Tests for FeatureFlagService core functionality"""
    
    def test_load_config(self, feature_service):
        """Test loading features from YAML config"""
        assert len(feature_service.features) == 6
        assert "test_enabled_feature" in feature_service.features
        assert "test_disabled_feature" in feature_service.features
    
    def test_enabled_feature(self, feature_service):
        """Test checking an enabled feature"""
        result = feature_service.is_enabled("test_enabled_feature")
        assert result is True
    
    def test_disabled_feature(self, feature_service):
        """Test checking a disabled feature"""
        result = feature_service.is_enabled("test_disabled_feature")
        assert result is False
    
    def test_undefined_feature(self, feature_service):
        """Test checking a feature that doesn't exist"""
        result = feature_service.is_enabled("nonexistent_feature")
        assert result is False
    
    def test_get_feature(self, feature_service):
        """Test getting feature definition"""
        feature = feature_service.get_feature("test_enabled_feature")
        assert feature is not None
        assert isinstance(feature, FeatureDefinition)
        assert feature.enabled is True
        assert feature.description == "Test feature that is enabled"
    
    def test_list_features(self, feature_service):
        """Test listing all features"""
        features = feature_service.list_features()
        assert len(features) == 6
        assert all(isinstance(f, FeatureDefinition) for f in features.values())
    
    def test_user_override(self, feature_service):
        """Test user-specific override for disabled feature"""
        # Feature disabled globally
        assert feature_service.is_enabled("test_user_override") is False
        
        # User in allowlist can access
        assert feature_service.is_enabled(
            "test_user_override",
            user_id="user-123"
        ) is True
        
        # User not in allowlist cannot access
        assert feature_service.is_enabled(
            "test_user_override",
            user_id="user-999"
        ) is False
    
    def test_org_override(self, feature_service):
        """Test org-specific override for disabled feature"""
        # Feature disabled globally
        assert feature_service.is_enabled("test_org_override") is False
        
        # Org in allowlist can access
        assert feature_service.is_enabled(
            "test_org_override",
            org_id="org-abc"
        ) is True
        
        # Org not in allowlist cannot access
        assert feature_service.is_enabled(
            "test_org_override",
            org_id="org-999"
        ) is False
    
    def test_org_override_priority(self, feature_service):
        """Test that org override takes priority over global flag"""
        # Org override should enable even if globally disabled
        assert feature_service.is_enabled(
            "test_org_override",
            org_id="org-abc"
        ) is True
    
    def test_get_enabled_features(self, feature_service):
        """Test getting list of enabled features for context"""
        # Free user - should only get free features
        enabled = feature_service.get_enabled_features(plan="free")
        assert "test_enabled_feature" in enabled
        assert "test_disabled_feature" not in enabled
        
        # With user override
        enabled_with_override = feature_service.get_enabled_features(
            user_id="user-123",
            plan="free"
        )
        assert "test_user_override" in enabled_with_override
    
    def test_reload_config(self, feature_service, temp_features_yaml):
        """Test hot-reloading config"""
        # Initial state
        assert feature_service.is_enabled("test_enabled_feature") is True
        
        # Modify config
        temp_features_yaml.write_text("""
features:
  test_enabled_feature:
    enabled: false
    description: "Now disabled"
""")
        
        # Reload
        feature_service.reload_config()
        
        # Should reflect new config
        assert feature_service.is_enabled("test_enabled_feature") is False
    
    def test_empty_config(self, tmp_path):
        """Test handling empty config file"""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        
        service = FeatureFlagService(config_path=empty_file)
        assert len(service.features) == 0
        assert service.is_enabled("any_feature") is False
    
    def test_missing_config(self, tmp_path):
        """Test handling missing config file"""
        missing_file = tmp_path / "nonexistent.yaml"
        
        service = FeatureFlagService(config_path=missing_file)
        assert len(service.features) == 0
        assert service.is_enabled("any_feature") is False


class TestFeatureGuards:
    """Tests for feature flag guards"""
    
    def create_auth_context(
        self,
        user_id=None,
        org_id=None,
        plan="free",
        role="member"
    ):
        """Helper to create AuthContext for testing"""
        return AuthContext(
            user_id=user_id or uuid4(),
            auth0_id="auth0|123",
            email="test@example.com",
            org_id=org_id or uuid4(),
            role=role,
            plan=plan,
            is_super_admin=False,
            token_expires_at=datetime.utcnow(),
            request_id="test-request-123"
        )
    
    def test_require_feature_enabled(self, feature_service, monkeypatch):
        """Test require_feature with enabled feature"""
        # Mock the global service
        monkeypatch.setattr(
            "backend.services.feature_flags._feature_flags_service",
            feature_service
        )
        
        auth = self.create_auth_context()
        
        # Should not raise
        require_feature(auth, "test_enabled_feature")
    
    def test_require_feature_disabled(self, feature_service, monkeypatch):
        """Test require_feature with disabled feature"""
        monkeypatch.setattr(
            "backend.services.feature_flags._feature_flags_service",
            feature_service
        )
        
        auth = self.create_auth_context()
        
        # Should raise FeatureDisabledError
        with pytest.raises(FeatureDisabledError) as exc_info:
            require_feature(auth, "test_disabled_feature")
        
        assert "test_disabled_feature" in str(exc_info.value)
    
    def test_require_feature_with_user_override(self, feature_service, monkeypatch):
        """Test require_feature with user override"""
        monkeypatch.setattr(
            "backend.services.feature_flags._feature_flags_service",
            feature_service
        )
        
        # User in allowlist - need to use actual UUID but match string in YAML
        user_uuid = uuid4()
        auth = self.create_auth_context(user_id=user_uuid)
        
        # Temporarily update the feature to include this user's UUID string
        feature_service.features["test_user_override"].enabled_for_users.append(str(user_uuid))
        
        require_feature(auth, "test_user_override")  # Should not raise
        
        # User not in allowlist
        auth = self.create_auth_context(user_id=uuid4())  # Different UUID
        with pytest.raises(FeatureDisabledError):
            require_feature(auth, "test_user_override")
    
    def test_require_feature_with_org_override(self, feature_service, monkeypatch):
        """Test require_feature with org override"""
        monkeypatch.setattr(
            "backend.services.feature_flags._feature_flags_service",
            feature_service
        )
        
        # Org in allowlist - need to use actual UUID but match string in YAML
        org_uuid = uuid4()
        auth = self.create_auth_context(org_id=org_uuid)
        
        # Temporarily update the feature to include this org's UUID string
        feature_service.features["test_org_override"].enabled_for_orgs.append(str(org_uuid))
        
        require_feature(auth, "test_org_override")  # Should not raise
        
        # Org not in allowlist
        auth = self.create_auth_context(org_id=uuid4())  # Different UUID
        with pytest.raises(FeatureDisabledError):
            require_feature(auth, "test_org_override")
    
    def test_require_feature_undefined(self, feature_service, monkeypatch):
        """Test require_feature with undefined feature"""
        monkeypatch.setattr(
            "backend.services.feature_flags._feature_flags_service",
            feature_service
        )
        
        auth = self.create_auth_context()
        
        # Undefined feature should raise
        with pytest.raises(FeatureDisabledError):
            require_feature(auth, "nonexistent_feature")


class TestFeatureDefinition:
    """Tests for FeatureDefinition model"""
    
    def test_basic_definition(self):
        """Test creating basic feature definition"""
        feature = FeatureDefinition(
            enabled=True,
            description="Test feature"
        )
        assert feature.enabled is True
        assert feature.description == "Test feature"
        assert feature.required_plan is None
        assert feature.enabled_for_users == []
        assert feature.enabled_for_orgs == []
    
    def test_definition_with_plan(self):
        """Test feature definition with plan requirement"""
        feature = FeatureDefinition(
            enabled=True,
            description="Pro feature",
            required_plan="pro"
        )
        assert feature.required_plan == "pro"
    
    def test_definition_with_overrides(self):
        """Test feature definition with user/org overrides"""
        feature = FeatureDefinition(
            enabled=False,
            description="Beta feature",
            enabled_for_users=["user-1", "user-2"],
            enabled_for_orgs=["org-1"]
        )
        assert len(feature.enabled_for_users) == 2
        assert len(feature.enabled_for_orgs) == 1
