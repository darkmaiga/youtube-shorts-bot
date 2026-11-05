import os
import requests
import asyncio
import time
import edge_tts
import google.generativeai as genai
from moviepy.editor import *
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build

# 1. Récupération des clés secrètes
GEMINI_KEY = os.environ['GEMINI_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Génération du script avec Gemini (avec gestion du quota)
genai.configure(api_key=GEMINI_KEY)

# On utilise un modèle avec un quota gratuit plus généreux
MODEL_NAME = 'gemini-3.1-flash-lite' 
model = genai.GenerativeModel(MODEL_NAME)

prompt = "Write a very short, engaging script (max 25 words) about a beginner finance tip. Give only the text, no intro."

# Mécanisme de sécurité pour réessayer en cas de surcharge temporaire
max_retries = 3
for attempt in range(max_retries):
    try:
        response = model.generate_content(prompt)
        script_text = response.text.strip()
        break
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            print(f"Quota atteint (tentative {attempt + 1}/{max_retries}). Attente de 60 secondes...")
            time.sleep(60)
        else:
            raise e
else:
    raise Exception("Impossible de générer le script après plusieurs tentatives. Quota probablement épuisé pour aujourd'hui.")

print(f"Script généré : {script_text}")

# 3. Création de la voix off (TTS)
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-AriaNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 4. Téléchargement d'une image de fond
img_data = requests.get("https://picsum.photos/1080/1920").content
with open("background.jpg", "wb") as handler:
    handler.write(img_data)

# 5. Montage vidéo (format Short 1080x1920)
audio = AudioFileClip("audio.mp3")
image = ImageClip("background.jpg").set_duration(audio.duration)
video = image.set_audio(audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac")

# 6. Upload sur YouTube
creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
youtube = build('youtube', 'v3', credentials=creds)

body = {
    'snippet': {
        'title': 'Daily Finance Tip 💡 #shorts',
        'description': 'Automated finance tips. #finance #money #shorts',
        'tags': ['finance', 'money', 'shorts'],
        'categoryId': '27'
    },
    'status': {
        'privacyStatus': 'public',
        'selfDeclaredMadeForKids': False
    }
}

media = MediaFileUpload("short.mp4", mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
request.execute()
print("Vidéo publiée avec succès sur YouTube ! 🚀")
