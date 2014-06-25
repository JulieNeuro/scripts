#!/usr/bin/env python
"""
Map reduce for parsimony.
"""

import time
import errno
import json
import sys, os, glob, argparse, re
#import warnings
import pickle
import nibabel
from multiprocessing import Process, cpu_count
import numpy as np
import pandas as pd

# Global data
DATA = dict()
param_sep = "_"

example = """
Example
-------

## Create dataset
n, p = 10, 5
X = np.random.rand(n, p)
beta = np.random.rand(p, 1)
y = np.dot(X, beta)
np.save('X.npy', X)
np.save('y.npy', y)

## Create config file
cv = [[tr.tolist(), te.tolist()] for tr,te in KFold(n, n_folds=2)]
params = [[1.0, 0.1], [1.0, 0.9], [0.1, 0.1], [0.1, 0.9]]
# enet_userfunc.py is a python file containing mapper(key, output_collector)
# and reducer(key, values) functions.

config = dict(data=dict(X="X.npy", y="y.npy"), params=params, user_func="enet_userfunc.py",
              map_output="map_results",
              resample=cv,
              ncore=2,
              reduce_input="map_results/*/*", reduce_group_by=".*/.*/(.*)")
json.dump(config, open("config.json", "w"))

"""


def load_data(key_filename):
    return {key:np.load(key_filename[key]) for key in key_filename}

_OUTPUT = 0
_PARAMS = 1
_RESAMPLE_NB = 2

def _build_job_table(options):
    params_list = json.load(open(options.params)) \
        if isinstance(options.params, str) else options.params
    jobs = [[os.path.join(options.map_output, str(resample_i),
                          param_sep.join([str(p) for p in params])),
            params,
            resample_i]
            for resample_i in xrange(len(options.resample))
            for params in params_list]
    return jobs

def _makedirs_safe(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def _import_module_from_filename(filename):
    sys.path.append(os.path.dirname(filename))
    name, _ = os.path.splitext(os.path.basename(filename))
    user_module = __import__(os.path.basename(name))
    return user_module

_import_user_func = _import_module_from_filename


class OutputCollector:
    """Map output collector

    Parameters:
    ----------
    output_dir: string output directory, where map results will be stored

    Example:
    --------
    oc = OutputCollector("/tmp/toto")
    oc.is_running()
    oc.set_running(True)
    oc.is_running()
    oc.set_running(False)
    oc.is_running()
    """
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def clean(self):
        if os.path.exists(self.output_dir) \
            and len(os.listdir(self.output_dir)) == 0:
            print "clean",self.output_dir
            os.rmdir(self.output_dir)

    def collect(self, key, value):
        _makedirs_safe(self.output_dir)
        for k in value:
            if isinstance(value[k], np.ndarray):
                np.savez_compressed(os.path.join(self.output_dir, k), value[k])
            elif isinstance(value[k], nibabel.Nifti1Image):
                value[k].to_filename(os.path.join(self.output_dir, k + ".nii"))
            else:
                try:
                    of = open(os.path.join(self.output_dir, k + ".json"), "w")
                    json.dump(value[k], of)
                    of.close()
                except:
                    of = open(os.path.join(self.output_dir, k + ".pkl"), "w")
                    pickle.dump(value[k], of)
                    of.close()

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.output_dir)

    def load(self, pattern="*"):
        res = dict()
        for filename in  glob.glob(os.path.join(self.output_dir, pattern)):
            o = None
            try:
                o = np.load(filename)['arr_0']
            except:
                try:
                    o = np.load(filename)
                except:
                    try:
                       o = json.load(open(filename, "r"))
                    except:
                        try:
                           o = pickle.load(open(filename, "r"))
                        except:
                            try:
                                o = nibabel.load(filename)
                            except:
                                pass
            if o is not None:
                name, ext = os.path.splitext(os.path.basename(filename))
                res[name] = o
        return res

output_collectors = list()
#
def clean_atexit():
    for oc in output_collectors:
        oc.clean()

import atexit
atexit.register(clean_atexit)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__, epilog=example)

    parser.add_argument('--map', action='store_true', default=False,
                        help="Run mapper: iterate over resamples and "
                        "parameters, and call mapper (defined in user_func)")

    parser.add_argument('--clean', action='store_true', default=False,
                        help="Clean execution: remove empty directories "
                        "in map_output. Use it if you suspect that some "
                        "mapper where not end not properly.")

    parser.add_argument('--reduce', action='store_true', default=False,
                        help="Run reducer: iterate over map_output and call"
                        "reduce (defined in user_func)")

    # Config file
    parser.add_argument('--config', help='Configuration json file that '
        'contains a dictionary of configuration options. There are 4 '
        'required arguments:'
        '(1) "data": (Required) dict(X="/tmp/X.npy", y="/tmp/X.npy").'
        '(2) "params":  (Required) List of list of parameters values. Ex:'
        '[[1.0, 0.1], [1.0, 0.9], [0.1, 0.1], [0.1, 0.9]]. '
        '(3) "map_output":  (Required) Mapper output root directory. '
        'Output hierarchy will be '
        'organized as follow: <map_output>/<resample_nb>/<params> and '
        ' <map_output>/0/<params> if no resampling is provided.'
        'override config options.'
        '(4) "user_func": (Required) Path to python file that contains 4 user '
        ' defined functions: '
        '(i) load_globals(config): executed ones at the beginning load all the data '
        '(ii) resample() is executed on each new reample'
        '(iii) mapper(key) is executed on each parameters x reample item'
        '(iv) reducer(key, values)'
        '"resample": (Optional) List of list of list of indices. '
        'Ex: [[[0, 2], [1, 3]], [[1, 3], [0, 2]]] for cross-validation like '
        'resampling.'
        'or list of list of indices, ex: [[0, 1, 2, 3], [1, 3, 0, 2]]. for '
        'bootstraping/permuation like resampling. '
        '"ncore", "reduce_input" and "reduce_output": see command line argument.'
        )
    default_nproc = cpu_count()
    parser.add_argument('--ncore',
        help='Nb cpu ncore to use (default %i)' % default_nproc, type=int)

    # Reducer options --------------------------------------------------------
    parser.add_argument('--reduce_input', help='Input root dir for reduce. '
        'Should match  --map_output. Required option for --mode=reduce.')
    parser.add_argument('--reduce_group_by', type=str,
                        help='Regular expression to match the grouping key. Example: MAP_OUTPUT/.*/(.*)  will group by parameters. While (MAP_OUTPUT/.*)/.* will match by resample.')
    parser.add_argument('--reduce_output', help='Reduce output, csv file.')


    options = parser.parse_args()

    if not options.config:
        print 'Required arguments --config'
        sys.exit(1)
    config = json.load(open(options.config))
    # set WD to be the dir on config file, this way all path can be relative
    os.chdir(os.path.dirname(options.config))
    for k in config:
        if not hasattr(options, k) or getattr(options, k) is None:
            setattr(options, k, config[k])

    if not hasattr(options, "resample"):
        setattr(options, "resample", None)
    if not hasattr(options, "user_func"):
        setattr(options, "user_func", None)
    if options.ncore is None:
        options.ncore = default_nproc

    # =======================================================================
    # == MAP                                                               ==
    # =======================================================================
    if options.map:
        if not options.user_func:
            print 'Required fields in config file: "user_func"'
            sys.exit(1)
        user_func = _import_user_func(options.user_func)
        ## Load globals
        user_func.load_globals(config)
        jobs = _build_job_table(options)
        print "** MAP WORKERS TO JOBS **"
        # Use this to load/slice data only once
        resamples_file_cur = resample_nb_cur = None
        data_cur = None
        workers = list()
        job_process_map = {} # This is only valid for a given machine
        for i in xrange(len(jobs)):
            # see if we can create a worker
            while len(workers) == options.ncore:
                for p in workers:
                    #print "Is alive", str(p), p.is_alive()
                    if not p.is_alive():
                        p.join()
                        workers.remove(p)
                        print "Joined:", str(p)
                time.sleep(1)
            job = jobs[i]
            try:
                os.makedirs(job[_OUTPUT])
            except:
                continue
            output_collector = OutputCollector(job[_OUTPUT])
            output_collectors.append(output_collector)
            if (not resample_nb_cur and job[_RESAMPLE_NB]) or \
               (resample_nb_cur != job[_RESAMPLE_NB]):  # Load
                resample_nb_cur = job[_RESAMPLE_NB]
                user_func.resample(config, resample_nb_cur)
            key = job[_PARAMS]
            p = Process(target=user_func.mapper, args=(key, output_collector))
            print "Start :", str(p), str(output_collector)
            p.start()
            job_process_map[p.pid] = job
            workers.append(p)

        for p in workers:  # Join remaining worker
            p.join()
            workers.remove(p)
            print "Joined:", str(p)

    if options.clean:
        jobs = _build_job_table(options)
        for i in xrange(len(jobs)):
            output_collector = OutputCollector(jobs[i][_OUTPUT])
            output_collector.clean()

    # =======================================================================
    # == REDUCE                                                            ==
    # =======================================================================
    if options.reduce:
        if not options.reduce_input:
            print 'Required arguments: --reduce_input'
            sys.exit(1)
        if not options.user_func:
            print 'Required arguments: --user_func'
            sys.exit(1)
        user_func = _import_user_func(options.user_func)
        print "** REDUCE **"
        items = glob.glob(options.reduce_input)
        items = [item for item in items if os.path.isdir(item)]
        options.reduce_group_by
        group_keys = set([re.findall(options.reduce_group_by, item)[0] for item
            in items])
        groups = {k:[] for k in group_keys}
        for item in items:
            which_group_key = [k for k in groups if re.findall(options.reduce_group_by, item)[0]==k]
            if len(which_group_key) != 1:
                raise ValueError("Many/No keys match %s" % item)
            output_collector = OutputCollector(item)
            groups[which_group_key[0]].append(output_collector)
        # Do the reduce
        scores = list()
        for k in groups:
            try:
                scores.append(user_func.reducer(key=k, values=groups[k]))
            except:
                print "Reducer failed in %s" % k
        #scores = [user_func.reducer(key=k, values=groups[k]) for k in groups]
        scores = pd.DataFrame(scores)
        print scores.to_string()
        if options.reduce_output is not None:
            scores.to_csv(options.reduce_output, index=False)
