import spacy
import os
import pandas as pd
import pdftotree
import mammoth
from tqdm import tqdm
from bs4 import BeautifulSoup as bs
import sys
import re
import json
import logging
import warnings
import xgboost

if not sys.warnoptions:
    import os
    import warnings
    warnings.simplefilter("ignore")  # Change the filter in this process
    os.environ["PYTHONWARNINGS"] = "ignore"


def term_count(string_to_search, term):
    # try:
    term = term.replace('+', '\+').replace('.', '\.')
    if len(term) == 1:
        term = ' '+term
    string_to_search = string_to_search.replace('. ', '.')
    regular_expression = re.compile(
        rf'{term}(?:\s+|$|\(|\)|,)', re.IGNORECASE)
    result = re.findall(regular_expression, string_to_search)
    return len(result)
    # except Exception:
    #     logging.error('Error occurred during regex search')
    #     return 0


def extract_email_and_phone(string):
    email = re.findall(r'\w+[.]?\w*@\w+[.]+\w+[.]?\w*', string)
    phone_no = re.findall(
        r'[+]?[(]?\d*[)]?[-]?[\ ]?\d[\ ]*\d[\ ]*\d[\ ]*\d[\ ]*\d[\ ]*\d[\ ]*\d[\ ]*\d[\ ]*\d*[\ ]*\d*', string)
    if len(email) > 0:
        email = email[0]
    else:
        email = ''
    if len(phone_no) > 0:
        phone_no = phone_no[0]
    else:
        phone_no = ''
    return (email, phone_no)


def candidate_name_extractor(input_string, nlp):

    doc = nlp(input_string)
    doc_entities = doc.ents
    doc_persons = filter(lambda x: x.label_ == 'PERSON', doc_entities)
    doc_persons = filter(lambda x: len(
        x.text.strip().split()) >= 2, doc_persons)
    doc_persons = map(lambda x: x.text.strip(), doc_persons)
    doc_persons = list(doc_persons)

    if len(doc_persons) > 0:
        return doc_persons[0]
    return "NOT FOUND"


def get_job_skills(job_path):
    with open(job_path, 'r') as fp:
        details = json.load(fp)
    return details


def match_keywords(text, keywords):
    skills = {}
    for k, skill in keywords.items():
        if k.lower() != "Specialization".lower():
            count = 0
            for s in skill:
                count += term_count(text, s)
            skills[k] = count
        else:
            for s in skill:
                skills[s] = term_count(text, s)
    return skills


def file2html(filepath, htmlpath):
    # if os.path.exists(htmlpath+.split('.')[0]+'.html'):
    #     print(htmlpath+f.split('.')[0]+'.html'+' exists')
    # try:
    if filepath[-4:] == 'docx':
        fr = open(filepath, 'rb')
        fw = open(filepath[:-4]+'html', 'wb')
        decoded = mammoth.convert_to_html(fr)
        fw.write(decoded.value.encode('utf-8'))
        path = filepath[:-4]+'html'
    else:
        print(htmlpath, filepath)
        warnings.simplefilter('ignore')
        print(pdftotree.parse(filepath, html_path=htmlpath+'/'))
        path = filepath[:-3]+'html'
    return path
    # except:
    #     return ""


def html2text(htmlpath):
    return bs(open(htmlpath)).text


def resume_details_extraction(resume_text, job_path):
    resume_dict = []
    job_keywords = get_job_skills(job_path)
    nlp = spacy.load('en_core_web_lg')
    for resume in resume_text:
        person = {}
        person['name'] = candidate_name_extractor(resume[0].text, nlp)
        person['email'], person['phone'] = extract_email_and_phone(
            resume[0].text)
        person.update(match_keywords(resume[0].text, job_keywords))
        file_name = resume[1][:-4]+'pdf'
        person['pdf_name'] = file_name
        resume_dict.append(person)
    return resume_dict


def extract_job_keywords(input_path, job_corpus_path, html_path, output_path=None):
    if input_path.split('.')[-1] in ['pdf', 'docx']:
        html_path = file2html(input_path, html_path)
        raw_job_data = html2text(html_path)
    elif input_path.split('.')[-1] == 'json':
        raw_job_data = str(json.load(open(input_path, 'r')))
    else:
        with open(input_path, 'r') as fp:
            raw_job_data = fp.read()
    job_keywords = {}
    with open(job_corpus_path, 'r') as fp:
        job_corpus = json.load(fp)
    for i, j in job_corpus.items():
        job_keywords[i] = []
        for k in j:
            cnt = 0
            # for line in raw_job_data:
            cnt += term_count(raw_job_data, k)
            if cnt > 0:
                job_keywords[i].append(k)
    return job_keywords
