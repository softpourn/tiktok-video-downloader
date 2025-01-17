from flask import Flask, request, jsonify, send_file
import os
import json
import zipfile
from datetime import datetime
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def extract_video_links(json_file_path):
    """Extract video links from the TikTok JSON file."""
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    video_links = []
    if "Activity" in data and "Favorite Videos" in data["Activity"]:
        favorite_videos = data["Activity"]["Favorite Videos"].get("FavoriteVideoList", [])
        video_links = [
            {"link": video["Link"], "timestamp": video["Time"]}
            for video in favorite_videos
        ]

    # Sort videos by timestamp (chronological order)
    video_links.sort(key=lambda x: datetime.strptime(x["timestamp"], '%Y-%m-%dT%H:%M:%S'))
    return video_links

def download_videos(video_links):
    """Download videos from TikTok and save them locally."""
    video_files = []
    for video in video_links:
        try:
            # Replace the TikTokApi functionality with direct requests
            video_url = video["link"].replace("www.tiktokv.com", "api.tiktokv.com")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            video_id = video["link"].split('/')[-2]
            filename = f"{video_id}.mp4"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)

            # Save video
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            video_files.append(filepath)
        except Exception as e:
            print(f"Failed to download video: {video['link']}, Error: {e}")
    return video_files

def create_zip_file(file_paths, zip_name="tiktok_videos.zip"):
    """Create a ZIP file containing the provided file paths."""
    zip_path = os.path.join(DOWNLOAD_FOLDER, zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in file_paths:
            zipf.write(file, os.path.basename(file))
    return zip_path

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and video processing."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'Invalid file type. Please upload a JSON file.'}), 400

    # Save uploaded file
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Process the JSON file
    try:
        video_links = extract_video_links(filepath)
        if not video_links:
            return jsonify({'error': 'No video links found in the JSON file.'}), 400

        # Download videos
        video_files = download_videos(video_links)

        # Create ZIP file
        zip_path = create_zip_file(video_files)

        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
