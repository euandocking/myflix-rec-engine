from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os

# Function to get video index from video data
def get_video_index(video_data, video_id):
    for i, video in enumerate(video_data):
        if str(video['_id']) == video_id:  # Convert ObjectId to string
            return i
    return -1

# Function to get recommendations for a user
def get_recommendations(user_id, user_similarity_matrix, user_item_matrix, video_data, num_recommendations=10):
    user_index = get_user_index(user_ratings, user_id)
    if user_index == -1:
        print(f"User {user_id} not found.")
        return []

    # Find similar users
    similar_users = np.argsort(user_similarity_matrix[user_index])[::-1][1:]

    # Get videos already rated by the user
    rated_videos = np.where(user_item_matrix[user_index] > 0)[0]

    # Generate recommendations excluding already rated videos
    recommendations = []
    for user in similar_users:
        unrated_videos = np.where(user_item_matrix[user_index] == 0)[0]
        unrated_videos = np.setdiff1d(unrated_videos, rated_videos)  # Exclude already rated videos
        for video in unrated_videos:
            recommendations.append(str(video_data[video]['_id']))  # Remove ['_id']['$oid']
            if len(recommendations) == num_recommendations:
                print("Recommendations generated successfully.")
                return recommendations

    return recommendations

# Function to get user index from user ratings
def get_user_index(user_ratings, user_id):
    for i, (uid, _) in enumerate(user_ratings.items()):
        if str(uid) == user_id:
            return i
    return -1

app = Flask(__name__)
CORS(app)

# Get MongoDB connection details from environment variables
mongo_host = os.environ.get('MONGO_HOST', 'myflix-mongo')
mongo_port = int(os.environ.get('MONGO_PORT', 27017))
mongo_db = os.environ.get('MONGO_DB', 'videocatalog')

# Connect to MongoDB
mongo_uri = f'mongodb://{mongo_host}:{mongo_port}/{mongo_db}'
client = MongoClient(mongo_uri)
db = client[mongo_db]
videos_collection = db['videos']

# Fetch video data
video_data = list(videos_collection.find())

# Create a dictionary to store user ratings
user_ratings = {}

# Populate the user ratings dictionary
for video in video_data:
    video_id = str(video['_id'])  # Convert ObjectId to string
    ratings = video.get('userRatings', [])
    for rating in ratings:
        user_id = str(rating['user'])  # Convert ObjectId to string
        user_ratings.setdefault(user_id, []).append({'video_id': video_id, 'rating': rating['rating']})

# Create a user-item matrix
user_item_matrix = np.zeros((len(user_ratings), len(video_data)))

# Populate the matrix with user ratings
for i, (user_id, ratings) in enumerate(user_ratings.items()):
    for rating in ratings:
        video_index = get_video_index(video_data, rating['video_id'])
        user_item_matrix[i, video_index] = rating['rating']

# Calculate cosine similarity between users
user_similarity_matrix = cosine_similarity(user_item_matrix)

# Flask route to handle recommendations
@app.route('/recommendations', methods=['POST'])
def recommend_videos():
    data = request.json
    user_id = data.get('user_id', None)

    if user_id:
        recommendations = get_recommendations(user_id, user_similarity_matrix, user_item_matrix, video_data, num_recommendations=10)
        return jsonify({'recommendations': recommendations})
    else:
        print("User ID not provided.")
        return jsonify({'error': 'User ID not provided'}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5002)