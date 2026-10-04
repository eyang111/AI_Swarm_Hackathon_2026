"""Shared settings for the Swarm Investigator pipeline (DESIGN.md v4)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # swarm-investigator/
SPEC = ROOT
SLICE = os.path.join(ROOT, 'test_slice')
RUN_DIR = os.environ.get('SI_RUN_DIR', os.path.join(ROOT, 'test_run'))
DB = os.path.join(RUN_DIR, 'investigation.db')
TRUTH_DIR = os.path.join(RUN_DIR, 'truth')          # hidden from every model stage
CALL_LOG = os.path.join(RUN_DIR, 'calls')            # raw requests/responses per call (for audit)
RAW_PAGES = '/mnt/project-files/dsewiki/raw/pages.jsonl.gz'

# Models (Peyton, 2026-10-04): readers and local linker on Sonnet; groupers, reconciler, analyzers, checker, lead on Opus.
SONNET = 'claude-sonnet-5-5'
OPUS = 'claude-opus-5-5'
TIER_MODEL = {
    'reader': SONNET, 'local_linker': SONNET,
    'grouper': OPUS, 'reconciler': OPUS,
    'analyzer': OPUS, 'checker': OPUS, 'lead': OPUS,
}
TIER_EFFORT = {'reader': 'low', 'local_linker': 'low'}   # Opus tiers: 'medium' (set explicitly)

# $ per million tokens (list). Batch = 50% off. Cache reads $0.20, cache writes 1.25x input.
PRICE = {SONNET: (2.0, 10.0), OPUS: (4.0, 20.0), 'claude-opus-4-8': (5.0, 25.0), 'claude-opus-5': (5.0, 25.0)}   # 4.8 / 5: server-side fallback targets
CACHE_READ = 0.20
BATCH_DISCOUNT = 0.5
CHARS_PER_TOKEN = 3.5

# Windows (DESIGN.md 5.2 scheme D)
CORE_MAX_SAVES, CORE_MAX_CHARS = 100, 60_000
HALO_PREV, HALO_PER_TOKEN, HALO_CAP, HALO_MAX_AGE_S = 50, 2, 150, 86_400
HALO_MAX_CHARS = 120_000          # keeps the S3 peak windows under ~60k input tokens

# Keyword distinctiveness (pipeline_v2 section 4)
DF_MIN, DF_CAP = 2, 50

LOCAL_LINK_CAP = 3                 # outgoing local links per segment (D2)
SEED_ASSERTIVE = 0.7               # assertive cluster seed

WITHHELD = '[technique withheld]'
AW_SUMMARY = 'access workaround; see msg_id'   # fixed summary (store_design section 2)
