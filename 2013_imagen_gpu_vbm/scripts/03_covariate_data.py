# -*- coding: utf-8 -*-
"""
Created on Mon Nov 5th 2013

@author: vf140245

This script perform :
    - the writing in a hdf5 

It uses a recent version of igutils.
The git repository can be cloned at https://github.com:VincentFrouin/igutils.git

Add the following in the script supposing you cloned the repos in ~/gits
import sys
sys.path.append('~/gits/igutils')

"""
import sys
import getpass
sys.path.append('/home/vf140245/gits/igutils')
import os
import igutils as ig
import numpy as np


def convert_path(path):
    if getpass.getuser() == "jl237561":
        path = '~' + path
        path = os.path.expanduser(path)
    return path

# Input
BASE_DIR='/neurospin/brainomics/2013_imagen_bmi/'
BASE_DIR = convert_path(BASE_DIR)
DATA_DIR=os.path.join(BASE_DIR, 'data')
CLINIC_DIR=os.path.join(DATA_DIR, 'clinic')


cfn = os.path.join(CLINIC_DIR, '1534bmi-vincent2.csv')
# load this file to check that there are 1534 common subjects accros
#   - csv file
#   - genotyping file
#   - image file

covdata = open(cfn).read().split('\n')[:-1]
cov_header = covdata[0]
covdata = covdata[1:]
cov_subj = ["%012d"%int(i.split(',')[0]) for i in covdata]

gfn = os.path.join(DATA_DIR, 'qc_sub_qc_gen_all_snps_common_autosome')
genotype = ig.Geno(gfn)
geno_subj = genotype.assayIID()

nb_samples = len(set(cov_subj).intersection(set(geno_subj)))

indices_cov_subj = np.in1d(np.asarray(cov_subj), np.asarray(geno_subj))
indices_geno_subj = np.in1d(np.asarray(geno_subj), np.asarray(cov_subj))

print "intersetion nb = ", len(set(cov_subj).intersection(set(geno_subj)))
print "nb from indices_cov_subj =", np.sum(indices_cov_subj)
print "nb from indices_geno_subj =", np.sum(indices_geno_subj)

nb_cols = len(covdata[0].split(',')[1:-1])
covdata_table = np.asarray([i.split(',')[1:-1] for i in covdata])
covdata[indices_cov_subj]
len(np.asarray(covdata)[indices_cov_subj])


#
data.shape
data.dtype
data.size
np.unique(data)
data.shape
genotype.assayIID()
genotype.snpList()
len(genotype.snpList())

#Prepare the data
# - imput with the median 128=Nan
# - get the list of individuals
# - get the list of SNPs
#Push it in an hdf5 cache file
