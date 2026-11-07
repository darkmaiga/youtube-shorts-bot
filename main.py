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

# 2. Moteur de Sujets
TOPICS = [
    "How to get out of credit card debt fast",
    "The hidden truth about crypto scams and how to spot them",
    "Why buying a new car is a terrible financial mistake",
    "The 50/30/20 budget rule explained for beginners",
    "How inflation is secretly stealing your wealth",
    "Why you need an emergency fund before investing",
    "The danger of lifestyle inflation when you get a raise",
    "How to start investing with only 50 dollars",
    "The difference between assets and liabilities",
    "Why student loans are a trap and how to pay them off faster"
]
chosen_topic = random.choice(TOPICS)

# 3. Génération du script (Ajusté pour 1 minute - environ 170 mots)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')
prompt = f"""
You are a strict, professional financial advisor. 
Write a hard-hitting script about: "{chosen_topic}".
Structure: 1. Hook. 2. The problem explained deeply. 3. Actionable steps to solve it. 4. Strong call to action.
Rules: Between 160 and 180 words (to make a 1-minute to 1-minute 20 video). English. ONLY the spoken text.
"""
script_text = model.generate_content(prompt).text.strip()
print(f"Script généré :\n{script_text}\n")

# 4. Création de la voix off
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Téléchargement d'une vidéo de fond (HD)
def get_background_video(topic):
    if "debt" in topic.lower(): query = "business stress"
    elif "crypto" in topic.lower(): query = "crypto bitcoin"
    elif "car" in topic.lower(): query = "luxury car driving"
    elif "budget" in topic.lower(): query = "calculator money"
    else: query = "city finance"
    
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={query}&video_type=film&orientation=vertical&per_page=10&min_height=1920"
    response = requests.get(url).json()
    
    if response.get('hits'):
        video_url = response['hits'][0]['videos']['large']['url']
        vid_data = requests.get(video_url).content
        with open("background.mp4", "wb") as handler:
            handler.write(vid_data)
        return True
    return False

if not get_background_video(chosen_topic):
    img_data = requests.get("https://picsum.photos/1080/1920").content
    with open("background.jpg", "wb") as handler:
        handler.write(img_data)

# 6. Téléchargement de la musique de fond
has_music = False
try:
    music_url = "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    music_data = requests.get(music_url, headers=headers).content
    if len(music_data) > 10000: 
        with open("music.mp3", "wb") as handler:
            handler.write(music_data)
        has_music = True
except Exception as e:
    print(f"Erreur musique : {e}")

# 7. Téléchargement de la police
font_url = "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
try:
    font_data = requests.get(font_url).content
    with open("Montserrat.ttf", "wb") as f:
        f.write(font_data)
    font_path = "Montserrat.ttf"
except:
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# 8. Fonction pour créer l'image d'un bloc de mots (Texte JAUNE)
def create_word_image(text, filename="temp_word.png"):
    img_width = 1080
    img_height = 300
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_size = 90
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (img_width - w) / 2
    y = (img_height - h) / 2
        
    # Texte JAUNE (Couleur or) avec contour noir
    draw.text((x, y), text, font=font, fill="#FFD700", stroke_width=8, stroke_fill="black")
    img.save(filename)
    return filename

# 9. Montage vidéo
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

if os.path.exists("background.mp4"):
    bg_clip = VideoFileClip("background.mp4")
    # On force la boucle pour qu'elle ne s'arrête jamais avant l'audio
    bg_clip = bg_clip.loop(duration=duration)
    bg_clip = bg_clip.resize(height=1920)
    if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
else:
    bg_clip = ImageClip("background.jpg").set_duration(duration).resize(height=1920)
    if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)

bg_clip = bg_clip.fx(vfx.colorx, 0.5) # Filtre sombre pour faire ressortir le texte

if has_music:
    try:
        music = AudioFileClip("music.mp3")
        music = music.loop(duration=duration).volumex(0.1)
        final_audio = CompositeAudioClip([voice_audio, music])
    except: final_audio = voice_audio
else:
    final_audio = voice_audio

# 10. Découpage en blocs de 3 mots (Style Karaoké)
words = script_text.replace('\n', ' ').split()
chunks = [" ".join(words[i:i+3]) for i in range(0, len(words), 3)]
time_per_chunk = duration / len(chunks)

subtitles = []
current_time = 0

for i, chunk in enumerate(chunks):
    text_img_file = f"chunk_{i}.png"
    create_word_image(chunk.upper(), text_img_file)
    
    txt_clip = ImageClip(text_img_file).set_position(('center', 500)).set_start(current_time).set_duration(time_per_chunk)
    subtitles.append(txt_clip)
    current_time += time_per_chunk

# 11. Assemblage
video = CompositeVideoClip([bg_clip] + subtitles).set_audio(final_audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

# 12. Upload
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build('youtube', 'v3', credentials=creds)

body = {
    'snippet': {
        'title': f'{chosen_topic[:80]} 💡 #shorts',
        'description': f'{chosen_topic}. Automated finance tips. #finance #money #shorts',
        'tags': ['finance', 'money', 'shorts'],
        'categoryId': '27'
    },
    'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
}

media = MediaFileUpload("short.mp4", mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
request.execute()
print("Vidéo publiée avec succès sur YouTube ! 🚀")
