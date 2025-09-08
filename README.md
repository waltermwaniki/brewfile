# Brewfile - Intelligent Homebrew Package Management

Brewfile is a command-line tool that provides intelligent Homebrew package management using `brew bundle` with JSON configuration and machine-aware installations.

## Features

- **Machine-aware configurations**: Different package sets for different machines
- **Package groups**: Organize packages into logical groups (e.g., "development", "media", "work")
- **Intelligent sync operations**: Install missing packages, remove extras, or adopt system packages
- **Interactive workflows**: Safe operations with confirmations
- **Full Homebrew support**: Formulas, casks, taps, and Mac App Store apps
- **Type-safe operations**: Automatic package type detection with manual overrides
- **Status reporting**: Clear visibility into what's installed, missing, or extra

## Installation

### From PyPI (Recommended)

```bash
pip install brewfile
```

### From Source

```bash
git clone https://github.com/waltermwaniki/brewfile.git
cd brewfile
uv sync
uv run brewfile --help
```

## Quick Start

1. **Initialize configuration:**

   ```bash
   brewfile init
   ```

2. **Check current status:**

   ```bash
   brewfile status
   ```

3. **Add packages:**

   ```bash
   brewfile add neovim
   brewfile add --cask visual-studio-code
   ```

4. **Sync your system:**

   ```bash
   brewfile sync-adopt    # Safe: installs missing, adopts extras
   brewfile sync-cleanup  # Removes extra packages (destructive)
   ```

## Configuration

Brewfile uses a JSON configuration file at `~/.config/brewfile.json`:

```json
{
  "version": "1.0",
  "packages": {
    "development": {
      "taps": ["homebrew/cask-fonts"],
      "brews": ["git", "neovim", "python"],
      "casks": ["visual-studio-code", "docker"],
      "mas": ["Xcode::497799835"]
    },
    "media": {
      "brews": ["ffmpeg", "youtube-dl"],
      "casks": ["vlc", "spotify"]
    }
  },
  "machines": {
    "work-laptop": ["development"],
    "personal-mac": ["development", "media"]
  }
}
```

## Commands

### Core Commands

- `brewfile init` - Initialize configuration with current system packages
- `brewfile status` - Show package status and synchronization state
- `brewfile add <package>` - Add package to configuration and install
- `brewfile remove <package>` - Remove package from system and configuration
- `brewfile edit` - Open configuration file in editor

### Sync Commands

- `brewfile sync-adopt` - Install missing packages + adopt extra packages to config (safe)
- `brewfile sync-cleanup` - Install missing packages + remove extra packages (destructive)

### Interactive Mode

Run `brewfile` without arguments to enter interactive mode with guided workflows.

## Advanced Usage

### Package Types

Brewfile automatically detects package types, but you can force specific types:

```bash
brewfile add --cask chrome        # Force as cask
brewfile add neovim               # Auto-detect (formula)
```

### Machine-Specific Configurations

Configure different package sets for different machines by hostname:

```json
{
  "machines": {
    "work-macbook": ["development", "work-tools"],
    "personal-imac": ["development", "gaming", "media"]
  }
}
```

### Mac App Store Apps

Include Mac App Store apps with app IDs:

```bash
brewfile add "Xcode::497799835"   # Format: AppName::AppID
```

## Configuration Management

### Package Groups

Organize packages into logical groups:

- **development**: Development tools and languages
- **media**: Audio/video tools and entertainment
- **work**: Work-specific applications
- **gaming**: Games and gaming tools

### Dotfiles Integration

**Brewfile works exceptionally well with dotfiles management systems!** 🔗

For multi-machine synchronization:

1. **Store your config in dotfiles**: Add `~/.config/brewfile.json` to your dotfiles repository
2. **Symlink on new machines**: Your dotfiles manager can symlink the config automatically
3. **Machine-aware setup**: Different machines automatically get their appropriate package groups
4. **One command setup**: Run `brewfile sync-adopt` on a new machine to get all your tools

```bash
# Example dotfiles setup
# In your dotfiles repo:
~/dotfiles/config/brewfile.json -> ~/.config/brewfile.json

# On a new machine after dotfiles setup:
brewfile sync-adopt  # Installs all packages for this machine
```

This approach ensures consistent development environments across all your machines while respecting machine-specific needs (e.g., work laptop vs. personal desktop).

### Best Practices

1. Keep packages in appropriate groups
2. Use machine-specific configurations for different setups
3. Store your brewfile config in your dotfiles repository
4. Regularly run `brewfile status` to maintain sync
5. Use `sync-adopt` for safe operations, `sync-cleanup` when you need to clean up

## Requirements

- macOS (Homebrew is macOS-specific)
- Python 3.9 or higher
- Homebrew installed
- Optional: `mas` for Mac App Store apps

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

If you encounter issues or have questions:

1. Check existing [GitHub Issues](https://github.com/waltermwaniki/brewfile/issues)
2. Create a new issue with details about your problem
3. Include your configuration file (with sensitive data removed)

---

**Happy brewing! 🍺**
