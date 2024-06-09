#!/usr/bin/python

import argparse
import os
import sys

import common_help

from argparse import RawTextHelpFormatter
from collections import defaultdict
from package_tree import package_tree
from xml.etree.ElementTree import ElementTree
from xml.etree import ElementTree


class stack_collapse:
    def __init__(self, p_tree):
        self.packaged_tree = p_tree

    def collapse(self, attribute_names, outputfile=sys.stdout):
        xml = self.packaged_tree
        main_package = xml.findall("entry")
        if len(main_package) != 1:
            raise Exception(
                f"Only 1 main package `entry` element is expected in pmccabe xml"
            )
        main_package_params = main_package[0].findall("params")
        if len(main_package_params) != 1:
            raise Exception(
                f"Only 1 main package `params` element is expected in pmccabe xml"
            )

        attr_value = defaultdict(int)
        for elem in main_package_params[0]:
            leaf_id = elem.get("id")
            leaft_search_attr_id = './/entry[@id="{}"]'.format(leaf_id)
            leaf_node = xml.findall(leaft_search_attr_id)
            if len(leaf_node) != 1:
                raise Exeption(f"Entry with id: {leaf_id} is not unique")
            function_name = leaf_node[0].get("item")
            for xml_child in leaf_node[0]:
                if xml_child.tag in attribute_names:
                    attr_value[xml_child.tag] = xml_child.text
                if xml_child.tag == "path":
                    path = xml_child.text
                    full_path = path.split("(")[0]
                    full_path = (
                            full_path.replace(os.sep, ";")
                            + ";"
                            + function_name
                            )
                    for attr_name in attribute_names:
                        print(full_path + ";" + "<<" + attr_name.upper() + ">> " + attr_value[attr_name], file=outputfile)


supported_attributes = ["mmcc", "tmcc", "sif", "lif"]

parser = argparse.ArgumentParser(
    formatter_class=RawTextHelpFormatter,
    prog="Stack collapsing for PMCCabe package tree builder",
    description="Consumes output of `pmccabe_build` utility and unfold the tree representation into plain stack by an leaf node attribute, thereby preparing it for crafting a FlameGraph.",
    epilog=common_help.PMCCABE_PARAMS_DESCR
)

parser.add_argument(
    "-attr", "--attributes",
    default=",".join(supported_attributes),
    help="Choose attributes: \"{}\" - which will be used as a final metric in a collapsed stack for crafting a FlameGraph.\nDefault: \"{}\"".format(
        "\",\"".join(supported_attributes), ",".join(supported_attributes))
)

args = parser.parse_args()

input_attributes = args.attributes.split(',')
for input_attr in input_attributes:
    if input_attr not in supported_attributes:
        raise Exception(
            'Entered attributes value: "{}" are not supported. Available attributes are: {}'.format(
                args.attributes, ",".join(supported_attributes)
            )
        )

pmccabe_tree_xml = sys.stdin.read()
if len(list(xml_root))==0:
    sys.stdout.write("")
    exit(0)

xml_root = ElementTree.fromstring(pmccabe_tree_xml)
if len(list(xml_root))==0:
    sys.stdout.write("")
    exit(0)

processor = stack_collapse(xml_root)
filtered_xml = processor.collapse(input_attributes, sys.stdout)
