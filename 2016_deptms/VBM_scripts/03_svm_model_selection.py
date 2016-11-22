# -*- coding: utf-8 -*-
"""
Created on Mon Nov 21 17:10:23 2016

@author: ad247405
"""


import os
import json
import numpy as np
from sklearn.cross_validation import StratifiedKFold
import nibabel
from sklearn import svm
from sklearn.metrics import precision_recall_fscore_support
from sklearn.feature_selection import SelectKBest
import brainomics.image_atlas
from scipy.stats import binom_test
from collections import OrderedDict
from sklearn import preprocessing
from sklearn.metrics import roc_auc_score, recall_score
import pandas as pd
from collections import OrderedDict

BASE_PATH = '/neurospin/brainomics/2016_deptms'
WD = '/neurospin/brainomics/2016_deptms/analysis/VBM/results/svm/svm_model_selection_5folds'

def config_filename(): return os.path.join(WD,"config_dCV.json")
def results_filename(): return os.path.join(WD,"results_dCV_5folds.xlsx")
#############################################################################


def load_globals(config):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])
    

def resample(config, resample_nb):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])
    resample = config["resample"][resample_nb]
    GLOBAL.DATA_RESAMPLED = {k: [GLOBAL.DATA[k][idx, ...] for idx in resample]
                            for k in GLOBAL.DATA}

def mapper(key, output_collector):
    import mapreduce as GLOBAL 
    Xtr = GLOBAL.DATA_RESAMPLED["X"][0]
    Xte = GLOBAL.DATA_RESAMPLED["X"][1]
    ytr = GLOBAL.DATA_RESAMPLED["y"][0]
    yte = GLOBAL.DATA_RESAMPLED["y"][1]

    
    c = float(key[0])
    print "c:%f" % (c)

    class_weight="auto" # unbiased
    
    mask = np.ones(Xtr.shape[0], dtype=bool)
   
    scaler = preprocessing.StandardScaler().fit(Xtr)
    Xtr = scaler.transform(Xtr)
    Xte=scaler.transform(Xte)    
    
    mod = svm.LinearSVC(C=c,fit_intercept=False,class_weight= class_weight)

    mod.fit(Xtr, ytr.ravel())
    y_pred = mod.predict(Xte)
    ret = dict(y_pred=y_pred, y_true=yte, beta=mod.coef_,  mask=mask)
    if output_collector:
        output_collector.collect(key, ret)
    else:
        return ret


       

def scores(key, paths, config, ret_y=False):
    import mapreduce
    print key
    values = [mapreduce.OutputCollector(p) for p in paths]
    values = [item.load() for item in values]
    #FOLD O is a refit on all samples. DOn't take into account in test.
    recall_mean_std = np.std([np.mean(precision_recall_fscore_support(
        item["y_true"].ravel(), item["y_pred"])[1]) for item in values]) / np.sqrt(len(values))
    y_true = [item["y_true"].ravel() for item in values]
    y_pred = [item["y_pred"].ravel() for item in values]
    #prob_pred = [item["proba_pred"].ravel() for item in values]
    y_true = np.concatenate(y_true)
    y_pred = np.concatenate(y_pred)
    #prob_pred = np.concatenate(prob_pred)
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, average=None)
    #auc = roc_auc_score(y_true, prob_pred) #area under curve score.
    n_ite = None
    betas = np.hstack([item["beta"] for item in values]).T
    scores = OrderedDict()
    try:    
        c = float(key[0])
        
        scores['c'] = c
    except:
        pass
    scores['recall_0'] = r[0]
    scores['recall_1'] = r[1]
    scores['recall_mean'] = r.mean()
    scores['recall_mean_std'] = recall_mean_std
    scores['precision_0'] = p[0]
    scores['precision_1'] = p[1]
    scores['precision_mean'] = p.mean()
    scores['f1_0'] = f[0]
    scores['f1_1'] = f[1]
    scores['f1_mean'] = f.mean()
    scores['support_0'] = s[0]
    scores['support_1'] = s[1]
    scores['prop_non_zeros_mean'] = float(np.count_nonzero(betas)) / \
                                    float(np.prod(betas.shape))
    scores['n_ite'] = n_ite
    scores['param_key'] = key
    if ret_y:
        scores["y_true"], scores["y_pred"] = y_true, y_pred
    return scores
    
    
def reducer(key, values):
    import os, glob, pandas as pd
    os.chdir(os.path.dirname(config_filename()))
    config = json.load(open(config_filename()))
    paths = glob.glob(os.path.join(config['map_output'], "*", "*", "*"))
    #paths = [p for p in paths if not p.count("0.8_-1")]

    def close(vec, val, tol=1e-4):
        return np.abs(vec - val) < tol

    def groupby_paths(paths, pos):
        groups = {g:[] for g in set([p.split("/")[pos] for p in paths])}
        for p in paths:
            groups[p.split("/")[pos]].append(p)
        return groups

    def argmaxscore_bygroup(data, groupby='fold', param_key="param_key", score="recall_mean"):
        arg_max_byfold = list()
        for fold, data_fold in data.groupby(groupby):
            assert len(data_fold) == len(set(data_fold[param_key]))  # ensure all  param are diff
            arg_max_byfold.append([fold, data_fold.ix[data_fold[score].argmax()][param_key], data_fold[score].max()])
        return pd.DataFrame(arg_max_byfold, columns=[groupby, param_key, score])

    print '## Refit scores'
    print '## ------------'
    byparams = groupby_paths([p for p in paths if not p.count("cvnested") and not p.count("refit/refit") ], 3) 
    byparams_scores = {k:scores(k, v, config) for k, v in byparams.iteritems()}

    data = [byparams_scores[k].values() for k in byparams_scores]

    columns = byparams_scores[byparams_scores.keys()[0]].keys()
    scores_refit = pd.DataFrame(data, columns=columns)
    
    print '## doublecv scores by outer-cv and by params'
    print '## -----------------------------------------'
    data = list()
    bycv = groupby_paths([p for p in paths if p.count("cvnested") and not p.count("refit/cvnested")  ], 1)
    for fold, paths_fold in bycv.iteritems():
        print fold
        byparams = groupby_paths([p for p in paths_fold], 3)
        byparams_scores = {k:scores(k, v, config) for k, v in byparams.iteritems()}
        data += [[fold] + byparams_scores[k].values() for k in byparams_scores]
        scores_dcv_byparams = pd.DataFrame(data, columns=["fold"] + columns)


    print '## Model selection'
    print '## ---------------'
    svm = argmaxscore_bygroup(scores_dcv_byparams); svm["method"] = "svm"
    
    scores_argmax_byfold = svm

    print '## Apply best model on refited'
    print '## ---------------------------'
    scores_svm = scores("nestedcv", [os.path.join(config['map_output'], row["fold"], "refit", row["param_key"]) for index, row in svm.iterrows()], config)

   
    scores_cv = pd.DataFrame([["svm"] + scores_svm.values()], columns=["method"] + scores_svm.keys())
   
         
    with pd.ExcelWriter(results_filename()) as writer:
        scores_refit.to_excel(writer, sheet_name='scores_all', index=False)
        scores_dcv_byparams.to_excel(writer, sheet_name='scores_dcv_byparams', index=False)
        scores_argmax_byfold.to_excel(writer, sheet_name='scores_argmax_byfold', index=False)
        scores_cv.to_excel(writer, sheet_name='scores_cv', index=False)

##############################################################################


if __name__ == "__main__":
    BASE_PATH = "/neurospin/brainomics/2016_deptms"
    WD = '/neurospin/brainomics/2016_deptms/analysis/VBM/results/svm/model_selection_5folds'
    INPUT_DATA_X = '/neurospin/brainomics/2016_deptms/analysis/VBM/data/X.npy'
    INPUT_DATA_y = '/neurospin/brainomics/2016_deptms/analysis/VBM/data/y.npy'
    INPUT_MASK_PATH = '/neurospin/brainomics/2016_deptms/analysis/VBM/data/mask.npy'
    INPUT_CSV = '/neurospin/brainomics/2016_deptms/analysis/VBM/population.csv'

    pop = pd.read_csv(INPUT_CSV,delimiter=' ')
    number_subjects = pop.shape[0]
    NFOLDS_OUTER = 5
    NFOLDS_INNER = 5

    #############################################################################
     ## Create config file
    y = np.load(INPUT_DATA_y)

    cv_outer = [[tr, te] for tr,te in StratifiedKFold(y.ravel(), n_folds=NFOLDS_OUTER, random_state=42)]
    if cv_outer[0] is not None: # Make sure first fold is None
        cv_outer.insert(0, None)   
        null_resampling = list(); null_resampling.append(np.arange(0,len(y))),null_resampling.append(np.arange(0,len(y)))
        cv_outer[0] = null_resampling
            
#     
    import collections
    cv = collections.OrderedDict()
    for cv_outer_i, (tr_val, te) in enumerate(cv_outer):
        if cv_outer_i == 0:
            cv["all"] = [tr_val, te]
            cv_inner = StratifiedKFold(y[tr_val].ravel(), n_folds=NFOLDS_INNER, random_state=42)
            for cv_inner_i, (tr, val) in enumerate(cv_inner):
                cv["all/cvnested%02d" % (cv_inner_i)] = [tr_val[tr], tr_val[val]]
        else:    
            cv["cv%02d/all" % (cv_outer_i -1)] = [tr_val, te]
            cv_inner = StratifiedKFold(y[tr_val].ravel(), n_folds=NFOLDS_INNER, random_state=42)
            for cv_inner_i, (tr, val) in enumerate(cv_inner):
                cv["cv%02d/cvnested%02d" % ((cv_outer_i-1), cv_inner_i)] = [tr_val[tr], tr_val[val]]
    for k in cv:
        cv[k] = [cv[k][0].tolist(), cv[k][1].tolist()]

       
    print cv.keys()  


    C_range = [[100],[10],[1],[1e-1],[1e-2],[1e-3],[1e-4],[1e-5],[1e-6],[1e-7],[1e-8],[1e-9]]
    #assert len(C_range) == 12
    
    
    user_func_filename = "/home/ad247405/git/scripts/2016_deptms/VBM_scripts/03_svm_model_selection.py"
    
    config = dict(data=dict(X=INPUT_DATA_X, y=INPUT_DATA_y),
                  params=C_range, resample=cv,
                  structure=INPUT_MASK_PATH,
                  map_output="model_selectionCV", 
                  user_func=user_func_filename,
                  reduce_input="results/*/*",
                  reduce_group_by="params",
                  reduce_output="model_selectionCV.csv")
    json.dump(config, open(os.path.join(WD, "config_dCV.json"), "w"))