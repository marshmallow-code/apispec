*******
restkit
*******

A collection of utilities for designing and documenting RESTful APIs built with `webargs <http://webargs.readthedocs.org/en/latest/>`_ and `marshmallow <http://marshmallow.readthedocs.org/en/latest/>`_.

Release v\ |version|. (:ref:`Changelog <changelog>`)

.. contents::
   :local:
   :depth: 2

Features
========

- Convert ``webarg.Args`` and ``marshmallow.Schemas`` into `Swagger 2.0 <http://swagger.io>`_ API definitions. (in progress)
- Pagination support for marshmallow serializers. (todo)
- Automatic API documentation. (todo)

Get it now
==========
::

   pip install -U restkit

restkit supports Python >= 2.7 or >= 3.3.

Dependencies
-------------

- webargs>=0.7.0
- marshmallow>=1.0-a

API Guide
=========

.. module:: restkit


restkit.swagger
---------------

.. automodule:: smore.swagger
    :inherited-members:


Project Info
============

.. toctree::
   :maxdepth: 1

   license
   changelog
   authors
