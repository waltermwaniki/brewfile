"""
Command-line interface for Brewfile.

Handles argument parsing, command dispatch, and help display.
"""

import sys

from .models import PackageType
from .utils import AnsiColor, error


def show_help():
    """Display comprehensive help information."""
    print(f"{AnsiColor.BLUE}BrewfileManager{AnsiColor.RESET} - Intelligent Homebrew package management")
    print("\nUSAGE:")
    print("  brewfile [COMMAND] [OPTIONS]")
    print("  brewfile                    # Interactive mode (default)")

    print("\nCOMMANDS:")
    print(f"  {AnsiColor.GREEN}init{AnsiColor.RESET}                    Initialize machine configuration")
    print(f"  {AnsiColor.GREEN}status{AnsiColor.RESET}                  Show package status and synchronization state")
    print(f"  {AnsiColor.GREEN}sync-adopt{AnsiColor.RESET}              Install missing packages + adopt extras")
    print(f"  {AnsiColor.GREEN}sync-cleanup{AnsiColor.RESET}            Install missing packages + remove extras")
    print(f"  {AnsiColor.GREEN}add{AnsiColor.RESET} <package> [--cask]   Add package to configuration and install")
    print(
        f"  {AnsiColor.GREEN}remove{AnsiColor.RESET} <package>        Remove package from system and configuration (idempotent)"
    )
    print(f"  {AnsiColor.GREEN}edit{AnsiColor.RESET}                    Open configuration file in editor")
    print(f"  {AnsiColor.GREEN}help{AnsiColor.RESET}, -h, --help        Show this help message")

    print("\nEXAMPLES:")
    print("  brewfile status              # Show current package status")
    print("  brewfile add neovim          # Add and install neovim (auto-detected as formula)")
    print("  brewfile add --cask chrome   # Add and install Chrome as cask")
    print("  brewfile remove python       # Remove python from system and config (idempotent)")
    print("  brewfile sync-adopt          # Sync packages and keep all extras")
    print("  brewfile sync-cleanup        # Sync packages and remove extras (destructive)")

    print("\nCONFIGURATION:")
    print(f"  Config file: {AnsiColor.GRAY}~/.config/brewfile.json{AnsiColor.RESET}")
    print(f"  Brewfile (Generated):    {AnsiColor.GRAY}~/Brewfile{AnsiColor.RESET}")

    print("\nMORE INFO:")
    print("  - Uses JSON configuration with package groups")
    print("  - Machine-aware installations")
    print("  - Leverages 'brew bundle' for all operations")
    print("  - Supports taps, formulas, casks, and Mac App Store apps")


def show_command_help(command: str) -> bool:
    """Show help for a specific command. Returns True if help was shown."""
    if len(sys.argv) >= 3 and sys.argv[2] in ["-h", "--help"]:
        if command == "init":
            print(f"{AnsiColor.BLUE}brewfile init{AnsiColor.RESET} - Initialize machine configuration")
            print("\nDESCRIPTION:")
            print("  Configure which package groups this machine should use.")
            print("  This must be run before using other commands.")
            print("\nEXAMPLE:")
            print("  brewfile init    # Interactive group selection")
        elif command == "status":
            print(f"{AnsiColor.BLUE}brewfile status{AnsiColor.RESET} - Show package status and synchronization state")
            print("\nDESCRIPTION:")
            print("  Shows which packages are installed, missing, or extra.")
            print("  Compares your configuration against the actual system state.")
            print("\nEXAMPLE:")
            print("  brewfile status  # Show detailed package status")
        elif command == "sync-adopt":
            print(f"{AnsiColor.BLUE}brewfile sync-adopt{AnsiColor.RESET} - Install missing packages + adopt extras")
            print("\nDESCRIPTION:")
            print("  Installs missing packages and adds extra packages to your config.")
            print("  Safe operation - nothing gets removed from your system.")
            print("\nEXAMPLE:")
            print("  brewfile sync-adopt  # Sync packages safely")
        elif command == "sync-cleanup":
            print(f"{AnsiColor.BLUE}brewfile sync-cleanup{AnsiColor.RESET} - Install missing packages + remove extras")
            print("\nDESCRIPTION:")
            print("  Installs missing packages and removes extra packages from your system.")
            print(f"  {AnsiColor.RED}WARNING: This will uninstall packages not in your config!{AnsiColor.RESET}")
            print("\nEXAMPLE:")
            print("  brewfile sync-cleanup  # Sync packages (destructive)")
        elif command == "add":
            print(f"{AnsiColor.BLUE}brewfile add{AnsiColor.RESET} - Add package to configuration and install")
            print("\nUSAGE:")
            print("  brewfile add <package_name> [--cask]")
            print("\nARGUMENTS:")
            print("  <package_name>    Name of the package to install")
            print("\nOPTIONS:")
            print("  --cask           Force package to be treated as a cask")
            print("\nEXAMPLES:")
            print("  brewfile add neovim          # Add formula (auto-detected)")
            print("  brewfile add --cask chrome   # Add cask (forced)")
        elif command == "remove":
            print(f"{AnsiColor.BLUE}brewfile remove{AnsiColor.RESET} - Remove package from system and configuration")
            print("\nUSAGE:")
            print("  brewfile remove <package_name>")
            print("\nARGUMENTS:")
            print("  <package_name>    Name of the package to remove")
            print("\nNOTE:")
            print("  This command removes the package from both your system and configuration.")
            print("  It's idempotent - only removes from config if system removal succeeds.")
            print("\nEXAMPLES:")
            print("  brewfile remove neovim       # Remove neovim from system and config")
            print("  brewfile remove --cask chrome # Remove chrome cask")
        elif command == "edit":
            print(f"{AnsiColor.BLUE}brewfile edit{AnsiColor.RESET} - Open configuration file in editor")
            print("\nDESCRIPTION:")
            print("  Opens the brewfile configuration file in your default editor.")
            print("  Uses $EDITOR environment variable, defaults to nano.")
            print(f"  Config file: {AnsiColor.GRAY}~/.config/brewfile.json{AnsiColor.RESET}")
            print("\nEXAMPLE:")
            print("  brewfile edit    # Edit configuration manually")
        return True
    return False


def parse_args() -> tuple[str, dict]:
    """Parse command-line arguments and return (command, args_dict)."""
    if len(sys.argv) < 2:
        return "interactive", {}

    command = sys.argv[1]

    # Handle help
    if command in ["help", "-h", "--help"]:
        return "help", {}

    # Handle command-specific help
    if show_command_help(command):
        return "help", {"already_shown": True}

    args = {}

    if command == "add":
        if len(sys.argv) < 3:
            error("Usage: brewfile add <package_name> [--cask]")
            sys.exit(1)
        args["package_name"] = sys.argv[2]
        args["package_type"] = PackageType.CASK if "--cask" in sys.argv else None

    elif command == "remove":
        if len(sys.argv) < 3:
            error("Usage: brewfile remove <package_name>")
            sys.exit(1)
        args["package_name"] = sys.argv[2]

    return command, args


def main():
    """Main CLI entry point."""
    from .manager import BrewfileManager

    command, args = parse_args()

    if command == "help":
        if args.get("already_shown"):
            return  # Help was already shown by show_command_help
        show_help()
        return

    manager = BrewfileManager()

    if command == "interactive":
        manager.cmd_interactive()
    elif command in ["init", "select"]:
        manager.cmd_init()
    elif command == "status":
        manager.cmd_status()
    elif command == "sync-adopt":
        manager.cmd_sync_adopt()
    elif command == "sync-cleanup":
        manager.cmd_sync_cleanup()
    elif command == "add":
        manager.cmd_add(args["package_name"], args.get("package_type"))
    elif command == "remove":
        manager.cmd_remove(args["package_name"])
    elif command == "edit":
        manager.cmd_edit()
    else:
        error(f"Unknown command: {command}")
        print(f"Run '{AnsiColor.GREEN}brewfile help{AnsiColor.RESET}' to see available commands.")
        sys.exit(1)
