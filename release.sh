#!/bin/bash
# Release script for Python Shell (psh)
# Usage: ./release.sh [major|minor|patch]

set -e

# Check if we have uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "Error: You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Get current version
CURRENT_VERSION=$(python3 -c "from version import __version__; print(__version__)")
echo "Current version: $CURRENT_VERSION"

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine new version based on argument
case "$1" in
    major)
        NEW_MAJOR=$((MAJOR + 1))
        NEW_VERSION="$NEW_MAJOR.0.0"
        ;;
    minor)
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="$MAJOR.$NEW_MINOR.0"
        ;;
    patch)
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
        ;;
    *)
        echo "Usage: $0 [major|minor|patch]"
        echo "  major: Increment major version (breaking changes)"
        echo "  minor: Increment minor version (new features)"
        echo "  patch: Increment patch version (bug fixes)"
        exit 1
        ;;
esac

echo "New version will be: $NEW_VERSION"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Update version in version.py
sed -i.bak "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" version.py
rm version.py.bak

# Get release notes
echo "Enter release notes (press Ctrl+D when done):"
RELEASE_NOTES=$(cat)

# Update VERSION_HISTORY in version.py
# This is more complex, so we'll just remind the user
echo
echo "Don't forget to update VERSION_HISTORY in version.py with:"
echo "$NEW_VERSION ($(date +%Y-%m-%d)) - <summary>"
echo "$RELEASE_NOTES"
echo

# Commit version change
git add version.py
git commit -m "Bump version to $NEW_VERSION"

# Create git tag
TAG_MESSAGE="Version $NEW_VERSION

$RELEASE_NOTES"

git tag -a "v$NEW_VERSION" -m "$TAG_MESSAGE"

echo
echo "Version bumped to $NEW_VERSION and tagged as v$NEW_VERSION"
echo "To push the changes and tag:"
echo "  git push origin master"
echo "  git push origin v$NEW_VERSION"