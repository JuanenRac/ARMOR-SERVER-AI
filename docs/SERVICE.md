# The observation service

`python -m armor_server_ai.service` watches the cameras the server has, notices movement, weighs it with the radars and the light, and tells the server. It does not decide
anything about the house: the server raises the alarm (or not) and every action stays with it.

## What it does, every few seconds, while the system is armed

1. Asks the server for the context (`GET /api/v1/ai/context`): the mode, the radar nodes with their tracks and light, the cameras it can look at. Disarmed, it stops there.
2. For each camera takes one grey frame of 64 x 36 pixels (`GET /api/v1/ai/cameras/{id}/frame`; the server takes it from the stream with FFmpeg and keeps nothing) and compares it
   with the previous one: the share of pixels that changed by more than a small threshold is the movement.
3. Ignores what is not movement: less than 1 % of the picture, or more than 60 % (a light switched on or the exposure changing), and anything seen in fewer than
   `ARMOR_AI_CONFIRM_FRAMES` (2) frames in a row.
4. Asks the policy (`policy.py`): strong movement with a radar track that agrees is **high**; movement the policy finds worth a look is **review**. The day/night profile comes from
   the radar nodes' light sensor, or from how bright the picture is when none says.
5. Reports it (`POST /api/v1/ai/observations`), at most once every `ARMOR_AI_COOLDOWN_S` (60) per camera. The server raises a `camera_motion` alarm - once until it is closed -
   which reaches the app, Studio, Telegram and Home Assistant.

## What it is not

It is **not a person detector**: it cannot tell a person from a cat, a car or a branch. It is movement plus the radars, which is a good start and will false-alarm now and then
(a tree in the wind on a camera that sees the street). Telling what moved needs the Jetson and a detector (see INFERENCE_BOUNDARY.md). Tune it with the environment, or leave
a camera out by not giving it a stream in the server.

## Safety

Its token (`ARMOR_AI_TOKEN`) opens four routes of the server and nothing else; not even an operator's token opens them, and this one cannot arm, disarm or read anything. It
holds no camera address or password. A failure of the server, of a camera or of FFmpeg is said once on stderr and tried again; nothing here can take the house down.

On the bench it is installed by `ARMOR-DEVOPS/scripts/install_cm5.sh --with-ai`.
