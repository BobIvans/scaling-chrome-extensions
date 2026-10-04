# Source-preservation verification

Complete source hashing/member verification passes locally. Ubuntu exact-head CI
3234d19 passed. Its Windows check exposed only ZipInfo.filename separator normalization
on the intentional traversal fixture; file bytes/hash checks all passed. The verifier
now compares ZipInfo.orig_filename, which retains the archive member name on both OS.
The independent local Windows-separator oracle passes. All hash/scope/criterion checks
remain mandatory; actual current Ubuntu/Windows run is available in GitHub Actions.
Source integrity does not establish runtime or physical-device qualification.
