Scripts behind DESIGN.md section 5 (run 2026-10-04 on `dsewiki/raw/revisions.jsonl.gz`, not in this repo).
`load.py` extracts added text and exact-copy hashes; `burst.py` builds token back-references and marks bursts
(writes `u.pkl`); `schemes.py` compares window schemes A to C; `schemesD.py` tests the token-routed halo (D).
They print counts only, never message text.
