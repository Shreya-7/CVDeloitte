from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory, jsonify
from pymongo import MongoClient
from bson.json_util import loads, dumps
from bson import ObjectId
import os
import time
import json

app=Flask(__name__, static_url_path='/static')
app.secret_key = "lol"
app.config["UPLOAD_FOLDER"] = "./files"
app.config['MAX_CONTENT_LENGTH'] = 4*1024*1024

client = MongoClient(os.getenv("DELOITTE_DB"))
user = client["users"]["user_details"]

#default signup page
@app.route("/")
def index():
    return render_template("index.html")

#after pressing signup button
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if(request.method=="GET"):
        return render_template("error.html", message = "Invalid request.")

    #checking if person had previously registered
    person = user.find_one({"email": request.form.get("email")})
    if(person!=None):
        message = "User already registered. Please log in."
        return render_template("index.html", message = message)   

    cred = {
        "name": request.form.get("username"),
        "email": request.form.get("email"),
        "password": request.form.get("password"),
        "type": request.form["person_type"].title(),
        "organisation": request.form.get("org"),
        "filenames": {}
    }

    #creating folders using email to store associated files
    folderpath = os.path.join(app.config["UPLOAD_FOLDER"], cred["email"])
    if(str(cred["email"]) not in os.listdir(app.config["UPLOAD_FOLDER"])):
        os.mkdir(folderpath)

    user.insert_one(cred) #inserting into database
    cred.pop('_id')

    #logging in
    session["person"] = cred
    return redirect("/home")

#after pressing login button
@app.route("/login", methods=["GET", "POST"])
def login():
    if(request.method=="GET"):
        return render_template("error.html", message = "Invalid request.")

    email = request.form.get("email")
    password = request.form.get("password")
    message = ""
    person = user.find_one({"email": email})
    
    if(person!=None):
        #login logic
        if(password==person["password"]):
            person.pop('_id')
            session["person"] = person
            return redirect("/home")
        else:
            message = "Incorrect password."
    else:
        message = "Not registered. Please sign up."

    return render_template("index.html", message = message)

@app.route("/home")
def home():    
    if("person" not in session.keys()): #if not logged in
        return redirect("/")
    return render_template("home.html", details = session["person"])

#after submitting a file for upload
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if("person" not in session.keys()): #if not logged in
        return redirect("/")

    if request.method == "GET":
        return render_template("error.html", message = "Invalid request.")

    if request.method == 'POST':
        f = request.files['file']
        #saving file
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],str(session["person"]["email"]),f.filename))
        
        session["current_file"] = f.filename

        #TBD: save to document - filename and json filename
        temp, extension = os.path.splitext(f.filename)
        jsonfile = temp+".json" #can be queried
        user.update_one({"email": session["person"]["email"]}, {"$set": { "filenames."+temp: {"extension": extension,"json": jsonfile, "processed": 0, "results": ["gfg.py"]}}})
        
        #TBD: "jsonify" the file and save in filesystem

        #show results after processing       
        return redirect("/" + f.filename) 

#for exceeding file size
@app.errorhandler(413)
def error413(e):
    flash(message="File size exceeded!", category=error)
    return render_template("error.html", message="The file could not be uploaded.")

#show results after processing for passed filename
@app.route("/<filename>")
def getresults(filename):

    if("person" not in session.keys()): #if not logged in
        return redirect("/")

    obj = user.find_one({"email": session["person"]["email"]}, {"filenames": 1})
    if(filename not in obj["filenames"].keys()): #if file doesnt exist(invalid url)
        return render_template("error.html", message = "Invalid filename.")

    temp = filename #only filename, without extension
    extension = obj["filenames"][temp]["extension"]
    filename = temp+extension 

    #processed or not, if processed it means accessing from history page, no processing req again   
    x = user.find_one({"email": session["person"]["email"]}, {"filenames."+temp+".processed": 1})

    if(x==0): #not processed
        something = "something"
        #TBD: processing logic, store filenames in document, store files in folder, set processed to 1
    
    jsonfile = temp+".json"
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'],str(session["person"]["email"]), jsonfile)
    jsontext = json.load(open(filepath, "r"))

    details = user.find_one({"email": session["person"]["email"]})

    return render_template("results.html", details = details, json = jsontext, current=temp) 

@app.route("/logout")
def logout():
    if("person" not in session.keys()): #if not logged in
        return redirect("/")
    session.pop("person", None)

    #go back to main login/signup screen
    return render_template("index.html")

#show usage history of user with clickable links
@app.route("/history")
def history(): 
    if("person" not in session.keys()): #if not logged in
        return redirect("/")
    details = user.find_one({"email": session["person"]["email"]})
    return render_template("history.html", details = details)

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], session["person"]["email"]), filename)





