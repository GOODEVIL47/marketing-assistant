# Marketing Assistant

Internal tool for finding relevant X posts, drafting replies, and generating daily growth digests.

Supports multiple product profiles. The first profile is **Signal Shift** — a calm AI-powered market briefing tool for retail investors.

---

## Project structure

```
marketing-assistant/
├── run_mock.py              # Entry point — run this
├── requirements.txt
├── .env.example             # Copy to .env for live mode
├── profiles/
│   └── signal_shift.yaml    # Signal Shift product profile
├── mock_data/
│   └── posts.py             # 8 fake X posts for mock mode
├── src/
│   ├── scorer.py            # Scores each post (Strong / Decent / Weak / Avoid)
│   ├── replier.py           # Generates 3 reply options for good-fit posts
│   ├── post_generator.py    # Drafts 1 founder post + 1 product post
│   └── digest.py            # Saves everything to a Markdown file
└── output/
    └── daily_digest_YYYY-MM-DD.md   # Generated here
```

---

## Running mock mode

Mock mode requires no API keys. Everything is hardcoded.

```bash
python run_mock.py
```

The digest is saved to `output/daily_digest_YYYY-MM-DD.md`.

---

## What mock mode produces

1. **8 fake X posts** scored as Strong fit, Decent fit, Weak fit, or Avoid
2. **Explanation** for why each post got that score
3. **Suggested account** to reply from (Founder / Product / Either / Do not reply)
4. **3 reply options** (A, B, C) for every Strong fit or Decent fit post
5. **1 founder account post draft**
6. **1 product account post draft** for @SignalShiftCo
7. Everything saved into `output/daily_digest_YYYY-MM-DD.md`

---

## Setup

```bash
pip install -r requirements.txt
python run_mock.py
```

No `.env` file needed for mock mode.
