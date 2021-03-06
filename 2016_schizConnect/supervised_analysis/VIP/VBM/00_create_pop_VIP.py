#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  9 14:04:05 2017

@author: ad247405
"""

#import os
#import numpy as np
#import pandas as pd
#import re
#import glob
#
#
#BASE_PATH = "/neurospin/brainomics/2016_schizConnect/analysis/VIP"
#INPUT_CLINIC_FILENAME =  '/neurospin/brainomics/2016_schizConnect/analysis/VIP/sujets_series.xls'
#OUTPUT_CSV = "/neurospin/brainomics/2016_schizConnect/analysis/VIP/population.csv"
#
#clinic = pd.read_excel(INPUT_CLINIC_FILENAME)
#assert clinic.shape == (139,23)
#
##Remove subjects that are not SCZ or Controls
#clinic = clinic[clinic.diagnostic !=2]
#assert clinic.shape == (101,23)
#clinic = clinic[clinic.diagnostic !=4]
#assert clinic.shape == (100,23)
#clinic = clinic[clinic.diagnostic.isnull()!= True]
#assert clinic.shape == (99,23)
#
#
#clinic["path_subject"] = "/neurospin/lnao/Pdiff/josselin/ellen/VIP/subjects/"+  (clinic["nip"]).values
#clinic["path_t1"] = (clinic["path_subject"]).values + "/fMRI/acquisition1/"+ clinic["nip"].values +".nii"
#list_subjects = clinic.nip.values
#clinic.to_csv(OUTPUT_CSV, index=False)
#
#
#
#
#OUTPUT_DATA = "/neurospin/brainomics/2016_schizConnect/analysis/VIP/data"
##script to find out missing images
#for p in clinic["path_t1"].values:
#    print(p)
#    new_path = "/neurospin/brainomics/2016_schizConnect/analysis/VIP/data"
#    cmd = "cp " + p + " " + new_path
#    a = os.system(cmd)
#    if a!=0:
#        print("ISSUE")

##################################################################################################


#   import os
import numpy as np
import pandas as pd
import glob

INPUT_DATA = "/neurospin/brainomics/2016_schizConnect/analysis/VIP/data"
BASE_PATH = '/neurospin/brainomics/2016_schizConnect/analysis/VIP/VBM'
INPUT_CLINIC_FILENAME =  '/neurospin/brainomics/2016_schizConnect/analysis/VIP/sujets_series.xls'
INPUT_CLINIC_SCORE = "/neurospin/brainomics/2016_schizConnect/analysis/VIP/Extraction_VIP_TOTAL_20151106 .csv"
OUTPUT_CSV = os.path.join(BASE_PATH,"population.csv")
OUTPUT_CSV_SCORES = os.path.join(BASE_PATH,"population_and_scores.csv")






scores = pd.read_csv(INPUT_CLINIC_SCORE,delimiter = ";",encoding = "ISO-8859-1")
#scores = scores[["code_patient","PANSS_NEGATIVE","PANSS_POSITIVE","PANSS_GALPSYCHOPAT",\
              "PANSS_COMPOSITE","CDSS_Total","FAST_TOT",\
#                 "PANSS_N1","PANSS_N2","PANSS_N3","PANSS_N4","PANSS_N5","PANSS_N6","PANSS_N7",\
#"TTT_VIE_NEURO_AAO",\
#"TTT_VIE_ANTIPSY_AAO",\
#"MEDNOM1","MEDLIATC1","MEDIND1","MEDPOSO1",
#"MEDNOM2","MEDLIATC2","MEDIND2","MEDPOSO2",
#"MEDNOM3","MEDLIATC3","MEDIND3","MEDPOSO3",
#"MEDNOM4","MEDLIATC4","MEDIND4","MEDPOSO4",
#"MEDNOM5","MEDLIATC5","MEDIND5","MEDPOSO5",
#"MEDNOM6","MEDLIATC6","MEDIND6","MEDPOSO6",
#"MEDNOM7","MEDLIATC7","MEDIND7","MEDPOSO7",
#"MEDNOM8","MEDLIATC8","MEDIND8","MEDPOSO8",
#"MEDNOM9","MEDLIATC9","MEDIND9","MEDPOSO9"]]

scores.set_value(477,"code_patient","C0828-001-207-001")
scores.set_value(478,"code_patient","C0828-001-208-001")
scores.set_value(479,"code_patient","C0828-001-209-001")

scores["code_patient"][477] = "C0828-001-207-001"
scores["code_patient"][478] = "C0828-001-208-001"
scores["code_patient"][479] = "C0828-001-209-001"

scores["code_vip"] = scores["code_patient"]


#
#scores.loc[len(scores)] = ["C0828-001-207-001","","","","","","","","",\
#"","","","","","","","","","","","","","","","","","","","","","","","","","",\
#"","","","","","","",\
#"","","","","","","","","","","C0828-001-207-001"]
#scores.loc[len(scores)] = ["C0828-001-208-001","","","","","","","","",\
#"","","","","","","","","","","","","","","","","","","","","","","","","","",\
#"","","","","","","",\
#"","","","","","","","","","","C0828-001-208-001"]
#scores.loc[len(scores)] = ["C0828-001-209-001","","","","","","","","",\
#"","","","","","","","","","","","","","","","","","","","","","","","","","",\
#"","","","","","","",\
#"","","","","","","","","","","C0828-001-209-001"]
#

# Read clinic data
clinic = pd.read_excel(INPUT_CLINIC_FILENAME)
clinic = clinic[clinic.diagnostic !=2]
clinic = clinic[clinic.diagnostic !=4]
clinic = clinic[clinic.diagnostic.isnull()!= True]
assert clinic.shape ==(99, 23)



# Read subjects with image
subjects = list()
path_subjects= list()
paths = glob.glob(os.path.join(INPUT_DATA,"mwc1*.nii"))
for i in range(len(paths)):
    path_subjects.append(paths[i])
    subjects.append(os.path.split(paths[i])[1][4:-4])



pop = pd.DataFrame(subjects, columns=["nip"])
pop["path_VBM"] = path_subjects
assert pop.shape == (92, 2)


pop = clinic.merge(pop, on = "nip")
assert pop.shape == (92, 24)


pop = pop.merge(scores,on="code_vip")
assert pop.shape ==(92, 69)

# Map group
DX_MAP = {1.0: 0, 3.0: 1}
SEX_MAP = {1.0: 0, 2.0: 1.0}
pop['dx'] = pop["diagnostic"].map(DX_MAP)
pop['sex_code'] = pop["sexe_x"].map(SEX_MAP)


assert sum(pop.dx.values==0) == 53
assert sum(pop.dx.values==1) == 39
assert sum(pop.sex_code.values==0) == 51
assert sum(pop.sex_code.values==1) == 41

from datetime import datetime, timedelta

pd.to_datetime(pop["ddn"])
pd.to_datetime(pop["acq date"],format='%Y%m%d')
pop.age_days = pd.to_datetime(pop["acq date"],format='%Y%m%d') - pd.to_datetime(pop["ddn"])
pop['age'] = pop.age_days/ timedelta(days=365)

# Save population information
pop.to_csv(OUTPUT_CSV_SCORES , index=False)

##############################################################################
