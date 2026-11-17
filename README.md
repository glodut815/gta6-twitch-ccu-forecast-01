[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/glodut815/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/glodut815/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Bounty: https://make.fun/bounty/gta6-twitch-ccu-forecast-01

# GTA VI Twitch CCU Forecast — make.fun entry

Forecasts, hour by hour, how many people watch Grand Theft Auto VI live on
Twitch over the 24 UTC hours of its release day (2026-11-19), from the first
hour's print, as five quantiles (5%, 25%, 50%, 75%, 95%) per hour.

## Method

Comparable-launch analog curves. For every comparable past launch in the
case, its release-day hourly viewer curve is expressed as log-ratios to that
launch's own hour-1 print. Each comparable is weighted by similarity to the
case: a Gaussian kernel on hour-1 scale (bandwidth 1.25 log units), an
unlock-shape match (rolling midnight vs simultaneous global, ×2 / ÷2), and a
tier weight (comparable ×1, early-access-contaminated ×0.4, weak ×0.2).
Per hour, the weighted median log-ratio is the centre and the weighted
standard deviation (×0.75, floored) is the log spread. Everything is
computed at run time from the case file, so the final case's 42
comparables are all used. No network, no randomness, deterministic.

## Validation (local)

Against SullyGnome hourly averages for the four practice launches'
release days:

| case | this entry | house persistence baseline |
| --- | --- | --- |
| Marvel's Wolverine | 0.360 | 0.744 |
| Red Dead Redemption 2 | 0.155 | 0.287 |
| God of War Ragnarök | 0.139 | 0.215 |
| Marvel's Spider-Man 2 | 0.189 | 0.303 |
| **mean pinball loss** | **0.211** | **0.387** |

Leave-one-out over the 38 comparables (148 pseudo-cases): loss 0.388 vs
baseline 0.930.

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only. ~0.03 s per case; two runs on the same
case write identical bytes.

## License

MIT — see LICENSE.
