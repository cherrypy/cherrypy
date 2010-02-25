***************
Drop privileges
***************

Use this engine :doc:`plugin </intro/concepts/engineplugins>` to start your
CherryPy site as root (for example, to listen on a privileged port like 80)
and then reduce privileges to something more restricted.

Parameters
==========

 * uid: the user id to switch to. Availability: Unix.
 * gid: the group id to switch to. Availability: Unix.
 * umask: the default permission mode for newly created files and directories.
   Usually expressed in octal format, for example, ``0644`` . Availability: Unix,
   Windows.

This priority of this plugin's "start" listener is slightly higher than the
priority for ``server.start`` in order to facilitate the most common use:
starting on a low port (which requires root) and then dropping to another user.

