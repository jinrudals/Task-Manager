# Task Manager

Control tasks from multiple clients.

Each client is connected with `websocket`. When enqueing, this task manager will calculate its priority and save it into `Redis`.

When dequeing, it first looks for the maximum running job counts. If is less than the maximum value, it deques one item from the pending list,
and sends to the corresponding client to execute the signal, meaning all clients need to wait until the task manager tells to launch.

The client proceeds the command, and after completion, it sends another singal to pop from the running queue.
