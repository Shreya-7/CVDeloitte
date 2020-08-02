import os
import glob
import pandas as pd
import json
import re
import pdftotree
from bs4 import BeautifulSoup as bs
import util


def predict_jobs(resume1, job_corpus_path, jobs_folder, output_path, filepath):

    resume1=util.html2text(resume1)

    file='resume'+'.txt'
    file1=open(file,'w')
    file1.write(resume1[0][0].text)
    file1.close()

    with open(filepath) as json_file:
        resume_keys = json.load(json_file)

    jobs = []
    for i in os.listdir(jobs_folder):
        try:
            with open(jobs_folder + i, encoding = 'utf8') as fp:
                jobs.append(fp.read())
        except:
            continue
    
    d = []
    for i in jobs:
        d.append(util.match_keywords(i,resume_keys))

    m = []
    for i in jobs:
        m.append(i.split('\n')[0])

    p = pd.DataFrame(d)
    p['Job Name'] = m
    c = p.set_index('Job Name')

    c.to_csv(os.path.join(output_path, "selected_jobs.csv"))
