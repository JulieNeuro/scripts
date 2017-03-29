#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 10 11:43:27 2017

@author: ad247405
"""

import os
import numpy as np
import pandas as pd
import re
import glob



BASE_PATH = "/neurospin/brainomics/2016_schizConnect/analysis/all_studies/Freesurfer/all_subjects_less_than_50years"
INPUT_CLINIC_FILENAME =  '/neurospin/brainomics/2016_schizConnect/completed_schizconnect_metaData_1829.csv'
OUTPUT_CSV = os.path.join(BASE_PATH,"population.csv")


INPUT_CSV_COBRE = "/neurospin/brainomics/2016_schizConnect/analysis/COBRE/Freesurfer/population.csv"
INPUT_CSV_NMorphCH = "/neurospin/brainomics/2016_schizConnect/analysis/NMorphCH/Freesurfer/population.csv"
INPUT_CSV_NUSDAST = "/neurospin/brainomics/2016_schizConnect/analysis/NUSDAST/Freesurfer/population.csv"


clinic_COBRE = pd.read_csv(INPUT_CSV_COBRE)
clinic_NMorphCH = pd.read_csv(INPUT_CSV_NMorphCH)
clinic_NUSDAST = pd.read_csv(INPUT_CSV_NUSDAST)


all_clinic = [clinic_COBRE, clinic_NMorphCH, clinic_NUSDAST]
pop = pd.concat(all_clinic)

#Only subjects less than 50 years old
pop = pop[pop.age<50]

#pop.site.unique() 
SITE_MAP = {'MRN': 1, 'NU': 2, "WUSTL" : 3}
pop['site_num'] = pop["site"].map(SITE_MAP)
assert sum(pop.site_num.values==1) == 131
assert sum(pop.site_num.values==2) == 82
assert sum(pop.site_num.values==3) == 235




assert sum(pop.dx_num.values==0) == 251
assert sum(pop.dx_num.values==1) == 197

assert sum(pop.sex_num.values==0) == 279
assert sum(pop.sex_num.values==1) == 169


# Save population information
pop.to_csv(OUTPUT_CSV, index=False)
