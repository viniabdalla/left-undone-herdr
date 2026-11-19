# Confirm queueing when the agent is busy

Vini approved prompting the user to queue a request with the agent when Send finds the agent busy. Confirm queues the request. Cancel preserves the selection. An idle agent receives the message directly. Sent and queued tasks stay open.

Use the native Codex queue (`codex queue --thread UUID --message TEXT`) with the verified account, without `--resume` or an interrupt message. The installed Claude CLI has no equivalent API. Report that queueing is unavailable and preserve the selection. Avoid an internal queue or delivery polling. Leave the UUID protection under development in the other worktree intact.

Freeze the selected IDs and text when the user requests delivery. Revalidate identity and items on confirmation. If an item changed or closed, cancel delivery. Errors and timeouts preserve selection without retrying. Success clears only the selection that was sent. The confirmation accepts mouse input and 1/2/Esc.

The native UUID queue preserves the destination and gives the harness control. Simulating Enter during work could interrupt a turn. A separate queue could deliver to the wrong session after a switch and would depart from the requested behavior.
