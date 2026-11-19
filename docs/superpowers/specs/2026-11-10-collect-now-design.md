# Collect now

The approved panel button requests immediate collection from the linked conversation and displays progress or errors. Automatic collection stays active.

## Approach

Reuse the single collector and its lock. A local request file for each binding triggers a pass, avoiding a second process or signals sent before startup. Key 5 triggers the same action as a click. Repeated requests coalesce. Requests during analysis wait for the current pass to finish. A request interrupts normal or error backoff, and identity validation still runs. Reads remain incremental, with the same models and no reanalysis of processed replies.

Sending, selection, completion, project association and UUID handling stay the same.
