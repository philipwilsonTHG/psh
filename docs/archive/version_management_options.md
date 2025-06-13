# Version Management Options for Python Projects

## Current Approach (Manual)
- Manually update version in multiple files
- Error-prone and easy to forget files
- Requires discipline to keep in sync

## Better Approaches

### 1. Single Source of Truth (Dynamic Reading)
Keep version in one place and read it dynamically from other locations.

**Option A: Version in pyproject.toml (Recommended for modern projects)**
```python
# In psh/__init__.py or psh/version.py
import importlib.metadata
__version__ = importlib.metadata.version("psh")
```

**Option B: Version in version.py**
```toml
# In pyproject.toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "psh.version.__version__"}
```

### 2. Build-time Version Management Tools

**setuptools-scm (Most Popular)**
- Derives version from git tags automatically
- No version stored in files at all
- Version is computed from git state

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]

[project]
dynamic = ["version"]

[tool.setuptools_scm]
# Version will be derived from git tags
```

**hatch-vcs**
- Similar to setuptools-scm but for Hatch
- Also derives version from git tags

### 3. Release Automation Tools

**bump2version / bumpversion**
- Updates version in multiple files with one command
- Creates git commit and tag automatically

```ini
# .bumpversion.cfg
[bumpversion]
current_version = 0.7.0
commit = True
tag = True

[bumpversion:file:pyproject.toml]
search = version = "{current_version}"
replace = version = "{new_version}"

[bumpversion:file:psh/version.py]
search = __version__ = "{current_version}"
replace = __version__ = "{new_version}"
```

**python-semantic-release**
- Fully automated versioning and release
- Follows semantic versioning based on commit messages
- Creates changelog, tags, and releases

### 4. Simple Makefile/Script Approach
Create a simple release script that updates all files:

```bash
#!/bin/bash
# release.sh
VERSION=$1
sed -i '' "s/__version__ = .*/__version__ = \"$VERSION\"/" psh/version.py
sed -i '' "s/version = .*/version = \"$VERSION\"/" pyproject.toml
git add -A
git commit -m "Bump version to $VERSION"
git tag -a "v$VERSION" -m "Version $VERSION"
```

## Recommendations

1. **For educational projects like psh**: Use setuptools dynamic version reading from version.py. It's simple, requires minimal changes, and teaches good practices.

2. **For production projects**: Use setuptools-scm to derive versions from git tags. This ensures git tags are the single source of truth.

3. **For projects with complex release processes**: Use python-semantic-release for full automation.

## Implementation for psh

The simplest improvement would be to make pyproject.toml read the version from version.py:

```toml
# pyproject.toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "psh.version.__version__"}
```

This way, you only need to update version.py, and the package version will automatically sync.