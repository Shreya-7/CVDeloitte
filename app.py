#for testing

from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
import os
import time
import json

app=Flask(__name__,static_url_path='/static')
app.secret_key = "lol"
app.config["UPLOAD_FOLDER"] = "./files"
app.config['MAX_CONTENT_LENGTH'] = 4*1024*1024

info = {} #database
people = {} #only for login ease
id = 1 # ID counter

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=["POST"])
def signup():
    global id
    cred = {}
    cred["id"] = id
    cred["name"] = request.form.get("username")
    cred["email"] = request.form.get("email")
    cred["password"] = request.form.get("password")
    cred["type"] = request.form["person_type"].title()
    cred["org"] = request.form.get("org")
    cred["past"] = []
    cred["current_file"] = ""

    #creating folders using ID to store associated files
    folderpath = os.path.join(app.config["UPLOAD_FOLDER"], str(id))
    if(str(id) not in os.listdir(app.config["UPLOAD_FOLDER"])):
        os.mkdir(folderpath)

    info[id] = cred
    people[cred["email"]] = cred["password"]
    id+=1

    return render_template("index.html", message = "Successfully registered! Please log in.")

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    message = ""
    if(email in people.keys()):
        #login logic
        if(password==people[email]):
            #finding "person" using email to load details into session
            for x in info.values():
                if(x["email"]==email):
                    session["person"] = x
            return redirect("/home")
        else:
            message = "Incorrect password."
    else:
        message = "Not registered. Please sign up."

    return render_template("index.html", message = message)

@app.route("/home")
def home():    
    return render_template("home.html", details = session["person"])

#after submitting a file for upload
@app.route("/upload", methods=["POST"])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],str(session["person"]["id"]),f.filename))
        
        #updating "database" and session variables
        info[session["person"]["id"]]["past"].append({f.filename: ["gfg.py"]})
        info[session["person"]["id"]]["current_file"]  = f.filename
        session["person"]["past"].append({f.filename: []})
        #TBD: either move result files in the directory or add in path
        #show results after processing
        return redirect("/getresults/" + f.filename)       

#for exceeding file size
@app.errorhandler(413)
def error413(e):
    flash(message="File size exceeded!", category=error)
    return render_template("error.html", message="The file could not be uploaded.")

#show results after processing for passed filename
#TBD: add processing logic file
@app.route("/getresults/<filename>")
def getresults(filename):
    input_file = session["person"]["current_file"]
    
    info[session["person"]["id"]]["current_file"] = filename

    #.json filename is "filename".json
    temp, extension = os.path.splitext(filename)
    jsonfile = temp+".json"
    #TBD: "jsonify" the file and save in the same folder
    filepath = os.path.join(app.config['UPLOAD_FOLDER'],str(session["person"]["id"]), jsonfile)
    jsontext = json.load(open(filepath, "r"))

    return render_template("results.html", details = info[session["person"]["id"]], json = jsontext) 

@app.route("/logout")
def logout():
    session.pop("person", None)
    #go back to main login/signup screen
    return render_template("index.html")

#show usage history of user with clickable links
@app.route("/history")
def history():
    return render_template("history.html", details = info[session["person"]["id"]])

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], str(id)), filename)





