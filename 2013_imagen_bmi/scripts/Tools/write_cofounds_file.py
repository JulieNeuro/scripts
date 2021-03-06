# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 09:56:26 2014

@author: hl237680

Generation of a dataframe containing cofounds of non interest (i.e. gender,
imaging city centre, tiv_gaser and mean pds) for the 745 subjects who passed
the quality control on sulci data for further use with Plink.


BEWARE!!!
- the first two columns must be IID and FID
- categorical variables require dummy coding


INPUT:
- "/neurospin/brainomics/2013_imagen_bmi/data/clinic/source_SHFJ/
    1534bmi-vincent2.xls"
    clinical data on IMAGEN population (.xls initial data file)
- "/neurospin/brainomics/2013_imagen_bmi/data/Imagen_mainSulcalMorphometry/
    full_sulci/Quality_control/sulci_depthMax_df.csv":
    sulci depthMax after quality control

OUTPUT:
- "/neurospin/brainomics/2013_imagen_bmi/data/genetics/Plink/Sulci_SNPs/
    confound_Gender_Centre_TIV_PDS_745id.cov:"
    .cov file with FID - IID - Gender - Centre - TIV - PDS

"""


import os
import csv
import xlrd
import pandas as pd


# Pathnames
BASE_PATH = '/neurospin/brainomics/2013_imagen_bmi/'
DATA_PATH = os.path.join(BASE_PATH, 'data')
CLINIC_DATA_PATH = os.path.join(DATA_PATH, 'clinic')
SHFJ_DATA_PATH = os.path.join(CLINIC_DATA_PATH, 'source_SHFJ')
SULCI_PATH = os.path.join(DATA_PATH, 'Imagen_mainSulcalMorphometry')
FULL_SULCI_PATH = os.path.join(SULCI_PATH, 'full_sulci')
QC_PATH = os.path.join(FULL_SULCI_PATH, 'Quality_control')
GENETICS_PATH = os.path.join(DATA_PATH, 'genetics')
PLINK_GENETICS_PATH = os.path.join(GENETICS_PATH, 'Plink')
SULCI_SNPS_PLINK_PATH = os.path.join(PLINK_GENETICS_PATH, 'Sulci_SNPs')
COFOUND_FILE = os.path.join(SULCI_SNPS_PLINK_PATH,
                            'confound_Gender_Centre_TIV_PDS_745id.cov')


# Excel file containing clinical data of the 1.265 subjects for whom we
# have both neuroimaging and genetic data
workbook = xlrd.open_workbook(os.path.join(SHFJ_DATA_PATH,
                                           '1534bmi-vincent2.xls'))
# Dataframe with right indexes
clinical_data_df = pd.io.excel.read_excel(workbook,
                                          sheetname='1534bmi-gaser.xls',
                                          engine='xlrd',
                                          header=0,
                                          index_col=0)

# Cofounds of non interest (dummy coding for categorical variables - Gender
# and Centre)
cofounds = ['Gender',
            'Londres',
            'Nottingham',
            'Dublin',
            'Berlin',
            'Hambourg',
            'Mannheim',
            'Paris',
            'tiv_gaser',
            'mean_pds']

#clinical_data_df = clinical_data_df[cofounds]

# Sulci features
sulci_depthMax_df = pd.io.parsers.read_csv(os.path.join(QC_PATH,
                                                    'sulci_depthMax_df.csv'),
                                           sep=',',
                                           index_col=0)

# Keep only subjects who passed the QC on sulci data
subjects_id_list = sulci_depthMax_df.index.values.tolist()

# Dataframe containing only non interest covariates for selected subjects
cofounds_df = clinical_data_df[cofounds].loc[subjects_id_list]

# Write .cov file
fp = open(COFOUND_FILE, 'wb')
cw = csv.writer(fp, delimiter=' ')
cw.writerow(['FID',
             'IID',
             'Gender',
             'Londres',
             'Nottingham',
             'Dublin',
             'Berlin',
             'Hambourg',
             'Mannheim',
             'Paris',
             'TIV',
             'PDS'])

for i, s in enumerate(subjects_id_list):
    tmp = []
    # Family ID (FID)
    tmp.append('%012d' % (int(s)))
    # Individual ID (IID)
    tmp.append('%012d' % (int(s)))
    # Gender
    tmp.append('%s' % (cofounds_df['Gender'].loc[s]))
    # Imaging centre city
    tmp.append('%s' % (cofounds_df['Londres'].loc[s]))
    tmp.append('%s' % (cofounds_df['Nottingham'].loc[s]))
    tmp.append('%s' % (cofounds_df['Dublin'].loc[s]))
    tmp.append('%s' % (cofounds_df['Berlin'].loc[s]))
    tmp.append('%s' % (cofounds_df['Hambourg'].loc[s]))
    tmp.append('%s' % (cofounds_df['Mannheim'].loc[s]))
    tmp.append('%s' % (cofounds_df['Paris'].loc[s]))
    # TIV
    tmp.append('%.5f' % (cofounds_df['tiv_gaser'].loc[s]))
    # PDS
    tmp.append('%.1f' % (cofounds_df['mean_pds'].loc[s]))
    cw.writerow(tmp)
fp.close()

print ('Cofounds file has been saved under: "/neurospin/brainomics/2013_imagen_bmi/data/genetics/Plink/Sulci_SNPs/confound_Gender_Centre_TIV_PDS_745id.cov".')