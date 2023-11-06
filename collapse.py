#!/usr/bin/python

import argparse
import os
import sys

from package_tree import package_tree
from xml.etree.ElementTree import ElementTree
from xml.etree import ElementTree


class stack_collapse:
    def __init__(self, p_tree):
        self.packaged_tree = p_tree

    def collapse(self, param_pos, outputfile=sys.stdout):
        xml = self.packaged_tree
        main_package = xml.findall("entry")
        if len(main_package) != 1:
            raise Exception(
                f"Only 1 main package `etry` element is expected in pmccabe xml"
            )
        main_package_params = main_package[0].findall("params")
        if len(main_package_params) != 1:
            raise Exception(
                f"Only 1 main package `params` element is expected in pmccabe xml"
            )

        for elem in main_package_params[0]:
            leaf_id = elem.get("id")
            leaft_search_attr_id = './/entry[@id="{}"]'.format(leaf_id)
            leaf_node = xml.findall(leaft_search_attr_id)
            if len(leaf_node) != 1:
                raise Exeption(f"Entry with id: {leaf_id} is not unique")
            for xml_child in leaf_node[0]:
                if xml_child.tag == "mmcc":
                    mmcc = xml_child.text
                if xml_child.tag == "path":
                    path = xml_child.text
                    full_path = path.split("(")[0]
                    full_path = (
                        full_path.replace(os.sep, ";")
                        + ";"
                        + leaf_node[0].get("item")
                        + " "
                        + mmcc
                    )
                    # output.write(full_path + "\n")
                    print(full_path, file=outputfile)


pmccabe_tree_xml = sys.stdin.read()
xml_root = ElementTree.fromstring(pmccabe_tree_xml)

processor = stack_collapse(xml_root)
filtered_xml = processor.collapse(0, sys.stdout)
