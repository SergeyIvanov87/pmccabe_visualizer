#!/usr/bin/python

import argparse
import os
import subprocess
import sys
import xml.etree.cElementTree as ET
from collections import defaultdict
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment, tostring

import package_tree

def add_limits_from_args(arg_limit_value, arg_name, storage, sep=','):
    if arg_limit_value:
        vals = arg_limit_value.split(sep)
        if len(vals) not in [1,2]:
            raise Exception(f"{arg_name} values must be a sequence of 2 values separated by '{sep}' or single value representing a bottom limit")
        if len(vals) == 1:
            vals.append("")
        storage[arg_name] = [int(v) if str.isdecimal(v) else None for v in vals]

parser = argparse.ArgumentParser(
    prog="PMCCabe package tree builder",
    description="Consume output of `pmccabe` utility and build its tree representation for further processing and analysis"
)

parser.add_argument("-mmcc", "--mmcc_range", help="Process MMCC matched this range of values. Example: -mmcc 1,90. No limit applied by default")
parser.add_argument("-tmcc", "--tmcc_range", help="Process TMCC matched this range of values. Example: -tmcc 1,90. No limit applied by default")
parser.add_argument("-sif", "--sif_range", help="Process SIF matched this range of values. Example: -sif 1,90. No limit applied by default")
parser.add_argument("-lif", "--lif_range", help="Process LIF matched this range of values. Example: -lif 1,90. No limit applied by default")
args = parser.parse_args()

limits = {}
add_limits_from_args(args.mmcc_range, "mmcc", limits, ',')
add_limits_from_args(args.tmcc_range, "tmcc", limits, ',')
add_limits_from_args(args.sif_range, "sif", limits, ',')
add_limits_from_args(args.lif_range, "lif", limits, ',')

files_to_check = sys.stdin.read()
pmc_result = subprocess.run(
    [
        "xargs",
        "pmccabe",
    ],
    input=files_to_check.encode('utf-8'),
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
)
scores_list = pmc_result.stdout.decode("utf-8").split("\n")

# build  hierarchy tree
tree = package_tree.package_tree()
for row in scores_list:
    if package_tree.package_tree.test(row,**limits):
        tree.parse(row)

xml_tree = tree.get_xml()
print(tree.tostring(xml_tree).decode("utf-8"), file=sys.stdout)
