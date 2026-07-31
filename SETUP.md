# Setup

## 1. Get the right repo
GitHub only renders a repo's README on your profile page if the repo is
named **exactly your username**. If `github.com/<you>/<you>` doesn't exist
yet, create it (public, initialize with a README so it's not empty).

## 2. Drop these files in
Copy into that repo, preserving structure:
```
.github/workflows/update-profile.yml
scripts/
requirements.txt
README.md        <- merge with your existing one, don't just overwrite
assets/fonts/     <- can stay empty, fonts are generated at build time
```
`data/` and `assets/generated/` get created by the workflow itself --
don't need to create them by hand, but it's fine to commit an empty
`.gitkeep` in each if you want the folders to exist before the first run.

## 3. Allow the workflow to push commits
Repo → **Settings → Actions → General → Workflow permissions** → select
**"Read and write permissions"**, then Save. Without this, the default
`GITHUB_TOKEN` can read but not `git push`, and the commit step will fail.

## 4. (Optional) add your photo for the ASCII portrait
Add a photo at `assets/source_photo.jpg` -- roughly centered subject,
reasonable separation from the background helps the background-removal
step. If the repo is public, this photo is public too.

Don't want the portrait? Just don't add the photo -- the workflow skips
that step automatically and the other three cards still generate fine.
Remove its `<img>` line from `README.md` too.

## 5. First run
Commit and push, then go to the **Actions** tab → "Update Profile" →
**Run workflow** to trigger it manually once (the cron schedule only
fires going forward, not retroactively). Check that
`assets/generated/*.svg` show up in a new commit afterward.

From then on it runs daily on the cron schedule in
`update-profile.yml` and only commits when something actually changed,
so your history doesn't fill up with empty "no-op" commits.

## Notes / limitations
- **Private contributions won't show.** The workflow authenticates as
  the repo's bot token, not as you, so `contributionsCollection` only
  returns your *public* activity -- same limitation every public stats
  card has. If you want private counts included too, generate a
  personal access token with `read:user` scope, add it as a repo secret
  (e.g. `STATS_TOKEN`), and swap `secrets.GITHUB_TOKEN` for
  `secrets.STATS_TOKEN` in the "Fetch GitHub stats" workflow step.
- **ASCII portrait quality** depends on background contrast, since it
  uses classical background removal (GrabCut) rather than a trained
  model, to keep the workflow fast and dependency-light. There's a note
  at the bottom of `scripts/generate_ascii_portrait.py` on swapping in
  `rembg` if you want sharper edges and don't mind the extra model
  download in CI.
- Test any script locally before pushing:
  ```
  pip install -r requirements.txt
  python scripts/fetch_github_data.py --mock   # no token needed
  python scripts/generate_stats_card.py
  python scripts/generate_languages_card.py
  python scripts/generate_contribution_calendar.py
  python scripts/generate_ascii_portrait.py --source assets/source_photo.jpg
  ```
