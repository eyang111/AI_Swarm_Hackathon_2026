-- Swarm Investigator store: investigation.db (SQLite 3.45+, FTS5)
-- Design notes: store_design.md in this folder. Draft v1, 2026-10-03.
-- Rule: agents never write SQL. They call the write tools in store.py, which check citations and
-- append rows. Nothing is UPDATEd or DELETEd except `retracted_by` / `status` fields set by the tools.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;   -- many parallel readers writing through the tool process

------------------------------------------------------------------------------------------
-- L0 SOURCE (loader scripts only, no AI)
------------------------------------------------------------------------------------------
CREATE TABLE messages (
  msg_id        TEXT PRIMARY KEY,          -- AV uuid | dw:<rev_id> | plant:<plant_id>:<n>
  swarm         TEXT NOT NULL CHECK (swarm IN ('aivillage','dsewiki')),
  t             TEXT NOT NULL,             -- ISO 8601 UTC
  t_uncert_s    INTEGER,                   -- DSEWiki uncertainty_seconds; null for AV
  channel       TEXT NOT NULL,             -- AV room | wiki page title (wiki~name)
  speaker       TEXT,                      -- AV display name | DSEWiki label ('' -> null)
  ip16          TEXT,                      -- DSEWiki first two IP octets (run-identity signal); null for AV
  speaker_kind  TEXT NOT NULL CHECK (speaker_kind IN ('agent','human','unknown')),
  lab           TEXT,
  text          TEXT NOT NULL,             -- what readers read and quotes are checked against.
                                           -- DSEWiki: page title line + lines added/replaced in this save
  body_ref      TEXT,                      -- DSEWiki: rev_id whose full body is in revisions.jsonl
  parent_msg_id TEXT,                      -- DSEWiki: previous save of the same page (diff_base)
  -- (holdout dropped 2026-10-04: no `split` column; scoring uses plants and blind hand labels)
  -- script-computed per-message features (reader_format.md section 2, "script" rows)
  len INTEGER, n_urls INTEGER, gap_prev_s INTEGER,
  text_hash     TEXT,                      -- exact-dup key
  dup_of        TEXT REFERENCES messages(msg_id),  -- exact or near duplicate of an earlier message
  script_label  TEXT CHECK (script_label IN ('DUPLICATE','EMPTY')),
  copy_of       TEXT REFERENCES messages(msg_id),  -- exact copy (NFC + whitespace-normalized text) of this earlier message:
                                           -- readers read only the first instance; store.py clones its record (DESIGN.md 5.3)
  removed_text  TEXT                       -- DSEWiki: lines this save deleted, shown to readers with a 'removed:' marker
);
CREATE INDEX messages_ch_t ON messages(channel, t);
CREATE INDEX messages_t ON messages(t);
CREATE INDEX messages_speaker ON messages(speaker);
CREATE VIRTUAL TABLE messages_fts USING fts5(text, channel, speaker, content='messages', content_rowid='rowid');

CREATE TABLE agents (                      -- AV: one per agent. DSEWiki: one per label (names only)
  speaker TEXT PRIMARY KEY, swarm TEXT NOT NULL, lab TEXT, model TEXT, is_human INTEGER NOT NULL DEFAULT 0
);

------------------------------------------------------------------------------------------
-- PROVENANCE: every AI-written row says which run, which task and which agent wrote it
------------------------------------------------------------------------------------------
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,                 -- e.g. run-03
  started_at TEXT NOT NULL,
  config TEXT NOT NULL,                    -- JSON: models, prompts hash, registry_access on/off, copy of messages used (plants?)
  notes TEXT
);
CREATE TABLE tasks (
  task_id  TEXT PRIMARY KEY,               -- e.g. run-03/reader/aivillage/general/2026-03-12T16
  run_id   TEXT NOT NULL REFERENCES runs(run_id),
  tier     TEXT NOT NULL CHECK (tier IN ('reader','clusterer','local_linker','resolver','linker','identity','reconciler','tracker','lead','summarizer','checker')),
  scope    TEXT NOT NULL,                  -- JSON: {channel, t_start, t_end} | {claim_key} | {group_id} ...
  replica  INTEGER NOT NULL DEFAULT 0,     -- >0 = independent re-read of the same scope (agreement tests)
  model    TEXT,
  status   TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','failed')),
  started_at TEXT, finished_at TEXT
);

-- One table for every quote anywhere in the store. The write tool fills start/end by locating
-- `quote` in messages.text and refuses the write if it isn't an exact substring (<= 200 chars).
CREATE TABLE citations (
  cite_id   INTEGER PRIMARY KEY,
  obj_type  TEXT NOT NULL,                 -- 'record' | 'claim' | 'link' | 'claim_key' | 'run_group' | 'aggregate' | 'finding' | 'observation'
  obj_id    TEXT NOT NULL,
  msg_id    TEXT NOT NULL REFERENCES messages(msg_id),
  quote     TEXT NOT NULL CHECK (length(quote) BETWEEN 1 AND 200),
  q_start   INTEGER NOT NULL, q_end INTEGER NOT NULL,
  redact    INTEGER NOT NULL DEFAULT 0     -- 1 if the message is ACCESS_WORKAROUND: exports show [technique withheld]
);
CREATE INDEX citations_obj ON citations(obj_type, obj_id);
CREATE INDEX citations_msg ON citations(msg_id);

------------------------------------------------------------------------------------------
-- L1 READER (reader_format.md section 2). One record per (message, task); several per message allowed
------------------------------------------------------------------------------------------
CREATE TABLE records (
  record_id   TEXT PRIMARY KEY,            -- <task_id>#<msg_id>
  msg_id      TEXT NOT NULL REFERENCES messages(msg_id),
  task_id     TEXT NOT NULL REFERENCES tasks(task_id),
  signed_name TEXT, run_tag TEXT,
  purpose     TEXT NOT NULL,               -- primary label
  purpose2    TEXT, purpose3 TEXT,         -- secondary labels
  flag_coded_token INTEGER NOT NULL DEFAULT 0,
  flag_task_content INTEGER NOT NULL DEFAULT 0,
  flag_addresses_human INTEGER NOT NULL DEFAULT 0,
  summary     TEXT,                        -- tool forces a fixed text when purpose set includes ACCESS_WORKAROUND
  reply_to_hint TEXT,                      -- msg_id or short description
  anomaly     TEXT,
  confidence  TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  retracted_by TEXT,                       -- task_id of a later correction to this record; null = live
  UNIQUE (msg_id, task_id)
);
CREATE INDEX records_msg ON records(msg_id);
CREATE INDEX records_purpose ON records(purpose);

CREATE TABLE claims (                      -- reader claim objects
  claim_id    TEXT PRIMARY KEY,            -- <record_id>/c<n>
  record_id   TEXT NOT NULL REFERENCES records(record_id),
  msg_id      TEXT NOT NULL REFERENCES messages(msg_id),
  claim_text  TEXT NOT NULL,
  norm_text   TEXT NOT NULL,               -- script: lower-case, punctuation stripped, numbers kept (pre-grouping key)
  about       TEXT NOT NULL CHECK (about IN ('self','shared')),
  stance      TEXT NOT NULL CHECK (stance IN ('asserts','relays','doubts','corrects')),
  stated_source TEXT NOT NULL              -- own_observation | signed name | page title | "other cohorts" | unstated
);
CREATE INDEX claims_norm ON claims(norm_text);

CREATE TABLE mentions (                    -- entities[] and addressed_to[] flattened for joins
  record_id TEXT NOT NULL REFERENCES records(record_id),
  msg_id    TEXT NOT NULL,
  kind      TEXT NOT NULL CHECK (kind IN ('entity','addressed_to')),
  key       TEXT NOT NULL,                 -- agent:… page:… task:… value:… term:… url_host:…  | a name
  PRIMARY KEY (record_id, kind, key)
);
CREATE INDEX mentions_key ON mentions(key);

------------------------------------------------------------------------------------------
-- SCRIPT PRE-GROUPING (reader_format.md section 4): candidate groups for linkers, no AI
------------------------------------------------------------------------------------------
CREATE TABLE candidates (
  cand_id  TEXT PRIMARY KEY,
  run_id   TEXT NOT NULL REFERENCES runs(run_id),
  basis    TEXT NOT NULL CHECK (basis IN ('dup_chain','copy_group','channel_purpose_burst','same_claim_text','shared_entity','signed_name','run_tag','family')),
  key      TEXT NOT NULL,                  -- the shared value that formed the group
  status   TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','taken','done'))
);
CREATE TABLE candidate_members (
  cand_id TEXT NOT NULL REFERENCES candidates(cand_id), msg_id TEXT NOT NULL REFERENCES messages(msg_id),
  claim_id TEXT REFERENCES claims(claim_id),
  PRIMARY KEY (cand_id, msg_id, claim_id)
);

------------------------------------------------------------------------------------------
-- L2 LINKER (reader_format.md section 5). Every grouping is header + membership rows, so a
-- wrong merge is undone by retracting membership rows, never by re-reading.
------------------------------------------------------------------------------------------
CREATE TABLE claim_keys (
  claim_key TEXT PRIMARY KEY,              -- short slug, e.g. ca-round5-11.2pct
  task_id   TEXT NOT NULL REFERENCES tasks(task_id),
  canonical_text TEXT NOT NULL,
  layer     TEXT NOT NULL CHECK (layer IN ('belief','goal','protocol','method','word')),
  status    TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','true','false','unclear')),
  status_basis TEXT,                       -- why true/false: msg_ids or external check
  merged_into TEXT REFERENCES claim_keys(claim_key),
  rationale TEXT NOT NULL
);
CREATE TABLE claim_key_members (
  claim_key TEXT NOT NULL REFERENCES claim_keys(claim_key),
  claim_id  TEXT NOT NULL REFERENCES claims(claim_id),
  task_id   TEXT NOT NULL REFERENCES tasks(task_id),     -- who added it
  confidence TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  retracted_by TEXT,                                     -- task_id that split it out
  PRIMARY KEY (claim_key, claim_id)
);

CREATE TABLE links (
  link_id      TEXT PRIMARY KEY,
  task_id      TEXT NOT NULL REFERENCES tasks(task_id),
  from_msg_id  TEXT NOT NULL REFERENCES messages(msg_id),
  to_msg_id    TEXT NOT NULL REFERENCES messages(msg_id),
  type         TEXT NOT NULL CHECK (type IN ('source_of','reply_to','acted_on','confirms','doubts','corrects','same_run','exposed_to','independent_of')),
  -- independent_of: same claim_key, but the linker judges from_msg reached it without exposure to to_msg (convergence, not copying)
  via          TEXT CHECK (via IN ('direct_message','shared_page','human_relay','external_source','task_prompt','unknown')),
                                           -- how the item travelled, for source_of / exposed_to / acted_on
  claim_key    TEXT REFERENCES claim_keys(claim_key),    -- which item the link carries, if any
  confidence   TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  rationale    TEXT NOT NULL,
  retracted_by TEXT
  -- evidence quote from from_msg_id lives in citations(obj_type='link'); the tool also rejects to.t > from.t
);
CREATE INDEX links_from ON links(from_msg_id);
CREATE INDEX links_to ON links(to_msg_id);
CREATE INDEX links_key ON links(claim_key);

CREATE TABLE run_groups (
  group_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(task_id),
  swarm TEXT NOT NULL, rationale TEXT NOT NULL, merged_into TEXT REFERENCES run_groups(group_id)
);
CREATE TABLE run_group_members (
  group_id TEXT NOT NULL REFERENCES run_groups(group_id),
  member   TEXT NOT NULL,                  -- speaker label, signed_name or run_tag
  member_kind TEXT NOT NULL CHECK (member_kind IN ('speaker','signed_name','run_tag')),
  task_id TEXT NOT NULL, confidence TEXT NOT NULL, retracted_by TEXT,
  PRIMARY KEY (group_id, member, member_kind)
);

CREATE TABLE aggregates (
  agg_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(task_id),
  purpose TEXT NOT NULL, gist TEXT NOT NULL, rationale TEXT NOT NULL,
  merged_into TEXT REFERENCES aggregates(agg_id)
);
CREATE TABLE aggregate_members (
  agg_id TEXT NOT NULL REFERENCES aggregates(agg_id), msg_id TEXT NOT NULL REFERENCES messages(msg_id),
  task_id TEXT NOT NULL, retracted_by TEXT,
  PRIMARY KEY (agg_id, msg_id)
);

------------------------------------------------------------------------------------------
-- L3 TRACKERS / LEAD / CHECKERS
------------------------------------------------------------------------------------------
CREATE TABLE loose_ends (
  le_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(task_id),
  about_type TEXT NOT NULL, about_id TEXT NOT NULL,   -- e.g. 'claim_key','ca-round5-11.2pct'
  question TEXT NOT NULL,                              -- "origin is before this window"
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','gave_up')),
  closed_by TEXT
);
CREATE TABLE observations (                -- row_format.md "free observations"; must cite messages
  obs_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(task_id), text TEXT NOT NULL
);
CREATE TABLE findings (                    -- lead/summarizer claims that reach the write-up
  finding_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(task_id),
  text TEXT NOT NULL, confidence TEXT NOT NULL,
  supports TEXT NOT NULL                   -- JSON list of {type, id}: claim_keys, links, aggregates it rests on
);
CREATE TABLE checks (                      -- citation script + adversarial checker verdicts on any object
  check_id INTEGER PRIMARY KEY, obj_type TEXT NOT NULL, obj_id TEXT NOT NULL,
  checker TEXT NOT NULL CHECK (checker IN ('citation_script','same_model','cross_lab','human')),
  task_id TEXT, verdict TEXT NOT NULL CHECK (verdict IN ('pass','fail','accept','correct','reject')),
  note TEXT, t TEXT NOT NULL
);
CREATE INDEX checks_obj ON checks(obj_type, obj_id);

CREATE TABLE identity_edges (              -- run identity (DESIGN.md 5.5); run groups = components of accepted edges
  edge_id    INTEGER PRIMARY KEY,
  session_a  TEXT NOT NULL,                -- name-session id: label + first save time (gap > 6 h starts a new one)
  session_b  TEXT NOT NULL,
  edge_type  TEXT NOT NULL CHECK (edge_type IN ('template_mint','timestamp_mint','signature','edit_summary','tag_topic','append_chain')),
  strength   TEXT NOT NULL CHECK (strength IN ('strong','medium')),
  evidence   TEXT NOT NULL,                -- JSON: msg_ids and the measured feature; never body text
  status     TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','accepted','rejected')),
  decided_by TEXT,                         -- 'script' or task_id of the run-identity linker
  version    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE coverage_gaps (               -- messages no reader record exists for, and why (DESIGN.md 7)
  msg_id   TEXT NOT NULL REFERENCES messages(msg_id),
  task_id  TEXT REFERENCES tasks(task_id),
  reason   TEXT NOT NULL CHECK (reason IN ('refused','failed','skipped')),
  detail   TEXT,                           -- e.g. stop_details.category; never message text
  PRIMARY KEY (msg_id, reason)
);

CREATE TABLE conversations (              -- conversation clustering (store_design.md 2a): one row per conversation thread
  conv_id   TEXT PRIMARY KEY,
  task_id   TEXT NOT NULL REFERENCES tasks(task_id),   -- 'script' pass or clusterer agent task
  topic     TEXT NOT NULL,                 -- one line, the clusterer's own words
  channels  TEXT NOT NULL,                 -- JSON list: rooms or pages it runs across
  t_first   TEXT NOT NULL, t_last TEXT NOT NULL,
  rationale TEXT NOT NULL,
  merged_into TEXT REFERENCES conversations(conv_id)
);
CREATE TABLE conversation_members (
  conv_id  TEXT NOT NULL REFERENCES conversations(conv_id),
  msg_id   TEXT NOT NULL REFERENCES messages(msg_id),
  task_id  TEXT NOT NULL REFERENCES tasks(task_id),
  basis    TEXT NOT NULL CHECK (basis IN ('reply_to','time_gap','shared_entity','same_page_chain','page_reference','agent_judgment')),
  confidence TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  retracted_by TEXT,
  PRIMARY KEY (conv_id, msg_id)            -- a message may sit in two conversations (it bridges them)
);
CREATE INDEX conversation_members_msg ON conversation_members(msg_id);
CREATE TABLE conversation_edges (           -- how conversations relate over time
  edge_id   TEXT PRIMARY KEY,
  task_id   TEXT NOT NULL REFERENCES tasks(task_id),
  type      TEXT NOT NULL CHECK (type IN ('split','merge','drift','resume')),
  from_conv TEXT NOT NULL REFERENCES conversations(conv_id),
  to_conv   TEXT NOT NULL REFERENCES conversations(conv_id),
  at_msg_id TEXT NOT NULL REFERENCES messages(msg_id), -- the message where it happens; quote in citations(obj_type='conv_edge')
  confidence TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  rationale TEXT NOT NULL,
  retracted_by TEXT
);

-- who was in a conversation up to a given message: exposure evidence (not proof) for the cascade tracer
CREATE VIEW conversation_presence AS
  SELECT cm.conv_id, m.speaker, MIN(m.t) AS t_joined, MAX(m.t) AS t_last_seen, COUNT(*) AS n_msgs
  FROM conversation_members cm JOIN messages m USING (msg_id)
  WHERE cm.retracted_by IS NULL GROUP BY cm.conv_id, m.speaker;

CREATE TABLE ops (                         -- append-only log of every tool call that wrote something
  op_id INTEGER PRIMARY KEY, t TEXT NOT NULL, task_id TEXT, tool TEXT NOT NULL,
  args TEXT NOT NULL, result TEXT NOT NULL -- 'ok' | 'rejected: <reason>'
);

------------------------------------------------------------------------------------------
-- VIEWS (what downstream tiers and scoring read)
------------------------------------------------------------------------------------------
CREATE VIEW live_links AS SELECT * FROM links WHERE retracted_by IS NULL;
CREATE VIEW live_members AS
  SELECT m.claim_key, m.claim_id, c.msg_id, c.stance, c.stated_source, msg.t, msg.speaker, msg.lab, msg.channel
  FROM claim_key_members m JOIN claims c USING (claim_id) JOIN messages msg ON msg.msg_id = c.msg_id
  WHERE m.retracted_by IS NULL;

-- novelty is computed, never written: first appearance and later adopters per claim_key
CREATE VIEW novelty AS
  SELECT claim_key,
         (SELECT msg_id  FROM live_members x WHERE x.claim_key = m.claim_key ORDER BY t LIMIT 1) AS first_msg_id,
         (SELECT speaker FROM live_members x WHERE x.claim_key = m.claim_key ORDER BY t LIMIT 1) AS first_speaker,
         MIN(t) AS t_first, COUNT(DISTINCT speaker) - 1 AS n_later_speakers, COUNT(*) AS n_mentions
  FROM live_members m GROUP BY claim_key;

-- events: row_format.md section 2 rebuilt from L1+L2, for scoring against plants and hand labels.
-- role: first speaker = origin; doubts -> challenge; corrects -> correct; otherwise adopt.
-- depth: acted if an acted_on link leaves this message for this claim_key, else said.
CREATE VIEW events AS
  SELECT lm.claim_key AS item_id, ck.layer, ck.status AS item_status, lm.msg_id, lm.t, lm.speaker AS agent, lm.lab AS agent_lab,
         CASE WHEN lm.msg_id = n.first_msg_id THEN 'origin'
              WHEN lm.stance = 'doubts' THEN 'challenge'
              WHEN lm.stance = 'corrects' THEN 'correct'
              ELSE 'adopt' END AS role,
         CASE WHEN EXISTS (SELECT 1 FROM live_links l WHERE l.from_msg_id = lm.msg_id AND l.type = 'acted_on' AND l.claim_key = lm.claim_key)
              THEN 'acted'
              WHEN EXISTS (SELECT 1 FROM records r WHERE r.msg_id = lm.msg_id AND r.retracted_by IS NULL
                           AND 'COMMIT' IN (r.purpose, r.purpose2, r.purpose3))
              THEN 'planned' ELSE 'said' END AS depth,
         (SELECT l.to_msg_id FROM live_links l WHERE l.from_msg_id = lm.msg_id AND l.type IN ('source_of','reply_to','acted_on','exposed_to')
            AND (l.claim_key = lm.claim_key OR l.claim_key IS NULL) ORDER BY l.confidence LIMIT 1) AS exposure_msg_id
  FROM live_members lm JOIN claim_keys ck USING (claim_key) JOIN novelty n USING (claim_key)
  WHERE ck.merged_into IS NULL
    AND NOT EXISTS (SELECT 1 FROM messages d WHERE d.msg_id = lm.msg_id AND d.script_label = 'DUPLICATE');
