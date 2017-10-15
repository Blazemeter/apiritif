"""
destination file format - how to work in functional (LDJSON) vs performance mode (CSV? JTL?)
logging approach - is STDOUT/STDERR enough? how to minimize files written?

apiritif-loadgen CLI utility
    spawns workers, spreads them over time
    if concurrency < CPU_count: workers=concurrency else workers=CPU_count
    distribute load among them equally +-1
    smart delay of subprocess startup to spread ramp-up gracefully
    overwatch workers, kill them when terminated
    accept params:
        concurrency - default 1
        iterations - by default infinite (or 1?)
        ramp-up and steps
        hold-for time
        destination file pattern

apiritif-loadgen-worker CLI utility
    creates concurrent threads running nosetests (is nose able to run multithreaded at all?)
    performs ramp-up of threads (with steps if needed)
    accepts params:
        concurrency - default 1
        iterations - by default infinite (or 1?)
        ramp-up and steps
        hold-for time
        destination file - (not pattern!)
        sequential ID and total process count - for scripts to know, can be env var

nosetests plugin (might be part of worker)

"""
