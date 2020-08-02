import os
import json
import xgboost
from shutil import copyfile
import pandas as pd
import util

model_path = './data/job_model.dat'

training_data_path = './data/Train Data/data.csv'

resume_path = './data/Test Resumes/'

parsed_resume_path = './data/Output/parsed_resume.csv'

def parse_resumes(input_resumes_path, html_path, output_path, job_path):

    html = util.file2html(filepath=input_resumes_path, htmlpath=html_path)
    resume_text = util.html2text(html_path)
    data = util.resume_details_extraction(resume_text, job_path)
    pd.DataFrame(data).to_csv(parsed_resume_path)

def predict_resumes(job_desc_path, output_path):
    print("Job description path: ", job_desc_path)
    xgb = xgboost.XGBClassifier()
    
    temp, extension = os.path.splitext(job_desc_path)
    job_desc_path = temp + '.json'
    

    with open(job_desc_path, 'r') as fp:
        job_keywords = json.load(fp)
    
    keys = list(job_keywords.keys())
    new_keys = []
    for i in range(len(keys)):
        if keys[i] == 'specialization':
            for j in job_keywords[keys[i]]:
                new_keys.append(j)
        else:
            new_keys.append(keys[i])
    keys = new_keys

    print("Keys: ", keys)

    if os.path.exists(model_path):
    
        xgb.load_model(model_path)
        print("loading {} model".format(model_path))

    else:

        print("No model present, Training using {}".format(training_data_path))

        data = pd.read_csv(training_data_path)
        
        
        train_x = data[keys].values
        train_y = data[['status']].values
        
        xgb.fit(train_x, train_y)

        xgb.save_model('job_model.dat')


    test_data = pd.read_csv(parsed_resume_path)

    test_x = test_data[keys].values

    test_y = xgb.predict(test_x)

    test_dict = test_data.to_dict('records')

    for i in range(len(test_x)):
        if test_y[i] == 'Yes':
            pdf_name = test_dict[i]['pdf_name']
            #print(pdf_name, "selected, pdf being saved in ./data/Output/Selected Resumes")
            copyfile(resume_path+pdf_name, output_path + "/"+pdf_name)
