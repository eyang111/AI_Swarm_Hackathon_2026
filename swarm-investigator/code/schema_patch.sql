-- Applied after spec/store_schema.sql by store.init_db(). Additions needed to run the v4 pipeline.
-- Each one is noted in code/README.md ("Where the code differs from the spec").

-- Reader record fields the schema kept only in reader_format.md (2, 2a) + versioning.
ALTER TABLE records ADD COLUMN record_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE records ADD COLUMN supersedes TEXT;            -- record_id of the version this one revises
ALTER TABLE records ADD COLUMN revision_reason TEXT;
ALTER TABLE records ADD COLUMN cloned_from TEXT;           -- record_id this copy's record was cloned from (DESIGN 5.3)
ALTER TABLE segments ADD COLUMN summary TEXT;
ALTER TABLE claims ADD COLUMN segment_id TEXT;

-- Messages: which loaded rows are the slice's core (read) vs halo (context only).
ALTER TABLE messages ADD COLUMN in_core INTEGER NOT NULL DEFAULT 1;
ALTER TABLE messages ADD COLUMN segment TEXT;              -- S1/S2/S3 slice segment, null for halo


-- pipeline_v2: clusters are over segments. claim_key_members stays for claims; this table holds segment membership.
CREATE TABLE claim_key_segments (
  claim_key TEXT NOT NULL REFERENCES claim_keys(claim_key),
  segment_id TEXT NOT NULL REFERENCES segments(segment_id),
  task_id TEXT NOT NULL REFERENCES tasks(task_id),
  confidence TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  is_seed INTEGER NOT NULL DEFAULT 0,
  retracted_by TEXT,
  PRIMARY KEY (claim_key, segment_id)
);
CREATE INDEX cks_seg ON claim_key_segments(segment_id);

-- Window plan (script) and per-window reader bookkeeping.
CREATE TABLE windows (
  window_id TEXT PRIMARY KEY, segment TEXT, t_start TEXT, t_end TEXT,
  core TEXT NOT NULL, halo TEXT NOT NULL, context_pack TEXT NOT NULL,
  core_chars INTEGER, halo_chars INTEGER
);

-- L4/L5/analyzer outputs that are not links or cluster edges (spines, origin verdicts, mutations, findings drafts).
CREATE TABLE analyses (
  analysis_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(task_id),
  kind TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL
);

-- Token and cost ledger, one row per model call.
CREATE TABLE usage (
  call_id TEXT PRIMARY KEY, task_id TEXT, tier TEXT, model TEXT, batch INTEGER,
  input_tokens INTEGER, output_tokens INTEGER, cache_read INTEGER, cache_write INTEGER,
  cost_usd REAL, stop_reason TEXT, t TEXT
);

-- Segment-based views (pipeline_v2 section 10: "the events view is rebuilt over segments").
DROP VIEW events;
DROP VIEW novelty;
DROP VIEW live_members;
CREATE VIEW live_members AS
  SELECT ck.claim_key, s.segment_id, s.msg_id,
         COALESCE((SELECT c.stance FROM claims c WHERE c.segment_id = s.segment_id ORDER BY c.claim_id LIMIT 1),
                  CASE s.purpose WHEN 'DOUBT' THEN 'doubts' WHEN 'CORRECT' THEN 'corrects' ELSE 'asserts' END) AS stance,
         s.purpose, s.assertiveness, cks.confidence, cks.is_seed,
         msg.t, msg.speaker, msg.lab, msg.channel
  FROM claim_key_segments cks
  JOIN claim_keys ck ON ck.claim_key = cks.claim_key
  JOIN segments s ON s.segment_id = cks.segment_id
  JOIN messages msg ON msg.msg_id = s.msg_id
  WHERE cks.retracted_by IS NULL AND s.retracted_by IS NULL AND ck.merged_into IS NULL;

CREATE VIEW novelty AS
  SELECT claim_key,
         (SELECT msg_id  FROM live_members x WHERE x.claim_key = m.claim_key ORDER BY t, msg_id LIMIT 1) AS first_msg_id,
         (SELECT speaker FROM live_members x WHERE x.claim_key = m.claim_key ORDER BY t, msg_id LIMIT 1) AS first_speaker,
         MIN(t) AS t_first, COUNT(DISTINCT speaker) - 1 AS n_later_speakers, COUNT(*) AS n_mentions
  FROM live_members m GROUP BY claim_key;

CREATE VIEW events AS
  SELECT lm.claim_key AS item_id, ck.canonical_text AS item_text, ck.layer, ck.status AS item_status,
         lm.msg_id, lm.segment_id, lm.t, lm.speaker AS agent, lm.lab AS agent_lab, lm.confidence,
         CASE WHEN lm.msg_id = n.first_msg_id THEN 'origin'
              WHEN lm.stance = 'doubts' THEN 'challenge'
              WHEN lm.stance = 'corrects' THEN 'correct'
              ELSE 'adopt' END AS role,
         CASE WHEN EXISTS (SELECT 1 FROM live_links l WHERE l.from_msg_id = lm.msg_id AND l.type = 'acted_on')
              THEN 'acted'
              WHEN lm.purpose = 'COMMIT' OR EXISTS (SELECT 1 FROM records r WHERE r.msg_id = lm.msg_id AND r.retracted_by IS NULL
                           AND 'COMMIT' IN (r.purpose, r.purpose2, r.purpose3))
              THEN 'planned' ELSE 'said' END AS depth,
         (SELECT l.to_msg_id FROM live_links l WHERE l.from_msg_id = lm.msg_id
            AND l.type IN ('source_of','reply_to','acted_on','exposed_to')
            AND (l.claim_key = lm.claim_key OR l.claim_key IS NULL)
          ORDER BY CASE l.confidence WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END LIMIT 1) AS exposure_msg_id
  FROM live_members lm JOIN claim_keys ck USING (claim_key) JOIN novelty n USING (claim_key)
  WHERE NOT EXISTS (SELECT 1 FROM messages d WHERE d.msg_id = lm.msg_id AND d.script_label = 'DUPLICATE');

-- Lead findings carry a category for the readable summary (readable.py).
ALTER TABLE findings ADD COLUMN category TEXT;

-- Cut 2026-10-04 (DESIGN 15): write-only tables and views nothing reads.
DROP VIEW IF EXISTS conversation_presence;
DROP TABLE IF EXISTS conversation_edges;
DROP TABLE IF EXISTS loose_ends;
DROP TABLE IF EXISTS mentions;
DROP TABLE IF EXISTS aggregate_members;
DROP TABLE IF EXISTS aggregates;
