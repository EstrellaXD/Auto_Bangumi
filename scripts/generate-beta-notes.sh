#!/bin/bash
# Generate release notes for beta versions
# Usage: ./generate-beta-notes.sh <new-tag> [previous-tag]

set -e

NEW_TAG="${1:?Usage: $0 <new-tag> [previous-tag]}"
REPO_URL="https://github.com/EstrellaXD/Auto_Bangumi"

# Auto-detect previous beta tag if not provided
if [ -z "$2" ]; then
    PREV_TAG=$(git tag --sort=-v:refname | grep -E "^${NEW_TAG%-*}" | grep beta | head -2 | tail -1)
else
    PREV_TAG="$2"
fi

if [ -z "$PREV_TAG" ] || [ "$PREV_TAG" = "$NEW_TAG" ]; then
    echo "## Initial Beta Release"
    echo ""
    echo "First beta for this version series."
    exit 0
fi

echo "## Changes since ${PREV_TAG#v}"
echo ""

# Get commits and categorize
FEATS=$(git log --oneline "$PREV_TAG..$NEW_TAG" --no-merges --grep="^feat" --format="- %s" 2>/dev/null || true)
FIXES=$(git log --oneline "$PREV_TAG..$NEW_TAG" --no-merges --grep="^fix" --format="- %s" 2>/dev/null || true)
PERFS=$(git log --oneline "$PREV_TAG..$NEW_TAG" --no-merges --grep="^perf" --format="- %s" 2>/dev/null || true)
DOCS=$(git log --oneline "$PREV_TAG..$NEW_TAG" --no-merges --grep="^docs" --format="- %s" 2>/dev/null || true)
OTHERS=$(git log --oneline "$PREV_TAG..$NEW_TAG" --no-merges --grep="^chore\|^refactor\|^test\|^ci" --format="- %s" 2>/dev/null || true)

if [ -n "$FEATS" ]; then
    echo "### Features"
    echo "$FEATS"
    echo ""
fi

if [ -n "$FIXES" ]; then
    echo "### Fixes"
    echo "$FIXES"
    echo ""
fi

if [ -n "$PERFS" ]; then
    echo "### Performance"
    echo "$PERFS"
    echo ""
fi

if [ -n "$DOCS" ]; then
    echo "### Documentation"
    echo "$DOCS"
    echo ""
fi

# Don't show chore/refactor/test in release notes (too noisy)

echo "---"
echo "**Full Changelog**: ${REPO_URL}/compare/${PREV_TAG}...${NEW_TAG}"
