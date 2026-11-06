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
    "Why student loans are a trap and how to pay them off faster",
    "How to negotiate your salary and get paid what you are worth",
    "The psychological tricks stores use to make you spend money"
]
chosen_topic = random.choice(TOPICS)
print(f"Sujet choisi : {chosen_topic}")

# 3. Génération du script
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')

prompt = f"""
You are a strict, professional, and highly experienced financial advisor. 
Write a hard-hitting, problem-solving script about this specific topic: "{chosen_topic}".
Follow this exact structure: 1. Strong hook. 2. The problem. 3. Actionable steps. 4. Call to action.
Rules: around 120-140 words. English. ONLY the spoken text. No formatting, no visual cues.
"""
script_text = model.generate_content(prompt).text.strip()
print(f"Script généré :\n{script_text}\n")

# 4. Création de la voix off (On récupère les timings précis des mots)
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Téléchargement d'une vidéo de fond
def get_background_video(topic):
    if "debt" in topic.lower(): query = "debt stress"
    elif "crypto" in topic.lower(): query = "crypto trading"
    elif "car" in topic.lower(): query = "luxury car"
    elif "inflation" in topic.lower(): query = "inflation economy"
    elif "invest" in topic.lower(): query = "stock market"
    else: query = "money finance"
    
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={query}&video_type=film&orientation=vertical&per_page=5"
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
    music_url = "https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    music_data = requests.get(music_url, headers=headers).content
    if len(music_data) > 10000: 
        with open("music.mp3", "wb") as handler:
            handler.write(music_data)
        has_music = True
except Exception as e:
    print(f"Erreur musique : {e}")

# 7. Téléchargement d'une belle police (Montserrat ExtraBold)
font_url = "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
try:
    font_data = requests.get(font_url).content
    with open("Montserrat.ttf", "wb") as f:
        f.write(font_data)
    font_path = "Montserrat.ttf"
except:
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Fallback

# 8. Fonction pour créer l'image d'un mot
def create_word_image(word, filename="temp_word.png"):
    img_width = 1080
    img_height = 300
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_size = 100 # Grosse police
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
        
    # Centrer le mot
    bbox = draw.textbbox((0, 0), word, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (img_width - w) / 2
    y = (img_height - h) / 2
        
    # Texte blanc avec un gros contour noir (très lisible)
    draw.text((x, y), word, font=font, fill="white", stroke_width=10, stroke_fill="black")
    img.save(filename)
    return filename

# 9. Montage vidéo
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

if os.path.exists("background.mp4"):
    bg_clip = VideoFileClip("background.mp4")
    bg_clip = bg_clip.resize(height=1920)
    if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
else:
    bg_clip = ImageClip("background.jpg").resize(height=1920)
    if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)

bg_clip = bg_clip.loop(duration=duration)
bg_clip = bg_clip.fx(vfx.colorx, 0.5) # Filtre encore plus sombre (0.5) pour faire ressortir le texte

if has_music:
    try:
        music = AudioFileClip("music.mp3")
        music = music.loop(duration=duration).volumex(0.1)
        final_audio = CompositeAudioClip([voice_audio, music])
    except: final_audio = voice_audio
else:
    final_audio = voice_audio

# 10. Découpage Mot par Mot (Le fameux style Karaoké)
words = script_text.replace('\n', ' ').split()
time_per_word = duration / len(words)

subtitles = []
current_time = 0

for i in range(len(words)):
    # On affiche le mot actuel, et parfois le mot suivant pour que ça se lise bien
    if i < len(words) - 1 and len(words[i]) < 5:
        text_to_show = f"{words[i]} {words[i+1]}" # Si le mot est court, on l'affiche avec le suivant
        display_duration = time_per_word * 2
        # (On saute le mot suivant dans la boucle pour ne pas le répéter)
        words[i+1] = "" 
    else:
        text_to_show = words[i]
        display_duration = time_per_word

    if text_to_show.strip() == "":
        continue

    # Création de l'image pour ce mot
    text_img_file = f"word_{i}.png"
    create_word_image(text_to_show.upper(), text_img_file) # ON MET TOUT EN MAJUSCULES
    
    # On place le texte en haut (y=400 au lieu du centre à 960)
    txt_clip = ImageClip(text_img_file).set_position(('center', 400)).set_start(current_time).set_duration(display_duration)
    subtitles.append(txt_clip)
    
    current_time += display_duration

# 11. Assemblage et Publication
video = CompositeVideoClip([bg_clip] + subtitles).set_audio(final_audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

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
