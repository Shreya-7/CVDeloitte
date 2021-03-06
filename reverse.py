import os
import glob
import pandas as pd
import json
import re
import pdftotree
from bs4 import BeautifulSoup as bs
import util
from sklearn.cluster import KMeans


def predict(resume1, job_corpus_path, output_path, db, typ):
    if typ == "resumes":
        search_type = "jobs"
    else:
        search_type = "resumes"
    jobs = list(db[search_type].find({}, {'_id': False}))
    resume = json.load(open(resume1, 'r'))
    r = {}
    r['name'] = resume1.split('/')[-1]
    r['path'] = resume1.replace(r['name'], '')
    for x, y in resume.items():
        for z in y:
            r[z.replace('.', '_')] = 1
    db[typ].insert_one(r)
    r.pop('_id')
    jobs.append(r)
    train_data = pd.DataFrame(jobs).fillna(0)
    cluster = train_kmeans(train_data)
    df = pd.DataFrame(cluster, columns=['Jobs'])
    df.to_csv(os.path.join(output_path, 'selected_resumes.csv'))


def train_kmeans(data):
    train_X = data.values[:, 2:]
    data = data.to_dict('records')
    km = KMeans(max_iter=128, n_clusters=12)
    km.fit(train_X)
    labels = km.labels_
    cluster = {}
    for i in range(len(labels[:-1])):
        if data[i]['path'] == 0:
            continue
        try:
            cluster[labels[i]].append(
                str(data[i]['path'])+'/'+str(data[i]['name']))
        except:
            cluster[labels[i]] = [
                str(data[i]['path'])+'/'+str(data[i]['name'])]
    return cluster[labels[-1]]
