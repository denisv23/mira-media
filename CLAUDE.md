# Mira — daily Instagram content (1 post + 1 reel)

This repo holds the renderer and the published media for **@mira.recepsioniste** (Instagram, Business account
linked to the Facebook Page "Mira • Recepsionistja AI"). Files here are public (drafts are pushed only after Denis approves): they are served to Instagram
through GitHub Pages URLs (denisv23.github.io/mira-media/...). Never put anything private in this repo.

## What Mira is (only claim these facts)
- AI receptionist for **salons and clinics** in Albania (based in Fier), works in **WhatsApp, 24/7, in Albanian**.
- Answers prices, hours, address in seconds — **only from the price/service list the owner set**; anything not
  on the list it does not invent: it tells the client the owner will reply and notifies the owner on **Telegram**.
- Books appointments only into free slots, straight into the calendar.
- Reminds the client **one day before** each appointment.
- Owner gets Telegram notifications; every **Monday** a weekly summary.
- Understands Albanian as people really write it (no ë, typos, "sa osht", "ne 9", "te shtunen").
- Offer: **14 days free**; sign up by DM ("Më shkruani MIRA në DM").
Do NOT invent client testimonials, real salon names presented as customers, statistics, or features not listed
here. Example businesses in visuals must be clearly illustrative (e.g. "Parukeria Ana" with a "SHEMBULL" badge).

## Voice & look
- Albanian, short, concrete, warm. Talk to owners ("ju"/"ti" — keep one per piece). Real-life moments: 23:40
  messages, busy hands mid-haircut, Sunday morning, no-shows, a client asking about a service not on the list.
- Visual system is fixed by `tools/mira.py` (light/dark themes, red accent, Bricolage Grotesque + Figtree +
  JetBrains Mono). Alternate light/dark across days. Numbering "NN / 07" on posts is decorative.
- Caption: 2–5 short paragraphs, ends with the 14-day offer + DM call, then 4–6 hashtags, Albanian-first
  (#sallon #parukeri #klinike #biznesivogel #fier #shqiperi …). No hashtag spam.

## Daily run (scheduled task, ~07:40 Europe/Tirane)
1. `add_repo denisv23/mira-media` with push access, clone to `/home/claude/mira-media`, read
   `content-log.md` — never repeat a headline/scenario from the last 30 entries.
   Denis also posts by hand sometimes. Read the latest ~10 Instagram captions too, with Zapier Instagram for
   Business "Make API GET Request" on `17841462171311044/media?fields=caption,timestamp,media_type&limit=10`,
   and avoid repeating those topics. If that call fails, continue without it.
2. Pick today's angle: one post idea + one different reel idea (see `ideas.md`; add new ones freely).
   **Variety (Denis, 25 Nov: "po duken të përsëritshme")**: rotate through the formats in `ideas.md`
   (A–F). The classic "client writes → Mira answers → U rezervua" chat is max 2 pieces per week; post and reel
   of the same day must come from different formats; also vary the business (parukeri, berber, thonj, estetikë,
   dentist, fizioterapi), the time of day and the main visual block (not chat every day).
3. Write `media/YYYY-MM-DD/post.json` and `reel.json` (format: `tools/SPEC.md`) and the two captions in
   `media/YYYY-MM-DD/captions.md`.
4. Render:
   `python3 tools/mira.py post media/DATE/post.json media/DATE/post.png`
   `python3 tools/mira.py reel media/DATE/reel.json media/DATE/reel.mp4`
   Look at the PNG and at 3–4 frames of the MP4 (ffmpeg -ss). Fix overflow, typos, wrong diacritics (ë, ç).
5. Do NOT commit or push the drafts yet — drafts stay in the workspace until Denis approves, so a rejected
   draft never becomes public.
6. Send Denis the drafts **for approval** (he must say ok first — never publish without his yes in that session):
   SendUserMessage with both captions + SendUserFile with post.png and reel.mp4. Write in Albanian.
   Say: post goes out at **11:00**, reel at **19:00**, reply "ok" (or ask for changes).
   Then send a phone push notification (PushNotification tool, load it with ToolSearch) in Albanian,
   e.g. "Mira: postimi dhe reel-i i sotëm janë gati — hyr dhe shkruaj ok". Also push when each item is published.
   If he asks for changes: edit, re-render, resend (still no push). If he rejects: delete the drafts, log
   "skipped" in content-log.md (no media), commit, push, done.
7. When he approves: right away commit + push `media/DATE/` (`git -c push.negotiate=true push`). Public URLs
   (GitHub Pages, correct MIME types): `https://denisv23.github.io/mira-media/media/DATE/post.png` and
   `.../media/DATE/reel.mp4`. Pages rebuilds 1–3 min after a push (the workspace shell and WebFetch cannot reach
   github.io, so don't try to verify). Then schedule publishing with `send_later` into this same session —
   post at 11:00, reel at 19:00 Europe/Tirane. If a time has already passed, wait 3 minutes after the push
   (`sleep 180`) and publish that item now.
   If Zapier says a media URL could not be fetched, wait 2 min and retry once, then fall back to
   `https://raw.githubusercontent.com/denisv23/mira-media/main/media/DATE/<file>`.
8. Publish with Zapier, Instagram for Business (default connection), account `instagramPageId`
   `17841462171311044` (Mira•Recepsionistja AI):
   - post → action `publish_media_v2`, params `media: [<post.png URL>]`, `caption`.
   - reel → action `publish_video`, params `video: <reel.mp4 URL>`, `caption`.
   After each, confirm success to Denis in one line. If Zapier errors, retry once, then tell Denis plainly.
9. Append a line to `content-log.md`: `DATE | post: <headline> | reel: <headline> | status`, commit, push.

If nothing in this file can be done (Zapier disconnected, push refused), tell Denis exactly what broke and stop.
