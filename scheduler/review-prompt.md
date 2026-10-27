Weekly skill review (task-observer), scheduled autonomous mode.

Workspace: {{WORKSPACE}}
Engine: {{ENGINE}}

In this order:

1. Probe the workspace folder (one `ls "{{WORKSPACE}}/skill-observations"`), then invoke the task-observer skill.
2. Write the started marker:
   printf '%s\n' "$(date '+%F %H:%M')" > "{{WORKSPACE}}/skill-observations/review-started.txt"
3. Run the comprehensive review that the skill's references/weekly-review.md defines, in scheduled autonomous mode, on this workspace.

Offline policy: if the probe finds no workspace, end with the one line "review skipped: workspace offline" and stop. If the path exists but this run cannot read or write it, end with "review skipped: workspace denied by the session sandbox; grant {{WORKSPACE}} in the task definition". No retries in either case.

If task-observer does not resolve as a skill in this session, read {{SKILL_DIR}}/SKILL.md and follow it, and say so in the first line of the summary.
