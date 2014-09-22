# -*- coding: utf-8 -*-
"""
Created on Wed Jul 16 14:35:13 2014

@authors: Mathieu Dubois and hl237680

Simple script to try to read SNPs related to a given set of genes from the
file database.
"""

import os
import collections


################
# Input/Output #
################

INPUT_DIR = "/neurospin/brainomics/bioinformatics_resources/data/"
INPUT_REFGENE_META = os.path.join(INPUT_DIR,
                                  "genetics",
                                  "hg19.refGene.meta")
INPUT_SNP138 = os.path.join(INPUT_DIR,
                            "snps",
                            "cleaned_snp138Common.txt")


##############
# Parameters #
##############

# Main genes associated to BMI according to the literature
TEST_GENES = ['BDNF', 'CADM2', 'COL4A3BP', 'ETV5', 'FAIM2', 'FANCL', 'FTO',
              'GIPR', 'GNPDA2', 'GPRC5B', 'HMGCR', 'KCTD15', 'LMX1B',
              'LRP1B', 'LINGO2', 'MAP2K5', 'MC4R', 'MTCH2', 'MTIF3', 'NEGR1',
              'NPC1', 'NRXN3', 'NTRK2', 'NUDT3', 'POC5', 'POMC', 'PRKD1',
              'PRL', 'PTBP2', 'PTER', 'QPCTL', 'RPL27A', 'SEC16B', 'SH2B1',
              'SLC39A8', 'SREBF2', 'TFAP2B', 'TMEM160', 'TMEM18', 'TNNI3K',
              'TOMM40', 'ZNF608']


##########
# Script #
##########

print "#####################"
print "# Reading databases #"
print "#####################"


class Gene(object):
    def __init__(self, name, chrom, brin, start, stop):
        self.name = name
        self.chrom = chrom
        self.brin = brin
        self.start = start
        self.stop = stop

    def snp_is_in(self, snp):
        if (snp.chrom == self.chrom) and \
           (snp.pos >= self.start) and \
           (snp.pos <= self.stop):
            return True
        else:
            return False


class SNP(object):
    def __init__(self, name, chrom, brin, pos):
        self.name = name
        self.chrom = chrom
        self.pos = pos


# Read & parse refGene
with open(INPUT_REFGENE_META) as f:
    lines = f.readlines()
    n_genes = len(lines)
    print "Found", n_genes, "genes"
    refGenes = collections.OrderedDict()
    for line in lines:
        gene, start, stop, chrom, brin = line.split()
        refGenes[gene] = Gene(gene, chrom, brin, int(start), int(stop))
    print len(refGenes), "genes in memory"
del lines, gene, chrom, brin, start, stop


# Read & parse dbSNP
with open(INPUT_SNP138) as f:
    lines = f.readlines()
    n_snps = len(lines)
    print "Found", n_snps, "SNPs"
    dbSNP = collections.OrderedDict()
    #print "Achtung, on se limite à", MAX_SNPS, "SNPs"
    for line in lines:
        tok = line.split()
        chrom = tok[1]
        pos = int(tok[3])
        snp = tok[4]
        brin = tok[6]
        dbSNP[snp] = SNP(snp, chrom, brin, pos)
    print len(dbSNP), "SNPs in memory"
del lines, chrom, snp, pos, brin, tok


print "#############################################################"
print "# Trying to find all the SNPs for genes in BMI tested genes #"
print "#############################################################"

all_snp = collections.OrderedDict.fromkeys(TEST_GENES)
for test_gene_name in TEST_GENES:
    test_gene = refGenes[test_gene_name]
    for snp in dbSNP.values():
        if test_gene.snp_is_in(snp):
            if all_snp[test_gene_name] is None:
                all_snp[test_gene_name] = [(snp.pos, snp.name)]
            else:
                all_snp[test_gene_name].append((snp.pos, snp.name))


print "###############################################################"
print "# Compare with files generated by awk (reference_genetics.py) #"
print "###############################################################"

for gene in TEST_GENES:
    # Read reference information
    snp_file_path = os.path.join('reference_genetics/', "%s.snp" % gene)
    snp_file = open(snp_file_path, 'r').readlines()
    snp_info = []
    for line in snp_file:
        tok = line.split()
        snp_info.append((int(tok[0]), tok[1]))
    if all_snp[gene] == snp_info:
        print "Gene", gene, "is OK"
    else:
        raise Exception("Gene {gene} is different".format(gene=gene))
