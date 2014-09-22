# -*- coding: utf-8 -*-
"""
Created on Wed May 28 12:08:39 2014

@author: md238665

Process Olivetti datasets with standard PCA, sklearn SparsePCA and our
structured PCA.
We use several values for global penalization, TV ratio and L1 ratio.

We generate a map_reduce configuration file and the files needed to run on the
cluster.

The output directory is results.

This file was copied from scripts/2014_pca_struct/mescog/01_all_models.py.

"""

import os
import json
import time

from itertools import product
from collections import OrderedDict

import numpy as np
import scipy

import sklearn.decomposition
from sklearn.cross_validation import StratifiedKFold

import parsimony.functions.nesterov.tv
import pca_tv
import metrics

import brainomics.cluster_gabriel as clust_utils

##################
# Input & output #
##################

INPUT_DIR = "/neurospin/brainomics/2014_pca_struct/Olivetti_faces"

INPUT_DATASET = os.path.join(INPUT_DIR,
                             "X.npy")
INPUT_TARGET = os.path.join(INPUT_DIR,
                            "y.npy")

OUTPUT_DIR = os.path.join("/neurospin", "brainomics",
                          "2014_pca_struct", "Olivetti_faces")

##############
# Parameters #
##############

RANDOM_STATE = 13031981
N_FOLDS = 2

# Real shape of images
INPUT_SHAPE = (64, 64)

N_COMP = 3
# Global penalty
GLOBAL_PENALTIES = np.array([1e-3, 1e-2, 1e-1, 1])
# Relative penalties
# 0.33 ensures that there is a case with TV = L1 = L2
TVRATIO = np.array([1, 0.5, 0.33, 1e-1, 1e-2, 1e-3, 0])
L1RATIO = np.array([1, 0.5, 1e-1, 1e-2, 1e-3, 0])

PCA_PARAMS = [('pca', 0.0, 0.0, 0.0)]
SPARSE_PCA_PARAMS = list(product(['sparse_pca'],
                                 GLOBAL_PENALTIES,
                                 [0.0],
                                 [1.0]))
STRUCT_PCA_PARAMS = list(product(['struct_pca'],
                                 GLOBAL_PENALTIES,
                                 TVRATIO,
                                 L1RATIO))

PARAMS = PCA_PARAMS + SPARSE_PCA_PARAMS + STRUCT_PCA_PARAMS

#############
# Functions #
#############


def load_globals(config):
    import mapreduce as GLOBAL
    Atv, n_compacts = parsimony.functions.nesterov.tv.A_from_shape(
                                                        config['image_size'])
    GLOBAL.Atv = Atv


def resample(config, resample_nb):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])
    resample = config["resample"][resample_nb]
    GLOBAL.DATA_RESAMPLED = {k: [GLOBAL.DATA[k][idx, ...] for idx in resample]
                            for k in GLOBAL.DATA}


def mapper(key, output_collector):
    import mapreduce as GLOBAL  # access to global variables:
    # GLOBAL.DATA
    # GLOBAL.DATA ::= {"X":[Xtrain, ytrain], "y":[Xtest, ytest]}
    # key: list of parameters
    model_name, global_pen, tv_ratio, l1_ratio = key
    if model_name == 'pca':
        # Force the key
        global_pen = tv_ratio = l1_ratio = 0
    if model_name == 'sparse_pca':
        # Force the key
        tv_ratio = 0
        l1_ratio = 1
        ll1 = global_pen
    if model_name == 'struct_pca':
        ltv = global_pen * tv_ratio
        ll1 = l1_ratio * global_pen * (1 - ltv)
        ll2 = (1 - l1_ratio) * global_pen * (1 - tv_ratio)

    X_train = GLOBAL.DATA_RESAMPLED["X"][0]
    n, p = X_train.shape
    X_test = GLOBAL.DATA_RESAMPLED["X"][1]

    # A matrices
    Atv = GLOBAL.Atv
    Al1 = scipy.sparse.eye(p, p)

    # Fit model
    if model_name == 'pca':
        model = sklearn.decomposition.PCA(n_components=N_COMP)
    if model_name == 'sparse_pca':
        model = sklearn.decomposition.SparsePCA(n_components=N_COMP,
                                                alpha=ll1)
    if model_name == 'struct_pca':
        model = pca_tv.PCA_SmoothedL1_L2_TV(n_components=N_COMP,
                                            l1=ll1, l2=ll2, ltv=ltv,
                                            Atv=Atv,
                                            Al1=Al1,
                                            criterion="frobenius",
                                            eps=1e-6,
                                            max_iter=100,
                                            inner_max_iter=int(1e4),
                                            output=False)
    t0 = time.clock()
    model.fit(X_train)
    t1 = time.clock()
    _time = t1 - t0
    #print "X_test", GLOBAL.DATA["X"][1].shape

    # Save the projectors
    if (model_name == 'pca') or (model_name == 'sparse_pca'):
        V = model.components_.T
    if model_name == 'struct_pca':
        V = model.V

    # Project train & test data
    if (model_name == 'pca') or (model_name == 'sparse_pca'):
        X_train_transform = model.transform(X_train)
        X_test_transform = model.transform(X_test)
    if (model_name == 'struct_pca'):
        X_train_transform, _ = model.transform(X_train)
        X_test_transform, _ = model.transform(X_test)

    # Reconstruct train & test data
    # For SparsePCA or PCA, the formula is: UV^t (U is given by transform)
    # For StructPCA this is implemented in the predict method (which uses
    # transform)
    if (model_name == 'pca') or (model_name == 'sparse_pca'):
        X_train_predict = np.dot(X_train_transform, V.T)
        X_test_predict = np.dot(X_test_transform, V.T)
    if (model_name == 'struct_pca'):
        X_train_predict = model.predict(X_train)
        X_test_predict = model.predict(X_test)

    # Compute Frobenius norm between original and recontructed datasets
    frobenius_train = np.linalg.norm(X_train - X_train_predict, 'fro')
    frobenius_test = np.linalg.norm(X_test - X_test_predict, 'fro')

    # Compute explained variance ratio
    evr_train = metrics.adjusted_explained_variance(X_train_transform)
    evr_train /= np.var(X_train, axis=0).sum()
    evr_test = metrics.adjusted_explained_variance(X_test_transform)
    evr_test /= np.var(X_test, axis=0).sum()

    # Remove predicted values (they are huge)
    del X_train_predict, X_test_predict

    # Compute geometric metrics and norms of components
    TV = parsimony.functions.nesterov.tv.TotalVariation(1, A=Atv)
    l0 = np.zeros((N_COMP,))
    l1 = np.zeros((N_COMP,))
    l2 = np.zeros((N_COMP,))
    tv = np.zeros((N_COMP,))
    for i in range(N_COMP):
        # Norms
        l0[i] = np.linalg.norm(V[:, i], 0)
        l1[i] = np.linalg.norm(V[:, i], 1)
        l2[i] = np.linalg.norm(V[:, i], 2)
        tv[i] = TV.f(V[:, i])

    ret = dict(frobenius_train=frobenius_train,
               frobenius_test=frobenius_test,
               components=V,
               X_train_transform=X_train_transform,
               X_test_transform=X_test_transform,
               evr_train=evr_train,
               evr_test=evr_test,
               l0=l0,
               l1=l1,
               l2=l2,
               tv=tv,
               time=_time)

    output_collector.collect(key, ret)


def reducer(key, values):
    global N_COMP
    # key : string of intermediary key
    # load return dict corresponding to mapper ouput. they need to be loaded.]
    values = [item.load() for item in values]

    comp_list = [item["components"] for item in values]
    frobenius_train = np.vstack([item["frobenius_train"] for item in values])
    frobenius_test = np.vstack([item["frobenius_test"] for item in values])
    l0 = np.vstack([item["l0"] for item in values])
    l1 = np.vstack([item["l1"] for item in values])
    l2 = np.vstack([item["l2"] for item in values])
    tv = np.vstack([item["tv"] for item in values])
    evr_train = np.vstack([item["evr_train"] for item in values])
    evr_test = np.vstack([item["evr_test"] for item in values])
    times = [item["time"] for item in values]

    # Average precision/recall across folds for each component
    av_frobenius_train = frobenius_train.mean(axis=0)
    av_frobenius_test = frobenius_test.mean(axis=0)
    av_evr_train = evr_train.mean(axis=0)
    av_evr_test = evr_test.mean(axis=0)
    av_l0 = l0.mean(axis=0)
    av_l1 = l1.mean(axis=0)
    av_l2 = l2.mean(axis=0)
    av_tv = tv.mean(axis=0)

    # Compute correlations of components between folds
    correlation = np.zeros((N_COMP,))
    comp0 = comp_list[0]
    comp1 = comp_list[1]
    for i in range(N_COMP):
        correlation[i] = metrics.abs_correlation(comp0[:, i], comp1[:, i])

    scores = OrderedDict((
        ('key', key),
        ('frobenius_train', av_frobenius_train[0]),
        ('frobenius_test', av_frobenius_test[0]),
        ('correlation_0', correlation[0]),
        ('correlation_1', correlation[1]),
        ('correlation_2', correlation[2]),
        ('correlation_mean', np.mean(correlation)),
        ('evr_train_0', av_evr_train[0]),
        ('evr_train_1', av_evr_train[1]),
        ('evr_train_2', av_evr_train[2]),
        ('evr_test_0', av_evr_test[0]),
        ('evr_test_1', av_evr_test[1]),
        ('evr_test_2', av_evr_test[2]),
        ('l0_0', av_l0[0]),
        ('l0_1', av_l0[1]),
        ('l0_2', av_l0[2]),
        ('l1_0', av_l1[0]),
        ('l1_1', av_l1[1]),
        ('l1_2', av_l1[2]),
        ('l2_0', av_l2[0]),
        ('l2_1', av_l2[1]),
        ('l2_2', av_l2[2]),
        ('tv_0', av_tv[0]),
        ('tv_1', av_tv[1]),
        ('tv_2', av_tv[2]),
        ('time', np.mean(times))))

    return scores


def run_test(wd, config):
    print "In run_test"
    import mapreduce
    os.chdir(wd)
    params = config['params'][-1]
    key = '_'.join([str(p) for p in params])
    load_globals(config)
    OUTPUT = os.path.join('test', key)
    oc = mapreduce.OutputCollector(OUTPUT)
    X = np.load(config['data']['X'])
    mapreduce.DATA_RESAMPLED = {}
    mapreduce.DATA_RESAMPLED["X"] = [X, X]
    mapper(params, oc)

#################
# Actual script #
#################

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Read target (used to split groups)
    y = np.load(INPUT_TARGET)
    print "Found", len(y), "images"

    # Stratification of subjects
    skf = StratifiedKFold(y=y,
                          n_folds=N_FOLDS,
                          shuffle=True,
                          random_state=RANDOM_STATE)
    resample_index = [[tr.tolist(), te.tolist()] for tr, te in skf]

    # Create files to synchronize with the cluster
    sync_push_filename, sync_pull_filename, CLUSTER_WD = \
    clust_utils.gabriel_make_sync_data_files(OUTPUT_DIR)

    # Create config file
    user_func_filename = os.path.abspath(__file__)

    config = dict(data=dict(X=os.path.basename(INPUT_DATASET)),
                  image_size=INPUT_SHAPE,
                  params=PARAMS,
                  resample=resample_index,
                  map_output="results",
                  user_func=user_func_filename,
                  ncore=4,
                  reduce_input="results/*/*",
                  reduce_group_by="results/.*/(.*)",
                  reduce_output="results.csv")
    config_full_filename = os.path.join(OUTPUT_DIR, "config.json")
    json.dump(config, open(config_full_filename, "w"))

    # Create job files
    cluster_cmd = "mapreduce.py -m %s/config.json  --ncore 12" % CLUSTER_WD
    clust_utils.gabriel_make_qsub_job_files(OUTPUT_DIR, cluster_cmd)

    DEBUG = False
    if DEBUG:
        run_test(OUTPUT_DIR, config)