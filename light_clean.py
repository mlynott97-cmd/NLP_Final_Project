#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 10:37:27 2026

@author: paulinaoliva
"""


import pandas as pd

out_path = "/Users/paulinaoliva/OneDrive/School/MS/NLP/out/"
data_path = "/Users/paulinaoliva/Library/CloudStorage/OneDrive-Personal/School/MS/NLP//NLP_final_corpus.csv"

# Load Data
raw_data = pd.read_csv(data_path)

# Removing duplicate articles
raw_data.shape
raw_data = raw_data.drop_duplicates(subset=["body"], keep= "first")
raw_data = raw_data.reset_index(drop=True)
raw_data.shape

# Removing copyright 

def remove_copyright(c_in):
    markers = [
        "Copyright Targeted News Services",
        "* * * Original text here:",
        "TM & ©",
        "Copyright ©",
        "All rights reserved"      
    ]
    tmp = c_in
    for m in markers:
        if m in tmp:
            tmp = tmp. split(m)[0]
    return tmp

raw_data["body_nocopyright"] = raw_data["body"].apply(remove_copyright)

# Cleaning

def clean(c_in):
    import re 
    new_text = re.sub(r"\s+", " ", c_in).strip()
    return new_text

raw_data["body_clean"] = raw_data["body_nocopyright"].apply(clean)

# Tokens

def tok_count(c_in, s_in):
    if s_in == "unique":
        cnt = len(set(c_in.split()))
    else:
        cnt = len(c_in.split())
    return cnt

raw_data["tokens"] = raw_data["body_clean"].apply(lambda x: x.split())
raw_data["tok_count"] = raw_data["body_clean"].apply(lambda x: tok_count(x,"total"))

# Saving

def write_pickle(obj_in, path_in, name_in):
    import pickle
    pickle.dump(obj_in, open(path_in + name_in +".pk", "wb"))
    
write_pickle(raw_data, out_path, "clean_corpus")
raw_data.to_csv(out_path + "clean_corpus.csv", index=False)



