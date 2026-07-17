# Member profile images

Drop each member's photo here, then set the `image` field in
`app/content/members.ts` to the path.

Suggested filenames (already scaffolded as commented-out `image:` lines
in `members.ts` — just uncomment after dropping the file):

- `xing.jpg`      — Xing Wang
- `abhisek.jpg`   — Abhisek Dwivedy
- `saurabh.jpg`   — Saurabh Umrao
- `catherine.jpg` — Catherine Zhang
- `henry.jpg`     — Henry He

Notes:

- Any web format works (`.jpg`, `.png`, `.webp`).
- Square images render best (the page displays them as 80×80 circles
  cropped via `object-cover`, so non-square images will be center-cropped).
- Roughly 200–400 px per side is plenty for a thumbnail.
- Files in `public/` are served from the site root, so a file placed at
  `public/images/members/xing.jpg` is reachable at
  `/images/members/xing.jpg`.
- Members without an image get an auto-generated initials circle.
