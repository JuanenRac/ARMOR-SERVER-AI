# The observation service

`python -m armor_server_ai.service` watches the cameras the server has, notices movement, weighs it with the radars and the light, and tells the server. It does not decide
anything about the house: the server raises the alarm (or not) and every action stays with it.

## What it does, every few seconds, while the system is armed

1. Asks the server for the context (`GET /api/v1/ai/context`): the mode, the radar nodes with their tracks and light, the cameras it can look at (each with the `nodes` that cover it: a camera that lists none has no radar or light counted for it). Disarmed, it stops there.
2. For each camera takes one grey frame of 64 x 36 pixels (`GET /api/v1/ai/cameras/{id}/frame`; the server takes it from the stream with FFmpeg and keeps nothing) and compares it
   with the previous one: the share of pixels that changed by more than a small threshold is the movement.
3. Ignores what is not movement: less than 1 % of the picture, or more than 60 % (a light switched on or the exposure changing), and anything seen in fewer than
   `ARMOR_AI_CONFIRM_FRAMES` (2) frames in a row.
4. Asks the policy (`policy.py`): strong movement with a radar track that agrees is **high**; movement the policy finds worth a look is **review**. The day/night profile comes from
   the radar nodes' light sensor, or from how bright the picture is when none says.
5. Reports it (`POST /api/v1/ai/observations`), at most once every `ARMOR_AI_COOLDOWN_S` (60) per camera. The server raises a `camera_motion` alarm - once until it is closed -
   which reaches the app, Studio, Telegram and Home Assistant.

`--status-file FILE` (or `ARMOR_AI_STATUS_FILE`) is off until given. With it, after each pass the service rewrites FILE as one JSON line: `passes`, `armed`, `cameras`, `observations_sent`, `observations_failed`, `cameras_with_problem` (id and what is wrong), `server_problem` (the last one, or null) and `updated` (UTC). A monitor or the operator can read it without asking the service anything; it holds no picture, address or secret.

## What it is not

It is **not a person detector**: it cannot tell a person from a cat, a car or a branch. It is movement plus the radars, which is a good start and will false-alarm now and then
(a tree in the wind on a camera that sees the street). Telling what moved needs the Jetson and a detector (see INFERENCE_BOUNDARY.md). Tune it with the environment, or leave
a camera out by not giving it a stream in the server.

## Safety

Its token (`ARMOR_AI_TOKEN`) opens three routes of the server (the context, one picture of a camera and the report of an observation) and nothing else; not even an operator's token opens them, and this one cannot arm, disarm or read anything. It
holds no camera address or password. A failure of the server or of a camera (its picture, FFmpeg) is said once on stderr and tried again, whatever shape the answer has; nothing here can take the house down. `ARMOR_AI_SERVER_URL` must be `https://` or `http://` to this same machine (the token must not cross a network in clear). With many cameras the pass is spaced out so the server's limit of 200 pictures a minute is never reached.

On the bench it is installed by `ARMOR-DEVOPS/scripts/install_cm5.sh --with-ai`.

The unit can also be limited by the kernel to the addresses it needs: with `--ai-ip-restrict on` the installer gives it `IPAddressDeny=any` and `IPAddressAllow=localhost`, and `--ai-ip-allow` adds the addresses or networks of a server that is on another machine. It is off by default and an upgrade keeps what the install had.

The separate daily report of the events of a day (`--daily-summary`, off by default) is described in DAILY_SUMMARY.md; it is not part of the service and opens no route.

## Where the radar track is in the picture (off by default)

With `ARMOR_AI_SPATIAL=1` a radar track counts as evidence for a movement on a camera only when it falls, seen from the camera, on the same side of the picture as a region of movement. Without it (the default) any track of the nodes that cover the camera counts, as always.

The geometry comes from the site design, which sends it with the context: a `pose` (`x_mm`, `y_mm`, `yaw_deg`, a position on the floor plan in millimetres and the direction the device faces in degrees clockwise from the +y axis) on each node and on each camera, the tracks of a node as `targets: [{x_mm, y_mm}]` (x to the right of the radar, y straight ahead of it), and on a camera optionally `fov_deg` (default 90) and `range_mm` (default 15000). A track is placed on the plan, projected on the picture as a pinhole camera would, and counts when its column is inside a region of movement with a margin of 12 % of the width. A track behind the camera, beyond its range or outside its view does not count.

It is a flat approximation, enough to tell the left of the picture from the right and to rule out what the camera cannot see. Geometry that is missing never takes evidence away: without the pose of the camera, without a region of movement, or for a node that has no pose or gives only a count, the tracks count as before. The adjustment of the fine position (the lens, the height) needs a real camera and radar, and is the pending physical check.

## Learning the busy parts of the pictures (off by default)

With `ARMOR_AI_LEARN=1` the service looks at the pictures of the cameras while the system is **disarmed** (it needs the person's permission, which is why it is off), compares each with the one before and adds one to a counter for every cell of the 16 x 9 grid that moved. What is kept is those counters and the number of comparisons, in `ARMOR_AI_LEARN_FILE` when it is set: never a picture. After `ARMOR_AI_LEARN_HOURS` hours (12 by default) and enough comparisons, the cells that moved in at least `ARMOR_AI_LEARN_BUSY_SHARE` of them (a quarter by default) are joined into rectangles and **proposed** as areas to ignore. The proposal is in the status of the service, under `learning`; nothing is applied until the person accepts it as an ignore zone of the camera in the site design. Nothing is told to the server while it learns, and while the system is armed it does not count.
