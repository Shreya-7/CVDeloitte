from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory, jsonify
from pymongo import MongoClient
from bson import ObjectId
from shutil import copyfile
import os
import json
from dotenv import load_dotenv
from gevent.pywsgi import WSGIServer
load_dotenv()


from util import extract_job_keywords
from main_prediction import predict_resumes, parse_resumes
from reverse import predict

app = Flask(__name__, static_url_path='/static')
app.secret_key = "lol"
app.config["UPLOAD_FOLDER"] = "./files"
app.config['MAX_CONTENT_LENGTH'] = 4*1024*1024

client = MongoClient(os.getenv("DELOITTE_DB"))
user = client["users"]["user_details"]

job_corpus_path = "./data/CORPUS.json"
input_resumes_path = "./data/Test Resumes"
train_data_path = "./data/Train Data/data.csv"
html_path = "./data/HTML_Resumes/"
output_path = "./data/Output/"
result_path = "./data/Output/Selected"
resume_path_input = "./data/Input Resume/"
test_jobs_path = "./data/Test Jobs/"

# default signup page


@app.route("/")
def index():
    return render_template("index.html")

# after pressing signup button


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if(request.method == "GET"):
        return render_template("error.html", message="Invalid request.")
    # checking if person had previously registered
    person = user.find_one({"email": request.form.get("email")})
    if(person != None):
        message = "User already registered. Please log in."
        return render_template("index.html", message=message)

    cred = {
        "name": request.form.get("username"),
        "email": request.form.get("email"),
        "password": request.form.get("password"),
        "type": request.form["person_type"].title(),
        "organisation": request.form.get("org"),
        "filenames": {}
    }

    # creating folders using email to store associated files
    folderpath = os.path.join(app.config["UPLOAD_FOLDER"], cred["email"])
    if(str(cred["email"]) not in os.listdir(app.config["UPLOAD_FOLDER"])):
        os.mkdir(folderpath)

    user.insert_one(cred)  # inserting into database
    cred.pop('_id')

    # logging in
    session["person"] = cred
    session["folder_path"] = os.path.join(
        app.config['UPLOAD_FOLDER'], str(session["person"]["email"]))
    return redirect("/home")

# after pressing login button


@app.route("/login", methods=["GET", "POST"])
def login():
    if(request.method == "GET"):
        return render_template("error.html", message="Invalid request.")

    email = request.form.get("email")
    password = request.form.get("password")
    message = ""
    person = user.find_one({"email": email})

    if(person != None):
        # login logic
        if(password == person["password"]):
            person.pop('_id')
            session["person"] = person
            session["folder_path"] = os.path.join(
                app.config['UPLOAD_FOLDER'], str(session["person"]["email"]))
            return redirect("/home")
        else:
            message = "Incorrect password."
    else:
        message = "Not registered. Please sign up."

    return render_template("index.html", message=message)


@app.route("/home")
def home():
    if("person" not in session.keys()):  # if not logged in
        return redirect("/")
    return render_template("home.html", details=session["person"])

# after submitting a file for upload


@app.route("/upload", methods=["GET", "POST"])
def upload():

    if("person" not in session.keys()):  # if not logged in
        return redirect("/")

    if request.method == "GET":
        return render_template("error.html", message="Invalid request.")

    if request.method == 'POST':
        f = request.files['file']
        temp, extension = os.path.splitext(f.filename)
        # saving file to user folder
        obj = user.find_one(
            {"email": session["person"]["email"]}, {"filenames": 1})
        # if(temp in obj["filenames"].keys()):
        #     return render_template("error.html", message="You have already uploaded this file. Please check your file history :)")
        f.save(os.path.join(session["folder_path"], f.filename))
        # saving file to processing folder
        copyfile(os.path.join(session["folder_path"], f.filename), os.path.join(
            resume_path_input, f.filename))

        session["current_file"] = f.filename

        # save to document - filename and json filename
        jsonfile = temp+".json"  # can be queried
        user.update_one({"email": session["person"]["email"]}, {"$set": {
                        "filenames."+temp: {"extension": extension, "json": jsonfile, "results": [], "processed": 0}}})

        # "jsonify" the file and save in filesystem
        jsonified = extract_job_keywords(os.path.join(
            session["folder_path"], f.filename), job_corpus_path, session["folder_path"])
        with open(os.path.join(session["folder_path"], jsonfile), 'w') as fp:
            json.dump(jsonified, fp)

        # show results after processing
        return redirect("/" + temp)

# for exceeding file size


@app.errorhandler(413)
def error413(e):
    flash(message="File size exceeded!", category=error)
    return render_template("error.html", message="The file could not be uploaded.")

# show results after processing for passed filename


@ app.route("/<filename>")
def getresults(filename):

    if("person" not in session.keys()):  # if not logged in
        return redirect("/")

    obj = user.find_one({"email": session["person"]["email"]})
    # if file doesnt exist(invalid url)
    if(filename not in obj["filenames"].keys()):
        return render_template("error.html", message="Invalid filename.")

    temp = filename  # only filename, without extension
    extension = obj["filenames"][temp]["extension"]
    filename = temp+extension

    jsonfile = temp+".json"
    filepath = os.path.join(session["folder_path"], jsonfile)
    jsontext = json.load(open(filepath, "r"))

    # if not processed already
    if(obj["filenames"][temp]["processed"] == 0):
        print("Processing file..")

        # try:
        if(obj["type"] == "Employer"):  # job as input
            predict(filepath, job_corpus_path, result_path,
                    client["users"], "jobs")
        else:  # resume as input
            predict(filepath, job_corpus_path,
                    result_path, client["users"], "resumes")
        # except:
        #     return render_template("error.html", message="An error occured when processing the file. Please try later.")

        # saving results
        selected_resumes = sorted(os.listdir(result_path))
        user.update_one({"email": session["person"]["email"]}, {"$addToSet": {
                        "filenames."+temp+".results": {"$each": [temp+i for i in selected_resumes]}}})
        for i in selected_resumes:
            copyfile(os.path.join(result_path, i),
                     os.path.join(session["folder_path"], temp+i))
        user.update_one({"email": session["person"]["email"]}, {
                        "$set": {"filenames."+temp+".processed": 1}})

        # delete all extra files made
        delete_files(selected_resumes, 'selected_resumes.csv')
    else:
        print("Showing pre-processed results..")

    details = user.find_one({"email": session["person"]["email"]})

    return render_template("results.html", details=details, json=jsontext, current=temp)


@ app.route("/logout")
def logout():
    if("person" not in session.keys()):  # if not logged in
        return redirect("/")
    session.pop("person", None)
    # go back to main login/signup screen
    return render_template("index.html")

# show usage history of user with clickable links


@ app.route("/history")
def history():
    if("person" not in session.keys()):  # if not logged in
        return redirect("/")
    details = user.find_one({"email": session["person"]["email"]})
    return render_template("history.html", details=details)


@ app.route("/download/<filename>")
def download(filename):
    print(os.path.join(app.config["UPLOAD_FOLDER"],
                       session["person"]["email"]))
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], session["person"]["email"]), filename, as_attachment=True)


def delete_files(selected_resumes, temp):
    try:
        htmls = os.listdir(html_path)
        for i in htmls:
            os.remove(os.path.join(html_path, i))

        htmls = os.listdir(resume_path_input)
        for i in htmls:
            os.remove(os.path.join(resume_path_input, i))

        selected_resumes = sorted(os.listdir(result_path))
        for i in selected_resumes:
            os.remove(os.path.join(result_path, i))

        os.remove(resume_path_input+temp+".html")
        os.remove("./data/Output/parsed_resume.csv")
        os.remove("./data/Output/selected_jobs.csv")
    except:
        return render_template("error.html", message="An error occured when processing the file. Please try later.")
if __name__=="__main__":
	http_server = WSGIServer(('0.0.0.0',80),app)
	http_server.serve_forever()
