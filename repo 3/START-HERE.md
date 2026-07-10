# Start here

You have two zip files. They do different things.

| File | What it is | Updates daily? |
|---|---|---|
| `unforced-error-site.zip` | Just the finished web pages | No |
| `unforced-error-repo.zip` | Pages + the robot + the checks | **Yes** |

**Use the repo one.** The site-only zip was for getting something live in two minutes before the robot existed.

---

## Why GitHub is necessary

The Daily Docket needs something to wake up at 6am, fetch what the government published overnight, and update the site. Your laptop can't be relied on for that — it might be closed.

GitHub runs it on their servers, for free, whether you're awake or not. That's the only reason it's in the picture.

You don't need to learn git. You'll use the website.

---

## Step 1 — Make a GitHub account

**github.com/signup**. Free. Two minutes.

## Step 2 — Make an empty repository

1. Go to **github.com/new**
2. Repository name: `unforced-error`
3. Choose **Public**. (I'd argue for this. The whole pitch is that anyone can check your work. A private repo makes that a promise instead of a fact. Your call.)
4. **Do not** check "Add a README" — you already have one.
5. Click **Create repository**

## Step 3 — Put your files in it

Unzip `unforced-error-repo.zip`. You'll get a folder called `repo` — rename it `unforced-error`.

On the empty repository page, click **"uploading an existing file"**.

Then drag in everything from inside the folder. Two things to watch:

- Drag the **contents** of the folder, not the folder itself.
- GitHub's web uploader sometimes skips folders starting with a dot. **`.github` must make it in** — that folder *is* the robot's schedule. If you don't see `.github` in the file list after uploading, that's the problem.

If the web uploader gives you trouble, install **GitHub Desktop** (desktop.github.com), click "Add existing repository," point it at the folder, and hit Publish. It handles the dot-folders correctly.

Scroll down, click **Commit changes**.

## Step 4 — Connect Netlify

1. **app.netlify.com** → sign up (you can use your GitHub account)
2. **Add new site → Import an existing project → GitHub**
3. Authorize, pick `unforced-error`
4. Netlify reads the settings from `netlify.toml` automatically. Don't change anything.
5. **Deploy**

Ninety seconds later you have a live URL like `graceful-tesla-9f3a21.netlify.app`.

## Step 5 — Test the robot

Don't wait until tomorrow morning to find out if it works.

1. In your GitHub repo, click the **Actions** tab
2. Click **Daily Docket** in the left sidebar
3. Click **Run workflow → Run workflow**

Watch it run. Green check means it worked. Red X means it caught something, and it will tell you what — that's the design.

If it found new filings, it commits them, Netlify redeploys, and your site is updated. If it found nothing, it says so and exits cleanly. **That's a normal outcome, not a failure.**

From then on it runs itself at 6:00 AM Eastern, Monday through Friday.

---

## Before you show anyone

**The corrections email is set to your Gmail** (`goldenbergaiden1@gmail.com`) everywhere, including the robot's ID card. If you'd rather use a dedicated address later, search the repo for `goldenbergaiden1@gmail.com` and swap it.

**Read the report once, all the way through.** It describes real accusations against a real named company. Every sentence is attributed as an accusation and bound to a hashed source document — that's what all the machinery is for. But your name is on it.

---

## What happens every morning after that

```
6:00 AM   GitHub wakes up
          → scout.py reads 6 government APIs
          → screens out the noise (budget footnotes, meeting notices)
          → copies one sentence, verbatim, from each real filing
          → verifies that sentence actually exists, character for character
          → rebuilds the site
          → audit.py re-checks every page for opinions and bad citations
          → if anything fails, NOTHING publishes and GitHub emails you
          → otherwise: commits, Netlify redeploys, site is fresh
```

No AI is involved in any of that. Nothing in the pipeline writes a sentence, so nothing in the pipeline can invent one.

---

## Changing the site later

Edit files directly in GitHub's web editor and commit. Netlify redeploys in about a minute.

**Two files you should never hand-edit:**

- `site/checks/*.html` — generated from the facts ledger
- `site/docket.html` — generated from `data/docket.json`

Edit them and they'll be silently overwritten on the next build, and CI will fail for having drifted. Change the source data instead.

---

## If something breaks

**Netlify build fails** → click into the deploy log. If you see `AUDIT COMPLETE — N failures`, the gate caught something. It names exactly what.

**Robot fails** → Actions tab, click the red run. The most likely message is `FATAL: <host> is not on the source allowlist` — meaning something tried to pull from a non-government source, and the build stopped it. Working as intended.

**Robot runs but nothing changes** → agencies didn't file anything relevant. Common on Mondays and holidays.

---

## What "foolproof" means now (hardening pass)

The scout was upgraded so no human or AI ever curates the docket:

- **Every quote is verified twice.** Once against the agency's abstract, then again against the full published document text, in a separate fetch. If the two disagree, the entry is held, not published.
- **Every entry carries a verification record** — what it was checked against, how, and when. An entry without one halts the build. (Tested.)
- **Network calls retry** with backoff, and a redirect to any off-allowlist host aborts the run.
- **CISA outages are handled honestly.** If the feed is unreachable, its advisories are *held* with the reason shown on the site. The scout never reads the text "another way." (Tested.)
- **The scout self-tests before it runs.** The GitHub Action runs `test_scout.py` and `test_audit.py` first; if either fails, the scout doesn't run and nothing publishes.

The docket now updates itself every weekday morning with zero human input, and the worst case remains a boring entry — never a false one.
