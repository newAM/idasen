Change Log
##########

`0.7.0`_ 2021-05-08
*******************

Changed
=======
- Updated bleak dependency from `0.9` to `0.11`.

`0.6.0`_ 2020-12-05
*******************

Changed
=======
- Stop moving the desk if the safety feature kicks in.

`0.5.0`_ 2020-11-14
*******************

Added
=====
- Added python 3.9 support.

Changed
=======
- Added automatic retry to failed connections.

Fixed
=====
- Allow the ``init`` subcommand to work without a MAC address.

`0.4.0`_ 2020-10-20
*******************

Added
=====
- Added ``save`` and ``delete`` sub-commands to the CLI to save and delete
  desk positions.

Changed
=======
- Changed the configuration file format, see the README for details.
- Updated bleak dependency to 0.9.0.

Fixed
=====
- Fixed a bug with the ``init`` sub-command raising an exception.

`0.3.0`_ 2020-10-10
*******************

Added
=====
- Added ``discover`` class method to ``IdasenDesk``.

Changed
=======
- The ``init`` subcommand will now attempt to discover the MAC address.

`0.2.1`_ 2020-10-07
*******************

Fixed
=====
- Fixed CLI `--verbose` argument doing nothing.

`0.2.0`_ 2020-09-26
*******************

Changed
=======
- Added URL to ``yaml`` file created with ``idasen init``.
- Updated bleak dependency to 0.8.0

`0.1.0`_ 2020-09-07
*******************
- Initial release

.. _0.7.0: https://github.com/newAM/idasen/releases/tag/v0.7.0
.. _0.6.0: https://github.com/newAM/idasen/releases/tag/v0.6.0
.. _0.5.0: https://github.com/newAM/idasen/releases/tag/v0.5.0
.. _0.4.0: https://github.com/newAM/idasen/releases/tag/v0.4.0
.. _0.3.0: https://github.com/newAM/idasen/releases/tag/v0.3.0
.. _0.2.1: https://github.com/newAM/idasen/releases/tag/v0.2.1
.. _0.2.0: https://github.com/newAM/idasen/releases/tag/v0.2.0
.. _0.1.0: https://github.com/newAM/idasen/releases/tag/v0.1.0
