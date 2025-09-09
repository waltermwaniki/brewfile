"""
BrewfileManager — High-level business logic for Homebrew package management.

Orchestrates configuration, package analysis, and Homebrew operations.
Focused on business logic without CLI concerns.
"""

import os
import socket
import subprocess
from pathlib import Path
from typing import Optional

from .brew import Brew, PackageCache, compare_packages
from .models import BrewfileConfig, InstallationStatus, PackageGroup, PackageInfo, PackageType
from .utils import AnsiColor, die, say, success, warn


class BrewfileManager:
    """Main manager for brewfile operations."""

    def __init__(self):
        """Initialize manager with paths and empty config."""
        self.hostname = socket.gethostname().split(".")[0]
        self.config_file = Path.home() / ".config" / "brewfile.json"
        self.brewfile_path = Path.home() / "Brewfile"
        self.config = BrewfileConfig()
        self.package_cache = PackageCache()

    @property
    def machine_packages(self) -> tuple[list[PackageInfo], list[PackageInfo], list[PackageInfo]]:
        """Get configured, missing, and extra packages for this machine."""
        # Ensure we have configuration
        self._ensure_configured()

        # Get configured packages for this machine
        configured_packages = self.config.get_machine_packages(self.hostname)

        # Update installation status
        self.package_cache.update_package_status(configured_packages)

        # Get installed packages from system
        installed_packages = self.package_cache.get_installed_packages()

        # Compare to find missing and extra
        missing_packages, extra_packages = compare_packages(configured_packages, installed_packages)

        return configured_packages, missing_packages, extra_packages

    def _ensure_configured(self) -> None:
        """Ensure we have a valid configuration loaded."""
        self.config = BrewfileConfig.load(self.config_file)

        # Check if machine is configured
        if self.hostname not in self.config.machines:
            die(f"Machine '{self.hostname}' is not configured. Run 'brewfile init' first.")

    def _ensure_brewfile(self) -> None:
        """Ensure Brewfile exists and is up to date."""
        self.dump_brewfile(self.hostname, self.brewfile_path)

    def dump_brewfile(self, machine_name: str, brewfile_path: Path) -> None:
        """Generate Brewfile from config for a specific machine."""
        packages = self.config.get_machine_packages(machine_name)

        # Group packages by type
        taps = [p.name for p in packages if p.package_type == PackageType.TAP]
        brews = [p.name for p in packages if p.package_type == PackageType.BREW]
        casks = [p.name for p in packages if p.package_type == PackageType.CASK]
        mas_apps = [p.name for p in packages if p.package_type == PackageType.MAS]

        lines = []

        # Add taps
        for tap in taps:
            lines.append(f'tap "{tap}"')

        if taps:
            lines.append("")  # Empty line after taps

        # Add brews
        for brew in brews:
            lines.append(f'brew "{brew}"')

        if brews:
            lines.append("")  # Empty line after brews

        # Add casks
        for cask in casks:
            lines.append(f'cask "{cask}"')

        if casks:
            lines.append("")  # Empty line after casks

        # Add mas apps with IDs
        for mas_app in mas_apps:
            if "::" in mas_app:
                app_name, app_id = mas_app.split("::", 1)
                lines.append(f'mas "{app_name}", id: {app_id}')
            else:
                # Fallback for entries without ID
                lines.append(f'# mas "{mas_app}" # ID needed - check with: mas list')

        content = "\n".join(lines) + "\n"
        try:
            with open(brewfile_path, "w") as f:
                f.write(content)
        except OSError as e:
            die(f"Could not write Brewfile: {e}")

    # Command methods
    def cmd_init(self) -> None:
        """Initialize machine configuration interactively."""
        say(f"Configuring machine: {AnsiColor.BLUE}{self.hostname}{AnsiColor.RESET}")

        # Step 1: Ensure config file exists (create empty one if needed)
        if not self.config_file.exists():
            say("Creating new brewfile configuration...")
            self.config = BrewfileConfig()  # Empty config
            self.config.save(self.config_file)
            success(f"Created configuration at {self.config_file}")
        else:
            self.config = BrewfileConfig.load(self.config_file)

        # Step 2: Check if package groups exist, create "core" if none
        if not self.config.packages:
            say("No package groups found. Creating empty 'core' group...")

            # Create empty "core" group
            core_group = PackageGroup()
            self.config.packages["core"] = core_group

            # Assign "core" group to this machine
            self.config.machines[self.hostname] = ["core"]
            self.config.save(self.config_file)

            success(f"Created empty 'core' group for {self.hostname}")
            print()
            say("Next steps:")
            print("  • Add packages: brewfile add <package_name>")
            print("  • Adopt current system: brewfile sync-adopt")
            print("  • Check status: brewfile status")
            return

        # Step 3: Groups exist - proceed with selection process
        # Show available groups
        print("\nAvailable package groups:")
        for i, group_name in enumerate(self.config.packages.keys(), 1):
            group = self.config.packages[group_name]
            total_pkgs = len(group.taps + group.brews + group.casks + group.mas)
            print(f"  {i}. {group_name} ({total_pkgs} packages)")

        # Let user select groups
        print(f"\nSelect groups for machine '{self.hostname}' (comma-separated numbers or 'all'):")
        try:
            selection = input("> ").strip()

            if selection.lower() == "all":
                selected_groups = list(self.config.packages.keys())
            else:
                indices = [int(x.strip()) for x in selection.split(",") if x.strip().isdigit()]
                group_names = list(self.config.packages.keys())
                selected_groups = [group_names[i - 1] for i in indices if 1 <= i <= len(group_names)]

            if not selected_groups:
                die("No valid groups selected.")

            # Update machine configuration
            self.config.machines[self.hostname] = selected_groups
            self.config.save(self.config_file)

            success(f"Machine '{self.hostname}' configured with groups: {', '.join(selected_groups)}")

        except (ValueError, KeyboardInterrupt):
            die("Invalid selection or cancelled.")

    def cmd_status(self) -> tuple[int, int]:
        """Show package status by comparing config and system state."""
        try:
            configured, missing, extra = self.machine_packages

            # Get machine groups for display
            groups = self.config.machines.get(self.hostname, [])

            print(f"\n{AnsiColor.BLUE}📦 Package Status for {self.hostname}:{AnsiColor.RESET}")
            print(f"Groups: {', '.join(groups)}")

            # Group packages by type for display
            packages_by_type = {
                pkg_type.plural: [p for p in configured if p.package_type == pkg_type] for pkg_type in PackageType
            }

            # Group extra packages by type for display
            extra_by_type = {
                pkg_type.plural: [p for p in extra if p.package_type == pkg_type] for pkg_type in PackageType
            }

            # Show each package type
            for pkg_type in PackageType:
                package_type_name = pkg_type.plural
                packages = packages_by_type[package_type_name]

                # Show configured packages
                if packages:
                    print(f"\n{package_type_name.title()}:")
                    for pkg in sorted(packages, key=lambda x: x.name):
                        if pkg.installed == InstallationStatus.INSTALLED:
                            print(f"  ✓ {pkg.name} {AnsiColor.GRAY}({pkg.group}){AnsiColor.RESET}")
                        else:
                            print(
                                f"  {AnsiColor.RED}✗{AnsiColor.RESET} {pkg.name} {AnsiColor.GRAY}({pkg.group}) - missing{AnsiColor.RESET}"
                            )

                # Show extra packages
                extra_packages = extra_by_type.get(package_type_name, [])
                if extra_packages:
                    if packages:  # Only add extra header if we had configured packages
                        print(f"\n{package_type_name.title()} (extra):")
                    else:  # No configured packages, so this is the main section
                        print(f"\n{package_type_name.title()}:")
                    for package in sorted(extra_packages, key=lambda x: x.name):
                        print(
                            f"  {AnsiColor.BLUE}+{AnsiColor.RESET} {package.name} {AnsiColor.GRAY}- not in config{AnsiColor.RESET}"
                        )

            # Summary counts
            total_missing = len(missing)
            total_extra = len(extra)

            print("\nSummary:")
            if total_missing > 0:
                print(f"  {AnsiColor.RED}✗{AnsiColor.RESET} {total_missing} package(s) need installation")
            if total_extra > 0:
                print(f"  {AnsiColor.BLUE}+{AnsiColor.RESET} {total_extra} extra package(s) not in current config")

            if total_missing == 0 and total_extra == 0:
                success("All packages synchronized! 🎉")

            return total_missing, total_extra

        except Exception as e:
            die(f"Failed to get package status: {e}")
            return 0, 0  # This won't be reached due to die(), but satisfies type checker

    def cmd_interactive(self) -> None:
        """Interactive mode with menu options."""
        total_missing, total_extra = self.cmd_status()

        # If everything is in sync, no need for interactive menu - just exit
        if total_missing == 0 and total_extra == 0:
            return  # Status already showed "All packages synchronized! 🎉"

        # Show sync options only when there's something to do
        print(f"{AnsiColor.BLUE}🛠️ Available Actions:{AnsiColor.RESET}")
        print("  1. Sync + Adopt (safe: install missing, keep extras)")
        print("  2. Sync + Cleanup (destructive: install missing, remove extras)")
        print("  3. Edit config file")
        print("  4. Exit")

        try:
            choice = input(f"\n{AnsiColor.GREEN}Choose action [1-4]:{AnsiColor.RESET} ").strip()

            if choice == "1":
                self.cmd_sync_adopt()
            elif choice == "2":
                self.cmd_sync_cleanup()
            elif choice == "3":
                self.cmd_edit()
            elif choice == "4":
                say("Goodbye! 👋")
            else:
                warn("Invalid choice. Exiting.")

        except KeyboardInterrupt:
            print(f"\n{AnsiColor.GRAY}Cancelled.{AnsiColor.RESET}")

    def cmd_sync_adopt(self) -> None:
        """Install missing packages and adopt extra packages to config."""
        configured, missing, extra = self.machine_packages

        if not missing and not extra:
            success("All packages are already synchronized!")
            return

        # Show detailed summary
        print(f"\n{AnsiColor.YELLOW}Sync + Adopt Summary:{AnsiColor.RESET}")
        if missing:
            print(f"\n{AnsiColor.GREEN}INSTALL ({len(missing)}):{AnsiColor.RESET}")
            missing_by_type = {
                pkg_type.plural: [p for p in missing if p.package_type == pkg_type] for pkg_type in PackageType
            }
            for pkg_type_name, packages in missing_by_type.items():
                if packages:
                    print(f"  {pkg_type_name.title()}: {', '.join(p.name for p in packages)}")

        if extra:
            print(f"\n{AnsiColor.BLUE}ADOPT ({len(extra)}):{AnsiColor.RESET}")
            extra_by_type = {
                pkg_type.plural: [p for p in extra if p.package_type == pkg_type] for pkg_type in PackageType
            }
            for pkg_type_name, packages in extra_by_type.items():
                if packages:
                    print(f"  {pkg_type_name.title()}: {', '.join(p.name for p in packages)}")

        print(f"\nThis will install missing packages and keep all extras in your {self.hostname} config.")
        print("No packages will be removed from your system.")

        try:
            confirm = input("\nProceed? (y/N): ").lower().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not confirm.startswith("y"):
            return

        try:
            # Install missing packages
            if missing:
                self._ensure_brewfile()
                say("Installing missing packages...")
                Brew.Bundle.install(self.brewfile_path)

            # Adopt extra packages
            if extra:
                say("Adopting extra packages to configuration...")
                # Add to first configured group or create new one
                groups = self.config.machines[self.hostname]
                target_group = groups[0] if groups else "adopted"

                if target_group not in self.config.packages:
                    self.config.packages[target_group] = PackageGroup()

                for pkg in extra:
                    self.config.packages[target_group].add_package(pkg.package_type, pkg.name)

                self.config.save(self.config_file)

            success("Sync + Adopt complete! ✨")

        except subprocess.CalledProcessError as e:
            die(f"Failed to sync packages: {e}")

    def cmd_sync_cleanup(self) -> None:
        """Install missing packages and remove extra packages."""
        configured, missing, extra = self.machine_packages

        if not missing and not extra:
            success("All packages are already synchronized!")
            return

        # Show detailed warning summary
        print(f"\n{AnsiColor.YELLOW}Sync + Cleanup Summary:{AnsiColor.RESET}")
        if missing:
            print(f"\n{AnsiColor.GREEN}INSTALL ({len(missing)}):{AnsiColor.RESET}")
            # Group by type for display
            missing_by_type = {
                pkg_type.plural: [p.name for p in missing if p.package_type == pkg_type] for pkg_type in PackageType
            }
            for pkg_type_name, packages in missing_by_type.items():
                if packages:
                    print(f"  {pkg_type_name.title()}: {', '.join(packages)}")

        if extra:
            print(f"\n{AnsiColor.RED}⚠ REMOVE ({len(extra)}):{AnsiColor.RESET}")
            # Group by type for display
            extra_by_type = {
                pkg_type.plural: [p.name for p in extra if p.package_type == pkg_type] for pkg_type in PackageType
            }
            for pkg_type_name, packages in extra_by_type.items():
                if packages:
                    print(f"  {pkg_type_name.title()}: {', '.join(packages)}")

        print("\nThis will install missing packages and remove extras from your system.")
        if extra:
            print(f"{AnsiColor.RED}WARNING: This will uninstall packages from your system!{AnsiColor.RESET}")

        try:
            confirm = input("\nProceed? (y/N): ").lower().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not confirm.startswith("y"):
            return

        try:
            # Install missing packages first
            if missing:
                self._ensure_brewfile()
                say("Installing missing packages...")
                Brew.Bundle.install(self.brewfile_path)

            # Remove extra packages
            if extra:
                # Regenerate Brewfile from config (not system) to ensure cleanup works correctly
                self._ensure_brewfile()
                say("Removing extra packages...")
                try:
                    Brew.Bundle.cleanup(self.brewfile_path)
                    success("Sync + Cleanup complete! ✨")
                except subprocess.CalledProcessError:
                    warn("Cleanup portion failed, but install may have succeeded.")
            else:
                success("Sync + Cleanup complete! ✨")

        except subprocess.CalledProcessError as e:
            die(f"Failed to sync packages: {e}")

    def cmd_add(self, package_name: str, package_type: Optional[PackageType] = None) -> None:
        """Add package to configuration and install it."""
        self._ensure_configured()

        # Auto-detect package type if not provided
        if package_type is None:
            package_type = Brew.detect_package_type(package_name)

        say(f"Adding {package_type.value}: {package_name}")

        # Add to first configured group
        groups = self.config.machines[self.hostname]
        if not groups:
            die("No package groups configured for this machine.")

        target_group = groups[0]
        if target_group not in self.config.packages:
            self.config.packages[target_group] = PackageGroup()

        self.config.packages[target_group].add_package(package_type, package_name)
        self.config.save(self.config_file)

        # Install the package
        try:
            self._ensure_brewfile()
            Brew.Bundle.install(self.brewfile_path)
            success(f"Added and installed {package_type.value}: {package_name}")
        except subprocess.CalledProcessError as e:
            die(f"Failed to install package: {e}")

    def cmd_remove(self, package_name: str) -> None:
        """Remove package from system and configuration."""
        self._ensure_configured()

        # Find package in configuration
        package_info = self.config.get_package_info(package_name)
        if not package_info:
            warn(f"Package '{package_name}' not found in configuration.")
            return

        say(f"Removing {package_info.package_type.value}: {package_name}")

        try:
            # Try to remove from system first
            if package_info.package_type == PackageType.BREW:
                subprocess.run(["brew", "uninstall", package_name], check=True)
            elif package_info.package_type == PackageType.CASK:
                subprocess.run(["brew", "uninstall", "--cask", package_name], check=True)
            elif package_info.package_type == PackageType.MAS:
                # MAS packages can't be uninstalled via CLI
                warn("MAS packages cannot be uninstalled automatically. Please remove manually from Applications.")
            elif package_info.package_type == PackageType.TAP:
                subprocess.run(["brew", "untap", package_name], check=True)

            # Remove from configuration only if system removal succeeded
            removed_type = self.config.remove_package(package_name, self.config_file)
            if removed_type:
                success(f"Removed {removed_type.value}: {package_name}")
            else:
                warn(f"Package was removed from system but not found in config: {package_name}")

        except subprocess.CalledProcessError:
            warn(f"Failed to remove {package_name} from system. Keeping in configuration.")

    def cmd_edit(self) -> None:
        """Open configuration file in editor."""
        editor = os.environ.get("EDITOR", "nano")
        say(f"Opening {self.config_file} with {editor}...")

        try:
            subprocess.run([editor, str(self.config_file)], check=True)
            # Reload config after editing
            self.config = BrewfileConfig.load(self.config_file)
            success("Config reloaded after editing.")
        except subprocess.CalledProcessError:
            warn("Failed to open editor.")
