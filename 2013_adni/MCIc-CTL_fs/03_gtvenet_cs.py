# -*- coding: utf-8 -*-
"""
Created on Fri May 30 20:03:12 2014

@author: edouard.duchesnay@cea.fr
"""

import os
import json
import numpy as np
from sklearn.cross_validation import StratifiedKFold
from sklearn.metrics import roc_curve, auc, roc_auc_score, precision_recall_fscore_support
from sklearn.feature_selection import SelectKBest
from parsimony.estimators import LogisticRegressionL1L2TV
import parsimony.functions.nesterov.tv as tv_helper


def load_globals(config):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])
    import brainomics.mesh_processing as mesh_utils
    mesh_coord, mesh_triangles = mesh_utils.mesh_arrays(config["structure"]["mesh"])
    mask = np.load(config["structure"]["mask"])
    GLOBAL.mesh_coord, GLOBAL.mesh_triangles, GLOBAL.mask = mesh_coord, mesh_triangles, mask
    A, _ = tv_helper.nesterov_linear_operator_from_mesh(GLOBAL.mesh_coord, GLOBAL.mesh_triangles, GLOBAL.mask)
    GLOBAL.A = A

def resample(config, resample_nb):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])
    resample = config["resample"][resample_nb]
    if resample is not None:
        GLOBAL.DATA_RESAMPLED = {k: [GLOBAL.DATA[k][idx, ...] for idx in resample]
                            for k in GLOBAL.DATA}
    else:  # resample is None train == test
        GLOBAL.DATA_RESAMPLED = {k: [GLOBAL.DATA[k] for idx in [0, 1]]
                            for k in GLOBAL.DATA}

def mapper(key, output_collector):
    import mapreduce as GLOBAL # access to global variables:
        #raise ImportError("could not import ")
    # GLOBAL.DATA, GLOBAL.STRUCTURE, GLOBAL.A
    # GLOBAL.DATA ::= {"X":[Xtrain, ytrain], "y":[Xtest, ytest]}
    # key: list of parameters
    Xtr = GLOBAL.DATA_RESAMPLED["X"][0]
    Xte = GLOBAL.DATA_RESAMPLED["X"][1]
    ytr = GLOBAL.DATA_RESAMPLED["y"][0]
    yte = GLOBAL.DATA_RESAMPLED["y"][1]
    print key, "Data shape:", Xtr.shape, Xte.shape, ytr.shape, yte.shape
    # STRUCTURE = GLOBAL.STRUCTURE
    #alpha, ratio_l1, ratio_l2, ratio_tv, k = key
    #key = np.array(key)
    penalty_start = 2
    class_weight="auto" # unbiased
    alpha = float(key[0])
    l1, l2, tv, k = alpha * float(key[1]), alpha * float(key[2]), alpha * float(key[3]), key[4]
    print "l1:%f, l2:%f, tv:%f, k:%i" % (l1, l2, tv, k)
    if k != -1:
        k = int(k)
        aov = SelectKBest(k=k)
        aov.fit(Xtr[..., penalty_start:], ytr.ravel())
        mask = GLOBAL.mask != 0
        mask[mask] = aov.get_support()
        #print mask.sum()
        A, _ = tv_helper.nesterov_linear_operator_from_mesh(GLOBAL.mesh_coord, GLOBAL.mesh_triangles, mask)
        Xtr_r = np.hstack([Xtr[:, :penalty_start], Xtr[:, penalty_start:][:, aov.get_support()]])
        Xte_r = np.hstack([Xte[:, :penalty_start], Xte[:, penalty_start:][:, aov.get_support()]])
    else:
        mask = np.ones(Xtr.shape[0], dtype=bool)
        Xtr_r = Xtr
        Xte_r = Xte
        A = GLOBAL.A
    mod = LogisticRegressionL1L2TV(l1, l2, tv, A, penalty_start=penalty_start,
                                   class_weight=class_weight)
    mod.fit(Xtr_r, ytr)
    y_pred = mod.predict(Xte_r)
    proba_pred = mod.predict_probability(Xte_r)
    ret = dict(y_pred=y_pred, y_true=yte, beta=mod.beta,  mask=mask, proba_pred=proba_pred)
    if output_collector:
        output_collector.collect(key, ret)
    else:
        return ret

def reducer(key, values):
    # key : string of intermediary key
    # load return dict correspondning to mapper ouput. they need to be loaded.
    # DEBUG
    #import glob, mapreduce
    #values = [mapreduce.OutputCollector(p) for p in glob.glob("/neurospin/brainomics/2013_adni/AD-CTL/results/*/0.1_0.0_0.0_1.0_-1.0/")]
    #values = [mapreduce.OutputCollector(p) for p in glob.glob("/home/ed203246/tmp/MCIc-MCInc_cs/results/*/0.1_0.0_0.0_1.0_-1.0/")]
    # values = [mapreduce.OutputCollector(p) for p in glob.glob("/home/ed203246/tmp/MCIc-CTL_cs/results/*/0.1_0.0_1.0_0.0_-1.0/")]
    # values = [mapreduce.OutputCollector(p) for p in glob.glob("/home/ed203246/tmp/MCIc-CTL_cs/results/*/0.1_0.0_0.5_0.5_-1.0/")]
    # Compute sd; ie.: compute results on each folds
    values = [item.load() for item in values]
    recall_mean_std = np.std([np.mean(precision_recall_fscore_support(
        item["y_true"].ravel(), item["y_pred"])[1]) for item in values]) / np.sqrt(len(values))
    y_true = [item["y_true"].ravel() for item in values]
    y_pred = [item["y_pred"].ravel() for item in values]
    prob_pred = [item["proba_pred"].ravel() for item in values]
    y_true = np.concatenate(y_true)
    y_pred = np.concatenate(y_pred)
    prob_pred = np.concatenate(prob_pred)
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, average=None)
    fpr, tpr, testholds = roc_curve(y_true, prob_pred, 1)
    auc_ = auc(fpr, tpr)
    n_ite = None
    betas = np.hstack([item["beta"] for item in values]).T
    R = np.corrcoef(betas)
    beta_cor_mean = np.mean(R[np.triu_indices_from(R, 1)])
    a, l1, l2 , tv , k = [float(par) for par in key.split("_")]
    print a, l1, l2, tv, k, beta_cor_mean
    scores = dict(key=key, a=a, l1=l1, l2=l2, tv=tv, k=k,
               recall_0=r[0], recall_1=r[1], recall_mean=r.mean(), recall_mean_std=recall_mean_std,
               precision_0=p[0], precision_1=p[1], precision_mean=p.mean(),
               f1_0=f[0], f1_1=f[1], f1_mean=f.mean(),
               support_0=s[0] , support_1=s[1], n_ite=n_ite,
               beta_cor_mean=beta_cor_mean, auc=auc_)
    return scores


##############################################################################
## Run all
def debug(config):
    import mapreduce
    WD = "/neurospin/brainomics/2013_adni/MCIc-CTL_fs"
    key = '0.01_0.999_0.0_0.001_-1.0'
    os.chdir(WD)
    config = json.load(open("config_5cv.json"))
    import mapreduce
    GLOBAL = mapreduce
    #class GLOBAL: DATA = dict()
    load_globals(config)
    resample(config, resample_nb=0)
    oc = mapreduce.OutputCollector(os.path.join('5cv', key))
    params = np.array([float(p) for p in key.split("_")])
    mapper(params, oc)
    alpha = np.load("/tmp/alpha.npy")
    A = GLOBAL.A
    import pickle
    a = pickle.load(open("/tmp/a.pkl"))
    
if __name__ == "__main__":
    WD = "/neurospin/brainomics/2013_adni/MCIc-CTL_fs"
    #BASE = "/neurospin/tmp/brainomics/testenettv"
    #WD_CLUSTER = WD.replace("/neurospin/brainomics", "/neurospin/tmp/brainomics")
    #print "Sync data to %s/ " % os.path.dirname(WD)
    #os.system('rsync -azvu %s %s/' % (BASE, os.path.dirname(WD)))
    INPUT_DATA_X = 'X.npy'
    INPUT_DATA_y = 'y.npy'
    STRUCTURE = dict(mesh="lrh.pial.gii", mask="mask.npy")
    NFOLDS = 5
    #WD = os.path.join(WD, 'logistictvenet_5cv')
    if not os.path.exists(WD): os.makedirs(WD)
    os.chdir(WD)

    #############################################################################
    ## Create config file
    y = np.load(INPUT_DATA_y)
    cv = [[tr.tolist(), te.tolist()] for tr,te in StratifiedKFold(y.ravel(), n_folds=5)]
    cv.insert(0, None)  # first fold is None
    # parameters grid
    # Re-run with
    tv_range = np.array([0., 1e-3, 5e-3, 1e-2, 5e-2, .1, .2, .3, .333, .4, .5, .6, .7, .8, .9])
    ratios = np.array([[1., 0., 1], [0., 1., 1], [.5, .5, 1], [.9, .1, 1],
                       [.1, .9, 1], [.01, .99, 1], [.001, .999, 1]])
    alphas = [.01, .05, .1 , .5, 1.]
    k_range = [-1]#[100, 1000, 10000, 100000, -1]
    l1l2tv =[np.array([[float(1-tv), float(1-tv), tv]]) * ratios for tv in tv_range]
    l1l2tv.append(np.array([[0., 0., 1.]]))
    l1l2tv = np.concatenate(l1l2tv)
    alphal1l2tv = np.concatenate([np.c_[np.array([[alpha]]*l1l2tv.shape[0]), l1l2tv] for alpha in alphas])
    alphal1l2tvk = np.concatenate([np.c_[alphal1l2tv, np.array([[k]]*alphal1l2tv.shape[0])] for k in k_range])
    params = [params.tolist() for params in alphal1l2tvk]
    # User map/reduce function file:
#    try:
#        user_func_filename = os.path.abspath(__file__)
#    except:
    user_func_filename = os.path.join(os.environ["HOME"],
        "git", "scripts", "2013_adni", "MCIc-CTL_fs",
        "03_gtvenet_cs.py")
    #print __file__, os.path.abspath(__file__)
    print "user_func", user_func_filename
    #import sys
    #sys.exit(0)
    # Use relative path from config.json
    config = dict(data=dict(X=INPUT_DATA_X, y=INPUT_DATA_y),
                  params=params, resample=cv,
                  structure=STRUCTURE,
                  map_output="5cv",
                  user_func=user_func_filename,
                  reduce_input="5cv/*/*",
                  reduce_group_by="5cv/.*/(.*)",
                  reduce_output="MCIc-CTL_fs.csv")
    json.dump(config, open(os.path.join(WD, "config_5cv.json"), "w"))

    #############################################################################
    # Build utils files: sync (push/pull) and PBS
    import brainomics.cluster_gabriel as clust_utils
    sync_push_filename, sync_pull_filename, WD_CLUSTER = \
        clust_utils.gabriel_make_sync_data_files(WD)
    cmd = "mapreduce.py --map  %s/config_5cv.json" % WD_CLUSTER
    clust_utils.gabriel_make_qsub_job_files(WD, cmd)
    #############################################################################
    # Sync to cluster
    print "Sync data to gabriel.intra.cea.fr: "
    os.system(sync_push_filename)
    #############################################################################
    print "# Start by running Locally with 2 cores, to check that everything os OK)"
    print "Interrupt after a while CTL-C"
    print "mapreduce.py --map %s/config_5cv.json --ncore 2" % WD
    print "# 1) Log on gabriel:"
    print 'ssh -t gabriel.intra.cea.fr'
    print "# 2) Run one Job to test"
    print "qsub -I"
    print "cd %s" % WD_CLUSTER
    print "./job_Global_long.pbs"
    print "# 3) Run on cluster"
    print "qsub job_Global_long.pbs"
    print "# 4) Log out and pull Pull"
    print "exit"
    print sync_pull_filename
    #############################################################################
    print "# Reduce"
    print "mapreduce.py --reduce %s/config_5cv.json" % WD
