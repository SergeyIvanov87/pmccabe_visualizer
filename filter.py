#!/usr/bin/python
import argparse
import os
import sys

from package_tree import package_tree
from xml.etree.ElementTree import ElementTree
from xml.etree import ElementTree


class attr_xml:
    def __init__(self, pmccabe_xml):
        self.packaged_tree = pmccabe_xml

    def filter_out(self, mmcc_limit, sif_limit):
        xml = self.packaged_tree

        leaf_to_remove = {}

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
            # for _, value in self.packaged_tree.nested_packages.values():
            leaf_id = elem.get("id")
            leaft_search_attr_id = './/entry[@id="{}"]'.format(leaf_id)
            leaf_node = xml.findall(leaft_search_attr_id)
            if len(leaf_node) != 1:
                raise Exeption(f"Entry with id: {leaf_id} is not unique")
            for xml_child in leaf_node[0]:
                if xml_child.tag == "mmcc":
                    mmcc = int(xml_child.text)
                    if not (mmcc >= mmcc_limit[0] and mmcc <= mmcc_limit[1]):
                        leaf_to_remove[leaf_id] = leaf_node
                if xml_child.tag == "sif":
                    sif = int(xml_child.text)
                    if not (sif >= sif_limit[0] and sif <= sif_limit[1]):
                        leaf_to_remove[leaf_id] = leaf_node

        # remove nodes
        for node_id, node in leaf_to_remove.items():
            elem_id_search = './/elem[@id="{}"]..'.format(node_id)
            parents_of_node_to_delete = xml.findall(elem_id_search)
            for p in parents_of_node_to_delete:
                node_to_delete = xml.find('.//elem[@id="{}"]'.format(node_id))
                p.remove(node_to_delete)

            parents_of_node_to_delete = xml.find('.//entry[@id="{}"]..'.format(node_id))
            node_to_delete = xml.find('.//entry[@id="{}"]'.format(node_id))
            parents_of_node_to_delete.remove(node_to_delete)

        return xml


pmccabe_tree_xml = sys.stdin.read()
xml_root = ElementTree.fromstring(pmccabe_tree_xml)

# filter out nodes
rules = {"mmcc_limit": [4, 15], "sif_limit": [2, 50]}
filter_processor = attr_xml(xml_root)
filtered_xml = filter_processor.filter_out(**rules)
print(ElementTree.tostring(filtered_xml).decode("utf-8"), file=sys.stdout)
