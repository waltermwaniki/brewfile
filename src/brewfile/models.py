"""
Core data models for Brewfile package management.

Contains enums, dataclasses, and core business objects used throughout
the application.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union


class PackageType(Enum):
    """Package types supported by Homebrew."""

    TAP = "tap"
    BREW = "brew"  # Formula
    CASK = "cask"
    MAS = "mas"  # Mac App Store

    @property
    def plural(self) -> str:
        """Get the plural form used in configuration storage."""
        if self == PackageType.TAP:
            return "taps"
        elif self == PackageType.BREW:
            return "brews"
        elif self == PackageType.CASK:
            return "casks"
        elif self == PackageType.MAS:
            return "mas"
        return self.value + "s"

    @classmethod
    def from_plural(cls, plural: str) -> "PackageType":
        """Create PackageType from plural form."""
        if plural == "taps":
            return cls.TAP
        elif plural == "brews":
            return cls.BREW
        elif plural == "casks":
            return cls.CASK
        elif plural == "mas":
            return cls.MAS
        raise ValueError(f"Unknown plural package type: {plural}")

    @classmethod
    def from_string(cls, value: str) -> "PackageType":
        """Create PackageType from various string representations."""
        value = value.lower().strip()
        if value in ("formula", "brew"):
            return cls.BREW
        elif value == "cask":
            return cls.CASK
        elif value == "tap":
            return cls.TAP
        elif value == "mas":
            return cls.MAS
        # Try plural forms
        try:
            return cls.from_plural(value)
        except ValueError:
            pass
        # Try direct enum value
        for pkg_type in cls:
            if pkg_type.value == value:
                return pkg_type
        raise ValueError(f"Unknown package type: {value}")


class InstallationStatus(Enum):
    """Installation status for packages."""

    UNKNOWN = "unknown"
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"


@dataclass
class PackageGroup:
    """Represents a group of packages with taps, brews, casks, and mas apps."""

    taps: list[str] = field(default_factory=list)
    brews: list[str] = field(default_factory=list)
    casks: list[str] = field(default_factory=list)
    mas: list[str] = field(default_factory=list)

    def get_all_packages(self) -> dict[str, list[str]]:
        """Get all packages as a dictionary."""
        return {
            "taps": self.taps.copy(),
            "brews": self.brews.copy(),
            "casks": self.casks.copy(),
            "mas": self.mas.copy(),
        }

    def add_package(self, package_type: PackageType, package_name: str) -> None:
        """Add a package to this group."""
        if package_type == PackageType.TAP:
            if package_name not in self.taps:
                self.taps.append(package_name)
        elif package_type == PackageType.BREW:
            if package_name not in self.brews:
                self.brews.append(package_name)
        elif package_type == PackageType.CASK:
            if package_name not in self.casks:
                self.casks.append(package_name)
        elif package_type == PackageType.MAS:
            if package_name not in self.mas:
                self.mas.append(package_name)
        else:
            raise ValueError(f"Unknown package type: {package_type}")

    def remove_package(self, package_type: PackageType, package_name: str) -> bool:
        """Remove a package from this group. Returns True if removed."""
        if package_type == PackageType.TAP and package_name in self.taps:
            self.taps.remove(package_name)
            return True
        elif package_type == PackageType.BREW and package_name in self.brews:
            self.brews.remove(package_name)
            return True
        elif package_type == PackageType.CASK and package_name in self.casks:
            self.casks.remove(package_name)
            return True
        elif package_type == PackageType.MAS and package_name in self.mas:
            self.mas.remove(package_name)
            return True
        return False

    def get_packages_of_type(self, package_type: PackageType) -> list[str]:
        """Get packages of a specific type."""
        if package_type == PackageType.TAP:
            return self.taps.copy()
        elif package_type == PackageType.BREW:
            return self.brews.copy()
        elif package_type == PackageType.CASK:
            return self.casks.copy()
        elif package_type == PackageType.MAS:
            return self.mas.copy()
        else:
            raise ValueError(f"Unknown package type: {package_type}")


@dataclass
class PackageInfo:
    """Information about a package including its metadata and installation status."""

    name: str
    group: Union[str, None]  # None for system packages
    package_type: PackageType
    installed: InstallationStatus = field(default_factory=lambda: InstallationStatus.UNKNOWN)


@dataclass
class BrewfileConfig:
    """Complete brewfile configuration."""

    version: str = "1.0"
    packages: dict[str, PackageGroup] = field(default_factory=dict)
    machines: dict[str, list[str]] = field(default_factory=dict)  # hostname -> group names

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrewfileConfig":
        """Create config from dictionary (loaded JSON)."""
        # Convert package groups from dict to PackageGroup objects
        packages = {}
        for name, pkg_data in data.get("packages", {}).items():
            packages[name] = PackageGroup(
                taps=pkg_data.get("taps", []),
                brews=pkg_data.get("brews", []),
                casks=pkg_data.get("casks", []),
                mas=pkg_data.get("mas", []),
            )

        return cls(
            version=data.get("version", "1.0"),
            packages=packages,
            machines=data.get("machines", {}),
        )

    @classmethod
    def load(cls, config_file: Path) -> "BrewfileConfig":
        """Load configuration from JSON file."""
        if not config_file.exists():
            return cls()  # Return default config

        try:
            with open(config_file, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Invalid configuration file: {e}")

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "packages": {name: group.get_all_packages() for name, group in self.packages.items()},
            "machines": self.machines.copy(),
        }

    def save(self, config_file: Path) -> None:
        """Save configuration to JSON file."""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)

    def get_machine_packages(self, machine_name: str) -> list["PackageInfo"]:
        """Get all packages configured for a specific machine."""
        if machine_name not in self.machines:
            return []
        
        packages = []
        for group_name in self.machines[machine_name]:
            if group_name in self.packages:
                group = self.packages[group_name]
                for pkg_type in PackageType:
                    for pkg_name in group.get_packages_of_type(pkg_type):
                        packages.append(PackageInfo(
                            name=pkg_name,
                            group=group_name,
                            package_type=pkg_type
                        ))
        return packages

    def get_package_info(self, package_name: str) -> Union["PackageInfo", None]:
        """Find a package by name across all groups."""
        for group_name, group in self.packages.items():
            for pkg_type in PackageType:
                if package_name in group.get_packages_of_type(pkg_type):
                    return PackageInfo(
                        name=package_name,
                        group=group_name,
                        package_type=pkg_type
                    )
        return None

    def remove_package(self, package_name: str, config_file: Optional[Path] = None) -> Union[PackageType, None]:
        """Remove a package from all groups. Returns the package type if found and removed."""
        removed_type = None
        removed_from_any_group = False
        
        for group in self.packages.values():
            for pkg_type in PackageType:
                if group.remove_package(pkg_type, package_name):
                    removed_type = pkg_type
                    removed_from_any_group = True
        
        # Auto-save if config_file provided and something was removed
        if removed_from_any_group and config_file:
            self.save(config_file)
        
        return removed_type
