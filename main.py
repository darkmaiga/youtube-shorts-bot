import os
import requests
import asyncio
import time
import edge_tts
import google.generativeai as genai
from moviepy.editor import *
from moviepy.editor import vfx
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
import textwrap
import random
from PIL import Image, ImageDraw, ImageFont

# 1. Récupération des clés
GEMINI_KEY = os.environ['GEMINI_API_KEY']
PIXABAY_KEY = os.environ['PIXABAY_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Génération du script
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')
prompt = """
Write a captivating and engaging script (around 150 words) about a beginner finance tip or money mindset. 
Write in English. Give only the text, no intro, no outro, no formatting. 
"""
script_text = model.generate_content(prompt).text.strip()
print(f"Script généré :\n{script_text}\n")

# 3. Création de la voix off
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 4. Téléchargement de la vidéo de fond
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

# 5. Téléchargement de la musique de fond (avec un lien ultra stable)
has_music = False
try:
    music_url = "https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    music_data = requests.get(music_url, headers=headers).content
    if len(music_data) > 10000: # Vérifie que le fichier n'est pas vide
        with open("music.mp3", "wb") as handler:
            handler.write(music_data)
        has_music = True
        print("Musique téléchargée avec succès.")
    else:
        print("Le fichier musique est vide ou invalide. On continue sans.")
except Exception as e:
    print(f"Erreur de téléchargement de la musique : {e}. On continue sans.")

# 6. Fonction pour créer une image de texte
def create_text_image(text, filename="temp_text.png"):
    img_width = 1080
    img_height = 1920
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_size = 80
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        
    lines = textwrap.wrap(text, width=20)
    total_height = len(lines) * (font_size + 20)
    y_start = (img_height - total_height) / 2
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (img_width - w) / 2
        y = y_start + i * (font_size + 20)
        draw.text((x, y), line, font=font, fill="white", stroke_width=6, stroke_fill="black")
        
    img.save(filename)
    return filename

# 7. Montage vidéo
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

if os.path.exists("background.mp4"):
    bg_clip = VideoFileClip("background.mp4")
    bg_clip = bg_clip.resize(height=1920)
    if bg_clip.w < 1080:
        bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
else:
    bg_clip = ImageClip("background.jpg").resize(height=1920)
    if bg_clip.w < 1080:
        bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)

bg_clip = bg_clip.loop(duration=duration)
# Application du filtre sombre
bg_clip = bg_clip.fx(vfx.colorx, 0.6)

# Gestion de l'audio final
if has_music:
    try:
        music = AudioFileClip("music.mp3")
        music = music.loop(duration=duration).volumex(0.1)
        final_audio = CompositeAudioClip([voice_audio, music])
    except Exception as e:
        print("Erreur lors de l'ajout de la musique, audio normal utilisé.")
        final_audio = voice_audio
else:
    final_audio = voice_audio

# Sous-titres
sentences = script_text.replace('\n', ' ').split('. ')
words = script_text.split()
time_per_word = duration / len(words)

subtitles = []
current_time = 0

for sentence in sentences:
    if not sentence.strip():
        continue
    
    wrapped_text = textwrap.fill(sentence.strip() + ".", width=20)
    word_count = len(sentence.split())
    sentence_duration = word_count * time_per_word
    
    text_img_file = create_text_image(wrapped_text)
    txt_clip = ImageClip(text_img_file).set_start(current_time).set_duration(sentence_duration)
    subtitles.append(txt_clip)
    current_time += sentence_duration

video = CompositeVideoClip([bg_clip] + subtitles).set_audio(final_audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

# 8. Upload
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build('youtube', 'v3', credentials=creds)

body = {
    'snippet': {
        'title': 'Daily Finance Tip 💡 #shorts',
        'description': 'Automated finance tips. #finance #money #shorts',
        'tags': ['finance', 'money', 'shorts'],
        'categoryId': '27'
    },
    'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
}

media = MediaFileUpload("short.mp4", mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
request.execute()
print("Vidéo publiée avec succès sur YouTube ! 🚀")
