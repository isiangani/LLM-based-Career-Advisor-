from typing import List
import os
import config  # Import config file
from flask import Flask
from pydantic import BaseModel, Field
from pymongo import MongoClient

# Your MongoDB connection information
mongo_uri = config.MONGO_URI
database_name = "recommendation_system"
collection_name = "courses"

# Create a MongoClient
client = MongoClient(mongo_uri)

# Connect to the database and collection
db = client[database_name]
collection = db[collection_name]


class CourseUser(BaseModel):
    course: str = Field(description="Field of study recommended based on the user's input.")
    explanation: str = Field(description="A longer explanation for why this field of study is recommended, based on the user's input.")


def get_course_name():
    courses_data = list(collection.find({}))  # Convert the cursor to a list
    courses_list = [course['course_name'] for course in courses_data]

    if courses_list:
        print("Courses details fetched from the database:")
        for course in courses_data:
            print(f"Course Name: {course['course_name']}, Course Details: {course}")
    else:
        print("No courses found in the 'Courses' collection.")


# Call the function to retrieve and print all courses
get_course_name()
