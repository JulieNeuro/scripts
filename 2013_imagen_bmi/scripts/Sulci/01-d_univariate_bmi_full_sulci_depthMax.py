# -*- coding: utf-8 -*-
"""
Created on Tue Sep 23 16:51:20 2014

@author: hl237680

Univariate correlation between BMI and the maximal depth of sulci of interest
on IMAGEN subjects.
The selected sulci are particularly studied because of their robustness to
the segmentation process. These sulci are respectively split into various
subsamples by the segmentation process. As a results, they have previously
been gathered again.
NB: Their features have previously been filtered by the quality control step.
(cf 00-a_quality_control.py)

The resort to sulci -instead of considering images of anatomical structures-
should prevent us from the artifacts that may be induced by the normalization
step of the segmentation process.

INPUT:
- /neurospin/brainomics/2013_imagen_bmi/data/Imagen_mainSulcalMorphometry/
  full_sulci/Quality_control/sulci_df_qc.csv:
    sulci features after quality control

- /neurospin/brainomics/2013_imagen_bmi/data/BMI.csv:
    BMI of the 1.265 subjects for which we also have neuroimaging data

METHOD: MUOLS

NB: Subcortical features, BMI and covariates are centered-scaled.

OUTPUT:
- /neurospin/brainomics/2013_imagen_bmi/data/Imagen_mainSulcalMorphometry/
  full_sulci/Quality_control/sulci_depthMax_df.csv:
    sulci maximal depth after quality control

- /neurospin/brainomics/2013_imagen_bmi/data/Imagen_mainSulcalMorphometry/
  full_sulci/Results/MULM_depthMax_after_Bonferroni_correction.txt:
    Since we focus here on the maximal depth of 85 sulci (after QC), we only
    keep the probability-values p < (0.05 / 85) that meet a significance
    threshold of 0.05 after Bonferroni correction.

- /neurospin/brainomics/2013_imagen_bmi/data/Imagen_mainSulcalMorphometry/
  full_sulci/Results/MUOLS_depthMax_beta_values_df.csv:
    Beta values from the General Linear Model run on sulci maximal depth.

"""

import os
import sys
import numpy as np
import pandas as pd
import csv

from mulm.models import MUOLS

from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.join(os.environ['HOME'], 'gits', 'scripts',
                             '2013_imagen_subdepression', 'lib'))
import utils


# Pathnames
BASE_PATH = '/neurospin/brainomics/2013_imagen_bmi/'
DATA_PATH = os.path.join(BASE_PATH, 'data')
CLINIC_DATA_PATH = os.path.join(DATA_PATH, 'clinic')
BMI_FILE = os.path.join(DATA_PATH, 'BMI.csv')
SULCI_PATH = os.path.join(DATA_PATH, 'Imagen_mainSulcalMorphometry')
FULL_SULCI_PATH = os.path.join(SULCI_PATH, 'full_sulci')
QC_PATH = os.path.join(FULL_SULCI_PATH, 'Quality_control')

# Output results
OUTPUT_DIR = os.path.join(FULL_SULCI_PATH, 'Results')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Shared data
BASE_SHARED_DIR = "/neurospin/tmp/brainomics/"
SHARED_DIR = os.path.join(BASE_SHARED_DIR,
                          'bmi_full_sulci_cache_IMAGEN')
if not os.path.exists(SHARED_DIR):
    os.makedirs(SHARED_DIR)


#############
# Read data #
#############
# Sulci and BMI
def load_residualized_bmi_data(cache):
    if not(cache):

        # BMI
        BMI_df = pd.io.parsers.read_csv(os.path.join(DATA_PATH, 'BMI.csv'),
                                     sep=',',
                                     index_col=0)

        # Sulci features
        sulci_df_qc = pd.io.parsers.read_csv(os.path.join(QC_PATH,
                                                          'sulci_df_qc.csv'),
                                              sep=',',
                                              index_col=0)

        # Extract only sulci depthMax among sulci features
        sulci_feature_colnames = []
        for sulcus_feature in sulci_df_qc.columns.tolist():
            if (sulcus_feature.find('depthMax') != -1):
                sulci_feature_colnames.append(sulcus_feature)

        sulci_depthMax_df = sulci_df_qc[sulci_feature_colnames]

        # Dataframe for picking out only clinical cofounds of non interest
        clinical_df = pd.io.parsers.read_csv(os.path.join(CLINIC_DATA_PATH,
                                                          'population.csv'),
                                             index_col=0)

        clinical_cofounds = ['Gender de Feuil2',
                             'ImagingCentreCity',
                             'tiv_gaser',
                             'mean_pds']

        clinical_df = clinical_df[clinical_cofounds]

        # Consider subjects for whom we have neuroimaging and genetic data
        subjects_id = np.genfromtxt(os.path.join(DATA_PATH,
                                                 'subjects_id.csv'),
                                    dtype=None,
                                    delimiter=',',
                                    skip_header=1)

        # Get the intersept of indices of subjects for whom we have
        # neuroimaging and genetic data, but also sulci features
        subjects_index = np.intersect1d(subjects_id,
                                        sulci_depthMax_df.index.values)

        # Check whether all these subjects are actually stored into the qc
        # dataframe
        sulci_data = sulci_depthMax_df.loc[subjects_index]

        # Keep only subjects for which we have ALL data (neuroimaging,
        # genetic data and sulci features)
        clinical_data = clinical_df.loc[subjects_index]
        BMI = BMI_df.loc[subjects_index]

        # Conversion dummy coding
        covar = utils.make_design_matrix(clinical_data,
                                    regressors=clinical_cofounds).as_matrix()

        # Center and scale covariates, but not constant regressor's column
        cov = covar[:, 0:-1]
        skl = StandardScaler()
        cov = skl.fit_transform(cov)

        # Center & scale BMI
        BMI = skl.fit_transform(BMI)

        # Center & scale sulci_data
        sulci_data = skl.fit_transform(sulci_data)
        print "Sulci data loaded."
        # Constant regressor to mimick the fit intercept
        constant_regressor = np.ones((sulci_data.shape[0], 1))

        # Concatenate BMI, constant regressor and covariates
        design_mat = np.hstack((cov, constant_regressor, BMI))

        X = design_mat
        Y = sulci_data

        np.save(os.path.join(SHARED_DIR, 'X.npy'), X)
        np.save(os.path.join(SHARED_DIR, 'Y.npy'), Y)

        print "Data saved."
    else:
        X = np.load(os.path.join(SHARED_DIR, 'X.npy'))
        Y = np.load(os.path.join(SHARED_DIR, 'Y.npy'))
        print "Data read from cache."
    return X, Y, sulci_depthMax_df


#"""#
#run#
#"""#
if __name__ == "__main__":

    # Set pathes
    WD = "/neurospin/tmp/brainomics/univariate_bmi_full_sulci_IMAGEN"
    if not os.path.exists(WD):
        os.makedirs(WD)

    print "#################"
    print "# Build dataset #"
    print "#################"

    # Load data
    X, Y, sulci_depthMax_df = load_residualized_bmi_data(cache=False)

    # Write quality control results on sulci maximal depth in a .csv file
    sulci_depthMax_df.to_csv(os.path.join(QC_PATH, 'sulci_depthMax_df.csv'))
    print "Dataframe containing sulci maximal depth after quality control has been saved."

    colnames = sulci_depthMax_df.columns
    penalty_start = 11

    # Initialize beta_map
    beta_map = np.zeros((X.shape[1], Y.shape[1]))

    print "##############################################################"
    print ("# Perform Mass-Univariate Linear Modeling "
           "based Ordinary Least Squares #")
    print "##############################################################"

    #MUOLS
    bigols = MUOLS()
    bigols.fit(X, Y)
    t, p, df = bigols.stats_t_coefficients(X, Y,
                                           contrast=[0.] * penalty_start +
                                           [1.] * (X.shape[1] - penalty_start),
                                           pval=True)

    proba = []
    for i in np.arange(0, p.shape[0]):
        if (p[i] > 0.95):
            p[i] = 1 - p[i]
        proba.append('%.15f' % p[i])

    # Beta values: coefficients of the fit
    beta_map = bigols.coef_

    beta_df = pd.DataFrame(beta_map[penalty_start:, :].transpose(),
                           index=colnames,
                           columns=['betas'])

    # Save beta values from the GLM on sulci features as a dataframe
    beta_df.to_csv(os.path.join(OUTPUT_DIR,
                                'MUOLS_depthMax_beta_values_df.csv'))
    print "Dataframe containing beta values for each sulcus has been saved."

    # Since we focus here on 85 sulci (after QC), and for each of them on
    # 6 features, we only keep the probability values p < (0.01 / (6 * 85))
    # that meet a significance threshold of 0.05 after Bonferroni correction.
    # Write results of MULM computation for each feature of interest in a
    # csv file
    # Bonferroni correction at 1% (or 5%)
    bonferroni_correction = 0.01 / (Y.shape[1])

    MULM_after_Bonferroni_correction_file_path = os.path.join(OUTPUT_DIR,
                              'MULM_depthMax_after_Bonferroni_correction.txt')

    with open(MULM_after_Bonferroni_correction_file_path, 'wb') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=' ', quotechar=' ')

        for i in np.arange(0, len(proba)):

            if float(proba[i]) < bonferroni_correction:
                sulcus_name = colnames[i][11:]
                spamwriter.writerow([
        'The MULM probability for the maximal depth of the sulcus']
        + [sulcus_name]
        + ['to be associated to the BMI is']
        + [float(proba[i]) * Y.shape[1]])