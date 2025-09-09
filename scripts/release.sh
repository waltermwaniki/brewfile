#!/bin/bash
set -e

# Simple release script for brewfile using uv and GitHub Actions
# Usage: ./scripts/release.sh [version_type]
# version_type: patch (default), minor, major, or specific version (e.g., 1.2.3)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

main() {
    local version_type="${1:-patch}"
    
    print_status "🚀 Starting brewfile release process..."
    
    # Preflight checks
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Working directory is not clean. Please commit or stash your changes."
        exit 1
    fi
    
    if [[ $(git branch --show-current) != "main" ]]; then
        print_error "Please switch to main branch before releasing."
        exit 1
    fi
    
    # Get current and new version using uv
    current_version=$(uv version --short)
    print_status "Current version: $current_version"
    
    # Calculate new version
    if [[ "$version_type" =~ ^(patch|minor|major)$ ]]; then
        new_version=$(uv version --bump "$version_type" --dry-run --short)
    elif [[ "$version_type" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        new_version="$version_type"
    else
        print_error "Invalid version. Use 'patch', 'minor', 'major', or a specific version (e.g., 1.2.3)"
        exit 1
    fi
    
    print_status "New version will be: $new_version"
    
    # Confirm release
    echo
    print_warning "This will:"
    echo "  1. 📝 Update version to $new_version using uv"
    echo "  2. 📦 Build and test the package locally"  
    echo "  3. 💾 Commit and push changes"
    echo "  4. 🏷️  Create git tag v$new_version"
    echo "  5. 🚀 Push tag to trigger GitHub Actions CI/CD:"
    echo "     - Publish to PyPI"
    echo "     - Update Homebrew formula"
    echo "     - Create GitHub release"
    echo
    read -p "Continue? (y/N): " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && { print_status "Release cancelled."; exit 0; }
    
    # Update version using uv
    print_status "📝 Updating version using uv..."
    if [[ "$version_type" =~ ^(patch|minor|major)$ ]]; then
        uv version --bump "$version_type"
    else
        uv version "$version_type"
    fi
    
    # Test build
    print_status "🔨 Building and testing package..."
    uv build
    
    # Test CLI works
    if ! uv run brewfile help >/dev/null 2>&1; then
        print_error "Build test failed - CLI not working"
        exit 1
    fi
    print_status "✅ Build test passed"
    
    # Update CHANGELOG date
    if [[ -f CHANGELOG.md ]]; then
        current_date=$(date +%Y-%m-%d)
        sed -i '' "s/## \[Unreleased\]/## [Unreleased]\n\n### Added\n- \n\n### Changed\n- \n\n### Fixed\n- \n\n## [$new_version] - $current_date/" CHANGELOG.md
        print_status "📝 Updated CHANGELOG.md"
    fi
    
    # Commit changes
    print_status "💾 Committing version bump..."
    git add pyproject.toml uv.lock dist/ CHANGELOG.md 2>/dev/null || true
    git commit -m "Bump version to v$new_version

- Updated version in pyproject.toml
- Updated CHANGELOG.md  
- Built package distribution"
    
    # Create and push tag
    print_status "🏷️  Creating tag v$new_version..."
    git tag -a "v$new_version" -m "Release v$new_version"
    
    print_status "🚀 Pushing changes and tag to trigger CI/CD..."
    git push origin main
    git push origin "v$new_version"
    
    echo
    print_status "🎉 Release v$new_version initiated!"
    echo
    echo "Next steps (automatic via GitHub Actions):"
    echo "  1. 📦 Publish to PyPI: https://pypi.org/project/brewfile/"
    echo "  2. 🍺 Update Homebrew formula automatically"
    echo "  3. 📋 Create GitHub release"
    echo
    echo "Monitor progress at:"
    echo "  🔄 GitHub Actions: https://github.com/waltermwaniki/brewfile/actions"
    echo "  📦 PyPI: https://pypi.org/project/brewfile/"
    echo
    print_status "Users will be able to install with:"
    echo "  brew tap waltermwaniki/brewfile && brew install brewfile"
    echo "  pip install brewfile==$new_version"
}

main "$@"
