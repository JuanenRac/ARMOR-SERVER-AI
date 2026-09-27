# Changelog

All notable changes to this project are documented here.

## [0.2.1]

- A GitHub Actions CI baseline (`.github/workflows/ci.yml`): validates the manifest, the version, CHANGELOG.md's heading, the seven README translations' structure and its own local Markdown links, then runs this project's real build/test through `tools/armor_project_tool.py build-test .` (vendored from ARMOR-COMMON, alongside `tools/armor_ci_validate.py` and `tools/_armor_readme_parity.py`, which do the manifest/docs checking).

## [0.2.0]

- Day/night profile with hysteresis, explainable fusion of detections and radar tracks, and checksum-verified engine registry.
- Decisions never authorise an action.
- 26 tests.
