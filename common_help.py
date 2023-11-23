#!/usr/bin/python


PMCCABE_PARAMS_DESCR ='\n'.join(["Parameters value description (see `man pmccabe`):",
                     "\tmmcc\t\tModified McCabe Cyclomatic Complexity",
                     "\ttmcc\t\tTraditional McCabe Cyclomatic Complexity",
                     "\tsif\t\t# Statements in function",
                     "\tlif\t\t# lines in function"])

mmcc_range_default = "1,"
tmcc_range_default = "1,"
sif_range_default = "1,"
lif_range_default = "1,"
