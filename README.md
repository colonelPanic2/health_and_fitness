# Exercise Tracker Bot

Run `discord_bot/exercise/bot.py` using the project's Python environment, or use
the desktop launcher. Restart the bot after changing its Python files.

## Data locations

Data defaults to the `data` folder beside this README, regardless of the current
working directory or the computer running the bot. The required exercise history
is `data/exercise_logs/exercise_history.csv`. Keep your existing history CSV;
the bot reports a missing history file rather than silently creating a new one.

To keep data elsewhere, set `EXERCISE_BOT_DATA_DIR` before launching the bot.
It names the folder containing `exercise_logs`. An absolute path points to that
folder directly; a relative path is resolved against this repository's root.
This setting applies to exercise history, schedules, and future workout saves.

The schedule image is optional. Place it at
`data/exercise_logs/schedule/schedule.jpg`, or use `schedule.jpeg`, `schedule.png`,
`schedule.webp`, or `schedule.gif` in the same folder. Missing schedules do not
prevent logging workouts. No schedule image is included in this checkout.

Schedule tables, when present, live alongside the image as `schedule_history.csv`
and `exercises.csv`. The desktop launcher and Docker use the same data rules.

If `/start_workout` says a workout is already active, finish it with
`/end_workout` or deliberately discard it with `/abort_workout`. Finish any
unsaved workout before restarting the bot; active workout state is kept in memory.

## Checks

Run `.venv/Scripts/python.exe -m unittest discover -s tests` on Windows for the
path and schedule regression checks. The desktop executable's `--check` option
checks startup without logging in to Discord or changing workout history.
