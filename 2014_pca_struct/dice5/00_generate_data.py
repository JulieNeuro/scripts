# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 10:57:39 2014

@author:  edouard.duchesnay@cea.fr
@license: BSD-3-Clause

Generate test data for PCA with various SNR (controlled by INPUT_ALPHAS).

We split the data into a train and test sets just for future usage.
Train and test indices are fixed here.

Finally center data.

"""

import os
import numpy as np

from sklearn.preprocessing import StandardScaler

from parsimony import datasets

import dice5

################
# Input/Output #
################

OUTPUT_BASE_DIR = "/neurospin/brainomics/2014_pca_struct/dice5/data"

OUTPUT_DIR_FORMAT = os.path.join(OUTPUT_BASE_DIR, "data_{s[0]}_{s[1]}_{snr}")
OUTPUT_DATASET_FILE = "data.npy"
OUTPUT_STD_DATASET_FILE = "data.std.npy"
OUTPUT_BETA_FILE = "beta3d.std.npy"
OUTPUT_INDEX_FILE_FORMAT = "indices_{subset}.npy"
OUTPUT_OBJECT_MASK_FILE_FORMAT = "mask_{i}.npy"
OUTPUT_MASK_FILE = "mask.npy"

##############
# Parameters #
##############

SHAPE = (100, 100, 1)
N_SAMPLES = 100
N_SUBSETS = 2
# Object model (modulated by SNR)
STDEV = np.asarray([1, 0.5, 0.5])
MODEL = dict(
        # Each point has an independant latent
        l1=.0, l2=.0, l3=STDEV[1], l4=.0, l5=.0,
        # Shared variance:
        l12=STDEV[0], l45=STDEV[2], l12345=0.,
        # Five dots contribute equally:
        b1=1., b2=1., b3=1., b4=-1., b5=-1.)
# SNR
SNRS = np.append(np.linspace(0.1, 1, num=10), 0.25)

########
# Code #
########

# Number of samples to generate
n = N_SUBSETS * N_SAMPLES

# Generate data for various alpha parameter
for snr in SNRS:
    X3d, y, beta3d, objects = dice5.load(n_samples=n,
                                         shape=SHAPE,
                                         model=MODEL,
                                         obj_pix_ratio=snr,
                                         random_seed=1)
    # Save data and scaled data
    output_dir = OUTPUT_DIR_FORMAT.format(s=SHAPE,
                                          snr=snr)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    X = X3d.reshape(n, np.prod(SHAPE))
    full_filename = os.path.join(output_dir, OUTPUT_DATASET_FILE)
    np.save(full_filename, X)
    scaler = StandardScaler(with_mean=True, with_std=False)
    X_std = scaler.fit_transform(X)
    full_filename = os.path.join(output_dir, OUTPUT_STD_DATASET_FILE)
    np.save(full_filename, X_std)
    # Save beta
    full_filename = os.path.join(output_dir, OUTPUT_BETA_FILE)
    np.save(full_filename, beta3d)

    # Split in train/test
    for i in range(N_SUBSETS):
        indices = np.arange(i*N_SAMPLES, (i+1)*N_SAMPLES)
        filename = OUTPUT_INDEX_FILE_FORMAT.format(subset=i)
        full_filename = os.path.join(output_dir, filename)
        np.save(full_filename, indices)

    # Generate mask with the last objects since they have the same geometry
    # We only use union12, d3, union45
    _, _, d3, _, _, union12, union45, _ = objects
    sub_objects = [union12, d3, union45]
    full_mask = np.zeros(SHAPE, dtype=bool)
    for i, o in enumerate(sub_objects):
        mask = o.get_mask()
        full_mask += mask
        filename = OUTPUT_OBJECT_MASK_FILE_FORMAT.format(i=i)
        full_filename = os.path.join(output_dir, filename)
        np.save(full_filename, mask)
    full_filename = os.path.join(output_dir, OUTPUT_MASK_FILE)
    np.save(full_filename, full_mask)
