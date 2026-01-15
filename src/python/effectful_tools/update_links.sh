#!/bin/bash
# Update all documentation links from documents/core/ to documents/engineering/
# Also renames files to new naming convention

set -e

echo "Updating documentation cross-references..."

# Find all markdown files in documents/ and root directory
FILES=$(find documents/ README.md CLAUDE.md -name "*.md" -type f 2>/dev/null || true)

for file in $FILES; do
    if [ -f "$file" ]; then
        echo "Updating: $file"

        # Update absolute paths: documents/core/ → documents/engineering/
        sed -i '' 's|documents/core/architecture\.md|documents/engineering/architecture.md|g' "$file"
        sed -i '' 's|documents/core/type_safety_doctrine\.md|documents/engineering/code_quality.md|g' "$file"
        sed -i '' 's|documents/core/purity\.md|documents/engineering/code_quality.md|g' "$file"
        sed -i '' 's|documents/core/purity_patterns\.md|documents/engineering/purity_patterns.md|g' "$file"
        sed -i '' 's|documents/core/testing_doctrine\.md|documents/engineering/testing.md|g' "$file"
        sed -i '' 's|documents/core/docker_doctrine\.md|documents/engineering/docker_workflow.md|g' "$file"
        sed -i '' 's|documents/core/observability_doctrine\.md|documents/engineering/observability.md|g' "$file"
        sed -i '' 's|documents/core/monitoring_standards\.md|documents/engineering/monitoring_and_alerting.md|g' "$file"
        sed -i '' 's|documents/core/alerting_policy\.md|documents/engineering/monitoring_and_alerting.md|g' "$file"

        # Update relative paths: core/ → engineering/ (from documents/)
        sed -i '' 's|core/architecture\.md|engineering/architecture.md|g' "$file"
        sed -i '' 's|core/type_safety_doctrine\.md|engineering/code_quality.md|g' "$file"
        sed -i '' 's|core/purity\.md|engineering/code_quality.md|g' "$file"
        sed -i '' 's|core/purity_patterns\.md|engineering/purity_patterns.md|g' "$file"
        sed -i '' 's|core/testing_doctrine\.md|engineering/testing.md|g' "$file"
        sed -i '' 's|core/docker_doctrine\.md|engineering/docker_workflow.md|g' "$file"
        sed -i '' 's|core/observability_doctrine\.md|engineering/observability.md|g' "$file"
        sed -i '' 's|core/monitoring_standards\.md|engineering/monitoring_and_alerting.md|g' "$file"
        sed -i '' 's|core/alerting_policy\.md|engineering/monitoring_and_alerting.md|g' "$file"

        # Update parent-relative paths: ../core/ → ../engineering/ (from tutorials/api/)
        sed -i '' 's|\.\./core/architecture\.md|../engineering/architecture.md|g' "$file"
        sed -i '' 's|\.\./core/type_safety_doctrine\.md|../engineering/code_quality.md|g' "$file"
        sed -i '' 's|\.\./core/purity\.md|../engineering/code_quality.md|g' "$file"
        sed -i '' 's|\.\./core/purity_patterns\.md|../engineering/purity_patterns.md|g' "$file"
        sed -i '' 's|\.\./core/testing_doctrine\.md|../engineering/testing.md|g' "$file"
        sed -i '' 's|\.\./core/docker_doctrine\.md|../engineering/docker_workflow.md|g' "$file"
        sed -i '' 's|\.\./core/observability_doctrine\.md|../engineering/observability.md|g' "$file"
        sed -i '' 's|\.\./core/monitoring_standards\.md|../engineering/monitoring_and_alerting.md|g' "$file"
        sed -i '' 's|\.\./core/alerting_policy\.md|../engineering/monitoring_and_alerting.md|g' "$file"

        # Update text references to doctrines (not file paths)
        sed -i '' 's|Testing Doctrine|Testing|g' "$file"
        sed -i '' 's|Type Safety Doctrine|Type Safety|g' "$file"
        sed -i '' 's|Purity Doctrine|Purity|g' "$file"
        sed -i '' 's|Docker Doctrine|Docker Workflow|g' "$file"
        sed -i '' 's|Observability Doctrine|Observability|g' "$file"
        sed -i '' 's|Alerting Policy|Alerting|g' "$file"
    fi
done

echo "✓ Link updates complete!"
echo ""
echo "Updated references:"
echo "  - documents/core/* → documents/engineering/*"
echo "  - File renames applied (e.g., type_safety_doctrine.md → code_quality.md)"
echo "  - Text references updated (e.g., 'Testing Doctrine' → 'Testing')"
