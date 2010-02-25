*********
PID files
*********

The PIDFile :doc:`Engine Plugin </intro/concepts/engineplugins>` is pretty
straightforward: it writes the process id to a file on start, and deletes the
file on exit. You must provide a 'pidfile' argument, preferably an absolute path.
