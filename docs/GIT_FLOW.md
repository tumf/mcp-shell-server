# Branch and release flow

`main` is the stable release branch; `develop` is the integration branch. Start new work from `develop` on `feature/<topic>` or `fix/<topic>` and merge it through a reviewed pull request into `develop`. Keep each pull request focused on one change. Run `make check` and `make coverage` before requesting review; the Test workflow checks pull requests to both long-lived branches.

To release, open a pull request from `develop` into `main`. Review the full diff, resolve conflicts, run the Test workflow on the pull request, and merge with a merge commit to preserve ancestry. Verify the merge commit and its Test run. Prepare the package version through a release pull request to `main`, build and smoke-test the resulting commit, then tag that exact `main` commit as `vX.Y.Z`. The Publish workflow runs on tags; verify its test and PyPI jobs and the published package before announcing a release. Do not tag a feature or `develop` commit.

For an urgent published fix, branch `hotfix/<topic>` from `main`, send a focused pull request to `main`, and test the result. Merge `main` back into `develop` by pull request before continuing integration work. Never rewrite published branches or move published release tags.

The old `develop` history from 2025 is preserved at `archive/develop-2025`; it is **not** a base for new work. Its six commits are not implicitly included in the new `develop`. If needed, port individual changes through separately reviewed pull requests rather than merging the archived branch wholesale.

Branch names are conventions, not security controls. Repository permissions, review rules, and CI must enforce the applicable gates.
