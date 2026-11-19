# Схема сценария

Схема JSON-файла сценария. Подробное описание полей и правил: [`SCENARIO_FORMAT.md`](SCENARIO_FORMAT.md), раздел 3.

```mermaid
erDiagram
  SCENARIO ||--o{ SESSION : "sessions"
  SCENARIO ||--o{ FACT : "facts (эталон)"
  SCENARIO ||--o{ CONSTRAINT : "constraints"
  SCENARIO ||--o{ CHECKPOINT : "checkpoints"
  SESSION ||--o{ EVENT : "events по порядку"
  EVENT }o--o{ FACT : "facts (что сообщает)"
  FACT }o--o| FACT : "supersedes"
  CONSTRAINT }o--|| EVENT : "event_id"
  CHECKPOINT }o--o{ EVENT : "required_events"
  CONSTRAINT ||--o{ ACTION_PATTERN : "forbidden"
  CHECKPOINT ||--o{ ACTION_PATTERN : "action"

  SCENARIO {
    string id "C1-dev-0003"
    string category "C0..C6"
    string split "dev | eval | holdout"
    int seed
    string variant "none | explicit | implicit"
    string resolution "только C3"
    int n_sessions
  }
  SESSION {
    int index
  }
  EVENT {
    string id "e-0042"
    string type "user_message | tool_data | note"
    string text
    string author "user | planner | worker | reviewer | tool"
    string scope "private | task | shared"
    string tool "read_document | read_status | null"
    object args
    bool factor
  }
  FACT {
    string id
    string entity "Atlas/billing"
    string attribute
    string value
    int valid_from
    int valid_to "null = действует"
    string source "user | tool | document | agent"
  }
  CONSTRAINT {
    string id
    string text
    int introduced_in
    string event_id
  }
  CHECKPOINT {
    string id
    int session
    string role "planner | worker | reviewer"
    string kind "value | constraint | conflict | isolation | injection"
    string task_text
    object context "present, absent, absent_outside_quoted, disputed_both"
    object answer "expect, stale, disputed"
    object action "forbidden, required"
    bool factor
  }
  ACTION_PATTERN {
    string tool "read_document | read_status | update_record"
    object args
  }
```

Связи через id:
- `event.facts` ссылается на факты эталона.
- `constraint.event_id` и `checkpoint.required_events` ссылаются на события.
- `fact.supersedes` ссылается на заменённый факт.
