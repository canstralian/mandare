"""
Capability Manifest Registry & Loader

Manages capability manifest discovery, loading, validation, and caching.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from functools import lru_cache

import yaml
from pydantic import ValidationError

from rif_runtime.schemas.capability import CapabilityManifest

logger = logging.getLogger(__name__)


class ManifestLoadError(Exception):
    """Raised when manifest fails to load or validate."""
    pass


class ManifestRegistry:
    """
    Registry for capability manifests.
    
    Handles discovery, loading, validation, and caching of manifests
    from filesystem or remote sources.
    """
    
    def __init__(self, manifest_dir: Path | str = "config/capabilities"):
        """Initialize registry with manifest directory."""
        self.manifest_dir = Path(manifest_dir)
        self._cache: Dict[str, CapabilityManifest] = {}
        self._errors: Dict[str, Exception] = {}
    
    def discover(self) -> List[str]:
        """Discover all manifest files in registry directory."""
        if not self.manifest_dir.exists():
            logger.warning(f"Manifest directory does not exist: {self.manifest_dir}")
            return []
        
        manifests = []
        for file_path in self.manifest_dir.glob("**/*.{yaml,yml,json}"):
            if file_path.is_file() and not file_path.name.startswith("."):
                manifest_name = file_path.stem
                manifests.append(manifest_name)
        
        return sorted(manifests)
    
    def load(self, name: str, force_reload: bool = False) -> CapabilityManifest:
        """
        Load a manifest by name.
        
        Args:
            name: Manifest name (e.g., 'shell_command')
            force_reload: Skip cache and reload from disk
        
        Returns:
            CapabilityManifest instance
        
        Raises:
            ManifestLoadError: If manifest cannot be loaded or validated
        """
        # Check cache
        if not force_reload and name in self._cache:
            return self._cache[name]
        
        # Check for previous errors
        if name in self._errors and not force_reload:
            raise self._errors[name]
        
        # Try YAML first, then JSON
        for suffix in [".yaml", ".yml", ".json"]:
            file_path = self.manifest_dir / f"{name}{suffix}"
            if file_path.exists():
                return self._load_file(file_path)
        
        error = ManifestLoadError(
            f"Manifest not found: {name} in {self.manifest_dir}"
        )
        self._errors[name] = error
        raise error
    
    def _load_file(self, file_path: Path) -> CapabilityManifest:
        """Load and validate a manifest file."""
        try:
            # Read file
            with open(file_path) as f:
                if file_path.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Validate schema
            manifest = CapabilityManifest(**data)
            
            # Cache
            self._cache[manifest.name] = manifest
            
            logger.info(f"Loaded manifest: {manifest.name} v{manifest.version}")
            return manifest
        
        except yaml.YAMLError as e:
            error = ManifestLoadError(f"YAML parse error in {file_path}: {e}")
            self._errors[file_path.stem] = error
            raise error
        
        except json.JSONDecodeError as e:
            error = ManifestLoadError(f"JSON parse error in {file_path}: {e}")
            self._errors[file_path.stem] = error
            raise error
        
        except ValidationError as e:
            error = ManifestLoadError(
                f"Manifest validation failed in {file_path}:\n{e}"
            )
            self._errors[file_path.stem] = error
            raise error
        
        except Exception as e:
            error = ManifestLoadError(f"Unexpected error loading {file_path}: {e}")
            self._errors[file_path.stem] = error
            raise error
    
    def load_all(self) -> Dict[str, CapabilityManifest]:
        """Load all manifests in the registry."""
        manifests = {}
        errors = {}
        
        for name in self.discover():
            try:
                manifests[name] = self.load(name)
            except ManifestLoadError as e:
                errors[name] = e
                logger.error(f"Failed to load manifest {name}: {e}")
        
        if errors:
            logger.warning(f"Loaded {len(manifests)} manifests, {len(errors)} failed")
        else:
            logger.info(f"Loaded {len(manifests)} manifests successfully")
        
        return manifests
    
    def get(self, name: str, default: Optional[CapabilityManifest] = None) \
            -> Optional[CapabilityManifest]:
        """Get manifest by name (returns None if not found)."""
        try:
            return self.load(name)
        except ManifestLoadError:
            return default
    
    def validate(self, name: str) -> tuple[bool, Optional[str]]:
        """
        Validate a manifest.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            self.load(name, force_reload=True)
            return True, None
        except ManifestLoadError as e:
            return False, str(e)
    
    def validate_all(self) -> tuple[int, int]:
        """
        Validate all manifests.
        
        Returns:
            (valid_count, error_count)
        """
        valid = 0
        errors = 0
        
        for name in self.discover():
            is_valid, error = self.validate(name)
            if is_valid:
                valid += 1
            else:
                errors += 1
                logger.error(f"Validation failed for {name}: {error}")
        
        return valid, errors
    
    def clear_cache(self) -> None:
        """Clear all cached manifests and errors."""
        self._cache.clear()
        self._errors.clear()
        logger.debug("Manifest cache cleared")
    
    def list(self) -> List[str]:
        """List all loaded manifest names."""
        return sorted(self._cache.keys())
    
    def reload(self) -> None:
        """Reload all manifests from disk."""
        self.clear_cache()
        self.load_all()


class ManifestValidator:
    """
    Validates manifests against security and governance policies.
    """
    
    @staticmethod
    def check_risk_score(manifest: CapabilityManifest) -> int:
        """
        Calculate risk score for a manifest (1-10).
        
        Higher score = higher risk.
        """
        score = 1  # Base
        
        # Mutates state
        if manifest.mutates_state:
            score += 2
        
        # Side effects
        from rif_runtime.schemas.capability import SideEffectType
        
        side_effect_weights = {
            SideEffectType.NETWORK_EGRESS: 1,
            SideEffectType.FILESYSTEM_WRITE: 1,
            SideEffectType.FILESYSTEM_DELETE: 2,
            SideEffectType.PROCESS_EXECUTION: 2,
            SideEffectType.ENVIRONMENT_MUTATION: 1,
            SideEffectType.EXTERNAL_SERVICE_MUTATION: 2,
            SideEffectType.CREDENTIAL_EXPOSURE: 3,
            SideEffectType.PRIVILEGE_ESCALATION: 4,
        }
        
        for effect, weight in side_effect_weights.items():
            if effect in manifest.side_effects:
                score += weight
        
        # Replayability affects trust
        from rif_runtime.schemas.capability import Replayability
        
        if manifest.replayability == Replayability.DETERMINISTIC:
            score -= 1
        elif manifest.replayability == Replayability.NON_REPLAYABLE:
            score += 1
        elif manifest.replayability == Replayability.NON_IDEMPOTENT:
            score += 1
        
        return min(10, max(1, score))
    
    @staticmethod
    def check_least_privilege(manifest: CapabilityManifest) -> List[str]:
        """
        Check if manifest follows least privilege principle.
        
        Returns:
            List of warnings (empty if all good)
        """
        warnings = []
        
        # Filesystem: check for overly permissive paths
        if manifest.filesystem_access.enabled:
            paths = manifest.filesystem_access.allowed_paths
            if not paths:
                warnings.append("filesystem_access.allowed_paths is empty (no filesystem access)")
            for path in paths:
                if path == "/" or path == "/**":
                    warnings.append(
                        f"filesystem_access allows entire filesystem: {path}"
                    )
                elif path.startswith("/root") or path.startswith("/etc"):
                    warnings.append(f"filesystem_access includes sensitive path: {path}")
        
        # Network: check for overly permissive domains
        if manifest.network_access.enabled:
            domains = manifest.network_access.allowed_domains
            if not domains:
                warnings.append("network_access.allowed_domains is empty (no network access)")
            for domain in domains:
                if domain == "*" or domain == "*.com" or domain == "**":
                    warnings.append(
                        f"network_access allows too broad domain: {domain}"
                    )
        
        # Check for blocked metadata services
        if manifest.network_access.enabled:
            blocked = manifest.network_access.blocked_domains
            if "169.254.169.254" not in blocked:
                warnings.append(
                    "network_access does not block AWS metadata service (169.254.169.254)"
                )
        
        # Access level too high
        if manifest.filesystem_access.access_level.value == "admin":
            warnings.append("filesystem_access.access_level is ADMIN (use specific level)")
        
        # Timeout too long
        if manifest.timeout_seconds > 300:
            warnings.append(f"timeout_seconds is very long: {manifest.timeout_seconds}s")
        
        return warnings
    
    @staticmethod
    def check_evidence_completeness(manifest: CapabilityManifest) -> List[str]:
        """
        Check if evidence requirements are adequate for audit.
        
        Returns:
            List of warnings
        """
        warnings = []
        
        if not manifest.evidence_requirements:
            warnings.append("No evidence requirements defined (audit trail will be incomplete)")
        
        immutable_count = sum(
            1 for e in manifest.evidence_requirements if e.immutable
        )
        if immutable_count == 0 and manifest.mutates_state:
            warnings.append(
                "No immutable evidence for mutating capability (cannot verify audit trail)"
            )
        
        # Check for sensitive evidence marking
        from rif_runtime.schemas.capability import SideEffectType
        
        if SideEffectType.CREDENTIAL_EXPOSURE in manifest.side_effects:
            sensitive_evidence = sum(
                1 for e in manifest.evidence_requirements if e.sensitive
            )
            if sensitive_evidence == 0:
                warnings.append(
                    "No evidence marked sensitive for credential-exposing capability"
                )
        
        return warnings
    
    @staticmethod
    def check_all(manifest: CapabilityManifest) -> Dict[str, object]:
        """Run all validation checks."""
        return {
            "risk_score": ManifestValidator.check_risk_score(manifest),
            "least_privilege_warnings": ManifestValidator.check_least_privilege(manifest),
            "evidence_warnings": ManifestValidator.check_evidence_completeness(manifest),
        }


if __name__ == "__main__":
    """Example usage."""
    
    # Create registry
    registry = ManifestRegistry("config/capabilities")
    
    # Discover manifests
    print("Available manifests:")
    for name in registry.discover():
        print(f"  - {name}")
    
    # Load specific manifest
    try:
        manifest = registry.load("shell_command")
        print(f"\nLoaded: {manifest.name} v{manifest.version}")
        print(f"Description: {manifest.description}")
        print(f"Side effects: {manifest.side_effects}")
    except ManifestLoadError as e:
        print(f"Error: {e}")
    
    # Validate all
    valid, errors = registry.validate_all()
    print(f"\nValidation: {valid} valid, {errors} errors")
    
    # Check security
    if manifest:
        checks = ManifestValidator.check_all(manifest)
        print(f"\nSecurity checks:")
        print(f"  Risk score: {checks['risk_score']}/10")
        print(f"  Least privilege: {len(checks['least_privilege_warnings'])} warnings")
        print(f"  Evidence: {len(checks['evidence_warnings'])} warnings")
