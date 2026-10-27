Scheduler probe for the weekly skill review (task-observer). This run proves the access grant and does nothing else.

Workspace: {{WORKSPACE}}
Engine: {{ENGINE}}

In this order:

1. Probe the workspace folder: one `ls "{{WORKSPACE}}/skill-observations"`.
2. Write the probe marker with one shell command:
   printf '%s probe %s\n' "$(date '+%F %H:%M')" "{{ENGINE}}" > "{{WORKSPACE}}/skill-observations/scheduler-probe.txt"
3. Say whether a skill named task-observer is available to you as a skill in this session. Do not invoke it and do not read its files.

End with exactly three lines: `workspace: reachable`, `offline` or `denied`; `write: ok` or `write: failed (<error>)`; `skill: available` or `skill: absent`. Nothing else: no review, no other file, no retries.
