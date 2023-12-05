import os
from operator import sub
from operator import add
import sys
import xml.etree.cElementTree as ET

from collections import defaultdict
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment, tostring

from math import sqrt

NODE_IDS = [0, 1, 2]
NODE_NAMES = ["package", "file", "item"]


def extract_package_name(package):
    return package.split("(")[0]


def check_integer_limit(val, min_max_limit):
    passed = True
    val = int(val)
    if min_max_limit is not None:
        passed = False if val < min_max_limit[0] else passed
        # if mmcc[1] is not None:
        passed = (
            False
            if (min_max_limit[1] is not None) and (val > min_max_limit[1])
            else passed
        )
    return passed


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
        self.mean = ()
        self.median = ()
        self.deviation = ()

    def set_params_for_node(self, node_name, pmccabe_attrs):
        mmcc = int(pmccabe_attrs[0])
        tmcc = int(pmccabe_attrs[1])
        sif = int(pmccabe_attrs[2])
        lif = int(pmccabe_attrs[4])
        self.params[node_name] = (mmcc, tmcc, sif, lif)

    def fill_child_data(self, child_node_id, inserted_leaf_node_id, pmccabe_attrs):
        item_file_path = pmccabe_attrs[5]
        package_name = item_file_path.split(os.sep)[0]
        last_node_id = super().fill(NODE_IDS[0], child_node_id, package_name)

        self.set_params_for_node(inserted_leaf_node_id, pmccabe_attrs)
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

    def calculate_statistic(self):
        N = len(self.params)
        if N == 0:
            return

        any_param = list(self.params.values())[0]
        param_len = len(any_param)
        median_array = tuple([] for _ in range(param_len))
        mean = tuple(0 for _ in range(param_len))

        for items in self.params.values():
            mean = tuple(map(add, mean, items))
            for i in range(0, param_len):
                median_array[i].append(items[i])

        self.mean = tuple(int(m / N) for m in mean)

        for i in range(0, param_len):
            median_array[i].sort()
        # find median element
        if N % 2:
            self.median = tuple(
                median_array[i][int(N / 2)] for i in range(0, param_len)
            )
        else:
            self.median = tuple(
                int((median_array[i][int(N / 2) - 1] + median_array[i][int(N / 2)]) / 2)
                for i in range(0, param_len)
            )

        deviation = tuple(0 for _ in range(param_len))
        for items in self.params.values():
            mean_diff = tuple(map(sub, self.mean, items))
            mean_diff_squarer = [pow(m, 2) for m in mean_diff]
            deviation = tuple(map(add, deviation, mean_diff_squarer))
        self.deviation = tuple(int(sqrt(d / N)) for d in deviation)

        # repeat recursive
        for t, child in self.nested_packages.values():
            if t in NODE_IDS[0:2]:
                child.calculate_statistic()

    def dump_statistic_xml(self, entry):
        stat = ET.SubElement(entry, "statistic")
        ET.SubElement(stat, "mean").text = str(self.mean)
        ET.SubElement(stat, "median").text = str(self.median)
        ET.SubElement(stat, "deviation").text = str(self.deviation)

    def dump_xml(self, parent):
        entry = super().dump_xml(parent)
        array = ET.SubElement(entry, "params")
        for child_id, items in self.params.items():
            elem = ET.SubElement(array, "elem", id=str(child_id), params=str(items))

        self.dump_statistic_xml(entry)

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

    def fill_child_data(self, child_node_id, filename, pmccabe_attrs):
        last_node_id = super().fill(NODE_IDS[1], child_node_id, filename)

        self.set_params_for_node(child_node_id, pmccabe_attrs)
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
            self.fill_child_data(inserted_child_node_id, file_name, pmccabe_attrs),
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

        self.mmcc += int(pmccabe_attrs[0])
        self.tmcc += int(pmccabe_attrs[1])
        self.sif += int(pmccabe_attrs[2])
        self.flf += int(pmccabe_attrs[3])
        self.lif += int(pmccabe_attrs[4])
        self.full_path = full_path

        last_occupied_node_id = super().fill(
            NODE_IDS[2], candidate_node_id, pmccabe_attrs[6] + ":" + str(self.flf)
        )
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
    def test(row, mmcc=None, tmcc=None, sif=None, lif=None):
        passed = False
        pmccabe_attrs = row.split()
        if len(pmccabe_attrs) > 5:
            mmcc_v = pmccabe_attrs[0]
            tmcc_v = pmccabe_attrs[1]
            sif_v = pmccabe_attrs[2]
            lif_v = pmccabe_attrs[4]
            if len(pmccabe_attrs) < 7:
                print(f"Unrecognized row format: {row}\n7 attributes expected at least", file=sys.stderr)
                return False

            passed = check_integer_limit(mmcc_v, mmcc)
            passed = passed and check_integer_limit(tmcc_v, tmcc)
            passed = passed and check_integer_limit(sif_v, sif)
            passed = passed and check_integer_limit(lif_v, lif)
        return passed

    def parse(self, row):
        pmccabe_attrs = row.split()
        package_names = pmccabe_attrs[5].split(os.sep)

        # empty node cause error in flamegraph generation and anyway makes no sense
        # remove it
        if package_names[0] == "":
            package_names = package_names[1:]
            pmccabe_attrs[5] = os.sep.join(package_names)
            row = " ".join(pmccabe_attrs)
        main_package = package_names[0]
        if main_package not in self.nested_packages.keys():
            self.nested_packages[main_package] = (
                NODE_IDS[0],
                node_factory(NODE_IDS[0]),
            )

        self.node_id_counter, _ = self.nested_packages[main_package][1].parse_node(
            row, pmccabe_attrs[5], self.node_id_counter
        )

    def calculate_statistic(self):
        for main_package in self.nested_packages.values():
            main_package[1].calculate_statistic()

    def get_xml(self):
        root = ET.Element("root")
        for _, p in self.nested_packages.values():
            p.dump_xml(root)
        return ET.ElementTree(root)

    def tostring(self, tree_xml):
        return tostring(tree_xml.getroot(), encoding="utf-8", method="xml")
