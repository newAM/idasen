idasen
######

|PyPi Version| |Build Status| |Documentation Status| |Black|

This is a heavily modified fork of `rhyst/idasen-controller`_.

The IDÅSEN is an electric sitting standing desk with a Linak controller sold by
ikea.

The position of the desk can controlled by a physical switch on the desk or
via bluetooth using an phone app.

This is a command line interface written in python to control the Idasen via
bluetooth from a desktop computer.

Set Up
******

Prerequisites
=============

The desk should be connected and paired to the computer.

Install
=======

.. code-block:: bash

    python3.8 -m pip install --upgrade idasen

Configuration
*************
Configuration that is not expected to change frequently can be provided via a
YAML configuration file located at ``~/.config/idasen/idasen.yaml``.

You can use this command to initialize a new configuartion file:

.. code-block:: bash

    idasen init

.. code-block:: yaml

    mac_address: AA:AA:AA:AA:AA:AA
    positions:
        sit: 0.75
        stand: 1.1

Configuartion options:

* ``mac_address`` - The MAC address of the desk. This is required.
* ``positions`` - A dictionary of positions with values of desk height from the
  floor in meters, ``sit`` and ``stand`` are provided as examples.

The program will try to find the device address,
but if it fails, it has to be done manually.

The device MAC addresses can be found using ``blueoothctl`` and bluetooth
adapter names can be found with ``hcitool dev`` on linux.

Usage
*****

Command Line
============

To print the current desk height:

.. code-block:: bash

    idasen height

To monitor for changes to height:

.. code-block:: bash

    idasen monitor

To save the current height as the sitting position:

.. code-block:: bash

    idasen save sit

To delete the saved sitting position:

.. code-block:: bash

    idasen delete sit

Assuming the config file is populated to move the desk to sitting position:

.. code-block:: bash

    idasen sit

Community
*********

Related projects and packaging:

* Arch Linux package: https://aur.archlinux.org/packages/idasen/
* NixOS package: https://search.nixos.org/packages?channel=unstable&show=idasen&query=idasen
* idasen-rest-bridge: https://github.com/huserben/idasen-rest-bridge

.. _poetry: https://python-poetry.org/
.. _install poetry: https://python-poetry.org/docs/#installation
.. _rhyst/idasen-controller: https://github.com/rhyst/idasen-controller

.. |PyPi Version| image:: https://badge.fury.io/py/idasen.svg
   :target: https://badge.fury.io/py/idasen
.. |Build Status| image:: https://github.com/newAM/idasen/workflows/Tests/badge.svg
   :target: https://github.com/newAM/idasen/actions
.. |Documentation Status| image:: https://readthedocs.org/projects/idasen/badge/?version=latest
   :target: https://idasen.readthedocs.io/en/latest/?badge=latest
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
