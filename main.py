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
import textwrap
import random

# 1. Récupération des clés
GEMINI_KEY = os.environ['GEMINI_API_KEY']
PIXABAY_KEY = os.environ['PIXABAY_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Génération du script (environ 150 mots pour 1 min 30)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')
prompt = """
Write a captivating and engaging script (around 150 words) about a beginner finance tip or money mindset. 
Write in English. Give only the text, no intro, no outro, no formatting. 
"""
script_text = model.generate_content(prompt).text.strip()
print(f"Script généré :\n{script_text}\n")

# 3. Création de la voix off (voix d'homme)
async def make_audio():
    # Voix masculine plus autoritaire
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 4. Téléchargement d'une vidéo de fond (Pixabay)
def get_background_video():
    keywords = ["finance", "money", "business", "office", "city"]
    query = random.choice(keywords)
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={query}&video_type=film&orientation=vertical&per_page=5"
    response = requests.get(url).json()
    
    if response.get('hits'):
        video_url = response['hits'][0]['videos']['large']['url']
        print(f"Vidéo trouvée : {video_url}")
        vid_data = requests.get(video_url).content
        with open("background.mp4", "wb") as handler:
            handler.write(vid_data)
        return True
    return False

if not get_background_video():
    print("Impossible de trouver une vidéo. Utilisation d'une image de secours.")
    img_data = requests.get("https://picsum.photos/1080/1920").content
    with open("background.jpg", "wb") as handler:
        handler.write(img_data)

# 5. Montage vidéo (Format Short 1080x1920 avec sous-titres)
audio = AudioFileClip("audio.mp3")
duration = audio.duration

# Préparation de la vidéo de fond
if os.path.exists("background.mp4"):
    bg_clip = VideoFileClip("background.mp4")
    # Redimensionner et recadrer pour le format vertical 9:16
    bg_clip = bg_clip.resize(height=1920)
    if bg_clip.w < 1080:
        bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
else:
    bg_clip = ImageClip("background.jpg").resize(height=1920)
    if bg_clip.w < 1080:
        bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)

# Boucler ou couper la vidéo pour qu'elle dure exactement le temps de l'audio
bg_clip = bg_clip.loop(duration=duration)

# Création des sous-titres (Découpage en phrases)
sentences = script_text.replace('\n', ' ').split('. ')
words = script_text.split()
time_per_word = duration / len(words)

subtitles = []
current_time = 0

for sentence in sentences:
    if not sentence.strip():
        continue
    # Envelopper le texte pour qu'il tienne à l'écran
    wrapped_text = textwrap.fill(sentence.strip() + ".", width=20)
    word_count = len(sentence.split())
    sentence_duration = word_count * time_per_word
    
    # Création du clip de texte avec la police Linux
    txt_clip = TextClip(wrapped_text, fontsize=70, color='white', font='DejaVu-Sans-Bold', 
                        stroke_color='black', stroke_width=3, method='caption', size=(900, None))
    txt_clip = txt_clip.set_position(('center', 'center')).set_start(current_time).set_duration(sentence_duration)
    subtitles.append(txt_clip)
    
    current_time += sentence_duration

# Assemblage final
video = CompositeVideoClip([bg_clip] + subtitles).set_audio(audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

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
