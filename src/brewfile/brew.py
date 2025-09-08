"""
Homebrew operations and package detection.

Contains classes and utilities for interacting with Homebrew,
detecting packages, and managing installation state.
"""

import contextlib
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .models import InstallationStatus, PackageInfo, PackageType
from .utils import LoadingIndicator, warn


class Brew:
    """Static utilities for brew operations."""

    class Bundle:
        @staticmethod
        def install(brewfile_path: Path) -> None:
            """Install packages using brew bundle."""
            subprocess.run(["brew", "bundle", "install", "--file", str(brewfile_path)], check=True)

        @staticmethod
        def cleanup(brewfile_path: Path) -> None:
            """Remove extra packages using brew bundle cleanup."""
            subprocess.run(["brew", "bundle", "cleanup", "--force", "--file", str(brewfile_path)], check=True)

        @staticmethod
        def dump_system(brewfile_path: Path) -> None:
            """Dump current system state to specified brewfile."""
            subprocess.run(
                ["brew", "bundle", "dump", "--force", "--no-vscode", "--file", str(brewfile_path)],
                check=True,
                capture_output=True,
            )

        @staticmethod
        def list_packages(brewfile_path: Path) -> dict[str, list[str]]:
            """Parse brewfile to get package lists."""
            packages = {pkg_type.plural: [] for pkg_type in PackageType}

            # Use brew bundle list commands with specific file
            for cmd, key in [
                (["brew", "bundle", "list", "--tap", "--file", str(brewfile_path)], "taps"),
                (["brew", "bundle", "list", "--formula", "--file", str(brewfile_path)], "brews"),
                (["brew", "bundle", "list", "--cask", "--file", str(brewfile_path)], "casks"),
                (["brew", "bundle", "list", "--mas", "--file", str(brewfile_path)], "mas"),
            ]:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    packages[key] = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
                except subprocess.CalledProcessError:
                    packages[key] = []  # Fallback to empty if command fails

            return packages

    @staticmethod
    def detect_package_type(package_name: str) -> PackageType:
        """Auto-detect if package is a cask or formula."""
        with LoadingIndicator(f"Detecting package type for '{package_name}'"):
            try:
                # First check if it's a cask
                result = subprocess.run(
                    ["brew", "search", "--cask", package_name],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                # If exact match found in cask search, it's a cask
                if f"\n{package_name}\n" in result.stdout or result.stdout.strip() == package_name:
                    return PackageType.CASK

                # Check if it's a formula
                result = subprocess.run(
                    ["brew", "search", package_name],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                # If exact match found in formula search, it's a formula
                if f"\n{package_name}\n" in result.stdout or result.stdout.strip() == package_name:
                    return PackageType.BREW

                # If no exact match, default to formula
                warn(f"Could not find exact match for '{package_name}', assuming it's a formula")
                return PackageType.BREW

            except subprocess.CalledProcessError:
                # If search fails, default to formula
                warn(f"Package search failed for '{package_name}', assuming it's a formula")
                return PackageType.BREW


class PackageCache:
    """Handles caching of system package state."""

    def __init__(self):
        """Initialize cache with lazy loading."""
        self._installed_packages = None

    def get_installed_packages(self) -> list[PackageInfo]:
        """Get installed packages as PackageInfo objects, loading them if needed."""
        if self._installed_packages is None:
            self.refresh()
        return self._installed_packages or []

    def refresh(self) -> list[PackageInfo]:
        """Refresh package cache using temporary brewfile."""
        # Clean up orphaned dependencies using brew autoremove
        with LoadingIndicator("Analyzing installed packages"):
            with contextlib.suppress(subprocess.CalledProcessError):
                subprocess.run(["brew", "autoremove"], check=False, capture_output=True)

            with self._temp_system_brewfile() as temp_path:
                package_dict = Brew.Bundle.list_packages(temp_path)

                # Convert dict to PackageInfo list
                packages = []
                for pkg_type in PackageType:
                    for pkg_name in package_dict[pkg_type.plural]:
                        packages.append(
                            PackageInfo(
                                name=pkg_name, group=None, package_type=pkg_type, installed=InstallationStatus.INSTALLED
                            )
                        )

                self._installed_packages = packages
                return packages

    @contextmanager
    def _temp_system_brewfile(self):
        """Create temporary brewfile with current system state."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".brewfile", delete=True) as tmp_file:
            temp_path = Path(tmp_file.name)
            Brew.Bundle.dump_system(temp_path)
            yield temp_path
            # Automatic cleanup when context exits

    def update_package_status(self, packages: list[PackageInfo]) -> None:
        """Update installation status for a list of packages."""
        installed_packages = self.get_installed_packages()
        installed_keys = {(pkg.name, pkg.package_type) for pkg in installed_packages}

        for pkg in packages:
            # For MAS apps, check if the app name (without ID) is installed
            if pkg.package_type == PackageType.MAS and "::" in pkg.name:
                app_name = pkg.name.split("::")[0]
                is_installed = any(
                    (app_name, PackageType.MAS) == (installed_pkg.name, installed_pkg.package_type)
                    for installed_pkg in installed_packages
                )
            else:
                is_installed = (pkg.name, pkg.package_type) in installed_keys

            pkg.installed = InstallationStatus.INSTALLED if is_installed else InstallationStatus.NOT_INSTALLED


def compare_packages(
    configured: list[PackageInfo], installed: list[PackageInfo]
) -> tuple[list[PackageInfo], list[PackageInfo]]:
    """Compare configured and installed packages, returning (missing, extra) packages.

    Args:
        configured: Packages that should be installed according to config
        installed: Packages currently installed on system

    Returns:
        tuple of (missing_packages, extra_packages)
        - missing: configured packages not installed
        - extra: installed packages not configured
    """
    # Build lookup sets for efficient comparison
    installed_keys = {(pkg.name, pkg.package_type) for pkg in installed}
    configured_keys = {(pkg.name, pkg.package_type) for pkg in configured}

    # Handle MAS app name matching (configured with ID, installed without ID)
    configured_mas_names = set()
    installed_mas_names = set()

    for pkg in configured:
        if pkg.package_type == PackageType.MAS and "::" in pkg.name:
            app_name = pkg.name.split("::")[0]
            configured_mas_names.add((app_name, PackageType.MAS))

    for pkg in installed:
        if pkg.package_type == PackageType.MAS:
            installed_mas_names.add((pkg.name, pkg.package_type))

    missing = []
    extra = []

    # Find missing packages (configured but not installed)
    for pkg in configured:
        if pkg.package_type == PackageType.MAS and "::" in pkg.name:
            # For MAS apps, check if the app name (without ID) is installed
            app_name = pkg.name.split("::")[0]
            if (app_name, PackageType.MAS) not in installed_mas_names:
                missing.append(pkg)
        elif (pkg.name, pkg.package_type) not in installed_keys:
            missing.append(pkg)

    # Find extra packages (installed but not configured)
    for pkg in installed:
        if pkg.package_type == PackageType.MAS:
            # For MAS apps, check both exact match and app name match
            if (pkg.name, pkg.package_type) not in configured_keys and (
                pkg.name,
                pkg.package_type,
            ) not in configured_mas_names:
                extra.append(pkg)
        elif (pkg.name, pkg.package_type) not in configured_keys:
            extra.append(pkg)

    return missing, extra
