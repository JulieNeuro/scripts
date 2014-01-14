# -*- coding: utf-8 -*-
"""
Created on Fri Jan 10 18:26:06 2014

@author: md238665

Try to detect outliers:
 - compute the distance matrix between samples (with Euclidean and Hamming distance)
 - cluster data with hierarchical clustering
 - find outliers as points far to other point (on average) with the Euclidean distance
   (because it is the one used by k-means)

This is inspired by some work on hierarchical clustering in which we realized
that some points are very far from all other.

As we have binary feature vectors, Hamming distance is the same as
Euclidean distance (up to normalization).

"""

import os

import numpy as np

import scipy
import scipy.cluster.hierarchy
import scipy.spatial.distance

import pandas as pd

import nibabel

import matplotlib.pyplot as plt

##################
# Input & output #
##################

INPUT_BASE_DIR = "/neurospin/"
INPUT_DATASET_DIR = os.path.join(INPUT_BASE_DIR,
                                 "mescog", "datasets")
INPUT_DATASET = os.path.join(INPUT_DATASET_DIR,
                             "CAD-WMH-MNI.npy")
INPUT_SUBJECTS = os.path.join(INPUT_DATASET_DIR,
                              "CAD-WMH-MNI-subjects.txt")
INPUT_MNI_MASK = os.path.join(INPUT_DATASET_DIR, "MNI152_T1_2mm_brain_mask.nii.gz")

OUTPUT_BASE_DIR = "/neurospin/"
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR,
                          "mescog", "results", "wmh_patterns",
                          "outliers_detection")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

OUTPUT_EUCL_DISTANCE_MATRIX = os.path.join(OUTPUT_DIR, "euclidean_distance_matrix.full.npy")
OUTPUT_EUCL_DISTANCE_MATRIX_IMG = os.path.join(OUTPUT_DIR, "euclidean_distance_matrix.png")

OUTPUT_HAMM_DISTANCE_MATRIX = os.path.join(OUTPUT_DIR, "hamming_distance_matrix.full.npy")
OUTPUT_HAMM_DISTANCE_MATRIX_IMG = os.path.join(OUTPUT_DIR, "hamming_distance_matrix.png")

OUTPUT_LINKAGE = os.path.join(OUTPUT_DIR, "dendrogram.npy")
OUTPUT_FULL_DENDROGRAM = os.path.join(OUTPUT_DIR, "dendrogram.full.svg")
OUTPUT_LASTP_DENDROGRAM = os.path.join(OUTPUT_DIR, "dendrogram.lastp.svg")
OUTPUT_LEVEL_DENDROGRAM = os.path.join(OUTPUT_DIR, "dendrogram.level.svg")

OUTPUT_MEAN_DISTANCE_BOXPLOT = os.path.join(OUTPUT_DIR, "mean_euclidean_distance.boxplot.png")
OUTPUT_ABOVE_WHISKER_ID = os.path.join(OUTPUT_DIR, "above_upper_whisker.txt")
OUTPUT_OUTLIERS_ID = os.path.join(OUTPUT_DIR, "outliers.txt")
OUTPUT_X = os.path.join(OUTPUT_DIR, "X.npy")
OUTPUT_X_OUTSIDE = os.path.join(OUTPUT_DIR, "outliers.npy")

##############
# Parameters #
##############

#################
# Actual script #
#################

# Read input data
X = np.load(INPUT_DATASET)
n, p = s = X.shape
print "Data loaded {s}".format(s=s)

# Read subjects ID
with open(INPUT_SUBJECTS) as f:
    SUBJECTS_ID = np.array([int(l) for l in f.readlines()])

# Read mask
babel_mask = nibabel.load(INPUT_MNI_MASK)
mask = babel_mask.get_data()
binary_mask = mask != 0
mask_lin = mask.ravel()
mask_index = np.where(mask_lin)[0]

# Extract mask
X_mask = X[:, mask_index]
n, p = s = X_mask.shape
print "Masked data {s}".format(s=s)

# Euclidean distance matrix
y_eucl = scipy.spatial.distance.pdist(X_mask, metric='euclidean')
Y_eucl = scipy.spatial.distance.squareform(y_eucl)
np.save(OUTPUT_EUCL_DISTANCE_MATRIX, Y_eucl)

distance_matrix_fig = plt.figure()
plt.matshow(Y_eucl, fignum=False)
plt.colorbar()
distance_matrix_fig.suptitle('Euclidean distance matrix')
distance_matrix_fig.savefig(OUTPUT_EUCL_DISTANCE_MATRIX_IMG)

# Hamming distance matrix
y_hamm = scipy.spatial.distance.pdist(X_mask, metric='hamming')
Y_hamm = scipy.spatial.distance.squareform(y_hamm)
np.save(OUTPUT_HAMM_DISTANCE_MATRIX, Y_hamm)

distance_matrix_fig = plt.figure()
plt.matshow(Y_hamm, fignum=False)
plt.colorbar()
distance_matrix_fig.suptitle('Hamming distance matrix')
distance_matrix_fig.savefig(OUTPUT_HAMM_DISTANCE_MATRIX_IMG)

# Hierarchical clustering with Ward criterion and euclidean distance
Z = scipy.cluster.hierarchy.linkage(X_mask,
                                    method='ward',
                                    metric='euclidean')
np.save(OUTPUT_LINKAGE, Z)

# Save dendrogram
dendrogram_full_fig = plt.figure()
R_FULL = scipy.cluster.hierarchy.dendrogram(Z,
           color_threshold=1,
           distance_sort='ascending')
dendrogram_full_fig.savefig(OUTPUT_FULL_DENDROGRAM)
dendrogram_lastp_fig = plt.figure()
R_LASTP = scipy.cluster.hierarchy.dendrogram(Z,
           color_threshold=1,
           truncate_mode='lastp',
           distance_sort='ascending')
dendrogram_lastp_fig.savefig(OUTPUT_LASTP_DENDROGRAM)
R_LEVEL = scipy.cluster.hierarchy.dendrogram(Z,
           color_threshold=1,
           truncate_mode='level',
           distance_sort='ascending')
dendrogram_lastp_fig.savefig(OUTPUT_LEVEL_DENDROGRAM)

# Average euclidean distance to other points
av_eucl_dst = pd.DataFrame(Y_eucl.mean(axis=0))
distance_matrix_boxplot = plt.figure()
plt.boxplot(av_eucl_dst.as_matrix())
plt.ylabel('Average distance')
distance_matrix_boxplot.suptitle('Average euclidean distance to other points')
distance_matrix_boxplot.savefig(OUTPUT_MEAN_DISTANCE_BOXPLOT)

# Find ID of subjects that are > 3rd quartile + 1.5*IQR
# Store it in a file for later examination
av_eucl_dst_describe = av_eucl_dst.describe()
third_quartile = av_eucl_dst_describe.loc['75%']
first_quartile = av_eucl_dst_describe.loc['25%']
IQR = third_quartile - first_quartile
max_val = third_quartile + 1.5 * IQR
above_upper_whisker_index = np.where(av_eucl_dst > max_val)[0]
above_upper_whisker_id = SUBJECTS_ID[above_upper_whisker_index]

with open(OUTPUT_ABOVE_WHISKER_ID, "w") as f:
    subject_list_newline = [str(subject) + "\n" for subject in above_upper_whisker_id]
    f.writelines(subject_list_newline)

# Store data without outliers & outliers
#insider_index = np.setdiff1d(range(n), outliers_index)
#X_inside = X[insider_index]
#np.save(OUTPUT_X, X_inside)
#
#X_outside = X[outliers_index]
#np.save(OUTPUT_X_OUTSIDE, X_outside)

# Compute & plot number of non-null voxel per subject
n_vox = X_mask.sum(axis=1)
n_vox_fig = plt.figure()
plt.plot(n_vox)

n_vox_av_eucl_dst_fig = plt.figure()
plt.scatter(n_vox, av_eucl_dst)
NAME = os.path.join(OUTPUT_DIR, "average_dst_n_vox.svg")
n_vox_av_eucl_dst_fig.savefig(NAME)
NAME = os.path.join(OUTPUT_DIR, "average_dst_n_vox.annot.svg")
for i in range(n):
    plt.annotate(str(SUBJECTS_ID[i]), xy=(n_vox[i], av_eucl_dst.iloc[i]))
n_vox_av_eucl_dst_fig.savefig(NAME)
    
# visible outliers
2001, 2002, 2009, 2017, 1075
# typical samples
1167, 2086, 2024, 1022

"""
anatomist \
2001/*rFLAIR-MNI.nii.gz 2001/*rT1-MNI.nii.gz  2001/*-M0-WMH-MNI.nii.gz \
2002/*rFLAIR-MNI.nii.gz 2002/*rT1-MNI.nii.gz  2002/*-M0-WMH-MNI.nii.gz \
2009/*rFLAIR-MNI.nii.gz 2009/*rT1-MNI.nii.gz  2009/*-M0-WMH-MNI.nii.gz \
2017/*rFLAIR-MNI.nii.gz 2017/*rT1-MNI.nii.gz  2017/*-M0-WMH-MNI.nii.gz \
1075/*rFLAIR-MNI.nii.gz 1075/*rT1-MNI.nii.gz  1075/*-M0-WMH-MNI.nii.gz \
1167/*rFLAIR-MNI.nii.gz 1167/*rT1-MNI.nii.gz  1167/*-M0-WMH-MNI.nii.gz \
2086/*rFLAIR-MNI.nii.gz 2086/*rT1-MNI.nii.gz  2086/*-M0-WMH-MNI.nii.gz \
2024/*rFLAIR-MNI.nii.gz 2024/*rT1-MNI.nii.gz  2024/*-M0-WMH-MNI.nii.gz \
1022/*rFLAIR-MNI.nii.gz 1022/*rT1-MNI.nii.gz  1022/*-M0-WMH-MNI.nii.gz
"""
