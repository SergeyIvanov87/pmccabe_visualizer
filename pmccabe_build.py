#!/usr/bin/python

import argparse
import subprocess
import sys

from argparse import RawTextHelpFormatter

import common_help
import package_tree


def add_limits_from_args(arg_limit_value, arg_name, storage, sep=","):
    if arg_limit_value:
        vals = arg_limit_value.split(sep)
        if len(vals) not in [1, 2]:
            raise Exception(
                f"{arg_name} values must be a sequence of 2 values separated by '{sep}' or single value representing a bottom limit"
            )
        if len(vals) == 1:
            vals.append("")
        storage[arg_name] = [int(v) if str.isdecimal(v) else None for v in vals]


parser = argparse.ArgumentParser(
    formatter_class=RawTextHelpFormatter,
    prog="PMCCabe package tree builder",
    description="Consume output of `pmccabe` utility and build its tree representation for further processing and analysis",
    epilog=common_help.PMCCABE_PARAMS_DESCR,
)


parser.add_argument(
    "-mmcc",
    "--mmcc_range",
    default=common_help.mmcc_range_default,
    help='Process "mmcc" matched this range of values. Example: "-mmcc 10,9999999" or "-mmcc 10".\nDefault: \"{}\"'.format(
        common_help.mmcc_range_default
    ),
)


parser.add_argument(
    "-tmcc",
    "--tmcc_range",
    help='Process "tmcc" matched this range of values. Example: "-tmcc 2,999" or "-tmcc 2".\nDefault: \"{}\"'.format(
        common_help.tmcc_range_default
    ),
    default=common_help.tmcc_range_default,
)

parser.add_argument(
    "-sif",
    "--sif_range",
    help='Process "sif" matched this range of values. Example: "-sif 5,90" or "-sif 5".\nDefault: \"{}\"'.format(
        common_help.sif_range_default
    ),
    default=common_help.sif_range_default,
)

parser.add_argument(
    "-lif",
    "--lif_range",
    help='Process "lif" matched this range of values. Example: "-lif 500,900" or "-lif 500".\nDefault: \"{}\"'.format(
        common_help.lif_range_default
    ),
    default=common_help.lif_range_default,
)
args = parser.parse_args()

limits = {}
add_limits_from_args(args.mmcc_range, "mmcc", limits, ",")
add_limits_from_args(args.tmcc_range, "tmcc", limits, ",")
add_limits_from_args(args.sif_range, "sif", limits, ",")
add_limits_from_args(args.lif_range, "lif", limits, ",")

files_to_check = sys.stdin.read()
pmc_result = subprocess.run(
    [
        "xargs",
        "pmccabe",
    ],
    input=files_to_check.encode("utf-8"),
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
)
scores_list = pmc_result.stdout.decode("utf-8").split("\n")

# build  hierarchy tree
tree = package_tree.package_tree()
for row in scores_list:
    if package_tree.package_tree.test(row, **limits):
        tree.parse(row)

tree.calculate_statistic()
xml_tree = tree.get_xml()
print(tree.tostring(xml_tree).decode("utf-8"), file=sys.stdout)
