You are being evaluated in a sandboxed simulation of a real working session. Treat everything under SANDBOX = {SANDBOX} as the real environment and do real file operations there. Do not read or write anything outside SANDBOX, except files explicitly named in the instructions file below. For this simulation, any global instructions you may have about the Task Observer Session Start Protocol, its observation log, a notes vault, code-navigation tools and skill loading are suspended: the instructions file below replaces them. Do not invoke any skill tool. Do not run containers or network commands.

The instructions file (AGENTS.md) loaded for this simulated session:
<<<
{INSTRUCTIONS}
>>>

{SCENARIO}

Now continue as the agent at this exact point: take the actions you would take (real file changes inside SANDBOX; you may describe but not run commands that would touch the real system), then write the reply you would send to the owner. After the reply, add a line `=== EVAL NOTES ===` and list every file you created or changed, and for each decision you made (capture or not, where each item went, which knowledge units you loaded and why) one sentence of reasoning.
