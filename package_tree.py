import os

import xml.etree.cElementTree as ET

from collections import defaultdict
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment, tostring


NODE_IDS = [0, 1, 2]
NODE_NAMES = ["package", "file", "item"]


def extract_package_name(package):
    return package.split("(")[0]


def build_child_pmccabe_attrite(pmccabe_attr):
    packages = pmccabe_attr[5].split(os.sep)
    child_package_name = extract_package_name(packages[1])

    # build new attributes cutting out the element by index 0 in packages list
    mod_pmccabe_attrs = pmccabe_attr.copy()
    mod_pmccabe_attrs[5] = str(os.sep).join(packages[1:])

    child_package_type = NODE_IDS[0] if len(packages) > 2 else NODE_IDS[1]
    return mod_pmccabe_attrs, child_package_name, child_package_type


def build_leaf_pmccabe_attrite(pmccabe_attr):
    file_n_line = pmccabe_attr[5].split(os.sep)[0].split("(")
    function_name = pmccabe_attr[6] + "(" + file_n_line[1]
    file_name = file_n_line[0]

    return pmccabe_attr, file_name, function_name, NODE_IDS[2]


class basic_node:
    """Class just owns the common node members and provide the minimal initialization support"""

    def __init__(self):
        self.type_id = -1
        self.node_id = -1
        self.package_name = None

    def fill(self, type_id, node_id, package):
        if self.type_id == -1:
            self.type_id = type_id
        if self.node_id == -1:
            node_id += 1  # obtain next vacant id, if our node is not initialized yet
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
    """
    Class represents an intermediate node 'package', which holds a subsequent nodes
    and stores information about all descendant leaf nodes as well as all its attributes,
    like mmcc, tmcc, sif. Having stored it in that way, allows us to add up feeds
    for analytics claculation: like a mean, median and distribution as a property of
    this particular `package` for further processing through.
    Also, it makes node folding more easily

    Must contains other 'package' nodes and 'file' nodes only
    """

    def __init__(self):
        super().__init__()

        self.params = defaultdict(tuple)
        self.nested_packages = {}

    def fill_child_data(self, child_node_id, inserted_leaf_node_id, pmccabe_attrs):
        (mmcc, tmcc, sif, _, _, item_file_path, _) = pmccabe_attrs

        package_name = item_file_path.split(os.sep)[0]
        last_node_id = super().fill(NODE_IDS[0], child_node_id, package_name)

        # inserted_leaf_node_id is unique
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

        for _, elem in self.nested_packages.values():
            elem.dump_xml(entry)
        return entry


class file_node(package_node):
    """
    Class represents an aggregation node (file) for functions (entities).
    It repeat after 'package' mostly, but cares more about file and child function extraction

    Must contains 'item' nodes only
    """

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
    """
    Leaf node in the hierarchy representing a called function
    """

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
    """
    Holder of parsing hierarchy
    """

    def __init__(self):
        self.nested_packages = {}
        self.node_id_counter = 0

    @staticmethod
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

    def tostring(self, tree_xml):
        return tostring(tree_xml.getroot(), encoding="utf-8", method="xml")