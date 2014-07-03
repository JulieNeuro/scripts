# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 14:33:15 2014

@author: hl237680

CV using mapreduce and ElasticNet between SNPs and BMI.
"""

import os, sys
import json
import numpy as np
import pandas as pd

from sklearn.cross_validation import KFold
from sklearn.metrics import r2_score
import parsimony.estimators as estimators
    
sys.path.append(os.path.join(os.environ["HOME"], "gits", "scripts", "2013_imagen_subdepression", "lib"))
import utils



def load_globals(config):
    import mapreduce as GLOBAL  # access to global variables
    GLOBAL.DATA = GLOBAL.load_data(config["data"])


def resample(config, resample_nb):
    import mapreduce as GLOBAL  # access to global variables
    #GLOBAL.DATA = GLOBAL.load_data(config["data"])
    resample = config["resample"][resample_nb]
    print "reslicing %d" %resample_nb
    GLOBAL.DATA_RESAMPLED = {k: [GLOBAL.DATA[k][idx, ...] for idx in resample]
                            for k in GLOBAL.DATA}                            
    print "done reslicing %d" %resample_nb


def mapper(key, output_collector):
    import mapreduce as GLOBAL # access to global variables:
    # key: list of parameters
    alpha, l1_ratio = key[0], key[1]
    Ytr = GLOBAL.DATA_RESAMPLED["Y"][0]
    Yte = GLOBAL.DATA_RESAMPLED["Y"][1]
    ztr = GLOBAL.DATA_RESAMPLED["z"][0]
    zte = GLOBAL.DATA_RESAMPLED["z"][1]
    print key, "Data shape:", Ytr.shape, Yte.shape, ztr.shape, zte.shape
    #
    mod = estimators.ElasticNet(l1_ratio, alpha, penalty_start=11, mean=True)     #since we residualized BMI with 2 categorical covariables (Gender and ImagingCentreCity - 8 columns) and 2 ordinal variables (tiv_gaser and mean_pds - 2 columns)
    z_pred = mod.fit(Ytr,ztr).predict(Yte)
    ret = dict(z_pred=z_pred, z_true=zte, beta=mod.beta)
    output_collector.collect(key, ret)


def reducer(key, values):
    # key : string of intermediary key
    # load return dict correspondning to mapper ouput. they need to be loaded.
    values = [item.load() for item in values]
    z_true = np.concatenate([item["z_true"].ravel() for item in values])
    z_pred = np.concatenate([item["z_pred"].ravel() for item in values])
    scores =  dict(param=key, r2=r2_score(z_true, z_pred))
    return scores


#############
# Read data #
#############
# SNPs and BMI
def load_residualized_bmi_data(cache):
    if not(cache):          
        # BMI        
        BMI = pd.io.parsers.read_csv(os.path.join(DATA_PATH, "BMI.csv"), index_col=0).as_matrix()
        # Dataframe      
        COFOUND = ["Subject", "Gender de Feuil2", "ImagingCentreCity", "tiv_gaser", "mean_pds"]
        df = pd.io.parsers.read_csv(os.path.join(CLINIC_DATA_PATH, "1534bmi-vincent2.csv"), index_col=0)
        df = df[COFOUND]
        # Conversion dummy coding
        design_mat = utils.make_design_matrix(df, regressors=COFOUND).as_matrix()
        # Keep only subjects for which we have all data and remove the 1. column containing subject_id from the numpy array design_mat
        subjects_id = np.genfromtxt(os.path.join(DATA_PATH, "subjects_id.csv"), dtype=None, delimiter=',', skip_header=1)
        design_mat = np.delete(np.delete(design_mat, np.where(np.in1d(design_mat[:,0], np.delete(design_mat, np.where(np.in1d(design_mat[:,0], subjects_id)), 0))), 0),0,1)               
        # SNPs
        SNPs = pd.io.parsers.read_csv(os.path.join(DATA_PATH, "SNPs_hl.csv"), index_col=0).as_matrix()
        # Center each SNP for all individuals
        SNPs -= SNPs.mean(axis=0)
        # Standardize each SNP for all individuals
        SNPs /= SNPs.std(axis=0)
        # Concatenate images with covariates gender, imaging city centre, tiv_gaser and mean pds status in order to do as though BMI had been residualized
        Y = np.concatenate((design_mat, SNPs), axis=1)
        z = BMI
        np.save(os.path.join(SHARED_DIR, "Y.npy"), Y)
        np.save(os.path.join(SHARED_DIR, "z.npy"), z)
        print "Data saved"
    else:
        Y = np.load(os.path.join(SHARED_DIR, "Y.npy"))        
        z = np.load(os.path.join(SHARED_DIR, "z.npy"))        
        print "Data read from cache"
    return Y, z

#"""
#run /home/hl237680/gits/scripts/2013_imagen_bmi/scripts/15_cv_multivariate_residualized_BMI.py
#"""
if __name__ == "__main__":

    ## Set pathes
    WD = "/neurospin/tmp/brainomics/residual_bmi_SNPs_opt_hyperparameters_e-1"
    if not os.path.exists(WD): os.makedirs(WD)

    print "#################"
    print "# Build dataset #"
    print "#################"
    if True:
        # Pathnames
        BASE_PATH = '/neurospin/brainomics/2013_imagen_bmi/'
        DATA_PATH = os.path.join(BASE_PATH, 'data')
        CLINIC_DATA_PATH = os.path.join(DATA_PATH, 'clinic')
        #SNPS_FILE = os.path.join(DATA_PATH, 'SNPs.csv')
        BMI_FILE = os.path.join(DATA_PATH, 'BMI.csv')
        
        # Shared data
        BASE_SHARED_DIR = "/neurospin/tmp/brainomics/"
        SHARED_DIR = os.path.join(BASE_SHARED_DIR, 'residualized_bmi_SNPs_cache_1')
        if not os.path.exists(SHARED_DIR):
            os.makedirs(SHARED_DIR)
        
        Y, z = load_residualized_bmi_data(cache=False)
        #assert X.shape == (1265, 336188)
        n = Y.shape[0]
        np.save(os.path.join(WD, "Y.npy"), Y)
        np.save(os.path.join(WD, "z.npy"), z)

    print "#####################"
    print "# Build config file #"
    print "#####################"
    ## Parameterize the mapreduce 
    ##   1) pathes
    NFOLDS = 5
    ## 2) cv index and parameters to test
    cv = [[tr.tolist(), te.tolist()] for tr,te in KFold(n, n_folds=NFOLDS)]    
    params = [[alpha, l1_ratio] for alpha in [0.0001, 0.0005, 0.0009, 0.001, 0.005, 0.009, 0.01, 0.05, 0.09, 0.1, 0.5, 0.9, 1, 5, 9, 10, 15, 20] for l1_ratio in np.arange(0.1, 1., .1)]
    # User map/reduce function file:
    user_func_filename = os.path.join("/home/hl237680",
        "gits", "scripts", "2013_imagen_bmi", "scripts", 
        "20_cv_multivariate_bmi_SNPs_opt_hyperparameter.py")
    #print __file__, os.path.abspath(__file__)
    print "user_func", user_func_filename
    # Use relative path from config.json
    config = dict(data=dict(Y='Y.npy', z='z.npy'),
                  params=params, resample=cv,
                  map_output="results",
                  user_func=user_func_filename,
                  reduce_input="results/*/*", 
                  reduce_group_by="results/.*/(.*)",
                  reduce_output="results.csv")
    json.dump(config, open(os.path.join(WD, "config.json"), "w"))

    #############################################################################
    # Build utils files: sync (push/pull) and PBS
    sys.path.append(os.path.join(os.getenv('HOME'),
                                'gits','scripts'))
    import brainomics.cluster_gabriel as clust_utils
    sync_push_filename, sync_pull_filename, WD_CLUSTER = \
        clust_utils.gabriel_make_sync_data_files(WD, user="hl237680")
    cmd = "mapreduce.py -m %s/config.json  --ncore 12" % WD_CLUSTER
    clust_utils.gabriel_make_qsub_job_files(WD, cmd)
    #############################################################################
    # Sync to cluster
    print "Sync data to gabriel.intra.cea.fr: "
    os.system(sync_push_filename)

    #############################################################################
    print "# Start by running Locally with 12 cores, to check that everything is OK)"
    print "Interrupt after a while CTL-C"
    print "mapreduce.py -m %s/config.json --ncore 12" % WD
    #os.system("mapreduce.py --mode map --config %s/config.json" % WD)
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
    print "mapreduce.py -r %s/config.json" % WD_CLUSTER
    #ATTENTION ! Si envoi sur le cluster, modifier le path de config-2.json : /neurospin/tmp/hl237680/residual_bmi_images_cluster-2/config-2.json