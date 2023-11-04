#!/usr/bin/python

import argparse
import os
import subprocess
import xml.etree.cElementTree as ET

from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment, tostring

NODE_IDS = [0, 1, 2]
NODE_NAMES = ["package", "file", "item"]


def extract_package_name(package):
    return package.split("(")[0]


def build_child_pmccabe_attrite(pmccabe_attr):
    packages = pmccabe_attr[5].split(os.sep)
    package_name = packages[0]
    child_package_name = extract_package_name(packages[1])

    child_packages = str(os.sep).join(packages[1:])

    mod_pmccabe_attrs = pmccabe_attr.copy()
    mod_pmccabe_attrs[5] = child_packages

    next_package_id = NODE_IDS[0] if len(packages) > 2 else NODE_IDS[1]
    return mod_pmccabe_attrs, child_package_name, next_package_id


def build_leaf_pmccabe_attrite(pmccabe_attr):
    file_n_line = pmccabe_attr[5].split(os.sep)[0].split("(")
    function_name = pmccabe_attr[6] + "(" + file_n_line[1]
    file_name = file_n_line[0]

    return pmccabe_attr, file_name, function_name, NODE_IDS[2]


class basic_node:
    def __init__(self):
        self.type_id = -1
        self.node_id = -1
        self.package_name = None

    def fill(self, type_id, node_id, package):
        if self.type_id == -1:
            self.type_id = type_id
        if self.node_id == -1:
            node_id += 1  # obtain next vacant id, if our node id is empty
            self.node_id = node_id
        if self.package_name is None:
            self.package_name = package
        return node_id

    def dump_xml(self, parent):
        entry = ET.SubElement(parent, "entry")
        entry.set("id", str(self.node_id))
        entry.set(NODE_NAMES[self.type_id], self.package_name)
        return entry


class package_node(basic_node):
    def __init__(self):
        super().__init__()

        self.params = dict()
        self.nested_packages = dict()

    def fill_child_data(self, child_node_id, inserted_leaf_node_id, pmccabe_attrs):
        (mmcc, tmcc, sif, _, _, item_file_path, _) = pmccabe_attrs

        package_name = item_file_path.split(os.sep)[0]
        last_node_id = super().fill(NODE_IDS[0], child_node_id, package_name)
        if inserted_leaf_node_id not in self.params.keys():
            self.params[inserted_leaf_node_id] = ()
        self.params[inserted_leaf_node_id] = (mmcc, tmcc, sif)

        return last_node_id

    def parse_node(self, raw_data, full_path, next_node_id=0):
        pmccabe_attrs = raw_data.split()
        (
            mod_pmccabe_attrs,
            child_package_name,
            child_type_id,
        ) = build_child_pmccabe_attrite(pmccabe_attrs)

        if child_package_name not in self.nested_packages.keys():
            self.nested_packages[child_package_name] = (
                child_type_id,
                node_factory(child_type_id),
            )
        child_node_id, inserted_leaf_node_id = self.nested_packages[child_package_name][
            1
        ].parse_node(" ".join(mod_pmccabe_attrs), full_path, next_node_id)

        return (
            self.fill_child_data(child_node_id, inserted_leaf_node_id, pmccabe_attrs),
            inserted_leaf_node_id,
        )

    def dump_xml(self, parent):
        entry = super().dump_xml(parent)
        array = ET.SubElement(entry, "params")
        for child_id, items in self.params.items():
            elem = ET.SubElement(array, "elem", id=str(child_id), params=str(items))
        #            ET.SubElement(array, "id").text = str(child_id)
        #           ET.SubElement(array, "val").text = str(mmcc)

        for id, elem in self.nested_packages.values():
            elem.dump_xml(entry)
        return entry


class file_node(package_node):
    def __init__(self):
        super().__init__()
        self.full_path = ""

    def fill_child_data(self, child_node_id, pmccabe_attrs, filename):
        (mmcc, tmcc, sif, _, _, _, _) = pmccabe_attrs
        last_node_id = super().fill(NODE_IDS[1], child_node_id, filename)
        if child_node_id not in self.params.keys():
            self.params[child_node_id] = ()
        self.params[child_node_id] = (mmcc, tmcc, sif)

        return last_node_id

    def parse_node(self, raw_data, full_path, next_node_id):
        pmccabe_attrs = raw_data.split()
        (
            mod_pmccabe_attrs,
            file_name,
            function_name,
            child_type_id,
        ) = build_leaf_pmccabe_attrite(pmccabe_attrs)

        if function_name not in self.nested_packages.keys():
            self.nested_packages[function_name] = (
                child_type_id,
                node_factory(child_type_id),
            )

        inserted_child_node_id = self.nested_packages[function_name][1].parse_node(
            " ".join(mod_pmccabe_attrs), full_path, next_node_id
        )

        return (
            self.fill_child_data(inserted_child_node_id, pmccabe_attrs, file_name),
            inserted_child_node_id,
        )

    def dump_xml(self, parent):
        entry = super().dump_xml(parent)
        ET.SubElement(entry, "path").text = str(self.full_path)
        return entry


class item_node(basic_node):
    def __init__(self):
        super().__init__()
        self.mmcc = 0
        self.tmcc = 0
        self.sif = 0
        self.flf = 0
        self.lif = 0
        self.full_path = ""

    def parse_node(self, raw_data, full_path, candidate_node_id):
        pmccabe_attrs = raw_data.split()

        last_occupied_node_id = super().fill(
            NODE_IDS[2], candidate_node_id, pmccabe_attrs[6]
        )
        self.mmcc += int(pmccabe_attrs[0])
        self.tmcc += int(pmccabe_attrs[1])
        self.sif += int(pmccabe_attrs[2])
        self.flf += int(pmccabe_attrs[3])
        self.lif += int(pmccabe_attrs[4])
        self.full_path = full_path
        return last_occupied_node_id

    def dump_xml(self, parent):
        entry = super().dump_xml(parent)
        ET.SubElement(entry, "mmcc").text = str(self.mmcc)
        ET.SubElement(entry, "tmcc").text = str(self.tmcc)
        ET.SubElement(entry, "sif").text = str(self.sif)
        ET.SubElement(entry, "flf").text = str(self.flf)
        ET.SubElement(entry, "lif").text = str(self.lif)
        ET.SubElement(entry, "path").text = str(self.full_path)
        return entry


def node_factory(type_id):
    if type_id == NODE_IDS[0]:
        return package_node()
    if type_id == NODE_IDS[1]:
        return file_node()
    return item_node()


class package_tree:
    def __init__(self):
        self.nested_packages = dict()
        self.node_id_counter = 0

    def test(row):
        return len(row.split()) != 0

    def parse(self, row):
        pmccabe_attrs = row.split()
        package_names = pmccabe_attrs[5].split(os.sep)

        main_package = package_names[0]
        if main_package not in self.nested_packages.keys():
            self.nested_packages[main_package] = (
                NODE_IDS[0],
                node_factory(NODE_IDS[0]),
            )

        self.node_id_counter, _ = self.nested_packages[main_package][1].parse_node(
            row, pmccabe_attrs[5], self.node_id_counter
        )

    def get_xml(self):
        root = ET.Element("root")
        for t, p in self.nested_packages.values():
            p.dump_xml(root)
        return ET.ElementTree(root)

    def dump_xml(self, tree_xml, filename):
        tree_xml.write(filename)


class attr_xml:
    def __init__(self, p_tree):
        self.packaged_tree = p_tree

    def colorize(self, mmcc, sif):
        self.mmcc, self.sif = rules

        xml = self.packaged_tree.get_xml()
        search_attr = './/entry[@type="{}"]'.format(NODE_NAMES[2])
        elems = xml.findall(search_attr)


class stack_collapse:
    def __init__(self, p_tree):
        self.packaged_tree = p_tree

    def collapse(self, param_pos, outputfile):
        self.param_pos = param_pos
        with open("outputfile", "w") as output:
            xml = self.packaged_tree.get_xml()
            for name, value in self.packaged_tree.nested_packages.values():
                for leaf_id in value.params.keys():
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
                            output.write(full_path + "\n")


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

tree = package_tree()
for row in scores_list:
    if package_tree.test(row):
        tree.parse(row)

# rules = {"mmcc": 15, "sif": 50}
# xml = attr_xml(tree)
# xml.colorize(**rules)
c = stack_collapse(tree)
c.collapse(0, "collapsed")
# xml_tree = tree.get_xml()
# tree.dump_xml(xml_tree, "filename_3.xml")
