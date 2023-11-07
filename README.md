# pmccabe C/C++ visualizer
Capture the output of  `pmccabe` UNIX utility used for calculating cyclomatic complexity of C/C++ code, transform it in a more representative format for further investigation.
If you know about Flame Graphs (https://www.brendangregg.com/flamegraphs.html) and prefer that representation then you can fold an output of this pmccabe builder into collapsed list, which is suitable for `flamegraph.pl` (https://github.com/brendangregg/FlameGraph#3-flamegraphpl). Having `flamegraph.pl` invoked, you can an SVG file representing Flame Graph of McCabe complexity of code in a project.

The **pmccabe_visualizer** is supposed to be the simplest as possible and fit KISS (Keep-It-Simple-Stupid) concept, thus it doesn't use much complicated configuration routines and stick to pipelining STDIN/OUT processing.
All you need is just supplement the main script `pmccabe_build.py` by files list belonged to your C/C++ project as STDIN, determine filtering conditions (excluding the functions with simplest cyclomatic complexisty, for example) then redicrect STDOUT  into desired destination.

**Example**:

```
clear && find <my-project-path> -regex ".*\.\(hpp\|cpp\|c\|h\)" | grep -v "build" | grep -v "thirdparty" | ./pmccabe_build.py | ./collapse.py | <FlameGraph-Repo>/flamegraph.pl > project.svg
```
