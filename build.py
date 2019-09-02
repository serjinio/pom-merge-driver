import glob
import os
from subprocess import check_call as run

from pybuilder.core import task

default_task = "test"


def flist():
    return glob.glob("*.py")


@task
def format(logger):
    """Format the code"""
    run(["isort", "-y"] + flist())
    run(["black"] + flist())
    run(["autopep8", "--in-place"] + flist())


@task
def check(logger):
    run(["python", "-m", "mypy", "--ignore-missing-imports"] + flist())


@task
def install_linux(logger):
    if not os.path.exists(os.path.expanduser('~/bin')):
        logger.info('Will create user bin dir: "%s"',
                    os.path.expanduser('~/bin'))
        os.mkdir(os.path.expanduser('~/bin'))
    run(['ln', '-s',
         os.path.abspath('mergepom.py'),
         os.path.expanduser('~/bin/mergepom.py')])
    logger.info('''
        Customize your ~/.gitconfig with:

        [merge "pommerge"]
        name = A custom merge driver for Maven's pom.xml
        driver = /home/serj/bin/mergepom.py %O %A %B "frontend.version"
    ''')
