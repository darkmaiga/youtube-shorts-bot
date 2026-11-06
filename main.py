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

# 2. Le Moteur de Sujets (On pioche un problème précis au hasard)
TOPICS = [
    "How to get out of credit card debt fast",
    "The hidden truth about crypto scams and how to spot them",
    "Why buying a new car is a terrible financial mistake",
    "The 50/30/20 budget rule explained for beginners",
    "How inflation is secretly stealing your wealth",
    "Why you need an emergency fund before investing",
    "The danger of lifestyle inflation when you get a raise",
    "How to start investing with only 50 dollars",
    "The difference between assets and liabilities (Rich Dad Poor Dad)",
    "Why student loans are a trap and how to pay them off faster",
    "How to negotiate your salary and get paid what you are worth",
    "The psychological tricks stores use to make you spend money"
]

# On choisit un sujet au hasard pour ne jamais être répétitif
chosen_topic = random.choice(TOPICS)
print(f"Sujet choisi : {chosen_topic}")

# 3. Génération du script (Rôle de conseiller pro + structure)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')

prompt = f"""
You are a strict, professional, and highly experienced financial advisor. 
Write a hard-hitting, problem-solving script about this specific topic: "{chosen_topic}".

Follow this exact structure:
1. A strong hook (catch the viewer's attention immediately).
2. Explain the problem clearly (why it's dangerous).
3. Give 2 or 3 actionable steps to solve it.
4. End with a strong call to action (e.g., "Subscribe for more financial freedom").

Rules:
- Length: around 150 words (to make a 1 min 30 video).
- Write in English.
- Give ONLY the spoken text. No formatting, no markdown, no visual cues, no intro/outro labels. Just the raw script.
"""
script_text = model.generate_content(prompt).text.strip()
print(f"Script généré :\n{script_text}\n")

# 4. Création de la voix off
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Recherche d'une vidéo de fond adaptée au sujet
def get_background_video(topic):
    # On extrait les mots-clés principaux du sujet pour Pixabay
    if "debt" in topic.lower(): query = "debt stress"
    elif "crypto" in topic.lower(): query = "crypto trading"
    elif "car" in topic.lower(): query = "luxury car"
    elif "inflation" in topic.lower(): query = "inflation economy"
    elif "invest" in topic.lower(): query = "stock market"
    else: query = "money finance"
    
    # On prend une vidéo verticale
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={query}&video_type=film&orientation=vertical&per_page=5"
    response = requests.get(url).json()
    
    if response.get('hits'):
        video_url = response['hits'][0]['videos']['large']['url']
        print(f"Vidéo trouvée pour '{query}': {video_url}")
        vid_data = requests.get(video_url).content
        with open("background.mp4", "wb") as handler:
            handler.write(vid_data)
        return True
    return False

if not get_background_video(chosen_topic):
    print("Impossible de trouver une vidéo. Utilisation d'une image de secours.")
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
        print("Musique téléchargée avec succès.")
except Exception as e:
    print(f"Erreur de musique : {e}. On continue sans.")

# 7. Fonction pour créer l'image des sous-titres
def create_text_image(text, filename="temp_text.png"):
    img_width = 1080
    img_height = 1920
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_size = 75
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        
    lines = textwrap.wrap(text, width=22)
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

# 8. Montage vidéo
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
bg_clip = bg_clip.fx(vfx.colorx, 0.6) # Filtre sombre

if has_music:
    try:
        music = AudioFileClip("music.mp3")
        music = music.loop(duration=duration).volumex(0.1)
        final_audio = CompositeAudioClip([voice_audio, music])
    except:
        final_audio = voice_audio
else:
    final_audio = voice_audio

# 9. Découpage des sous-titres
sentences = script_text.replace('\n', ' ').split('. ')
words = script_text.split()
time_per_word = duration / len(words)

subtitles = []
current_time = 0

for sentence in sentences:
    if not sentence.strip():
        continue
    
    wrapped_text = textwrap.fill(sentence.strip() + ".", width=22)
    word_count = len(sentence.split())
    sentence_duration = word_count * time_per_word
    
    text_img_file = create_text_image(wrapped_text)
    txt_clip = ImageClip(text_img_file).set_start(current_time).set_duration(sentence_duration)
    subtitles.append(txt_clip)
    current_time += sentence_duration

# 10. Assemblage et Publication
video = CompositeVideoClip([bg_clip] + subtitles).set_audio(final_audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build('youtube', 'v3', credentials=creds)

# Le titre de la vidéo sera le sujet choisi (super pour le SEO !)
body = {
    'snippet': {
        'title': f'{chosen_topic[:80]} 💡 #shorts',
        'description': f'{chosen_topic}. Automated finance tips. #finance #money #shorts',
        'tags': ['finance', 'money', 'shorts', 'investing'],
        'categoryId': '27'
    },
    'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
}

media = MediaFileUpload("short.mp4", mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
request.execute()
print("Vidéo publiée avec succès sur YouTube ! 🚀")
