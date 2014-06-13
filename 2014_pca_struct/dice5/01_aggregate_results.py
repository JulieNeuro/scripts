# -*- coding: utf-8 -*-
"""
Created on Wed Jun  4 12:16:54 2014

@author: md238665

Aggregates results of previous scripts.

"""

import os

import pandas as pd
import numpy as np
import scipy
import matplotlib.pylab as plt

import dice5_pca

################
# Input/Output #
################

INPUT_BASE_DIR = "/neurospin/brainomics/2014_pca_struct/dice5"
INPUT_DIR = os.path.join(INPUT_BASE_DIR, "data")
INPUT_STD_DATASET_FILE_FORMAT = "data_{alpha}.std.npy"
INPUT_INDEX_FILE_FORMAT = "indices_{subset}.npy"
INPUT_OBJECT_MASK_FILE_FORMAT = "mask_{o}.npy"

INPUT_SHAPE = (100, 100, 1)
INPUT_N_SUBSETS = 2
INPUT_SNRS = np.array([0.1, 0.5, 1.0])
INPUT_BETA_FILE_FORMAT = "beta3d_{alpha}.std.npy"
INPUT_N_COMP = 3

INPUT_MODELS = ["pca", "sparse_pca", "struct_pca"]
INPUT_DATASET_DIR = "{alpha}"
INPUT_RESULT_FILE = "results.csv"

OUTPUT_DIR = INPUT_BASE_DIR
OUTPUT_RESULTS = os.path.join(OUTPUT_DIR, "consolidated_results.csv")

##############
# Parameters #
##############

##########
# Script #
##########

# Read input files in a large df
input_files = []
total_df = None
N = 0
for model in INPUT_MODELS:
    input_dir = os.path.join(INPUT_BASE_DIR, model)
    for snr in INPUT_SNRS:
        subdir = os.path.join(input_dir, INPUT_DATASET_DIR.format(alpha=snr))
        full_filename = os.path.join(subdir, INPUT_RESULT_FILE)
        input_files.append(full_filename)
        if os.path.exists(full_filename):
            # Read it
            df = pd.io.parsers.read_csv(full_filename,
                                        index_col=11)
            n, p = df.shape
            print "Reading", full_filename, "(", n, "lines)"
            N += n
            # Add columns
            snrs = pd.Series.from_array(np.asarray([snr]*n),
                                        name='SNR',
                                        index=pd.Index(np.arange(n)))
            models = pd.Series.from_array(np.asarray([model]*n),
                                          name='model',
                                          index=pd.Index(np.arange(n)))
            # Create multiindex (model, alpha, key) for this file
            df.index = pd.MultiIndex.from_arrays([models, snrs, df.index])
            if total_df is None:
                total_df = df
            else:
                total_df = total_df.append(df)
total_df.to_csv(OUTPUT_RESULTS)