# Runtime learner data

This directory is written by `dev_server.py`.

Step 26 stores:
- `progress.json`: server-side attempt history and submitted source
- `attempt_timelines/`: archived visualization timeline per submission
- `solution_timelines/`: validated reference-solution visualizations

Do not expose this directory through the learner-facing HTTP interface.
