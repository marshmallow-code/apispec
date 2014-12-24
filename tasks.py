# -*- coding: utf-8 -*-
import os
import sys

from invoke import task, run

docs_dir = 'docs'
build_dir = os.path.join(docs_dir, '_build')

@task
def test():
    run('py.test', pty=True)

@task
def watch():
    """Run tests when a file changes."""
    import pytest
    errcode = pytest.main(['-f'])
    sys.exit(errcode)

@task
def clean():
    run("rm -rf build")
    run("rm -rf dist")
    run("rm -rf smore.egg-info")
    clean_docs()
    print("Cleaned up.")

@task
def clean_docs():
    run("rm -rf %s" % build_dir)

@task
def browse_docs():
    platform = str(sys.platform).lower()
    command_map = {
        'darwin': 'open ',
        'linux': 'idle ',
        'win32': '',
    }
    cmd = command_map.get(platform)
    if cmd:
        run("{0}{1}".format(cmd, os.path.join(build_dir, 'index.html')))
    else:
        print('Unsure how to open the built file on this operating system.')
        sys.exit(1)

@task
def docs(clean=False, browse=False):
    if clean:
        clean_docs()
    run("sphinx-build %s %s" % (docs_dir, build_dir), pty=True)
    if browse:
        browse_docs()

@task
def readme(browse=False):
    run('rst2html.py README.rst > README.html')

@task
def publish(test=False):
    """Publish to the cheeseshop."""
    try:
        __import__('wheel')
    except ImportError:
        print("wheel required. Run `pip install wheel`.")
        sys.exit(1)
    if test:
        run('python setup.py register -r test sdist bdist_wheel upload -r test')
    else:
        run("python setup.py register sdist bdist_wheel upload")
