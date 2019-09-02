#! /usr/bin/env python

# Copyright 2013 Ralf Thielow <ralf.thielow@gmail.com>
# Licensed under the GNU GPL version 2.

import codecs
import re
import shlex
import subprocess
import sys
import xml.dom.minidom as dom
import xml.etree.ElementTree as ElementTree
from typing import Optional, List


def get_enc(line, default):
    m = re.search("encoding=['\"](.*?)['\"]", line)
    if m is not None:
        return m.group(1)
    return default


def change_tag(old_tag, new_tag, cont, cms_tag_tag):
    return cont.replace(
        '<{0}>{1}</{0}>'.format(cms_tag_tag, old_tag),
        '<{0}>{1}</{0}>'.format(cms_tag_tag, new_tag)
    )


def get_tag(f):
    try:
        tree = dom.parse(f)
        matchingNodes = (
            tree.getElementsByTagName("tag")[0]
            if tree.getElementsByTagName("tag")
            else None
        )
        if matchingNodes is not None and matchingNodes.firstChild is not None:
            return matchingNodes.firstChild.nodeValue
        return None
    except Exception as e:
        print(e)
        print(sys.argv[0] + ": error while parsing pom.xml")
        return None


def change_version(old_version, new_version, cont, version_tag):
    return cont.replace(
        '<{0}>{1}</{0}>'.format(version_tag, old_version),
        '<{0}>{1}</{0}>'.format(version_tag, new_version)
    )


def _get_version_value(node, tag_path: List[str]):
    if node is None:
        return None
    if not tag_path:
        return node.firstChild.data

    child_nodes = node.getElementsByTagName(tag_path[0])
    if len(child_nodes) == 0:
        val = None
    else:
        val = _get_version_value(child_nodes[0], tag_path[1:])
    return val


def get_version(f, version_tag: str) -> Optional[str]:
    val = None
    try:
        val = _get_version_value(dom.parse(f), version_tag.split('/'))
    except BaseException as e:
        print(sys.argv[0] + ": error while parsing pom.xml - " + e)
    print('returning version value: ', val, 'for tag:', version_tag)
    return None


def run(mine_fname, their_fname, base_fname, version_tag, cms_tag_tag):
    base_version = get_version(base_fname, version_tag)
    my_version = get_version(mine_fname, version_tag)
    their_version = get_version(theirs_fname, version_tag)

    my_tag = get_tag(mine_fname)
    their_tag = get_tag(theirs_fname)
    have_tags = True if my_tag is not None and their_tag is not None else False

    # change current version in order to avoid merge conflicts
    if (
        my_version is not None
        and their_version is not None
        and base_version is not None
        and my_version != their_version
        and their_version != base_version
    ):
        with open(mine_fname, "r") as f:
            enc = get_enc(f.readline(), "utf-8")
        with codecs.open(mine_fname, "r", enc) as f:
            other = f.read()
        other = change_version(my_version, their_version, other, version_tag)
        other = change_tag(my_tag, their_tag, other, cms_tag_tag) if have_tags else other
        with codecs.open(mine_fname, "w", enc) as f:
            f.write(other)

    cmd = (
        "git merge-file -p -L mine -L base -L theirs "
        + mine_fname
        + " "
        + base_fname
        + " "
        + theirs_fname
    )
    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    git_merge_res = p.communicate()[0]
    ret = p.returncode

    enc = "utf-8"
    try:
        git_merge_res_str = git_merge_res.decode(enc)
    except:
        # utf-8 failed, try again with iso-8859-1
        enc = "iso-8859-1"
        git_merge_res_str = git_merge_res.decode(enc)

    oenc = get_enc(git_merge_res_str.splitlines()[0], enc)
    if enc != oenc:
        enc = oenc
        git_merge_res_str = git_merge_res.decode(enc)

    cmd = "git rev-parse --abbrev-ref HEAD"
    p = subprocess.check_output(shlex.split(cmd))
    branch = p.strip().decode("utf-8")

    # revert pom project version on current branch, unless in master.
    # Allows for gitflow release-finish, hotfix-finish,
    # and feature-finish to work better
    if my_version is not None and branch != "master":
        print(
            "Merging pom version "
            + their_version
            + " into "
            + branch
            + ". Keeping version "
            + my_version
        )
        git_merge_res_str = change_version(
            their_version, my_version, git_merge_res_str, version_tag
        )
        git_merge_res_str = (
            change_tag(their_tag, my_tag, git_merge_res_str, cms_tag_tag)
            if have_tags
            else git_merge_res_str
        )

    with codecs.open(mine_fname, "w", enc) as f:
        f.write(git_merge_res_str)

    return ret


# ##############################################################################
# main proc
# ##############################################################################

if len(sys.argv) < 5:
    print("Wrong number of arguments.")
    print('USAGE: ', sys.argv[0], '''<BASE> <MY> <THEIRS> <VERSION_TAG> [<VERSION_TAG>,...]

    Where <BASE>, <MY>, <THEIRS> are the filenames of the conflicted pom.xmls.
    <VERSION_TAG> the tag name which contains version value to merge.
    Tag name should be given as a full path, for ex. "parent/version".
    ''')
    sys.exit(-1)

# file in coflict - from corresponding branches
base_fname = sys.argv[1]
mine_fname = sys.argv[2]
theirs_fname = sys.argv[3]
# this is the list of version tags to merge
pom_version_tags = sys.argv[4:]

print('Version tags that will be processed: ', pom_version_tags)

for version_tag in pom_version_tags:
    ret = run(base_fname, mine_fname, theirs_fname, version_tag, 'tag')
sys.exit(ret)
