# OVERHAUL-PLAN.md — Leave No Stone Unturned v2.1 (Universal – Cline + Windsurf)

**Status**: Draft → Approved → In Progress → Completed  
**Branch**: `overhaul-2026` (create if missing)  
**Last updated**: {{CURRENT_DATE}}  
**Last checkpoint**:  
**Active tools**: Cline + Windsurf (both respect this single plan)

## PROJECT METADATA (auto-filled by either agent)
- Tech stack & architecture:
- Total files: code ___ | .md ___ | other ___
- Git status:
- Test coverage baseline:
- TODO/FIXME/XXX count:
- Linter errors baseline:

## ACTIVE TOOLS & COMPATIBILITY
- **Cline**: Uses Plan/Act mode + Memory Bank (projectbrief.md, activeContext.md, progress.md). Always create checkpoint before Act.
- **Windsurf Cascade**: Uses Planning Mode. Update this plan in real time.
- Both tools share this exact file — never create a second copy.

## PHASE 0 – DISCOVERY & COMPLETE INVENTORY (start here)
### 0.1 Filesystem snapshot (run & paste outputs)
```bash
tree -a --gitignore > tree-full.txt
find . -type f | sort > inventory-all.txt
find . -name "*.md" | sort > inventory-docs.md
find . \( -name "*.py" -o -name "*.ts" ... \) | sort > inventory-code.txt
grep -r --include="*.md" -E "TODO|FIXME|XXX|DEPRECATED" . --exclude-dir={node_modules,venv,.git,archive} > todos.md