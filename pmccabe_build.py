#!/usr/bin/python

import argparse
import os
import subprocess
import sys
import xml.etree.cElementTree as ET
from collections import defaultdict
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment, tostring

from package_tree import package_tree


parser = argparse.ArgumentParser(
    prog="ProgramName",
    description="What the program does",
    epilog="Text at the bottom of help",
)
parser.add_argument("path")

args = parser.parse_args()
sources_path = args.path
find_result = subprocess.run(
    ["find", sources_path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
)

grep_result = subprocess.run(
    ["grep", "cpp"], input=find_result.stdout, stdout=subprocess.PIPE
)
grep_2_result = subprocess.run(
    ["grep", "-v", "thirdparty"], input=grep_result.stdout, stdout=subprocess.PIPE
)
grep_3_result = subprocess.run(
    ["grep", "-v", "build"], input=grep_2_result.stdout, stdout=subprocess.PIPE
)
pmc_result = subprocess.run(
    [
        "xargs",
        "pmccabe",
    ],
    input=grep_3_result.stdout,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
)
scores_list = pmc_result.stdout.decode("utf-8").split("\n")

# build  hierarchy tree
tree = package_tree()
for row in scores_list:
    if package_tree.test(row):
        tree.parse(row)

xml_tree = tree.get_xml()
print(tree.tostring(xml_tree).decode("utf-8"), file=sys.stdout)
