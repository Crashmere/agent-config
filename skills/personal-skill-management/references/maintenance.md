# Skill maintenance

Read this reference when real use exposes a problem in a personal skill or bundled script, or when a required skill cannot be found or loaded.

## Correct a failing skill

1. Complete the immediate task with a verified solution when possible. Investigate why the documented workflow failed rather than stopping at a workaround.
2. Compare the failure and working solution with the skill's instructions, commands, scripts, assumptions, trigger description, and referenced dependencies.
3. Distinguish a reusable defect from a one-off environmental condition. Update the repository only when the correction generalizes or the environment-specific condition needs documentation.
4. Make the smallest appropriate correction. Update scripts, metadata, routing, and README only when their behavior or purpose changed.
5. Re-run only the corrected command or smallest affected workflow when safe. Do not repeat an expensive workflow unless the change affects it broadly or focused validation cannot establish confidence.
6. Follow [repository-workflow.md](repository-workflow.md) for focused validation, committing, pushing, and reporting. Include both the original cause and durable correction.

## Handle a missing skill

1. Stop the workflow that depends on the missing skill. Do not silently improvise a replacement or continue destructive or state-changing actions.
2. Perform a quick, read-only source check using the name and context:
   - inspect skills exposed by the runtime;
   - check this personal repository;
   - check relevant user, project, system, and plugin skill locations;
   - inspect lockfiles, plugin metadata, repository documentation, or known upstream sources that may identify the installer or owner.
3. Avoid broad filesystem or network searches when likely locations and metadata are sufficient.
4. Report the missing skill, expected location, checked sources, most likely source or cause, and what is needed to restore it.
5. Wait for the user's direction before installing, relinking, replacing, or removing anything. Resume only after the skill is available or the user explicitly authorizes an alternative.
