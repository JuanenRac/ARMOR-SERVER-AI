# Inference boundary

This repository holds the **decisions**; cameras, RTSP ingestion, TensorRT
runtimes and PTZ actions are adapters that must be tested on the target Jetson
before anything is described as operational.

## Profile selection

`ProfileSelector` chooses the daylight or low-light model from validated lux. A
single threshold would toggle on every reading near it (a passing cloud, a light
being switched on), so it uses hysteresis: it enters low-light below 30 lux,
returns to daylight only above 60 lux and never changes twice within 30 seconds.
`choose_profile` remains for callers with no history.

## Fusion policy

`decide` correlates one visual detection with the radar tracks active for the same
node and returns a `Decision`: a severity (`ignore`, `review`, `high`), the reasons
behind it and `authorizes_action = False`.

* `high`: a person seen with at least 80 % confidence **and** at least one radar track.
* `review`: a confident detection (55 % in daylight, 45 % in low light, where a camera
  is less certain) or a radar track without a visual match.
* `ignore`: anything else, and any detection older than 10 seconds.

The policy only recommends. It cannot switch lights, sound sirens or move
cameras: the central server authenticates and authorises the event and performs the
final action. There is no field here that could be read as an instruction.

## Engines

`discover_engines` accepts only existing, non-empty pre-built `daylight.engine` and
`low_light.engine` files and never compiles or downloads a model. With an
`engines.json` manifest (`{"daylight": "<sha256>", "low_light": "<sha256>"}`) every
engine must match its recorded SHA-256, so a swapped or corrupted engine is refused
before it reaches the GPU; without one the result says `verified = False`.

## Not proven yet

RTSP ingestion, TensorRT inference, real latency and any Jetson behaviour. Those
are separate, evidence-based milestones.
