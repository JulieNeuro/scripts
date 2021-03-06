# -*- coding: utf-8 -*-
"""



Process dice5 datasets with standard PCA and our structured PCA.
We use several values for global penalization, TV ratio and L1 ratio.

We generate a map_reduce configuration file for each dataset and the files
needed to run on the cluster.
Due to the cluster setup and the way mapreduce work we need to copy the datsets
and the masks on the cluster. Therefore we copy them on the output directory
which is synchronised on the cluster.

The output directory is results/data_{shape}_{snr}.
"""

import os
import json
import shutil
from collections import OrderedDict
import numpy as np
import sklearn.decomposition
from sklearn import metrics
import parsimony.functions.nesterov.tv
import pca_struct
import metrics
from brainomics import array_utils
import brainomics.cluster_gabriel as clust_utils
from sklearn.cross_validation import StratifiedKFold
import scipy.sparse as sparse
import parsimony.functions.nesterov.tv as nesterov_tv
import nibabel
import parsimony.functions.nesterov.tv as tv_helper
################
# Input/Output #
################
WD = '/neurospin/brainomics/2016_pca_struct/fmri/2017_GraphNet_fmri_10000ite'
NFOLDS_OUTER = 5
NFOLDS_INNER = 5
def config_filename(): return os.path.join(WD,"config_dCV.json")
def results_filename(): return os.path.join(WD,"results_dCV_5folds.xlsx")

##############
# Parameters #
##############

N_COMP = 10
NFOLDS_OUTER = 2
NFOLDS_INNER = 5


#############
# Functions #
#############


def load_globals(config):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])
    STRUCTURE = nibabel.load(config["structure"])
    A = sparse.vstack(tv_helper.linear_operator_from_mask(STRUCTURE.get_data()))
    N_COMP = config["N_COMP"]
    GLOBAL.A, GLOBAL.STRUCTURE,GLOBAL.N_COMP = A, STRUCTURE,N_COMP



def resample(config, resample_nb):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])
    resample = config["resample"][resample_nb]
    GLOBAL.DATA_RESAMPLED = {k: [GLOBAL.DATA[k][idx, ...] for idx in resample]
                            for k in GLOBAL.DATA}



def mapper(key, output_collector):
    import mapreduce as GLOBAL  # access to global variables:
    model_name, global_pen, gn_ratio, l1_ratio = key
    lgn = global_pen * gn_ratio
    ll1 = l1_ratio * global_pen * (1 - gn_ratio)
    ll2 = (1 - l1_ratio) * global_pen * (1 - gn_ratio)
    assert(np.allclose(ll1 + ll2 + lgn, global_pen))

    X_train = GLOBAL.DATA_RESAMPLED["X"][0]
    X_test = GLOBAL.DATA_RESAMPLED["X"][1]
    Agn = GLOBAL.A
    N_COMP = GLOBAL.N_COMP


    model = pca_struct.PCAGraphNet(n_components=N_COMP,
                                    l1=ll1, l2=ll2, lgn=lgn,
                                    Agn=Agn,
                                    criterion="frobenius",
                                    eps=1e-6,
                                    max_iter=10000,
                                    output=False)

    model.fit(X_train)


    V = model.V
    X_train_transform, _ = model.transform(X_train)
    X_test_transform, _ = model.transform(X_test)
    X_train_predict = model.predict(X_train)
    X_test_predict = model.predict(X_test)

    # Compute Frobenius norm between original and recontructed datasets
    frobenius_train = np.linalg.norm(X_train - X_train_predict, 'fro')
    frobenius_test = np.linalg.norm(X_test - X_test_predict, 'fro')
    print(frobenius_test)


    # Remove predicted values (they are huge)
    del X_train_predict, X_test_predict

    ret = dict(frobenius_train=frobenius_train,
               frobenius_test=frobenius_test,
               components=V,
               X_train_transform=X_train_transform,
               X_test_transform=X_test_transform)


    output_collector.collect(key, ret)


def scores(key, paths, config):
    import mapreduce
    values = [mapreduce.OutputCollector(p) for p in paths]
    values = [item.load() for item in values]
    model = "graphNet"


    frobenius_train = np.vstack([item["frobenius_train"] for item in values])
    frobenius_test = np.vstack([item["frobenius_test"] for item in values])
    comp = np.stack([item["components"] for item in values])



    #Mean frobenius norm across folds
    mean_frobenius_train = frobenius_train.mean()
    mean_frobenius_test = frobenius_test.mean()

    comp_t = np.zeros(comp.shape)
    comp_t_non_zero = np.zeros((5,10))
    for i in range(comp.shape[0]):
        for j in range(comp.shape[2]):
            comp_t[i,:,j] = array_utils.arr_threshold_from_norm2_ratio(comp[i, :,j], .99)[0]
            comp_t_non_zero[i,j] = float(np.count_nonzero(comp_t[i,:,j]))/float(comp.shape[1])
    prop_non_zero_mean = np.mean(comp_t_non_zero[:,1:])#do not count first comp

#
    print(prop_non_zero_mean)
    print(key)
    scores = OrderedDict((
        ('param_key',key),
        ('model', model),
        ('frobenius_test', mean_frobenius_test),
        ('frob_test_fold0',float(frobenius_test[0])),
        ('frob_test_fold1',float(frobenius_test[1])),
        ('frob_test_fold2',float(frobenius_test[2])),
        ('frob_test_fold3',float(frobenius_test[3])),
        ('frob_test_fold4',float(frobenius_test[4])),
        ('frobenius_train', mean_frobenius_train),
        ('frob_train_fold0',float(frobenius_train[0])),
        ('frob_train_fold1',float(frobenius_train[1])),
        ('frob_train_fold2',float(frobenius_train[2])),
        ('frob_train_fold3',float(frobenius_train[3])),
        ('frob_train_fold4',float(frobenius_train[4])),
        ('prop_non_zeros_mean',prop_non_zero_mean)))
    return scores



def reducer(key, values):
    import os, glob, pandas as pd
    dir_path =os.getcwd()
    config_path = os.path.join(dir_path,"config_alpha_dCV.json")
    results_file_path = os.path.join(dir_path,"results_dCV_5folds.xlsx")
    config = json.load(open(config_path))
    paths = glob.glob(os.path.join(config['map_output'], "*", "*", "*"))
    #paths = [p for p in paths if not p.count("sparse_pca_0.0_0.0_5.0")]


    def close(vec, val, tol=1e-4):
        return np.abs(vec - val) < tol

    def groupby_paths(paths, pos):
        groups = {g:[] for g in set([p.split("/")[pos] for p in paths])}
        for p in paths:
            groups[p.split("/")[pos]].append(p)
        return groups

    def argmaxscore_bygroup(data, groupby='fold', param_key="param_key", score="frobenius_test"):
        arg_min_byfold = list()
        for fold, data_fold in data.groupby(groupby):
            assert len(data_fold) == len(set(data_fold[param_key]))  # ensure all  param are diff
            arg_min_byfold.append([fold, data_fold.ix[data_fold[score].argmin()][param_key], data_fold[score].min()])
        return pd.DataFrame(arg_min_byfold, columns=[groupby, param_key, score])

    print('## Refit scores')
    print('## ------------')
    byparams = groupby_paths([p for p in paths if p.count("all") and not p.count("all/all")],3)
    byparams_scores = {k:scores(k, v, config) for k, v in list(byparams.items())}

    data = [list(byparams_scores[k].values()) for k in byparams_scores]

    columns = list(byparams_scores[list(byparams_scores.keys())[0]].keys())
    scores_refit = pd.DataFrame(data, columns=columns)

    print('## doublecv scores by outer-cv and by params')
    print('## -----------------------------------------')
    data = list()
    bycv = groupby_paths([p for p in paths if p.count("cvnested")],1)
    for fold, paths_fold in list(bycv.items()):
        print(fold)
        byparams = groupby_paths([p for p in paths_fold], 3)
        byparams_scores = {k:scores(k, v, config) for k, v in list(byparams.items())}
        data += [[fold] + list(byparams_scores[k].values()) for k in byparams_scores]
        scores_dcv_byparams = pd.DataFrame(data, columns=["fold"] + columns)

    #exclude when less than 1% of voxels are zero ---> too sparse
    rm = (scores_dcv_byparams.prop_non_zeros_mean <0.01)
    np.sum(rm)
    scores_dcv_byparams = scores_dcv_byparams[np.logical_not(rm)]

    #exclude when less than 1% of voxels are zero ---> too sparse
    rm = (scores_dcv_byparams.prop_non_zeros_mean >0.50)
    np.sum(rm)
    scores_dcv_byparams = scores_dcv_byparams[np.logical_not(rm)]

    print('## Model selection')
    print('## ---------------')
    folds_graphNet = argmaxscore_bygroup(scores_dcv_byparams[scores_dcv_byparams["model"] == "graphNet"])
    scores_argmax_byfold_graphNet = folds_graphNet


    print('## Apply best model on refited')
    print('## ---------------------------')
    scores_graphNet = scores("nestedcv", [os.path.join(config['map_output'], row["fold"], "all", row["param_key"]) for index, row in folds_graphNet.iterrows()], config)

    scores_cv_graphNet= pd.DataFrame([["enettv"] + list(scores_graphNet.values())], columns=["method"] + list(scores_graphNet.keys()))


    with pd.ExcelWriter(results_file_path) as writer:
        scores_refit.to_excel(writer, sheet_name='scores_all', index=False)
        scores_dcv_byparams.to_excel(writer, sheet_name='scores_dcv_byparams', index=False)
        scores_argmax_byfold_graphNet.to_excel(writer, sheet_name='scores_argmax_byfold_graphNet', index=False)
        scores_cv_graphNet.to_excel(writer, sheet_name = 'scores_cv_graphNet', index=False)

#################
# Actual script #
#################

if __name__ == "__main__":

    WD = '/neurospin/brainomics/2016_pca_struct/fmri/2017_GraphNet_fmri_10000ite'
    INPUT_DATA_X = '/neurospin/brainomics/2016_pca_struct/fmri/data/T_hallu_only.npy'
    INPUT_DATA_y = '/neurospin/brainomics/2016_pca_struct/fmri/data/y_hallu_only.npy'
    INPUT_MASK_PATH = '/neurospin/brainomics/2016_pca_struct/fmri/data/mask.nii.gz'

    NFOLDS_OUTER = 5
    NFOLDS_INNER = 5
    NCOMP = 10
    number_features = np.load(INPUT_DATA_X).shape[1]

    #############################################################################
    ## Create config file
    ###########################
    #create DOUbleCV resampling pipeline
    y = np.load(INPUT_DATA_y)
    cv_outer = [[tr, te] for tr,te in StratifiedKFold(y.ravel(), n_folds=NFOLDS_OUTER, random_state=42)]
    if cv_outer[0] is not None: # Make sure first fold is None
        cv_outer.insert(0, None)
        null_resampling = list(); null_resampling.append(np.arange(0,len(y))),null_resampling.append(np.arange(0,len(y)))
        cv_outer[0] = null_resampling

    import collections
    cv = collections.OrderedDict()
    for cv_outer_i, (tr_val, te) in enumerate(cv_outer):
        if cv_outer_i == 0:
            cv["all/all"] = [tr_val, te]
        else:
            cv["cv%02d/all" % (cv_outer_i -1)] = [tr_val, te]
            cv_inner = StratifiedKFold(y[tr_val].ravel(), n_folds=NFOLDS_INNER, random_state=42)
            for cv_inner_i, (tr, val) in enumerate(cv_inner):
                cv["cv%02d/cvnested%02d" % ((cv_outer_i-1), cv_inner_i)] = [tr_val[tr], tr_val[val]]
    for k in cv:
        cv[k] = [cv[k][0].tolist(), cv[k][1].tolist()]

    print((list(cv.keys())))
    ###########################
    #Grid of parameters to explore
    ###########################
    params = [('graphNet_pca', 0.1, 0.1, 0.1),('graphNet_pca', 0.1, 0.1, 0.5),\
             ('graphNet_pca', 0.1, 0.5, 0.1),('graphNet_pca', 0.1, 0.5, 0.5),('graphNet_pca', 0.01, 0.1, 0.1),\
             ('graphNet_pca', 0.01, 0.1, 0.5),('graphNet_pca', 0.01, 0.5, 0.1),('graphNet_pca', 0.01, 0.5, 0.5)]


    user_func_filename = os.path.abspath(__file__)

    shutil.copy(INPUT_DATA_X, WD)
    shutil.copy(INPUT_DATA_y, WD)
    shutil.copy(INPUT_MASK_PATH, WD)

    config = dict(data=dict(X="T_hallu_only.npy", y="y_hallu_only.npy"),
                  params=params, resample=cv,
                  structure = "mask.nii.gz",
                  N_COMP = NCOMP,
                  map_output="model_selectionCV",
                  user_func=user_func_filename,
                  reduce_input="results/*/*",
                  reduce_group_by="params",
                  reduce_output="model_selectionCV.csv")
    json.dump(config, open(os.path.join(WD, "config_dCV.json"), "w"))




        # Build utils files: sync (push/pull) and PBS
    import brainomics.cluster_gabriel as clust_utils
    sync_push_filename, sync_pull_filename, WD_CLUSTER = \
    clust_utils.gabriel_make_sync_data_files(WD)
    cmd = "mapreduce.py --map  %s/config_dCV.json" % WD_CLUSTER
    clust_utils.gabriel_make_qsub_job_files(WD, cmd,walltime = "250:00:00")  #################################################################
    # Build utils files: sync (push/pull) and PBS
#    import brainomics.cluster_gabriel as clust_utils
#    sync_push_filename, sync_pull_filename, WD_CLUSTER = \
#        clust_utils.gabriel_make_sync_data_files(WD)
#    cmd = "mapreduce.py --map  %s/config_dCV.json" % WD_CLUSTER
#    clust_utils.gabriel_make_qsub_job_files(WD, cmd)
#        ################################################################
        # Sync to cluster
    #print ("Sync data to gabriel.intra.cea.fr: ")
    #os.system(sync_push_filename)

    """######################################################################
    print "# Start by running Locally with 2 cores, to check that everything is OK)"
    print ("mapreduce.py --map %s/config.json --ncore 2" % WD)
    #os.system("mapreduce.py --mode map --config %s/config_dCV.json" % WD)
    print ("# 1) Log on gabriel:")
    print ('ssh -t gabriel.intra.cea.fr')
    print ("# 2) Run one Job to test")
    print ("qsub -I")
    print ("cd %s" % WD_CLUSTER)
    print ("./job_Global_long.pbs")
    print ("# 3) Run on cluster")
    print ("qsub job_Global_long.pbs")
    print ("# 4) Log out and pull Pull")
    print ("exit")
    print (sync_pull_filename)
    #########################################################################
    print "# Reduce"
    print "mapreduce.py --reduce %s/config.json" % WD"""






