from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
import bcrypt
import os
import plotly.express as px
from datetime import datetime
from functools import wraps
from functions import is_logged_in, get_formatted_course_list 
from llm_model import get_course_name,get_subject_name
import openai
import config 
from subject_llm import get_subject_name
import pandas as pd
from flask import jsonify 
import openai
from openai import OpenAI
from langchain_openai import ChatOpenAI



#OpenAI api Key
openai.api_key = config.OPENAI_API_KEY

#openai.api_key = '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'


# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config)  # Load configurations from config.py

# Initialize MongoDB
client = MongoClient(app.config['MONGO_URI'])
db = client["recommendation_system"]
users = db["users"]
users_survey_data = db['users_survey_data']
semester_details = db["semester_details"]

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if str(password) == str(confirm_password):                 
            password = password.encode('utf-8')
            hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
            users.insert_one({'fullname': fullname,'email':email, 'password': hashed_password})
            return redirect(url_for('login'))
        elif str(password) != str(confirm_password):
            print("Passowrd not same")
            render_template('register.html')
            
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        user = users.find_one({'email': email})
        if user and bcrypt.checkpw(password, user['password']):
            session['email'] = email
            # Check if the user has completed the survey
            user_survey = users_survey_data.find_one({'user_email': email})
            if user_survey:
                # User has completed the survey, redirect to user profile
                return redirect(url_for('user_profile'))
            else:
                # User hasn't completed the survey, redirect to the survey page
                return redirect(url_for('survey'))
        else:
            message = "Wrong email or password. Please try again."

    return render_template('login.html', message=message)


@app.route('/logout')
def logout():
    if is_logged_in():
        session.pop('email', None)
    return redirect(url_for('index'))


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password == confirm_password:
            user = users.find_one({'email': email})
            if user:
                new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                users.update_one({'email': email}, {'$set': {'password': new_hashed_password}})
                return redirect(url_for('login'))
            else:
                print("User not found")
        else:
            print("Passwords do not match")

    return render_template('reset_password.html')


@app.route('/survey')
def survey():
    if is_logged_in():
        return render_template('survey.html')
    return redirect(url_for('login'))


@app.route('/submit_survey', methods=['POST'])
def submit_survey():
    if is_logged_in():
        user_email = session['email']  # Get the user's email from the session
        data = request.form.to_dict()
        data['user_email'] = user_email  # Add the user's email to the survey data
        data['timestamp'] = datetime.now()  # Add a timestamp to track the submission time
        
        # Find the existing entry for the user
        existing_entry = users_survey_data.find_one({'user_email': user_email})
        
        if existing_entry:
            # If an entry exists, update it with the new data and keep the same ObjectID
            data['_id'] = existing_entry['_id']  # Retain the same ObjectID
            users_survey_data.replace_one({'_id': existing_entry['_id']}, data)  # Replace the existing entry with new data
        else:
            # If no entry exists, insert the new data
            users_survey_data.insert_one(data)
            
        return redirect(url_for('user_profile'))
    return redirect(url_for('login'))
    

@app.route('/user_profile')
def user_profile():
    if is_logged_in():
        # user_data = survey_collection.find_one()
        user_email = session['email']  # Get the user's email from the session
        user_data = users_survey_data.find_one({'user_email': user_email})  # Find all entries for the user
        # print(user_data)
        return render_template('user_profile.html', user_data=user_data)
    return redirect(url_for('login'))



@app.route('/show_results')
def show_pie_chart():
    if is_logged_in():
        user_email = session['email']
        user_data = users_survey_data.find_one({'user_email': user_email})

        if user_data:
            custom_titles = {
                'aiInterest': 'Artificial Intelligence',
                'dbInterest': 'Databases and Search',
                'seInterest': 'Software Engineering',
                'algoInterest': 'Algorithms and Computers',
            }

            interest_counts = {}

            for field, title in custom_titles.items():
                interests = user_data.get(field, '').split(' and ')
                count = len(interests)
                interest_counts[title] = count

            df = pd.DataFrame({'Interest': list(interest_counts.keys()), 'Count': list(interest_counts.values())})

            fig = px.pie(df, names='Interest', values='Count', title=f'Interests of {user_email}')

            chart_html = fig.to_html(full_html=False)

            return render_template('pie_chart.html', chart=chart_html)
        else:
            return "Enter correct email."

    return render_template('pie_chart.html', chart=chart_html)

@app.route('/recommendations', methods=['POST'])
def recommendations():
    if is_logged_in():
        # user_course_name = request.form.get('course_name', 'Software Engineering')
        user_semester = request.form.get('semester', 'Semester 1')
        email= session["email"]
        user_course_name, explanation = get_course_name(email)
        print(f"Recommended course: {user_course_name}")
        print(f"Explanation: {explanation}")
        
    


        # Make a request to the OpenAI API for career recommendations
        prompt = f"Based on my academic courses {user_course_name}, what are potential career paths for me?"
        """
        response = openai.chat.completions.create(
            engine="text-davinci-002",  # Choose the appropriate engine
            model="gpt-4",
            prompt=prompt,
            max_tokens=2000  
        
        )"""
       
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content":prompt,
        },
    ],
)
        survey_data = users_survey_data.find_one({'user_email': email})
        return render_template('recommendations.html',
                                user_semester=user_semester,
                                  #courses=formatted_courses,
                                    user_course_name=user_course_name,
                                      survey_data=survey_data,
                                        explanation=explanation)
                                        #subject_results=subject_results)
    
    """
        query ={
  "$or": [
    {
      "semester": {
        "$in": ["Semester 1", "Semester 2", "Semester 3", "Semester 4", "Semester 9", "Semester 10"]
      }
    },
    {
      "$and": [
        {
          "semester": {
            "$in": ["Semester 5", "Semester 6", "Semester 7", "Semester 8"]
          }
        },
        {
          "course_name": user_course_name
        }
      ]
    }
  ]
}

        print(query)

        results = semester_details.find(query)
        #formatted_courses = get_formatted_course_list(course_data_from_mongo=results)
        print("************************************")
       #print(f"Formatted courses: {formatted_courses}")
        print("-------------------------------------")

        
        subject_results = get_subject_name(email,
                                           user_course_name,)
                                           formatted_courses)
        print("subject results" , subject_results)

        """

""""
        survey_data = users_survey_data.find_one({'user_email': email})
        return render_template('recommendations.html',
                                user_semester=user_semester,
                                  #courses=formatted_courses,
                                    user_course_name=user_course_name,
                                      survey_data=survey_data,
                                        explanation=explanation)
                                        #subject_results=subject_results)

    return redirect(url_for('login'))
"""

if __name__ == '__main__':
    app.run(debug=True)


 