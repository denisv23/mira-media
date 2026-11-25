# Spec format for `tools/mira.py`

```json
{
  "theme": "light | dark",
  "num": "05 / 07",                       // post only, optional (top-right counter)
  "headline": "Mira nuk\n*hamendëson.*",   // \n = line break, *x* = accent colour
  "sub": "One short supporting line.",
  "blocks": [ ...see below... ],
  "footer": ["Recepsionistja AI për sallone dhe klinika", "Na ndiqni →"],   // post only
  "cta": {                                                               // reel only (red end card)
    "headline": "Kush përgjigjet i pari, e merr klientin.",
    "pill": "Provojeni falas për 14 ditë",
    "note": "Më shkruani MIRA në DM"
  }
}
```

Blocks (stacked top to bottom; in a reel they appear one by one, chat messages and cards one at a time):

| type | fields |
|---|---|
| `spacer` | pushes following blocks to the bottom (posts) |
| `big` | `text` (e.g. "23:40", shown huge in mono), `side` (small grey note) |
| `chat` | `messages`: list of `{from: client|mira|booked, text, time?, title?}`; `booked` = green "U rezervua" confirmation |
| `cards` | `items`: 1–4 of `{icon, title, text}`; icons: chat, calendar, bell, clock, check, list, shield, chart, lang, send, users |
| `list` | `title` ("LISTA JOTE"), `rows`: [["Prerje flokësh","700 L"], ...] |
| `notif` | `app`: telegram|whatsapp, `label`, `text`, `when?` ("E martë · 15:12") |
| `stats` | `title`, `badge?` ("SHEMBULL"), `when?`, `rows`: [["Rezervime nga Mira","12"], ...] (2nd row is green) |
| `quote` | `text` (big statement, *accent* allowed) |
| `bar` | `text` — dark Telegram strip ("Klientja pyet për keratinë. Shkruaji vetë.") |

Fit: the renderer auto-shrinks text that does not fit and prints a note/warning. If it warns, cut words.
A reel lasts ≈ 1.6 s + 1.5 s per reveal + 2.2 s + 3.4 s CTA. Aim for 5–7 reveals → 13–16 s.
