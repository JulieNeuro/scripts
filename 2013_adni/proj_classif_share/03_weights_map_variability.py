# -*- coding: utf-8 -*-
"""
@author: edouard.Duchesnay@cea.fr

Compute variability over weights maps

cd /neurospin/brainomics/2013_adni
find . -name beta.npy | while read f ; do gzip $f ; done

INPUT:
- mask.nii
- glob pattern directory/*/1.1

OUTPUT: 

"""

import os
import numpy as np
import glob
import nibabel
import gzip

BASE_PATH = "/neurospin/brainomics/2013_adni"

STUDY = "proj_classif_MCIc-MCInc"
PARAMS = [\
'0.01_0.0_0.999_0.001',
'0.01_0.000999_0.998001_0.001',
'0.01_0.0_1.0_0.0',
'0.01_0.001_0.999_0.0']
#RUN = 'logistictvenet_5cv'
RUN = 'logistictvenet_2cv'

for param in PARAMS:
    #param = '0.01_0.0_0.999_0.001'
    INPUT_MASK = os.path.join(BASE_PATH, "proj_classif_MCIc-MCInc", "mask.nii")
    INPUT_PATTERN = os.path.join(BASE_PATH, "proj_classif_MCIc-MCInc",
        '%s/results/*/%s/beta.npy.gz' % (RUN, param))
    OUTPUT_DIR = os.path.join(BASE_PATH, STUDY, RUN, "weights")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    mask_image = nibabel.load(INPUT_MASK)
    mask = mask_image.get_data() != 0
    files = glob.glob(INPUT_PATTERN)
    W = list()
    for f in files:
        W.append(np.load(gzip.open(f))[3:].ravel())
    W = np.vstack(W)
    #means = np.mean(W, axis=1)[:, np.newaxis]
    #Wc = (W - means)
    #n2 = np.sqrt(np.sum(Wc ** 2, axis=1))[:, np.newaxis]
    #Ws = Wc / n2
    #print means, n2
    #print "norm 2 =", np.sqrt(np.sum(W ** 2, axis=1))
    R = np.corrcoef(W)
    #W = Ws
    print "#", param, "\t", np.mean(R[np.tri(R.shape[0], k=-1 , dtype=bool)])
    
    sd = np.std(W, axis=0)
    mean = np.mean(W, axis=0)
    sd.max()
    arr = np.zeros(mask.shape)
    arr[mask] = sd
    out_im = nibabel.Nifti1Image(arr,affine=mask_image.get_affine())
    out_im.to_filename(os.path.join(OUTPUT_DIR, param + "_sd.nii"))
    arr[mask] = mean
    out_im = nibabel.Nifti1Image(arr,affine=mask_image.get_affine())
    out_im.to_filename(os.path.join(OUTPUT_DIR, param + "_mean.nii"))

# run scripts/2013_adni/proj_classif_share/03_weights_map_variability.py

# 5cv
# 0.01_0.0_0.999_0.001 	       0.754342357596
# 0.01_0.000999_0.998001_0.001 	 0.722244719063
# 0.01_0.0_1.0_0.0 	            0.745822675348
# 0.01_0.001_0.999_0.0 	      0.712485569432
