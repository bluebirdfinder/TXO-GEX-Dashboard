# 🚀 Release & Version Alignment Mandatory Rule

Whenever releasing a new version or bumping the version number (e.g. v49.0 -> v49.1):

## MANDATORY WORKFLOW:
1. **Update Python Engine Version**: Change `ENGINE_VERSION = "vX.Y"` in `scripts/fetch_and_calc_vision.py`.
2. **RE-RUN DATA ENGINE IMMEDIATELY (CRITICAL)**:
   Must execute `python scripts/fetch_and_calc_vision.py` BEFORE staging/pushing.
   This ensures `data/gex_data.json` and `data/embedded_data.js` contain `"engine_version": "vX.Y"`.
   *Failure to re-run causes HTML/JS version mismatch where the UI briefly displays the new version and then flashes back to the old version upon loading JSON data.*
3. **Verify Version Consistency Across Workspace**:
   Ensure all 8 target locations have the exact same version string `vX.Y`:
   - `scripts/fetch_and_calc_vision.py`
   - `index.html`
   - `data/gex_data.json`
   - `data/embedded_data.js`
   - `README.md`
   - `HISTORY.md`
   - `STATUS.md`
   - `PROJECT_HANDOVER.md`
4. **Git Commit & Push**: Execute `git add .`, `git commit -m "..."`, and `git push`.
