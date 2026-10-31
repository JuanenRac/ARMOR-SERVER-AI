# The daily summary

`armor-vision-policy --daily-summary FILE --summary-config CONFIG` turns the events of one day into a **structured summary**, a **readable text in eight languages** and a list of **patterns with their evidence**. It is off until the settings file says `"enabled": true`; without it the command refuses (exit code 2) and the policy worker behaves exactly as before. It is a report for a person: it raises no alarm and authorizes nothing.

```powershell
$env:PYTHONPATH = "src"
python -m armor_server_ai.cli --daily-summary day.jsonl --summary-config docs/daily_summary.example.json            # refuses: "enabled" is false
python -m armor_server_ai.cli --daily-summary day.jsonl --summary-config my-settings.json --lang pt                 # text
python -m armor_server_ai.cli --daily-summary day.jsonl --summary-config my-settings.json --json                    # the structured report
```

There is no new network route: the service in this repository listens on no port, so the summary is a command, not a `GET /summary/daily`. A server that wants to offer it would run the command (or call `armor_server_ai.daily.daily_report`) and keep its own authentication.

## The events

A JSON list or JSON lines. Each event:

| Key | Meaning |
|---|---|
| `t_s` | seconds from the start of the day, from 0 up to (not including) 86 400 |
| `type` | `alarm` (default), `node_link_lost`, `reading` or `power` |
| `code`, `zone`, `node`, `sensor` | identifiers of 1 to 64 letters, digits, `_`, `.` or `-`; an alarm needs `code`, a link loss `node`, a reading `node`, `sensor` and `value`, a power sample `watts` |
| `severity` | `info`, `low`, `medium`, `high` or `critical` |
| `false_alarm` | `true` when the alarm was dismissed as false |
| `duration_s` | how long a link was lost |
| `detail` | free text (500 characters at most): read to check it, then dropped; it is never in the summary or sent anywhere |

Alarms use the same keys as the alarms that `ARMOR-SIMULATOR --verify-alarms` reads. Lines `{"topic", "payload"}` printed by `python -m armor_simulator ... --start-ms 0` are accepted as they are (do not mix them with events): a node that is silent for longer than `summary.link_gap_s` becomes a `node_link_lost`, and the `house` channel of the electrical messages becomes a `power` sample. A node that stays silent until the end of the data is not seen as lost (nothing says when the day ended).

Nothing is read loosely: a key that is not listed, a wrong type or range, a repeated key, `NaN`, an odd identifier, a file over 8 MB or more than 100 000 events refuses the **whole** file with the number of the event, and nothing is printed on the standard output.

## The summary

Deterministic (the same events in any order give the same bytes): `totals` (events, alarms, serious alarms, false alarms), the counts `by_type`, `by_zone` (`-` when an event has no zone) and `by_hour` (24 numbers), each of which adds up to `totals.events`; the `busiest_hour`; the `serious_alarms` (severity in `summary.serious_severities` or code in `summary.serious_codes`, never a false alarm); the `nodes_link_lost` with how many times and for how long; the `outlier_readings` (far from the median of their own sensor, by the median absolute deviation; `summary.outlier_mad_k`, `summary.outlier_min_scale`, `summary.outlier_min_samples`); and the `consumption` (samples, mean, maximum and the highest peaks).

## The patterns

Each finding has `kind`, `subject`, `count`, `detail` (the numbers that were compared) and `evidence` (the events, at most 20).

| `kind` | When | Settings (`patterns.`) |
|---|---|---|
| `hourly_repeat` | the same alarm code in the same zone, at the same minute of the hour (within a margin) in at least N different hours | `hourly_repeat_min_hours`, `hourly_repeat_tolerance_min` |
| `intermittent_sensor` | at least N faults (`sensor_fault_codes`) of one node and zone, each no further than a limit from the previous one | `intermittent_min_faults`, `intermittent_max_gap_s`, `sensor_fault_codes` |
| `intermittent_link` | a node that lost its link at least N times | `link_loss_min` |
| `recurrent_false_alarm` | at least N false alarms (`false_alarm: true` or a code of `false_alarm_codes`) in one zone | `false_alarm_min`, `false_alarm_codes` |
| `anomalous_consumption` | a sample above the mean of the previous `consumption_window` samples by more than `consumption_sigma` deviations and by at least `consumption_min_ratio` times | `consumption_window`, `consumption_sigma`, `consumption_min_ratio` |

A day holds one date, so "the same hour" means the same time of the hour inside that day; comparing days is left to whoever keeps the summaries.

## The text

Templates in the eight languages (`en`, `es`, `de`, `fr`, `it`, `ja`, `zh`, `pt` with Portuguese of Portugal), chosen by `language` in the settings or `--lang`. Nothing is generated and no service is called. A test keeps the eight languages with the same keys and the same placeholders.

## The AI note (optional, off)

`ai.enabled` is `false` by default. When it is `true` the note of a **provider** is added to the text. A provider is anything with `name`, `external` and `enrich(payload) -> str` (see `daily_ai.py`); only a **simulated** one ships: deterministic, with no network. A provider that is `external` (it would send the data off this machine) is refused unless `ai.allow_external` is `true`, which is `false` by default, and the repository ships no external provider.

Before any provider sees the data it is **redacted**: the payload is only the structured summary and findings (never the free text of the events), every text loses e-mails, URLs, IPv4, IPv6 and MAC addresses, bearer tokens, `password=...` assignments, long token-like strings and the names in `ai.redact_names`, and a field named like a name, address, user, password, token or key is replaced entirely. The answer is redacted again and cut to 2 000 characters. The same redaction runs on the final text and the JSON, so a name that slipped into an identifier does not leave in the report either. An unknown provider or one that answers something other than text ends the command with a message and exit code 2.

## The settings

Every value is in the JSON file; `docs/daily_summary.example.json` holds all of them with their defaults. An unknown key, a wrong type or a value out of its range refuses the whole file.
