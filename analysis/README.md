# Goal-adoption analysis of the AI Village dataset

- `goal_adoption_report.md`: the report. It contains the candidate table, timelines, comparison cases and coverage log.
- `evidence_index.csv`: every message, memory or event ID cited in the report, with its full UUID, UTC timestamp, speaker and a snippet.
- `working_notes.md`: case notes kept during the analysis.
- `scripts/`: code to rebuild the indexes from the raw files. No dataset files are committed; the dataset is gated.

To reproduce, run everything from one working directory:

1. `python scripts/download.py` downloads the raw files into `av/`.
2. `mkdir idx && python scripts/build_idx.py` builds the chat, events and sessions indexes as parquet.
3. `python scripts/build_big.py mem` and `python scripts/build_big.py turns` build the memories and turns indexes.
4. `python scripts/sweep.py` runs the lexical sweep.

Helper tools:

- `show.py KEY era` prints keyword-in-context hits from the sweep.
- `tl.py AGENT START END` prints a timeline for one agent.
- `memgrep.py AGENT START END REGEX` searches an agent's memory rows in a time window.

Requirements: `huggingface_hub`, `pandas`, `pyarrow`, `duckdb`, `orjson`.
