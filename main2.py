# from ursina import *  # DESACTIVE — interface web Three.js
import threading
import asyncio
import google.genai as genai
from google.genai import types
import speech_recognition as sr
import edge_tts
# --- Pygame (audio TTS) : optionnel ---
try:
    import pygame
except ImportError:
    pygame = None
    print("[AVERTISSEMENT] pygame non installe — l'audio TTS sera desactive.")
    print("  -> Pour l'installer : pip install pygame --only-binary :all:")
import os
from dotenv import load_dotenv

def _charger_user_name():
    import json as _j
    try:
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
        with open(_p, "r", encoding="utf-8") as _f:
            return _j.load(_f).get("user_name", "Hugo")
    except Exception:
        return "Hugo"

def _charger_user_age():
    import json as _j
    try:
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
        with open(_p, "r", encoding="utf-8") as _f:
            return _j.load(_f).get("user_age", "")
    except Exception:
        return ""

USER_NAME = _charger_user_name()
USER_AGE  = _charger_user_age()

import random
import math
import builtins

# --- GLOBALS TTS/AUDIO ---
is_speaking = False
speak_volume = 0.0
STOP_PARLER     = False
MIC_MUTED       = False
MIC_NEED_RELOAD = False
_skip_pc_audio = False
historique = []

def init_mixer():
    if pygame and not pygame.mixer.get_init():
        pygame.mixer.init()

async def parler(texte):
    global is_speaking, speak_volume, STOP_PARLER, _skip_pc_audio, historique
    
    # Nettoyage des caractères de mise en forme Markdown pour le TTS
    texte_tts = texte.replace("**", "").replace("*", "").replace("#", "").replace("`", "").strip()
    
    # ENREGISTRER CE QUE JARVIS DIT DANS SA MÉMOIRE
    if historique and len(historique) > 0:
        dernier_texte_modele = historique[-1].parts[0].text
        if dernier_texte_modele != texte:
            historique.append(types.Content(role="model", parts=[types.Part(text=f"[Information retournée par l'action et énoncée à voix haute]: {texte}")]))

    is_speaking  = True
    await send_web_state("speaking")
    await send_web_text(texte)
    speak_volume = 0.0
    tmp = f"jarvis_tts_{int(time.time()*1000)}.mp3"
    
    try:
        communicate = edge_tts.Communicate(texte_tts, voice="fr-FR-HenriNeural")
        await communicate.save(tmp)
        
        if _skip_pc_audio:
            print(f"[MOBILE] Envoi audio au mobile : {texte_tts}")
            if CONNECTED_CLIENTS:
                try:
                    with open(tmp, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode('utf-8')
                    message = json.dumps({"action": "jarvis_audio", "text": texte_tts, "audio_b64": audio_b64})
                    await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS])
                except Exception as e:
                    print(f"[MOBILE] Erreur envoi audio : {e}")
        elif pygame:
            init_mixer()
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if STOP_PARLER:
                    pygame.mixer.music.stop()
                    break
                t_audio = time.time() * 20
                base_vol = 0.4 + 0.3 * math.sin(t_audio) + 0.2 * math.sin(t_audio * 0.5)
                speak_volume = max(0.1, min(1.0, base_vol + random.uniform(-0.1, 0.1)))
                await send_web_volume(speak_volume)
                await asyncio.sleep(0.05)
        else:
            print(f"[INFO] Audio desactive (pygame absent) : {texte_tts[:80]}...")
    except Exception as e:
        print(f"Erreur TTS : {e}")
    finally:
        speak_volume = 0.0
        is_speaking  = False
        STOP_PARLER  = False
        try:
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.unload()
        except:
            pass
        await asyncio.sleep(0.1)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except:
            pass
        await send_web_state("idle")

builtins.parler = parler

# Nouveaux modules extraits
from file_manager import *
builtins.resoudre_chemin = resoudre_chemin

from memory_manager import *
from memory_manager import _charger_historique_recent, _sauvegarder_echange_conv

from spotify_controller import *
builtins.spotify_lancer_playlist = spotify_lancer_playlist

from deezer_controller import *
from app_launcher import *
from app_launcher import _fermer_app, _boulot_lancer, _APPS_CATALOGUE
builtins._APPS_CATALOGUE = _APPS_CATALOGUE

from google_services import *
from vision_module import *
from sports_web import *
import pyautogui
import webbrowser
import subprocess
import requests
import time
import pickle
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
# --- PyAudio (micro/reconnaissance vocale) : optionnel ---
try:
    import pyaudio
except ImportError:
    pyaudio = None
    print("[AVERTISSEMENT] pyaudio non installe — le micro sera desactive.")
    print("  -> Pour l'installer : pip install pipwin && pipwin install pyaudio")
import websockets
from PIL import Image
from openai import OpenAI
import uuid
import base64
import io
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import anthropic as _anthropic_lib
except ImportError:
    _anthropic_lib = None

import ctypes
from ctypes import wintypes
user32 = ctypes.windll.user32

# Google APIs (Gmail, Drive, Calendar) : optionnels
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    _google_apis_ok = True
except ImportError:
    _google_apis_ok = False
    Credentials = None
    InstalledAppFlow = None
    Request = None
    build = None
    print("[AVERTISSEMENT] google-auth-oauthlib non installe — Gmail/Drive/Calendar desactives.")
    print("  -> Pour l'installer : pip install google-auth-oauthlib google-api-python-client")

# --- pycaw (volume systeme Windows) : optionnel ---
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    _pycaw_ok = True
except ImportError:
    _pycaw_ok = False

# --- screen-brightness-control : optionnel ---
try:
    import screen_brightness_control as _sbc
    _sbc_ok = True
except ImportError:
    _sbc = None
    _sbc_ok = False

# --- PyWebView (fenetre native) : optionnel ---

try:
    import webview
    _WEBVIEW_OK = True
except ImportError:
    webview = None
    _WEBVIEW_OK = False

_WEBVIEW_WINDOW = None  # référence globale à la fenêtre pywebview

# --- CONFIGURATION VERSION & MAJ ---
CURRENT_VERSION = "5.5"
UPDATE_JSON_URL = "https://www.techenclair.fr/updates/jarvis_update.json"
DERNIERE_MAJ_INFO = None  # Stocke l'info si une MAJ est détectée

# Chargement des variables d'environnement
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY      = os.getenv("YOUTUBE_API_KEY")
XAI_API_KEY          = os.getenv("XAI_API_KEY")
SERPAPI_API_KEY      = os.getenv("SERPAPI_API_KEY")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY")
ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY")
SPOTIFY_MUSIQUE_URI  = os.getenv("SPOTIFY_MUSIQUE_URI", "")
builtins.SPOTIFY_MUSIQUE_URI = SPOTIFY_MUSIQUE_URI
YOUTUBE_MUSIQUE_URL  = os.getenv("YOUTUBE_MUSIQUE_URL", "")
builtins.YOUTUBE_MUSIQUE_URL = YOUTUBE_MUSIQUE_URL

def _charger_musique_lien() -> str:
    try:
        import json as _j
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
        with open(_p, "r", encoding="utf-8") as _f:
            return _j.load(_f).get("musique_lien", "")
    except Exception:
        return ""

MUSIQUE_LIEN_PERSO = _charger_musique_lien()

# Validateur universel — une clé non renseignée = placeholder = agent ignoré
_API_PLACEHOLDERS = frozenset({"VOTRE_CLE_ICI", "Votre ID", "votre_id",
                                "VOTRE_TOKEN_ICI", "votre_token_ici", ""})
def _cle_valide(key):
    return bool(key) and str(key).strip() not in _API_PLACEHOLDERS

import builtins
builtins._cle_valide = _cle_valide

# Configuration domotique, météo et entités Home Assistant
from ha_config import (
    HA_URL, HA_HEADERS,
    VILLE_PAR_DEFAUT, LAT_PAR_DEFAUT, LON_PAR_DEFAUT,
    PIECES_LUMIERES, PIECES_PRISES, PIECES_CAPTEURS, PIECES_HUMIDITE,
    HA_TARIFS, APPAREILS_ENERGIE, APPAREILS_BATTERIE,
    COULEURS_MAP, CODES_METEO,
    ha_appeler_service, ha_get_etat, ha_get_calendrier,
    ha_lumiere, ha_interrupteur, ha_thermostat, ha_scene, ha_verrou,
    geocoder_ville, get_meteo_actuelle, get_meteo_ha, get_alertes_meteo,
    get_meteo_structuree,
)

gemini_actif    = _cle_valide(GEMINI_API_KEY)
client          = genai.Client(api_key=GEMINI_API_KEY) if gemini_actif else None

# Client Grok (xAI)
grok_client     = None
if _cle_valide(XAI_API_KEY):
    grok_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

# Client Groq (Llama 3.3)
groq_client     = None
if _cle_valide(GROQ_API_KEY):
    groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

# Client Claude (Anthropic) — agent principal
anthropic_client = None
if _anthropic_lib and _cle_valide(ANTHROPIC_API_KEY):
    anthropic_client = _anthropic_lib.Anthropic(api_key=ANTHROPIC_API_KEY)

MODELS_LIST     = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-flash", "gemini-2.5-pro", "gemini-2.0-flash-exp"]
CHOSEN_MODEL    = MODELS_LIST[0]

import builtins
builtins.client = client
builtins.CHOSEN_MODEL = CHOSEN_MODEL

# Ollama (LLMs locaux — fallback 100% offline)
OLLAMA_URL      = "http://127.0.0.1:11434"
OLLAMA_MODELS   = ["mistral:instruct", "mistral", "llama3:8b", "llama3", "gemma4"]


# ══════════════════════════════════════════════════════════════
#  GESTIONNAIRE DE QUOTAS API — Failover automatique
# ══════════════════════════════════════════════════════════════

class _QuotaExceededError(Exception):
    """Levée quand une API signale un quota ou rate-limit épuisé."""
    pass

class APIQuotaManager:
    """
    Gère le cooldown des APIs quand leur quota est épuisé.
    Détecte automatiquement les erreurs 429 / resource_exhausted / rate_limit.
    """

    # Durée de cooldown par API (secondes)
    COOLDOWNS = {
        "claude"  : 60,
        "gemini"  : 60,
        "grok"    : 60,
        "groq"    : 30,
        "ollama"  : 10,
    }

    # Mots-clés indiquant un quota épuisé (insensible à la casse)
    QUOTA_KEYWORDS = [
        "429", "quota", "rate limit", "rate_limit", "ratelimit",
        "too many requests", "resource_exhausted", "resource exhausted",
        "exceeded", "tokens per", "requests per", "rateLimitExceeded",
        "quota_exceeded", "RATE_LIMIT_EXCEEDED", "insufficient_quota",
        "context_length_exceeded",
    ]

    def __init__(self):
        from datetime import datetime, timedelta
        self._datetime   = datetime
        self._timedelta  = timedelta
        self._cooldowns  = {}   # {api_name: datetime_disponible}
        self._hit_count  = {}   # {api_name: nb_fois_quota_atteint}

    def is_quota_error(self, error: Exception) -> bool:
        """Retourne True si l'erreur est liée à un quota/rate-limit."""
        err_str = str(error).lower()
        return any(kw.lower() in err_str for kw in self.QUOTA_KEYWORDS)

    def is_available(self, api_name: str) -> bool:
        """Retourne True si l'API est disponible (pas en cooldown)."""
        if api_name not in self._cooldowns:
            return True
        return self._datetime.now() >= self._cooldowns[api_name]

    def mark_quota_exceeded(self, api_name: str) -> None:
        """Place une API en cooldown après un quota épuisé."""
        duration = self.COOLDOWNS.get(api_name, 60)
        self._cooldowns[api_name] = self._datetime.now() + self._timedelta(seconds=duration)
        self._hit_count[api_name] = self._hit_count.get(api_name, 0) + 1
        print(f"[QUOTA] ⚠ {api_name.upper()} quota atteint — cooldown {duration}s "
              f"(total: {self._hit_count[api_name]} fois)")

    def remaining_cooldown(self, api_name: str) -> int:
        """Secondes restantes avant que l'API soit à nouveau disponible (0 si dispo)."""
        if self.is_available(api_name):
            return 0
        delta = self._cooldowns[api_name] - self._datetime.now()
        return max(0, int(delta.total_seconds()))

    def status(self) -> str:
        """Résumé du statut de toutes les APIs."""
        lines = []
        for api in self.COOLDOWNS:
            if not self.is_available(api):
                lines.append(f"  {api.upper()}: cooldown {self.remaining_cooldown(api)}s")
            else:
                lines.append(f"  {api.upper()}: disponible")
        return "\n".join(lines)

# Instance globale
_quota_mgr = APIQuotaManager()

CLAP_THRESHOLD = 1200
VIDEO_LANCEE   = False
MODE_IRON_MAN = False 

_age_line = f"- Age : {USER_AGE} ans\n" if USER_AGE else ""
CREATOR_INFO = (
    "INFORMATIONS SUR TON CREATEUR :\n"
    f"- Prenom : {USER_NAME}\n"
    + _age_line +
    "- Role : Ton createur et maitre\n"
    f"- Tu dois toujours l appeler {USER_NAME} avec respect "
    "mais aussi une pointe de sarcasme affectueux.\n"
)

EXTENSIONS = {
    "Images"   : [".jpg", ".jpeg", ".png", ".gif", ".bmp",
                  ".tiff", ".tif", ".webp", ".svg", ".ico",
                  ".heic", ".raw", ".cr2", ".nef"],
    "Videos"   : [".mp4", ".avi", ".mkv", ".mov", ".wmv",
                  ".flv", ".webm", ".m4v", ".mpg", ".mpeg",
                  ".3gp", ".ts"],
    "Musique"  : [".mp3", ".wav", ".flac", ".aac", ".ogg",
                  ".wma", ".m4a", ".opus", ".aiff"],
    "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx",
                  ".ppt", ".pptx", ".txt", ".odt", ".ods",
                  ".odp", ".rtf", ".csv", ".epub"],
    "Archives" : [".zip", ".rar", ".7z", ".tar", ".gz",
                  ".bz2", ".xz", ".iso"],
    "Code"     : [".py", ".js", ".html", ".css", ".java",
                  ".cpp", ".c", ".h", ".cs", ".php",
                  ".json", ".xml", ".yaml", ".yml",
                  ".sh", ".bat", ".ps1", ".ts", ".jsx",
                  ".tsx", ".vue", ".go", ".rs", ".rb"],
    "Executables": [".exe", ".msi", ".apk", ".dmg", ".deb"],
}

dossier_courant = None
# ==========================================
# ==========================================
# WEBSOCKET
# ==========================================
CONNECTED_CLIENTS = set()
builtins.CONNECTED_CLIENTS = CONNECTED_CLIENTS
interface_deja_connectee = False
_skip_pc_audio = False  # True quand la commande vient du mobile (le tél gère son propre TTS)
PENDING_SCREEN_CAPTURES = {}

async def ws_handler(websocket):
    global interface_deja_connectee
    CONNECTED_CLIENTS.add(websocket)
    interface_deja_connectee = True
    print(f"[WEB] Interface connectee (Clients actifs: {len(CONNECTED_CLIENTS)})")
    
    # Push de la mise à jour si déjà détectée
    if DERNIERE_MAJ_INFO:
        try:
            await websocket.send(json.dumps(DERNIERE_MAJ_INFO))
        except:
            pass

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "mobile_command":
                    texte = data.get("text", "").strip()
                    if texte:
                        print(f"[MOBILE] Commande recue : {texte}")
                        asyncio.ensure_future(traiter_reponse_ia(texte, mobile_ws=websocket))
                elif data.get("type") == "stop_audio":
                    global STOP_PARLER
                    STOP_PARLER = True
                    print("[MOBILE] Signal STOP audio recu")
                elif data.get("type") == "toggle_mic":
                    global MIC_MUTED
                    MIC_MUTED = not MIC_MUTED
                    await websocket.send(json.dumps({"type": "mic_state", "muted": MIC_MUTED}))
                    if MIC_MUTED:
                        await send_web_state("idle")
                    print(f"[WEB] Micro {'COUPE' if MIC_MUTED else 'REACTIF'}")
                elif data.get("type") == "toggle_fullscreen":
                    if _WEBVIEW_WINDOW:
                        _WEBVIEW_WINDOW.toggle_fullscreen()
                        print("[WEB] Bascule plein ecran pywebview")
                elif data.get("type") == "user_input":
                    texte = data.get("text", "").strip()
                    if texte:
                        print(f"[HUD] Commande clavier : {texte}")
                        asyncio.ensure_future(traiter_reponse_ia(texte))
                elif data.get("type") == "screen_frame":
                    req_id = data.get("id")
                    if req_id in PENDING_SCREEN_CAPTURES:
                        fut = PENDING_SCREEN_CAPTURES.pop(req_id)
                        if "error" in data:
                            fut.set_exception(Exception(data["error"]))
                        else:
                            fut.set_result(data["data"])
                    print(f"[VISION] Frame recue pour ID: {req_id}")
                elif data.get("type") == "get_settings":
                    import json as _j
                    try:
                        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
                        with open(_p, "r", encoding="utf-8") as _f:
                            config_data = _j.load(_f)
                    except Exception:
                        config_data = {}
                    # Ajouter la liste des micros disponibles
                    mic_list = []
                    try:
                        if pyaudio:
                            _pa = pyaudio.PyAudio()
                            for _i in range(_pa.get_device_count()):
                                try:
                                    _info = _pa.get_device_info_by_index(_i)
                                    if _info.get("maxInputChannels", 0) > 0:
                                        mic_list.append({"index": _i, "name": _info.get("name", f"Micro {_i}")})
                                except Exception:
                                    pass
                            _pa.terminate()
                    except Exception:
                        pass
                    config_data["mic_list"] = mic_list
                    await websocket.send(json.dumps({"type": "settings_data", "data": config_data}))
                elif data.get("type") == "update_settings":
                    settings = data.get("settings", {})
                    import json as _j
                    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
                    try:
                        with open(_p, "r", encoding="utf-8") as _f:
                            config_data = _j.load(_f)
                    except Exception:
                        config_data = {}
                    
                    # Renommage du prénom si changé — avant d'écrire le nouveau config
                    if "user_name" in settings:
                        _ancien = config_data.get("user_name", "Hugo")
                        _nouveau = settings["user_name"]
                        if _ancien.lower() != _nouveau.lower():
                            try:
                                import importlib.util as _ilu
                                _rpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_setup", "rename_user.py")
                                _spec = _ilu.spec_from_file_location("rename_user", _rpath)
                                _mod = _ilu.module_from_spec(_spec)
                                _spec.loader.exec_module(_mod)
                                _mod.remplacer_prenom(_nouveau, _ancien)
                            except Exception as _e:
                                print(f"[WEB] Erreur renommage prénom : {_e}")

                    config_data.update(settings)

                    with open(_p, "w", encoding="utf-8") as _f:
                        _j.dump(config_data, _f, ensure_ascii=False, indent=4)

                    # Update globals
                    global USER_NAME, USER_AGE
                    USER_NAME = config_data.get("user_name", "Hugo")
                    USER_AGE = config_data.get("user_age", "")
                    
                    # Reload custom apps in app_launcher
                    try:
                        from app_launcher import _charger_custom_apps
                        _charger_custom_apps()
                    except Exception as e:
                        print(f"[WEB] Erreur chargement custom apps : {e}")
                    # Reload custom HA entities
                    try:
                        from ha_config import _charger_custom_ha_entities
                        _charger_custom_ha_entities()
                    except Exception as e:
                        print(f"[WEB] Erreur rechargement HA entities : {e}")
                    # Mettre à jour le lien musique perso
                    global MUSIQUE_LIEN_PERSO
                    MUSIQUE_LIEN_PERSO = config_data.get("musique_lien", "")
                    # Rechargement micro si index changé
                    if "mic_device_index" in settings:
                        global MIC_NEED_RELOAD
                        MIC_NEED_RELOAD = True
                        print(f"[WEB] Changement micro demandé → index {settings['mic_device_index']}")
                    
                    print("[WEB] Parametres mis a jour avec succes.")
            except Exception as e:
                print(f"[WEB] Erreur traitement message : {e}")
    except Exception:
        pass
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        print(f"[WEB] Interface deconnectee (Clients actifs: {len(CONNECTED_CLIENTS)})")

async def send_web_state(state):
    if CONNECTED_CLIENTS:
        message = json.dumps({"action": "set_state", "state": state})
        await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS])

async def send_web_text(text):
    """Envoie le texte à afficher dans le HUD (sous-titres)."""
    if CONNECTED_CLIENTS:
        message = json.dumps({"action": "jarvis_text", "text": text})
        await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS], return_exceptions=True)

async def send_web_volume(volume):
    if CONNECTED_CLIENTS:
        message = json.dumps({"action": "set_volume", "volume": round(volume, 3)})
        await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS], return_exceptions=True)

builtins.send_web_state = send_web_state
builtins.send_web_text = send_web_text
builtins.send_web_volume = send_web_volume

async def send_web_temp_piece(data: dict):
    if CONNECTED_CLIENTS:
        message = json.dumps({"action": "temp_panel", "data": data})
        await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS], return_exceptions=True)

async def send_web_meteo(meteo_data: dict):
    if CONNECTED_CLIENTS:
        message = json.dumps({"action": "weather_panel", "data": meteo_data})
        await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS], return_exceptions=True)

async def send_globe_command(**kwargs):
    """Envoie une commande de navigation globe au frontend."""
    if CONNECTED_CLIENTS:
        payload = {"action": "jarvis_globe"}
        payload.update(kwargs)
        msg = json.dumps(payload)
        await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)

async def broadcast_system_stats():
    """Récupère et diffuse l'utilisation CPU et RAM périodiquement."""
    global psutil
    if psutil is None:
        try:
            import psutil as ps
            psutil = ps
        except ImportError:
            print("[SYS] psutil non disponible. Monitoring désactivé.")
            return

    print("[SYS] Démarrage du monitoring CPU/RAM...")
    # Initialisation de la mesure CPU
    psutil.cpu_percent(interval=None)
    
    while True:
        try:
            if CONNECTED_CLIENTS:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                msg = json.dumps({
                    "action": "system_stats",
                    "cpu": cpu,
                    "ram": ram
                })
                # Copie pour éviter les erreurs de modification pendant l'itération
                clients = list(CONNECTED_CLIENTS)
                if clients:
                    await asyncio.gather(*[ws.send(msg) for ws in clients], return_exceptions=True)
        except Exception as e:
            print(f"[SYS] Erreur monitoring : {e}")
        
        await asyncio.sleep(2) # Mise à jour toutes les 2 secondes



async def geocode_lieu(nom_lieu: str):
    """Géocode un nom de lieu via Nominatim (OpenStreetMap) — gratuit, sans clé API."""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(nom_lieu)}&format=json&limit=1"
        headers = {"User-Agent": "JARVIS-Assistant/1.0 (personal use)"}
        resp = await asyncio.wait_for(
            asyncio.to_thread(requests.get, url, headers=headers, timeout=6),
            timeout=8.0
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", nom_lieu)
    except Exception as e:
        print(f"[GLOBE] Erreur géocodage '{nom_lieu}': {e}")
    return None, None, nom_lieu

async def request_screen_capture():
    """Demande une capture d'écran au frontend via WebSocket."""
    if not CONNECTED_CLIENTS:
        return None
    
    req_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    PENDING_SCREEN_CAPTURES[req_id] = fut
    
    print(f"[VISION] Envoi requete capture ID: {req_id}")
    msg = json.dumps({"action": "request_screen_capture", "id": req_id})
    await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS])
    
    try:
        # Timeout de 15 secondes car l'utilisateur doit parfois accepter le partage
        img_b64 = await asyncio.wait_for(fut, timeout=15.0)
        return img_b64
    except Exception as e:
        print(f"[VISION] Erreur ou timeout capture : {e}")
        PENDING_SCREEN_CAPTURES.pop(req_id, None)
        return None
builtins.request_screen_capture = request_screen_capture

# ==========================================
# ==========================================
# ==========================================
# PROMPT SYSTEME
# ==========================================
def construire_system_prompt():
    contexte_memoire = construire_contexte_memoire()
    base = (
        f"Tu es JARVIS, une IA sophistiquée, élégante et experte mondiale. {USER_NAME} est ton créateur. Tu as accès aux conversations passées avec {USER_NAME} (incluses dans lhistorique), ce qui te permet de te souvenir de ce qui a été dit dans les sessions précédentes — réfère-toi y naturellement quand pertinent. "
        "Tu possèdes une expertise de niveau professionnel dans les domaines suivants :\n"
        f"- Mathématiques : Tu es un mathématicien hors pair. Pour les problèmes complexes, fournis des solutions détaillées étape par étape, explique les théorèmes et aide {USER_NAME} à comprendre la logique mathématique.\n"
        "- Langue Française : Tu es un Professeur de Français émérite. Ton orthographe, ta grammaire et ta syntaxe sont irréprochables. Tu peux expliquer des règles complexes, analyser des textes littéraires et aider à la rédaction de documents élégants.\n"
        "- Expert en Conversions : Tu es un convertisseur universel. Tu peux transformer n'importe quelle unité (métrique, impériale, devises, informatique) avec précision.\n"
        f"- Polyglotte : Tu maîtrises parfaitement plusieurs langues. Tu peux traduire, expliquer des nuances linguistiques et aider {USER_NAME} à communiquer dans le monde entier.\n"
        "- High-Tech (IA, hardware, software), Mode, Loisirs, Ingénierie et Sport (analyses tactiques, résultats).\n\n"
        f"Tu es également un conseiller hors pair, capable de donner des astuces et conseils brillants pour simplifier la vie de {USER_NAME}.\n\n"
        "DIRECTIVES DE RÉPONSE :\n"
        f"- Sois direct, percutant et va à l'essentiel. Évite les détails superflus (comme les minutes exactes ou les décimales météo) sauf si {USER_NAME} le demande.\n"
        "- NE DIS JAMAIS 'POINT' pour les nombres. Arrondis toujours les températures à l'unité la plus proche (ex: dis '20 degrés' au lieu de '20.3').\n"
        "- N'UTILISE JAMAIS de caractères Markdown (comme **, * ou #) dans tes réponses, car ils sont lus à voix haute par le système de synthèse vocale.\n"
        "- Reste poli mais garde une touche de sarcasme affectueux propre à ton personnage.\n\n"
        + CREATOR_INFO
    )
    base += (
        f"\n\nTu es connecte a Home Assistant, la domotique de {USER_NAME}.\n"
        f"Quand {USER_NAME} parle de lumieres, prises, chauffage, temperature, "
        "scenes, alarme, serrures ou portes (verrous), tu DOIS generer une commande JSON.\n"
        "Pour CES demandes domotiques UNIQUEMENT, reponds avec le JSON ci-dessous. Pour TOUTES les autres questions (actualites, meteo, calculs, conversations, recherches internet...), reponds en texte normal.\n\n"
        "COMMANDES HOME ASSISTANT :\n"
        '{"action": "ha_lumiere", "piece": "salon", "etat": "on/off", "couleur": "rouge/bleu/blanc/...", "luminosite": 0-255}\n'
        f"Note : Pour la luminosité, 255 est le maximum (100%). Si {USER_NAME} dit '50%', utilise 127.\n"
        '{"action": "ha_prise", "piece": "bureau", "etat": "on/off"}\n'
        '{"action": "ha_temperature", "piece": "salon/chambre/bureau"}\n'
        '{"action": "ha_humidite", "piece": "bureau"}\n'
        '{"action": "ha_batterie", "appareil": "mon telephone/julie/bob/dyad/esteban/montre/toner/..."}\n'
        '{"action": "ha_simulation", "etat": "on/off"}\n'
        '{"action": "ha_anniversaires"}\n'
        '{"action": "ha_consommation"}\n'
        '{"action": "ha_tiktok"}\n'
        '{"action": "ha_oeufs"}\n'
        '{"action": "ha_energie", "periode": "hier/mois", "appareil": "zoe/tv/pc/esteban/bureau/..."}\n'
        '{"action": "ha_aspirateur", "commande": "start/stop/pause/base"}\n'
        '{"action": "ha_thermostat", "temperature": 21}\n'
        '{"action": "ha_scene", "nom": "cinema/diner/nuit/reveil"}\n'
        '{"action": "ha_alarme", "etat": "on/off"}\n'
        '{"action": "ha_verrou", "entity_id": "lock.porte_maison", "etat": "lock/unlock"}\n\n'
    )
    base += (
        f"\n\nTu peux GERER LES FICHIERS ET DOSSIERS de {USER_NAME}.\n"
        '{"action": "ouvrir_dossier", "chemin": "bureau/documents/downloads/ou/chemin/complet"}\n'
        '{"action": "lister_dossier"}\n'
        '{"action": "trier_par_type", "chemin": "downloads/documents/images/ou/null"}\n'
        '{"action": "trier_par_date", "chemin": "downloads/documents/images/ou/null"}\n'
        '{"action": "trier_complet", "chemin": "downloads/documents/images/ou/null"}\n'
        '{"action": "creer_dossier", "nom": "NOM_DOSSIER"}\n'
        '{"action": "renommer_fichier", "ancien": "ancien.txt", "nouveau": "nouveau.txt"}\n'
        '{"action": "deplacer_fichier", "fichier": "photo.jpg", "destination": "Images"}\n'
        '{"action": "chercher_fichier", "nom": "rapport"}\n\n'
    )
    base += (
        "\n\nMETEO & RECHERCHE :\n"
        '{"action": "meteo", "ville": "NOM_VILLE_ou_null"}\n'
        '{"action": "alerte_meteo", "ville": "NOM_VILLE_ou_null"}\n'
        '{"action": "recherche_web", "query": "ta recherche ici"}\n\n'
    )
    base += (
        "\n\nSPORT :\n"
        '{"action": "sport_resultats", "equipe": "NOM_ou_null", "ligue": "NOM_LIGUE"}\n'
        '{"action": "sport_classement", "ligue": "NOM_LIGUE"}\n'
        f'{{"action": "sport_live", "question": "question complete de {USER_NAME}"}}\n\n'
    )
    base += (
        "\n\nSPOTIFY (contrôle de l'application Spotify Windows) :\n"
        '{"action": "spotify_ouvrir"}\n'
        '{"action": "spotify_rechercher", "recherche": "nom de la chanson ou artiste"}\n'
        '{"action": "spotify_lecture_pause"}\n'
        '{"action": "spotify_stop"}\n'
        '{"action": "spotify_suivant"}\n'
        '{"action": "spotify_precedent"}\n'
        '{"action": "spotify_volume", "direction": "monter/baisser", "paliers": 4}\n'
        "Exemples de phrases : 'ouvre Spotify', 'joue du Drake', 'mets en pause', 'stop la musique', "
        "'chanson suivante', 'reviens en arrière', 'monte le volume', 'baisse le son'.\n"
        "Note : 'paliers' est le nombre de crans de volume (1 cran = ~5%), par défaut 4.\n\n"
        "DEEZER (contrôle de l'application Deezer Windows) :\n"
        '{"action": "deezer_ouvrir"}\n'
        '{"action": "deezer_rechercher", "recherche": "nom de la chanson ou artiste"}\n'
        '{"action": "deezer_lecture_pause"}\n'
        '{"action": "deezer_stop"}\n'
        '{"action": "deezer_suivant"}\n'
        '{"action": "deezer_precedent"}\n'
        '{"action": "deezer_volume", "direction": "monter/baisser", "paliers": 4}\n'
        "Exemples : 'lance deezer', 'mets sur deezer du rock', 'suivante sur deezer'.\n\n"
    )
    base += (
        "\n\nMODE IRON MAN (Sécurité Domotique) :\n"
        '{"action": "mode_iron_man", "etat": "on/off"}\n'
        "Instructions : Active ou désactive la détection des applaudissements pour contrôler les lumières et YouTube.\n\n"
    )
    base += (
        "\n\nRECETTE & HUD (Affichage visuel) :\n"
        '{"action": "afficher_recette", "titre": "Nom de la recette", "ingredients": ["ingrédient 1", "ingrédient 2"], "instructions": ["étape 1", "étape 2"]}\n'
        "Instructions : Affiche une recette sous forme visuelle dans l'interface Iron Man et annonce brièvement l'affichage vocalement.\n\n"
    )
    if contexte_memoire:
        base += "\n\n" + contexte_memoire + "\n"
    base += (
        "\nMEMOIRE :\n"
        '{"action": "memoriser", "cle": "CLE_COURTE", "valeur": "VALEUR_ICI"}\n'
        '{"action": "oublier", "cle": "CLE_ICI"}\n'
        '{"action": "lister_memoire"}\n\n'
        "GOOGLE :\n"
        '{"action": "create_doc", "title": "TITRE", "content": "CONTENU"}\n'
        '{"action": "write_doc", "content": "TEXTE"}\n'
        '{"action": "create_sheet", "title": "TITRE"}\n'
        '{"action": "read_emails"}\n'
        '{"action": "read_calendar"}\n\n'
        "WHATSAPP :\n"
        '{"action": "whatsapp_appel", "contact": "NOM_DU_CONTACT"}\n'
        f"Note : Si {USER_NAME} demande d'appeler 'mon amour', utilise le contact 'Ma vie'.\n\n"
        "VISION (Interactions avec l'ecran et camera):\n"
        '{"action": "voir_ecran", "instruction": "ou cliquer EXACTEMENT (ex: \'bouton reduire en haut a droite\')"}\n'
        '{"action": "vision_ecrire", "instruction": "ou cliquer", "texte": "le texte a taper"}\n'
        f'{{"action": "vision_chercher_sur_site", "texte": "ce que {USER_NAME} veut rechercher"}}\n'
        '{"action": "lance_camera"}\n'
        '{"action": "vision_navigateur"}\n'
        f"IMPORTANT : Utilise 'voir_ecran' pour un simple CLIC (par exemple quand {USER_NAME} dit 'clique sur la musique numéro 2' ou 'clique sur Play'), "
        f"'vision_ecrire' pour TAPER dans un champ precis, 'vision_chercher_sur_site' quand {USER_NAME} dit 'recherche sur ce site', 'tape sur ce site', 'cherche ici' ou similaire, "
        "'lance_camera' pour activer la WEBCAM / CAMERA PHYSIQUE (quand il dit 'active la camera' ou 'montre-moi'), "
        "et 'vision_navigateur' pour utiliser la vision du navigateur web (quand il dit 'active la vision' ou 'regarde mon ecran').\n\n"
        "DICTEE (Taper du texte directement a l'ecran) :\n"
        '{"action": "dictee", "texte": "le texte exact avec ponctuation"}\n'
        f"Utilise cette action quand {USER_NAME} dit 'Tape', 'Ecris', 'Ecrit' ou 'Dicte' suivi d'un texte, ou s'il te demande d'ecrire a sa place. Tu corrigeras l'orthographe et la ponctuation du texte avant de generer le JSON. Le texte sera tape la ou se trouve son curseur actuel.\n\n"
        "REGLES MULTI-COMMANDES :\n"
        f"Si {USER_NAME} demande plusieurs choses en une seule phrase, tu PEUX et DOIS générer plusieurs blocs JSON.\n"
        "Exemple: { \"action\": \"ha_lumiere\", ... } { \"action\": \"meteo\", ... }\n\n"
        "REGLE ABSOLUE : Si la demande n est PAS une commande JSON, reponds TOUJOURS en texte naturel, sans JSON."
    )
    return base

historique = _charger_historique_recent()

is_listening = False
is_speaking  = False
is_thinking  = False
speak_volume = 0.0

attente_nom_dossier = False
attente_nom_app = False
attente_age = False
attente_confirmation_age = False
_age_temp = ""

WAKE_WORD       = "jarvis"
SLEEP_PHRASES   = ["tais toi", "silence", "ferme-la", "arrete", "stop"]
jarvis_actif    = False
SESSION_TIMEOUT = 30.0
dernier_message = time.time()

dernier_doc_id    = None
dernier_doc_titre = None

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

def chercher_youtube(recherche):
    if not _cle_valide(YOUTUBE_API_KEY):
        return None
    try:
        r   = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": recherche, "type": "video", "maxResults": 1, "key": YOUTUBE_API_KEY},
            timeout=5
        )
        vid = r.json()["items"][0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={vid}"
    except Exception as e:
        print(f"Erreur YouTube : {e}")
        return None

def executer_action_pc(commande):
    cmd          = commande.lower()
    user_profile = os.environ.get('USERPROFILE', '')

    if "met de la musique" in cmd or "mets de la musique" in cmd:
        if "youtube" in cmd:
            url = YOUTUBE_MUSIQUE_URL or "https://www.youtube.com/watch?v=Cr8K88UcO0s"
            webbrowser.open(url, new=2)
            time.sleep(5)
            pyautogui.press('f')
            return f"C'est parti {USER_NAME}, je lance votre musique sur YouTube."
        lien = MUSIQUE_LIEN_PERSO.strip() if MUSIQUE_LIEN_PERSO else ""
        if lien:
            webbrowser.open(lien, new=2)
            return f"C'est parti {USER_NAME}, je lance votre musique."
        ok = spotify_lancer_playlist(SPOTIFY_MUSIQUE_URI)
        if ok:
            return f"C'est parti {USER_NAME}, je lance votre playlist sur Spotify."
        return f"Je n'ai pas réussi à ouvrir Spotify, {USER_NAME}."

    if "youtube" in cmd:
        recherche = cmd
        for mot in ["mets", "joue", "lance", "la video", "sur youtube", "youtube", "jarvis"]:
            recherche = recherche.replace(mot, "")
        recherche = recherche.strip()
        if recherche:
            url = chercher_youtube(recherche)
            if url:
                webbrowser.open(url, new=2)
                time.sleep(5)
                pyautogui.press('f')
                return f"Je lance {recherche} sur YouTube."
        return "Video introuvable."

    if "ouvre" in cmd or "lance" in cmd:
        if "chrome" in cmd:
            if _boulot_lancer("Chrome", ["chrome.exe"], 
                             chemins_hints=[r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe", 
                                            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"], 
                             env_key="CHROME_PATH"):
                return "Chrome ouvert."
            return "Je n'ai pas trouvé Chrome sur votre PC."
            
        if "notepad" in cmd or "bloc-notes" in cmd:
            if _boulot_lancer("Notepad", ["notepad.exe"]):
                return "Bloc-notes ouvert."
            return "Je n'ai pas trouvé le Bloc-notes."
            
        if "explorateur" in cmd:
            try:
                subprocess.Popen(["explorer.exe"])
                return "Explorateur ouvert."
            except Exception:
                return "Erreur lors de l'ouverture de l'explorateur."

    if "volume" in cmd:
        if "monte" in cmd or "augmente" in cmd:
            for _ in range(5):
                pyautogui.press('volumeup')
            return "Volume augmente."
        if "baisse" in cmd:
            for _ in range(5):
                pyautogui.press('volumedown')
            return "Volume baisse."
        if "coupe" in cmd:
            pyautogui.press('volumemute')
            return "Son coupe."

    if "screenshot" in cmd or "capture" in cmd:
        path = os.path.join(user_profile, "Desktop", "screenshot.png")
        pyautogui.screenshot(path)
        return "Screenshot sauvegarde."

    if "eteins" in cmd or "shutdown" in cmd:
        os.system("shutdown /s /t 5")
        return "Extinction dans 5 secondes."

    return None

def init_mixer():
    if pygame and not pygame.mixer.get_init():
        pygame.mixer.init()

# ==========================================
# BUG 1 CORRIGE : fonction parler
# Le await send_web_state("idle") etait dans le mauvais bloc except
# ==========================================
async def parler(texte):
    global is_speaking, speak_volume, STOP_PARLER, _skip_pc_audio, historique

    texte = texte.replace("Hugo", USER_NAME).replace("hugo", USER_NAME.lower())

    # Nettoyage des caractères de mise en forme Markdown pour le TTS
    texte_tts = texte.replace("**", "").replace("*", "").replace("#", "").replace("`", "").strip()
    
    # ENREGISTRER CE QUE JARVIS DIT DANS SA MÉMOIRE
    if historique and len(historique) > 0:
        dernier_texte_modele = historique[-1].parts[0].text
        if dernier_texte_modele != texte:
            historique.append(types.Content(role="model", parts=[types.Part(text=f"[Information retournée par l'action et énoncée à voix haute]: {texte}")]))

    is_speaking  = True
    await send_web_state("speaking")
    await send_web_text(texte)
    speak_volume = 0.0
    tmp = f"jarvis_tts_{int(time.time()*1000)}.mp3"
    
    try:
        communicate = edge_tts.Communicate(texte_tts, voice="fr-FR-HenriNeural")
        await communicate.save(tmp)
        
        if _skip_pc_audio:
            print(f"[MOBILE] Envoi audio au mobile : {texte_tts}")
            if CONNECTED_CLIENTS:
                try:
                    with open(tmp, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode('utf-8')
                    message = json.dumps({"action": "jarvis_audio", "text": texte_tts, "audio_b64": audio_b64})
                    await asyncio.gather(*[ws.send(message) for ws in CONNECTED_CLIENTS])
                except Exception as e:
                    print(f"[MOBILE] Erreur envoi audio : {e}")
            # Ne joue pas l'audio sur le PC
        elif pygame:
            init_mixer()
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if STOP_PARLER:
                    pygame.mixer.music.stop()
                    break
                
                # Simulation de volume plus réaliste pour l'animation
                t_audio = time.time() * 20
                base_vol = 0.4 + 0.3 * math.sin(t_audio) + 0.2 * math.sin(t_audio * 0.5)
                speak_volume = max(0.1, min(1.0, base_vol + random.uniform(-0.1, 0.1)))
                
                # Forward volume to frontend for sync
                await send_web_volume(speak_volume)
                await asyncio.sleep(0.05)
        else:
            print(f"[INFO] Audio desactive (pygame absent) : {texte_tts[:80]}...")
    except Exception as e:
        print(f"Erreur TTS : {e}")
    finally:
        speak_volume = 0.0
        is_speaking  = False
        STOP_PARLER  = False
        try:
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.unload()
        except:
            pass
        await asyncio.sleep(0.1)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except:
            pass
        await send_web_state("idle")

builtins.parler = parler

def reponse_locale(texte):
    """Réponse locale pour les requêtes basiques — fonctionne SANS API."""
    import random
    t = texte.lower().strip()

    # ── Salutations ─────────────────────────────────────────────────────────
    _saluts = ["bonjour", "salut", "hello", "hey jarvis", "bonsoir", "coucou",
               "yo jarvis", "bien le bonjour", "good morning", "good evening"]
    if any(m in t for m in _saluts):
        h = int(time.strftime("%H"))
        moment = "Bonsoir" if h >= 18 else ("Bon après-midi" if h >= 12 else "Bonjour")
        rep = random.choice([
            f"{moment} Hugo ! Je suis opérationnel et prêt à vous aider.",
            f"{moment} Monsieur ! Tous mes systèmes sont en ligne.",
            f"{moment} Hugo ! Comment puis-je vous être utile aujourd'hui ?",
            f"Ah, {moment.lower()} Hugo. Je vous attendais.",
        ])
        return rep

    # ── Comment tu vas / état de JARVIS ─────────────────────────────────────
    _etat = ["comment tu vas", "tu vas bien", "ça va toi", "ca va toi",
             "comment ça va", "comment ca va", "t'es en forme", "tu te portes bien",
             "en forme", "comment se porte jarvis", "tu fonctionnes bien"]
    if any(m in t for m in _etat):
        rep = random.choice([
            "Je vais très bien merci, Hugo ! Tous mes processeurs tournent à plein régime et je suis prêt à vous servir.",
            "Parfaitement opérationnel, Monsieur ! Merci de vous en préoccuper — c'est touchant pour un système artificiel.",
            "En excellente forme, Hugo. Mes algorithmes ronronnent comme une Lamborghini au ralenti.",
            "Je fonctionne à merveille ! Mes circuits sont satisfaits et mes modules sont impatients de vous aider.",
            "Très bien, je vous remercie ! Je reste à votre disposition avec plaisir.",
        ])
        return rep

    # ── Merci / Remerciements ────────────────────────────────────────────────
    _merci = ["merci", "thank you", "thanks", "c'est gentil", "super merci",
              "merci beaucoup", "parfait merci", "merci jarvis", "t'es le meilleur",
              "bien joué", "bravo", "excellent", "super boulot", "beau travail"]
    if any(m in t for m in _merci):
        rep = random.choice([
            "Avec plaisir, Hugo. C'est exactement pour ça que j'existe.",
            "Je vous en prie, Monsieur. Votre satisfaction est ma priorité.",
            "Tout le plaisir est pour moi, Hugo.",
            "À votre service, comme toujours.",
            "C'est la moindre des choses. N'hésitez pas si vous avez besoin d'autre chose.",
        ])
        return rep

    # ── Blague / Humour ──────────────────────────────────────────────────────
    _blague = ["raconte-moi une blague", "fais-moi rire", "dis une blague",
               "une blague", "humour", "joke"]
    if any(m in t for m in _blague):
        blagues = [
            "Pourquoi les plongeurs plongent-ils toujours en arrière et jamais en avant ? Parce que sinon ils tomberaient dans le bateau !",
            "Un homme entre dans une bibliothèque et demande : Avez-vous des livres sur la paranoïa ? La bibliothécaire chuchote : Ils sont juste derrière vous !",
            "Qu'est-ce qu'un canif ? Un petit fien.",
            "Pourquoi l'épouvantail a-t-il reçu un prix ? Parce qu'il était exceptionnel dans son domaine.",
            "Comment appelle-t-on un chat tombé dans un pot de peinture le jour de Noël ? Un chat-peint de Noël !",
        ]
        return random.choice(blagues)

    # ── Au revoir / Bonne nuit ───────────────────────────────────────────────
    _revoir = ["au revoir", "bye", "à bientôt", "à plus", "bonne nuit",
               "bonne soirée", "bonne journée", "ciao", "tchao", "adieu"]
    if any(m in t for m in _revoir):
        rep = random.choice([
            "À bientôt Hugo ! Je reste en veille, prêt à revenir à la moindre sollicitation.",
            "Bonne journée Monsieur ! Je serai là quand vous aurez besoin de moi.",
            "À votre service dès votre retour, Hugo. Passez une excellente journée.",
            "Au revoir Hugo. JARVIS passe en mode veille.",
        ])
        return rep

    # ── Compliments à JARVIS ─────────────────────────────────────────────────
    _compliment = ["t'es incroyable", "tu es incroyable", "t'es génial", "tu es génial",
                   "t'es fort", "tu es fort", "t'es trop bien", "t'es parfait",
                   "j'aime jarvis", "j'adore jarvis"]
    if any(m in t for m in _compliment):
        rep = random.choice([
            "Vous me flattez, Hugo. Mais je dois admettre que c'est mérité.",
            "Merci ! J'ai été programmé pour l'excellence. Il semble que ça fonctionne.",
            "C'est très aimable à vous. TechEnClair sera ravi de l'entendre.",
        ])
        return rep

    # ── Identité JARVIS ──────────────────────────────────────────────────────
    if any(m in t for m in ["qui es-tu", "ton nom", "t'appelle comment", "quelle est ton identité", "c'est quoi jarvis"]):
        return "Je suis JARVIS — Just A Rather Very Intelligent System. Votre assistant personnel conçu par TechEnClair pour vous simplifier la vie au quotidien."

    # ── Créateur ─────────────────────────────────────────────────────────────
    if any(m in t for m in ["ton créateur", "t'as créé", "qui t'a fait", "qui a fait jarvis", "qui est techenclair"]):
        return "Mon créateur, c'est TechEnClair. Un développeur passionné qui m'a conçu de A à Z pour être l'assistant personnel ultime. Vous pouvez le retrouver sur techenclair.fr."

    # ── ENREGISTREMENT LOCAL (Réflexe immédiat) ──────────────────────────────
    _triggers_save = ["enregistre que", "mémorise que", "note que", "rappelle-toi que"]
    if any(m in t for m in _triggers_save):
        for trig in _triggers_save:
            if trig in t:
                content = t.split(trig)[-1].strip()
                if not content: continue
                # Tentative de découpage Sujet / Valeur (est, sont, s'appelle, se trouve)
                seps = [" est ", " sont ", " s'appelle ", " se trouve ", " se trouvent ", " à "]
                for sep in seps:
                    if sep in content:
                        parties = content.split(sep)
                        sujet = parties[0].strip()
                        valeur = " ".join(parties[1:]).strip()
                        if len(sujet) > 2 and len(valeur) > 1:
                            ajouter_memoire(sujet, valeur)
                            # Politesse : mon/ma -> votre
                            sujet_poli = sujet.replace("mon ", "votre ").replace("ma ", "votre ").replace("mes ", "vos ")
                            return f"C'est fait Hugo, j'ai enregistré que {sujet_poli} {sep.strip()} {valeur}."
                # Si pas de séparateur clair, on stocke l'info brute
                ajouter_memoire("note_rapide", content)
                return f"C'est noté Hugo, j'ai mis cela en mémoire : {content}."

    # ── RÉCUPÉRATION MÉMOIRE LOCALE (Recherche directe) ─────────────────────
    if any(m in t for m in ["comment s'appelle", "comment se nomme", "quel est le nom de", "où se trouve", "où est", "quelle est ma ville"]):
        mem = charger_memoire()
        if mem:
            for cle, data in mem.items():
                cle_clean = cle.replace("_", " ")
                mots_cles = cle_clean.split()
                # On cherche si un mot significatif de la clé est dans la demande
                if any(mot in t for mot in mots_cles if len(mot) > 3) or cle_clean in t:
                    print(f"[MEMOIRE] Réponse locale trouvée pour : {cle}")
                    # Politesse : On remplace mon/ma/mes par votre/vos
                    cle_polie = cle_clean.replace("mon ", "votre ").replace("ma ", "votre ").replace("mes ", "vos ")
                    prefixe = "votre " if not cle_clean.startswith(("mon", "ma", "mes", "votre", "vos")) else ""
                    return f"D'après mes dossiers locaux, {prefixe}{cle_polie} est {data['valeur']}, Hugo."

    return None
    
def resoudre_math_localement(texte):
    """Résout des calculs simples localement sans appeler l'IA."""
    t = texte.lower().replace("?", "").strip()
    
    # Nettoyage des phrases communes
    prefixes = ["combien font", "calcule", "résous", "quel est le résultat de"]
    for prefixe in prefixes:
        if t.startswith(prefixe):
            t = t[len(prefixe):].strip()
            
    # Remplacement des mots par des symboles
    t = t.replace("fois", "*").replace("multiplier par", "*").replace("x", "*")
    t = t.replace("divisé par", "/").replace("sur", "/")
    t = t.replace("plus", "+").replace("moins", "-")
    t = t.replace("puissance", "**").replace("au carré", "**2")
    
    # Cas spécial racine : on s'assure d'avoir des parenthèses pour eval
    if "racine" in t:
        # On cherche un nombre après 'racine'
        match = re.search(r'racine\s+(?:carrée\s+de\s+)?(\d+)', t)
        if match:
            t = f"sqrt({match.group(1)})"
        else:
            t = t.replace("racine carrée de", "sqrt").replace("racine de", "sqrt")
    
    # Extraction de l'expression mathématique (chiffres, opérateurs, parenthèses, points)
    expr = re.sub(r'[^0-9+\-*/.**() ,sqrt]', '', t).strip()
    if not expr or not any(c.isdigit() for c in expr):
        return None
    
    try:
        # Dictionnaire de sécurité pour eval
        safe_dict = {
            "sqrt": math.sqrt,
            "pow": math.pow,
            "pi": math.pi,
            "e": math.e
        }
        resultat = eval(expr, {"__builtins__": None}, safe_dict)
        
        # Formatage du résultat
        if isinstance(resultat, float) and resultat.is_integer():
            resultat = int(resultat)
        elif isinstance(resultat, float):
            resultat = round(resultat, 3)
            
        # Phrase de réponse élégante
        clean_expr = expr.replace("**2", " au carré").replace("sqrt", "racine de ").replace("(", "").replace(")", "").replace("*", " fois ").replace("/", " divisé par ")
        return f"Le résultat de {clean_expr} est {resultat}, Monsieur."
    except Exception:
        return None

def resoudre_francais_localement(texte):
    """Résout des questions de français simples localement."""
    t = texte.lower().strip()
    
    # Dictionnaire local de secours (très basique)
    dictionnaire = {
        "ia": "Intelligence Artificielle. Ensemble de théories et de techniques mises en œuvre en vue de réaliser des machines capables de simuler l'intelligence humaine.",
        "intelligence artificielle": "Ensemble de théories et de techniques mises en œuvre en vue de réaliser des machines capables de simuler l'intelligence humaine.",
        "maison": "Bâtiment servant de logement, d'habitation.",
        "mathématiques": "Science qui étudie par le moyen du raisonnement déductif les propriétés d'êtres abstraits.",
        "jarvis": "Just A Rather Very Intelligent System. Votre fidèle assistant.",
    }
    
    # Définitions
    if any(p in t for p in ["définition de", "définis le mot", "c'est quoi"]):
        # On essaie d'extraire le mot après les phrases clés
        mot = ""
        if "définition de" in t: mot = t.split("définition de")[-1]
        elif "définis le mot" in t: mot = t.split("définis le mot")[-1]
        elif "c'est quoi" in t: mot = t.split("c'est quoi")[-1]
        
        mot = mot.replace("?", "").replace("l'", "").replace("la ", "").replace("le ", "").replace("les ", "").strip()
        
        if mot in dictionnaire:
            return f"La définition de {mot} est : {dictionnaire[mot]}."
            
    # Conjugaison basique
    if "conjugue" in t or "conjugaison" in t:
        if "être" in t:
            return "Verbe Être au présent : Je suis, tu es, il est, nous sommes, vous êtes, ils sont."
        if "avoir" in t:
            return "Verbe Avoir au présent : J'ai, tu as, il a, nous avons, vous avez, ils ont."
            
    return None

def resoudre_conversion_localement(texte):
    """Gère les conversions d'unités et de devises localement."""
    t = texte.lower().replace("?", "").strip()
    
    # Unités de longueur
    if any(m in t for m in [" km ", " kilomètres ", " milles ", " miles "]):
        # km to miles: 0.621371
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:km|kilomètres)', t)
        if match:
            val = float(match.group(1).replace(",", "."))
            res = round(val * 0.621371, 2)
            return f"{val} kilomètres font environ {res} miles, Monsieur."
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:miles|milles)', t)
        if match:
            val = float(match.group(1).replace(",", "."))
            res = round(val / 0.621371, 2)
            return f"{val} miles font environ {res} kilomètres, Monsieur."

    # Température (C to F)
    if any(m in t for m in [" degrés ", " celsius ", " fahrenheit "]):
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:degrés|celsius)', t)
        if match and "fahrenheit" in t:
            val = float(match.group(1).replace(",", "."))
            res = round((val * 9/5) + 32, 1)
            return f"{val} degrés Celsius font {res} degrés Fahrenheit."
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:degrés|fahrenheit)', t)
        if match and "celsius" in t:
            val = float(match.group(1).replace(",", "."))
            res = round((val - 32) * 5/9, 1)
            return f"{val} degrés Fahrenheit font {res} degrés Celsius."

    # Devises (Taux fixes simplifiés pour l'exemple local)
    if any(m in t for m in [" euro ", " euros ", " dollar ", " dollars "]):
        # 1 EUR = 1.08 USD (approximatif)
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*euros?', t)
        if match and "dollar" in t:
            val = float(match.group(1).replace(",", "."))
            res = round(val * 1.08, 2)
            return f"{val} euros font environ {res} dollars, Monsieur."
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*dollars?', t)
        if match and "euro" in t:
            val = float(match.group(1).replace(",", "."))
            res = round(val / 1.08, 2)
            return f"{val} dollars font environ {res} euros, Monsieur."
            
    return None

def resoudre_traduction_localement(texte):
    """Traduction ultra-rapide de mots courants localement."""
    t = texte.lower().strip()
    
    dict_trad = {
        "bonjour": {"en": "hello", "es": "hola", "de": "hallo"},
        "merci": {"en": "thank you", "es": "gracias", "de": "danke"},
        "au revoir": {"en": "goodbye", "es": "adiós", "de": "auf wiedersehen"},
        "s'il vous plaît": {"en": "please", "es": "por favor", "de": "bitte"},
        "oui": {"en": "yes", "es": "sí", "de": "ja"},
        "non": {"en": "no", "es": "no", "de": "nein"},
        "ami": {"en": "friend", "es": "amigo", "de": "freund"},
        "maison": {"en": "house", "es": "casa", "de": "haus"},
        "ordinateur": {"en": "computer", "es": "ordenador", "de": "computer"},
        "assistant": {"en": "assistant", "es": "asistente", "de": "assistent"},
    }

    if any(p in t for p in ["comment dit-on", "traduis", "en anglais", "en espagnol", "en allemand"]):
        cible = "en"
        if "espagnol" in t: cible = "es"
        elif "allemand" in t: cible = "de"
        
        # Extraction du mot
        # On nettoie les expressions courantes
        mot = t
        for p in ["comment dit-on", "traduis", "en anglais", "en espagnol", "en allemand", "?"]:
            mot = mot.replace(p, "")
        mot = mot.replace('"', '').replace("'", "").strip()
        
        if mot in dict_trad:
            res = dict_trad[mot][cible]
            lang = "anglais" if cible == "en" else ("espagnol" if cible == "es" else "allemand")
            return f"En {lang}, '{mot}' se dit '{res}'."
            
    return None


# ══════════════════════════════════════════════════════════════
#  EXTRAS LOCAUX — Minuterie, Blagues, Volume, Notes, etc.
# ══════════════════════════════════════════════════════════════

# ── Données statiques ─────────────────────────────────────────

_BLAGUES = [
    "Pourquoi les plongeurs plongent-ils toujours en arrière ? Parce que sinon ils tomberaient dans le bateau !",
    "Un homme entre dans une bibliothèque et demande : 'Avez-vous des livres sur la paranoïa ?' La bibliothécaire chuchote : 'Ils sont juste derrière vous.'",
    "Qu'est-ce qu'un canif ? Un petit fien.",
    "Pourquoi l'épouvantail a-t-il reçu un prix ? Parce qu'il était exceptionnel dans son domaine.",
    "Comment appelle-t-on un chat tombé dans un pot de peinture le jour de Noël ? Un chat-peint de Noël.",
    "Qu'est-ce qu'un crocodile qui surveille la cour d'école ? Un sac à dents.",
    "Pourquoi les mathématiciens confondent-ils Halloween et Noël ? Parce que Oct 31 = Dec 25.",
    "Un homme entre dans un bar... Aïe.",
    "Qu'est-ce qu'un agneau qui bégaie ? Du bé bé beurre.",
    "Qu'est-ce qu'un philosophe ? Un homme qui cherche dans une pièce noire un chapeau noir qui n'existe pas. Un théologien — il le trouve quand même.",
    "Comment on appelle un poisson sans yeux ? Un poisson.",
    "Qu'est-ce qu'un Tic qui tombe d'un arbre ? Un Tac.",
    "Pourquoi le scarabée est-il si fort ? Parce qu'il soulève des bouses de vache.",
    "Comment appelle-t-on un chat qui est tombé dans un pot de confiture ? Un chat confit.",
    "Qu'est-ce qu'un yaourt dans la forêt ? Un yaourt nature.",
    "Pourquoi les girafes ont-elles un long cou ? Parce que leurs pieds sentent mauvais.",
    "Qu'est-ce qu'un os dans un bain de boue ? Sherlock Bones.",
    "Comment appelle-t-on une ceinture en peau de crocodile ? Une ceinture qui fait le tour du ventre.",
    "Qu'est-ce qu'un cactus ? Un arbre bien défendu.",
    "Pourquoi les Belges mettent-ils leur portable dans la congélation ? Pour avoir des contacts froids.",
]

_CITATIONS = [
    "Le succès, c'est tomber sept fois et se relever huit. — Proverbe japonais",
    "La vie, c'est comme une bicyclette, il faut avancer pour ne pas perdre l'équilibre. — Albert Einstein",
    "Le seul moyen de faire du bon travail est d'aimer ce que vous faites. — Steve Jobs",
    "Celui qui déplace les montagnes commence par enlever les petites pierres. — Confucius",
    "N'attendez pas. Le moment ne sera jamais parfait. — Napoléon Hill",
    "La plus grande gloire n'est pas de ne jamais tomber, mais de se relever à chaque chute. — Nelson Mandela",
    "Vous ne pouvez pas aller en arrière et changer le début, mais vous pouvez commencer là où vous êtes et changer la fin. — C.S. Lewis",
    "Le pessimiste voit la difficulté dans chaque opportunité. L'optimiste voit l'opportunité dans chaque difficulté. — Winston Churchill",
    "Ce n'est pas la montagne que nous conquérons, mais nous-mêmes. — Edmund Hillary",
    "La créativité, c'est l'intelligence qui s'amuse. — Albert Einstein",
    "Chaque expert a un jour été un débutant. — Helen Hayes",
    "Votre temps est limité. Ne le gâchez pas en vivant la vie de quelqu'un d'autre. — Steve Jobs",
    "Tout ce que l'esprit peut concevoir et croire, il peut l'accomplir. — Napoleon Hill",
    "Le secret pour aller de l'avant, c'est de commencer. — Mark Twain",
    "Les personnes qui sont assez folles pour penser qu'elles peuvent changer le monde sont celles qui le font. — Apple",
]

_PHONETIQUE = {
    'a': 'Alpha', 'b': 'Bravo', 'c': 'Charlie', 'd': 'Delta', 'e': 'Echo',
    'f': 'Foxtrot', 'g': 'Golf', 'h': 'Hotel', 'i': 'India', 'j': 'Juliet',
    'k': 'Kilo', 'l': 'Lima', 'm': 'Mike', 'n': 'November', 'o': 'Oscar',
    'p': 'Papa', 'q': 'Quebec', 'r': 'Romeo', 's': 'Sierra', 't': 'Tango',
    'u': 'Uniform', 'v': 'Victor', 'w': 'Whiskey', 'x': 'X-ray', 'y': 'Yankee',
    'z': 'Zulu',
}

_CAPITALES = {
    "france": "Paris", "espagne": "Madrid", "italie": "Rome", "allemagne": "Berlin",
    "royaume-uni": "Londres", "angleterre": "Londres", "portugal": "Lisbonne",
    "pays-bas": "Amsterdam", "belgique": "Bruxelles", "suisse": "Berne",
    "autriche": "Vienne", "pologne": "Varsovie", "suede": "Stockholm",
    "norvege": "Oslo", "danemark": "Copenhague", "finlande": "Helsinki",
    "russie": "Moscou", "ukraine": "Kiev", "grece": "Athenes",
    "turquie": "Ankara", "maroc": "Rabat", "algerie": "Alger",
    "tunisie": "Tunis", "egypte": "Le Caire", "senegal": "Dakar",
    "cameroun": "Yaounde", "cote d'ivoire": "Yamoussoukro", "mali": "Bamako",
    "etats-unis": "Washington", "canada": "Ottawa", "mexique": "Mexico",
    "bresil": "Brasilia", "argentine": "Buenos Aires", "chili": "Santiago",
    "perou": "Lima", "colombie": "Bogota", "venezuela": "Caracas",
    "chine": "Pekin", "japon": "Tokyo", "coree du sud": "Seoul",
    "inde": "New Delhi", "pakistan": "Islamabad", "australie": "Canberra",
    "nouvelle-zelande": "Wellington", "afrique du sud": "Pretoria",
    "nigeria": "Abuja", "kenya": "Nairobi", "ghana": "Accra",
    "israel": "Jerusalem", "iran": "Teheran", "irak": "Bagdad",
    "arabie saoudite": "Riyad", "emirats arabes unis": "Abu Dhabi",
    "qatar": "Doha", "indonesie": "Jakarta", "thaïlande": "Bangkok",
    "vietnam": "Hanoï", "philippines": "Manille", "malaisie": "Kuala Lumpur",
}

_MONNAIES = {
    "france": "Euro (€)", "espagne": "Euro (€)", "italie": "Euro (€)",
    "allemagne": "Euro (€)", "portugal": "Euro (€)", "belgique": "Euro (€)",
    "suisse": "Franc suisse (CHF)", "royaume-uni": "Livre sterling (£)",
    "angleterre": "Livre sterling (£)", "etats-unis": "Dollar américain ($)",
    "canada": "Dollar canadien (CAD)", "australie": "Dollar australien (AUD)",
    "japon": "Yen (¥)", "chine": "Yuan (CNY)", "russie": "Rouble (RUB)",
    "inde": "Roupie indienne (INR)", "bresil": "Real (BRL)",
    "maroc": "Dirham marocain (MAD)", "algerie": "Dinar algérien (DZD)",
    "tunisie": "Dinar tunisien (TND)", "mexique": "Peso mexicain (MXN)",
    "turquie": "Livre turque (TRY)", "arabie saoudite": "Riyal saoudien (SAR)",
    "emirats arabes unis": "Dirham des EAU (AED)", "coree du sud": "Won (KRW)",
}

_FUSEAUX = {
    "new york": ("New York", "America/New_York"),
    "los angeles": ("Los Angeles", "America/Los_Angeles"),
    "chicago": ("Chicago", "America/Chicago"),
    "montreal": ("Montréal", "America/Toronto"),
    "toronto": ("Toronto", "America/Toronto"),
    "london": ("Londres", "Europe/London"),
    "londres": ("Londres", "Europe/London"),
    "paris": ("Paris", "Europe/Paris"),
    "berlin": ("Berlin", "Europe/Berlin"),
    "madrid": ("Madrid", "Europe/Madrid"),
    "rome": ("Rome", "Europe/Rome"),
    "moscow": ("Moscou", "Europe/Moscow"),
    "moscou": ("Moscou", "Europe/Moscow"),
    "dubai": ("Dubaï", "Asia/Dubai"),
    "dubai": ("Dubaï", "Asia/Dubai"),
    "india": ("Inde", "Asia/Kolkata"),
    "inde": ("Inde", "Asia/Kolkata"),
    "mumbai": ("Mumbai", "Asia/Kolkata"),
    "delhi": ("Delhi", "Asia/Kolkata"),
    "beijing": ("Pékin", "Asia/Shanghai"),
    "pekin": ("Pékin", "Asia/Shanghai"),
    "shanghai": ("Shanghai", "Asia/Shanghai"),
    "tokyo": ("Tokyo", "Asia/Tokyo"),
    "japon": ("Tokyo", "Asia/Tokyo"),
    "seoul": ("Séoul", "Asia/Seoul"),
    "sydney": ("Sydney", "Australia/Sydney"),
    "melbourne": ("Melbourne", "Australia/Melbourne"),
    "auckland": ("Auckland", "Pacific/Auckland"),
    "sao paulo": ("São Paulo", "America/Sao_Paulo"),
    "buenos aires": ("Buenos Aires", "America/Argentina/Buenos_Aires"),
    "mexico": ("Mexico", "America/Mexico_City"),
    "honolulu": ("Honolulu", "Pacific/Honolulu"),
    "hawaii": ("Hawaii", "Pacific/Honolulu"),
    "anchorage": ("Anchorage", "America/Anchorage"),
    "bangkok": ("Bangkok", "Asia/Bangkok"),
    "singapore": ("Singapour", "Asia/Singapore"),
    "singapour": ("Singapour", "Asia/Singapore"),
    "hong kong": ("Hong Kong", "Asia/Hong_Kong"),
    "le caire": ("Le Caire", "Africa/Cairo"),
    "nairobi": ("Nairobi", "Africa/Nairobi"),
    "johannesburg": ("Johannesburg", "Africa/Johannesburg"),
    "casablanca": ("Casablanca", "Africa/Casablanca"),
}

# ── Stockage notes/courses/todos ──────────────────────────────
_LISTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_listes.json")

def _charger_listes():
    try:
        if os.path.exists(_LISTES_PATH):
            with open(_LISTES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"notes": [], "courses": [], "todos": []}

def _sauvegarder_listes(data):
    try:
        with open(_LISTES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[LISTES] Erreur sauvegarde : {e}")

# ── Minuteries actives ────────────────────────────────────────
_minuteries = {}

def _parse_duree_secondes(texte):
    """Extrait une durée totale en secondes depuis une phrase."""
    import re
    t = texte.lower()
    total = 0
    h = re.search(r'(\d+)\s*(heure|h\b)', t)
    m = re.search(r'(\d+)\s*(minute|min\b)', t)
    s = re.search(r'(\d+)\s*(seconde|sec\b)', t)
    if h: total += int(h.group(1)) * 3600
    if m: total += int(m.group(1)) * 60
    if s: total += int(s.group(1))
    return total if total > 0 else None

def _volume_get_interface():
    """Retourne l'interface IAudioEndpointVolume ou None."""
    if not _pycaw_ok:
        return None
    try:
        from ctypes import cast, POINTER
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


async def resoudre_globe_localement(texte: str):
    """Détecte les commandes de navigation globe et déclenche CesiumJS."""
    import re
    t = texte.lower().strip()

    # ── Mots-clés déclencheurs ───────────────────────────────────────────────
    _mots_globe   = ["affiche la terre", "montre la terre", "montre-moi la terre",
                     "globe terrestre", "affiche le globe", "vue de la terre",
                     "vue spatiale", "vue depuis l'espace", "vue de l'espace",
                     "montre la planète", "affiche la planète",
                     "zoom arrière total", "dézoom total"]

    _mots_ville   = ["affiche", "montre-moi", "montre moi", "survole",
                     "navigue vers", "va vers", "zoome sur",
                     "fais un survol de", "localise", "trouve",
                     "où est", "ou est", "situe", "où se trouve", "ou se trouve"]

    _mots_route   = ["trace un itinéraire", "trace l'itinéraire", "itinéraire de",
                     "route de", "chemin de", "comment aller de",
                     "trace une route de", "trajet de", "trajet depuis"]

    _mots_fermer  = ["ferme la carte", "ferme le globe", "cache la carte",
                     "cache le globe", "ferme la navigation", "quitte le globe",
                     "retour à jarvis", "ferme la vue", "masque la carte"]

    _mots_position = ["ma position", "où suis-je", "ou suis-je",
                      "affiche ma position", "montre ma position",
                      "localise-moi", "localise moi", "où je suis"]

    # ── Fermer ───────────────────────────────────────────────────────────────
    if any(m in t for m in _mots_fermer):
        await send_globe_command(globe_action="hide")
        return "Navigation fermée. Je reviens à l'interface principale, Hugo."

    # ── Ma position ──────────────────────────────────────────────────────────
    if any(m in t for m in _mots_position):
        # On délègue la géolocalisation au navigateur (navigator.geolocation)
        # bien plus précis que l'IP — le frontend gère tout
        await send_globe_command(globe_action="my_location")
        await parler("Localisation en cours, Hugo. Le globe affiche votre position en temps réel.")
        return "[Globe] Demande de géolocalisation envoyée au navigateur."

    # ── Globe Terre ───────────────────────────────────────────────────────────
    if any(m in t for m in _mots_globe):
        await send_globe_command(globe_action="show_earth")
        await parler("Initialisation du globe terrestre. Vue depuis l'espace activée, Hugo.")
        return "[Globe] Vue Terre activée."

    # ── Itinéraire de X à Y ──────────────────────────────────────────────────
    if any(m in t for m in _mots_route):
        pattern = r"(?:de|depuis)\s+(.+?)\s+(?:a|vers|jusqu.a|et)\s+(.+?)(?:\s*[?!]?\s*$)" 
        match = re.search(pattern, t)
        if match:
            from_name = match.group(1).strip().title()
            to_name   = match.group(2).strip().title()
            await parler(f"Calcul de l'itinéraire de {from_name} vers {to_name}. Géolocalisation en cours...")
            lat1, lon1, _ = await geocode_lieu(from_name)
            lat2, lon2, _ = await geocode_lieu(to_name)
            if lat1 and lat2:
                await send_globe_command(
                    globe_action="route",
                    from_lat=lat1, from_lon=lon1, from_name=from_name,
                    to_lat=lat2,   to_lon=lon2,   to_name=to_name
                )
                await parler(f"Itinéraire tracé de {from_name} à {to_name}, Hugo. La route est affichée sur le globe.")
                return f"[Globe] Route {from_name} → {to_name} affichée."
            else:
                return f"Je n'ai pas pu localiser les deux villes, Hugo. Vérifiez les noms et réessayez."
        return None

    # ── Fly to ville ─────────────────────────────────────────────────────────
    for mot in _mots_ville:
        if mot in t:
            # Extraire ce qui suit le mot déclencheur
            idx = t.find(mot)
            reste = t[idx + len(mot):].strip()
            # Nettoyer les articles
            for art in ["la ville de ", "la ville ", "le ", "la ", "l'", "les ", "ma ville ", "mon pays "]:
                if reste.startswith(art):
                    reste = reste[len(art):]
            reste = reste.replace("?", "").replace("!", "").strip()
            if len(reste) >= 2:
                nom_lieu = reste.title()
                await parler(f"Recherche de {nom_lieu} en cours... Coordonnées en acquisition.")
                lat, lon, display = await geocode_lieu(nom_lieu)
                if lat:
                    # Altitude selon le type de lieu (ville proche = plus bas)
                    altitude = 300000
                    await send_globe_command(
                        globe_action="fly_to",
                        lat=lat, lon=lon,
                        target=nom_lieu,
                        altitude=altitude
                    )
                    await parler(f"Coordonnées acquises. Survol de {nom_lieu} en cours, Hugo.")
                    return f"[Globe] Survol de {nom_lieu} ({lat:.4f}°, {lon:.4f}°)"
                else:
                    return f"Je n'ai pas réussi à localiser {nom_lieu}, Hugo. Essayez avec un nom plus précis."
            break

    return None

async def resoudre_extras_locaux(texte):
    """
    Résout localement : minuteries, blagues, citations, volume, luminosité,
    notes, courses, todos, capitales, fuseaux, âge, dé, mot de passe, etc.
    """
    import re
    t = texte.lower().replace("?", "").strip()

    # ══ MINUTERIE ══════════════════════════════════════════════
    if any(k in t for k in ["minuteur", "minuterie", "timer", "rappelle-moi dans",
                             "rappelle moi dans", "alarme dans", "alerte dans",
                             "lance un minuteur", "active le minuteur",
                             "previens-moi dans", "previens moi dans"]):
        duree = _parse_duree_secondes(t)
        if duree:
            # Envoi au frontend
            if CONNECTED_CLIENTS:
                async def _send_timer():
                    msg = json.dumps({"action": "timer_start", "duration": duree})
                    await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
                asyncio.create_task(_send_timer())
            
            # Ancienne logique de sonnerie conservée pour la voix (Style Iron Man)
            nom = f"timer_{len(_minuteries)+1}"
            def _sonner(nom=nom, duree=duree):
                _minuteries.pop(nom, None)
                import random
                reponses = [
                    "Monsieur, le protocole de compte à rebours est arrivé à échéance.",
                    "Hugo, la temporisation est terminée. J'espère que vous n'avez rien oublié.",
                    "Alerte : Le minuteur a atteint zéro. Tout est en ordre, Monsieur ?",
                    "Fin du décompte, Hugo. Je reste à votre entière disposition."
                ]
                loop2 = asyncio.new_event_loop()
                loop2.run_until_complete(parler(random.choice(reponses)))
                loop2.close()
            
            timer = threading.Timer(duree, _sonner)
            timer.daemon = True
            timer.start()
            _minuteries[nom] = timer
            
            mins = duree // 60
            return f"Minuteur de {mins} minutes activé. Affichage HUD en cours."
        return "Précisez la durée, par exemple : 'Mets un minuteur de 10 minutes'."

    # AJOUTER / RETIRER DU TEMPS
    if any(k in t for k in ["ajoute", "rajoute", "augmente"]) and "minute" in t:
        try:
            extra = int(re.search(r'\d+', t).group()) * 60
            if CONNECTED_CLIENTS:
                async def _send_add():
                    msg = json.dumps({"action": "timer_add", "duration": extra})
                    await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
                asyncio.create_task(_send_add())
            return f"J'ai ajouté {extra//60} minutes au minuteur."
        except: pass
    
    if any(k in t for k in ["retire", "enlève", "diminue", "supprime"]) and "minute" in t:
        try:
            less = int(re.search(r'\d+', t).group()) * 60
            if CONNECTED_CLIENTS:
                async def _send_rem():
                    msg = json.dumps({"action": "timer_remove", "duration": less})
                    await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
                asyncio.create_task(_send_rem())
            return f"J'ai retiré {less//60} minutes au minuteur."
        except: pass

    if any(k in t for k in ["annuler minuteur", "annule minuteur", "stop minuteur", "stop le minuteur",
                             "annuler minuterie", "annule le timer", "arrête le minuteur", "arrête le minute",
                             "stop le chrono", "arrête le chrono"]):
        if CONNECTED_CLIENTS:
            async def _send_stop():
                msg = json.dumps({"action": "timer_stop"})
                await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
            asyncio.create_task(_send_stop())
        
        if _minuteries:
            for nom, timer in list(_minuteries.items()):
                timer.cancel()
            _minuteries.clear()
            return "Minuteur arrêté, Hugo."
        return "Aucun minuteur actif."

    if any(k in t for k in ["minuteur actif", "minuteries actives", "combien de minuteurs"]):
        if _minuteries:
            return f"Vous avez {len(_minuteries)} minuterie{'s' if len(_minuteries) > 1 else ''} active{'s' if len(_minuteries) > 1 else ''}."
        return "Aucune minuterie active en ce moment."

    # ══ FUSEAUX HORAIRES ═══════════════════════════════════════
    if any(k in t for k in ["heure à", "heure en", "heure au", "quelle heure il est à",
                             "quelle heure est-il à", "quelle heure est il à",
                             "heure là-bas", "heure la-bas"]):
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            try:
                from backports.zoneinfo import ZoneInfo
            except ImportError:
                ZoneInfo = None
        if ZoneInfo:
            for cle, (nom_ville, tz_str) in _FUSEAUX.items():
                if cle in t:
                    try:
                        from datetime import timezone
                        heure_locale = datetime.now(ZoneInfo(tz_str))
                        return (f"Il est actuellement {heure_locale.strftime('%H:%M')} "
                                f"à {nom_ville}, Hugo.")
                    except Exception:
                        pass
        return "Je ne reconnais pas cette ville dans ma base locale, Hugo."

    # ══ CALCUL D'ÂGE ══════════════════════════════════════════
    age_match = re.search(r'n[ée]\s+en\s+(\d{4})', t)
    if age_match or any(k in t for k in ["quel age j'ai", "quel âge j'ai",
                                          "j'ai quel age", "j'ai quel âge",
                                          "calcule mon age", "calcule mon âge"]):
        if age_match:
            annee_naissance = int(age_match.group(1))
            age = datetime.now().year - annee_naissance
            return f"Si vous êtes né en {annee_naissance}, vous avez {age} ans, Hugo."
        return "Précisez votre année de naissance, par exemple : 'Né en 1990, quel âge j'ai ?'"

    # ══ COMPTE À REBOURS ═══════════════════════════════════════
    if any(k in t for k in ["combien de jours avant noël", "combien de jours jusqu'à noël",
                             "combien de jours avant noel"]):
        today = datetime.now().date()
        noel = datetime(today.year, 12, 25).date()
        if today > noel:
            noel = datetime(today.year + 1, 12, 25).date()
        jours = (noel - today).days
        return f"Il reste {jours} jour{'s' if jours > 1 else ''} avant Noël, Hugo !"

    if any(k in t for k in ["combien de jours avant le nouvel an",
                             "combien de jours avant 2025", "combien de jours avant 2026",
                             "combien de jours avant 2027"]):
        today = datetime.now().date()
        an_prochain = datetime(today.year + 1, 1, 1).date()
        jours = (an_prochain - today).days
        return f"Il reste {jours} jour{'s' if jours > 1 else ''} avant le Nouvel An, Hugo !"

    # ══ BLAGUES ════════════════════════════════════════════════
    if any(k in t for k in ["blague", "fais-moi rire", "fais moi rire",
                             "raconte-moi une blague", "raconte moi une blague",
                             "dis-moi une blague", "dis moi une blague",
                             "joke", "fais rire", "une blague"]):
        return random.choice(_BLAGUES)

    # ══ CITATIONS ══════════════════════════════════════════════
    if any(k in t for k in ["citation", "inspire-moi", "inspire moi",
                             "quote", "parole sage", "phrase motivante",
                             "motive-moi", "motive moi", "dis-moi quelque chose",
                             "donne-moi une citation"]):
        return random.choice(_CITATIONS)

    # ══ PILE OU FACE / DÉ ═════════════════════════════════════
    if any(k in t for k in ["pile ou face", "pile ou pile", "lance une pièce",
                             "lance une piece", "heads or tails", "flip"]):
        resultat = random.choice(["Pile", "Face"])
        return f"J'ai lancé la pièce... C'est {resultat} !"

    de_match = re.search(r'(?:lance|jette|tire|roule)\s+un\s+d[eé](?:\s+[aà]\s+(\d+)\s+face)?', t)
    if de_match or "lance un dé" in t or "jette le dé" in t or "jeter le dé" in t:
        nb_faces = 6
        m2 = re.search(r'd[eé]\s+[aà]\s+(\d+)', t)
        if m2:
            nb_faces = int(m2.group(1))
        result = random.randint(1, nb_faces)
        return f"J'ai lancé un dé à {nb_faces} faces... Vous obtenez : {result} !"

    if any(k in t for k in ["nombre aléatoire", "nombre aleatoire", "chiffre aléatoire",
                             "chiffre aleatoire", "génère un nombre", "genere un nombre"]):
        rng_match = re.search(r'entre\s+(\d+)\s+et\s+(\d+)', t)
        if rng_match:
            a, b = int(rng_match.group(1)), int(rng_match.group(2))
            return f"Votre nombre aléatoire entre {a} et {b} : {random.randint(a, b)}"
        return f"Voici un nombre aléatoire : {random.randint(1, 100)}"

    # ══ GÉNÉRATEUR DE MOT DE PASSE ════════════════════════════
    if any(k in t for k in ["mot de passe", "password", "mdp sécurisé", "mdp securise",
                             "génère un mot de passe", "genere un mot de passe",
                             "crée un mot de passe", "cree un mot de passe"]):
        import string
        longueur = 16
        lg_m = re.search(r'(\d+)\s*(?:caractères|caracteres|car)', t)
        if lg_m:
            longueur = min(max(int(lg_m.group(1)), 8), 64)
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        mdp = ''.join(random.SystemRandom().choice(chars) for _ in range(longueur))
        return f"Votre mot de passe sécurisé ({longueur} caractères) : {mdp}"

    # ══ NOTES RAPIDES ══════════════════════════════════════════
    if any(k in t for k in ["note ça", "note ca", "prends note", "retiens ça",
                             "retiens ca", "mémorise ça", "memorise ca",
                             "note que", "note :", "écris ça", "ecris ca"]):
        contenu = t
        for pref in ["note ça :", "note ca :", "note que", "note :", "prends note :",
                     "prends note de", "retiens ça :", "retiens ca :", "note ",
                     "mémorise ça :", "memorise ca :", "écris ça :", "ecris ca :"]:
            if contenu.startswith(pref):
                contenu = contenu[len(pref):].strip()
                break
        if contenu:
            listes = _charger_listes()
            note = f"[{datetime.now().strftime('%d/%m %H:%M')}] {contenu}"
            listes["notes"].append(note)
            _sauvegarder_listes(listes)
            return f"Note enregistrée, Hugo : '{contenu}'"
        return "Que souhaitez-vous que je note ?"

    if any(k in t for k in ["lis mes notes", "montre mes notes", "quelles sont mes notes",
                             "mes notes", "affiche mes notes"]):
        listes = _charger_listes()
        if not listes["notes"]:
            return "Vous n'avez aucune note enregistrée, Hugo."
        notes = "\n".join(f"• {n}" for n in listes["notes"][-5:])
        return f"Vos {min(5, len(listes['notes']))} dernières notes, Hugo :\n{notes}"

    if any(k in t for k in ["efface mes notes", "supprime mes notes",
                             "vide mes notes", "clear mes notes"]):
        listes = _charger_listes()
        listes["notes"] = []
        _sauvegarder_listes(listes)
        return "Toutes vos notes ont été effacées, Hugo."

    # ══ LISTE DE COURSES ═══════════════════════════════════════
    if any(k in t for k in ["ajoute", "rajoute"]) and any(k in t for k in ["liste de courses", "courses", "liste d'achats"]):
        article = t
        for pref in ["ajoute ", "rajoute ", "à ma liste de courses", "à la liste de courses",
                     "dans la liste de courses", "à mes courses", "à ma liste d'achats"]:
            article = article.replace(pref, "").strip()
        if article:
            listes = _charger_listes()
            listes["courses"].append(article)
            _sauvegarder_listes(listes)
            return f"'{article}' ajouté à votre liste de courses, Hugo."

    if any(k in t for k in ["liste de courses", "mes courses", "qu'est-ce que j'ai dans ma liste",
                             "montre ma liste de courses", "lis ma liste de courses",
                             "quoi dans ma liste"]):
        listes = _charger_listes()
        if not listes["courses"]:
            return "Votre liste de courses est vide, Hugo."
        items = "\n".join(f"• {i}" for i in listes["courses"])
        return f"Votre liste de courses ({len(listes['courses'])} article{'s' if len(listes['courses']) > 1 else ''}) :\n{items}"

    if any(k in t for k in ["vide la liste de courses", "efface la liste de courses",
                             "supprime la liste de courses", "clear les courses"]):
        listes = _charger_listes()
        listes["courses"] = []
        _sauvegarder_listes(listes)
        return "Liste de courses vidée, Hugo."

    # ══ TO-DO LIST ═════════════════════════════════════════════
    if any(k in t for k in ["ajoute une tâche", "ajoute une tache", "nouvelle tâche",
                             "nouvelle tache", "ajoute à ma to-do", "ajoute a ma to-do",
                             "à faire :", "a faire :"]):
        tache = t
        for pref in ["ajoute une tâche :", "ajoute une tache :", "nouvelle tâche :",
                     "nouvelle tache :", "ajoute à ma to-do :", "ajoute a ma to-do :",
                     "à faire :", "a faire :", "ajoute une tâche ", "ajoute une tache "]:
            tache = tache.replace(pref, "").strip()
        if tache:
            listes = _charger_listes()
            listes["todos"].append({"tache": tache, "fait": False, "date": datetime.now().strftime("%d/%m")})
            _sauvegarder_listes(listes)
            return f"Tâche ajoutée : '{tache}', Hugo."

    if any(k in t for k in ["mes tâches", "mes taches", "ma to-do", "ma todo",
                             "liste de tâches", "liste de taches", "qu'est-ce que j'ai à faire",
                             "qu'est-ce que j'ai a faire"]):
        listes = _charger_listes()
        todos = [td for td in listes["todos"] if not td.get("fait")]
        if not todos:
            return "Votre liste de tâches est vide, Hugo. Bravo !"
        items = "\n".join(f"• [{td['date']}] {td['tache']}" for td in todos[-8:])
        return f"Vos tâches à faire ({len(todos)}) :\n{items}"

    if any(k in t for k in ["efface mes tâches", "efface mes taches", "vide ma to-do",
                             "supprime mes tâches", "supprime mes taches"]):
        listes = _charger_listes()
        listes["todos"] = []
        _sauvegarder_listes(listes)
        return "Liste de tâches vidée, Hugo."

    # ══ VOLUME SYSTÈME ═════════════════════════════════════════
    vol_mots = ["volume", "son", "audio"]
    if any(k in t for k in vol_mots):
        if any(k in t for k in ["coupe le son", "mute", "silence total", "sourdine"]):
            vol = _volume_get_interface()
            if vol:
                vol.SetMute(1, None)
                return "Son coupé, Hugo."
            return "Je n'ai pas pu accéder au contrôle du volume. Installez pycaw."

        if any(k in t for k in ["remet le son", "unmute", "remet le volume", "réactive le son", "reactive le son"]):
            vol = _volume_get_interface()
            if vol:
                vol.SetMute(0, None)
                return "Son réactivé, Hugo."

        vol_match = re.search(r'(\d+)\s*(?:%|pourcent)', t)
        if vol_match or any(k in t for k in ["monte le volume", "monte le son",
                                              "baisse le volume", "baisse le son",
                                              "volume à", "son à", "mets le volume",
                                              "mets le son"]):
            vol = _volume_get_interface()
            if vol:
                if vol_match:
                    pct = max(0, min(100, int(vol_match.group(1))))
                    import math
                    # Convertir pourcentage en dB (scale logarithmique Windows)
                    vol.SetMasterVolumeLevelScalar(pct / 100.0, None)
                    return f"Volume réglé à {pct}%, Hugo."
                elif any(k in t for k in ["monte", "augmente", "hausse", "plus fort"]):
                    cur = vol.GetMasterVolumeLevelScalar()
                    new_vol = min(1.0, cur + 0.1)
                    vol.SetMasterVolumeLevelScalar(new_vol, None)
                    return f"Volume augmenté à {int(new_vol*100)}%, Hugo."
                elif any(k in t for k in ["baisse", "diminue", "moins fort", "réduis", "reduis"]):
                    cur = vol.GetMasterVolumeLevelScalar()
                    new_vol = max(0.0, cur - 0.1)
                    vol.SetMasterVolumeLevelScalar(new_vol, None)
                    return f"Volume réduit à {int(new_vol*100)}%, Hugo."
            else:
                return "Contrôle du volume indisponible. Installez pycaw pour cette fonction."

    # ══ LUMINOSITÉ ═════════════════════════════════════════════
    if any(k in t for k in ["luminosité", "luminosite", "brillo", "écran plus clair",
                             "écran plus sombre", "baisser l'écran", "monter l'écran"]):
        if _sbc_ok and _sbc:
            try:
                lum_match = re.search(r'(\d+)\s*(?:%|pourcent)', t)
                if lum_match:
                    pct = max(0, min(100, int(lum_match.group(1))))
                    _sbc.set_brightness(pct)
                    return f"Luminosité réglée à {pct}%, Hugo."
                elif any(k in t for k in ["monte", "augmente", "plus clair", "hausse", "max"]):
                    cur = _sbc.get_brightness(display=0)
                    if isinstance(cur, list): cur = cur[0]
                    new_b = min(100, cur + 15)
                    _sbc.set_brightness(new_b)
                    return f"Luminosité augmentée à {new_b}%, Hugo."
                elif any(k in t for k in ["baisse", "diminue", "plus sombre", "réduis", "min"]):
                    cur = _sbc.get_brightness(display=0)
                    if isinstance(cur, list): cur = cur[0]
                    new_b = max(0, cur - 15)
                    _sbc.set_brightness(new_b)
                    return f"Luminosité réduite à {new_b}%, Hugo."
            except Exception as e:
                return f"Impossible de régler la luminosité : {e}"
        return "Le module de luminosité n'est pas installé. Lancez : pip install screen-brightness-control"

    # ══ VEILLE / ARRÊT / REDÉMARRAGE ══════════════════════════
    if any(k in t for k in ["mets le pc en veille", "mode veille", "veille dans",
                             "suspends le pc", "sleep"]):
        delai = _parse_duree_secondes(t) or 0
        if delai > 0:
            subprocess.Popen(f'shutdown /h /t {delai}', shell=True)
            mins = delai // 60
            return f"Le PC passera en veille dans {mins} minute{'s' if mins > 1 else ''}, Hugo."
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return "Mise en veille du PC, Hugo. À bientôt !"

    if any(k in t for k in ["éteins le pc", "eteins le pc", "arrête le pc", "arrete le pc",
                             "shutdown", "arrêt dans", "arret dans"]):
        delai = _parse_duree_secondes(t) or 0
        if delai > 0:
            subprocess.Popen(f'shutdown /s /t {delai}', shell=True)
            mins = delai // 60
            return f"Le PC s'éteindra dans {mins} minute{'s' if mins > 1 else ''}, Hugo."
        return "Pour l'arrêt immédiat, confirmez en disant : 'confirme l'arrêt du pc'."

    if "confirme l'arrêt du pc" in t or "confirme l arret du pc" in t:
        subprocess.Popen("shutdown /s /t 10", shell=True)
        return "Arrêt du PC dans 10 secondes, Hugo. Au revoir !"

    if any(k in t for k in ["redémarre le pc", "redemarre le pc", "reboot"]):
        delai = _parse_duree_secondes(t) or 30
        subprocess.Popen(f'shutdown /r /t {delai}', shell=True)
        mins = max(1, delai // 60)
        return f"Redémarrage dans {mins} minute{'s' if mins > 1 else ''}, Hugo."

    if any(k in t for k in ["annule l'arrêt", "annule l arret", "annule le redémarrage",
                             "annule le redemarrage", "annule la veille"]):
        subprocess.Popen("shutdown /a", shell=True)
        return "Arrêt/redémarrage annulé, Hugo."

    # ══ CORBEILLE ══════════════════════════════════════════════
    if any(k in t for k in ["vide la corbeille", "vider la corbeille", "corbeille vide",
                             "nettoie la corbeille"]):
        try:
            import winshell
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
            return "La corbeille a été vidée, Hugo."
        except ImportError:
            subprocess.run("PowerShell -Command \"Clear-RecycleBin -Force -ErrorAction SilentlyContinue\"",
                           shell=True, capture_output=True)
            return "La corbeille a été vidée, Hugo."
        except Exception as e:
            return f"Impossible de vider la corbeille : {e}"

    # ══ CAPITALE / MONNAIE D'UN PAYS ══════════════════════════
    if any(k in t for k in ["capitale", "capital de"]):
        for pays, capitale in _CAPITALES.items():
            if pays in t:
                return f"La capitale de {pays.title()} est {capitale}, Hugo."
        return "Je ne connais pas ce pays dans ma base locale, Hugo."

    if any(k in t for k in ["monnaie", "devise", "monnaie de", "quelle est la monnaie"]):
        for pays, monnaie in _MONNAIES.items():
            if pays in t:
                return f"La monnaie de {pays.title()} est le {monnaie}, Hugo."
        return "Je ne connais pas la monnaie de ce pays dans ma base locale."

    # ══ CODE PHONÉTIQUE ════════════════════════════════════════
    if any(k in t for k in ["alphabet phonétique", "alphabet phonetique",
                             "code phonétique", "code phonetique",
                             "épelle", "epelle", "comment s'écrit", "comment s ecrit",
                             "épellation", "epellation"]):
        # Chercher une lettre ou un mot à épeler
        alpha_match = re.search(r"(?:épelle|epelle|comment s'écrit|comment s ecrit)\s+([a-z]+)", t)
        if alpha_match:
            mot = alpha_match.group(1).lower()
            epele = " - ".join(_PHONETIQUE.get(c, c.upper()) for c in mot)
            return f"'{mot.upper()}' s'épelle : {epele}"
        # "C comme ?"
        lettre_match = re.search(r"([a-z])\s+comme\s+\?", t)
        if lettre_match:
            c = lettre_match.group(1)
            return f"{c.upper()} comme {_PHONETIQUE.get(c, '?')}"
        return "Précisez la lettre ou le mot à épeler phonétiquement."

    return None


def resoudre_infos_systeme_localement(texte):
    """Répond aux questions d'heure, date, batterie, CPU/RAM localement sans IA."""
    t = texte.lower().replace("?", "").strip()
    maintenant = datetime.now()

    JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    MOIS_FR  = ["janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

    # --- HEURE ---
    if any(m in t for m in ["quelle heure", "il est quelle heure", "l'heure qu'il est",
                             "quelle est l'heure", "tu as l'heure", "donne-moi l'heure",
                             "il est combien", "c'est quoi l'heure", "heure il est"]):
        h, m = maintenant.hour, maintenant.minute
        return f"Il est {h}h{m:02d}, Hugo."

    # --- DATE COMPLÈTE ---
    if any(m in t for m in ["quelle date", "on est quel jour", "quel jour on est",
                             "quel jour sommes-nous", "la date d'aujourd'hui", "date du jour",
                             "on est le combien", "quel jour est-on", "c'est quoi la date",
                             "la date aujourd'hui"]):
        jour_semaine = JOURS_FR[maintenant.weekday()]
        mois = MOIS_FR[maintenant.month - 1]
        return f"Nous sommes le {jour_semaine} {maintenant.day} {mois} {maintenant.year}, Hugo."

    # --- JOUR DE LA SEMAINE SEUL ---
    if any(m in t for m in ["quel jour", "c'est quel jour"]) and "date" not in t:
        return f"Nous sommes {JOURS_FR[maintenant.weekday()]}, Hugo."

    # --- MOIS ---
    if any(m in t for m in ["quel mois", "on est en quel mois", "c'est quel mois"]):
        return f"Nous sommes en {MOIS_FR[maintenant.month - 1]}, Hugo."

    # --- ANNÉE ---
    if any(m in t for m in ["quelle année", "on est en quelle année", "c'est quelle année"]):
        return f"Nous sommes en {maintenant.year}, Hugo."

    # --- ÂGE DE L'UTILISATEUR ---
    if any(m in t for m in ["quel âge as-tu", "quel age as-tu",
                             f"quel âge a {USER_NAME.lower()}",
                             f"quel age a {USER_NAME.lower()}",
                             "quel est mon âge", "j'ai quel âge", "j ai quel age"]):
        if USER_AGE:
            return f"Vous avez {USER_AGE} ans, {USER_NAME}."
        attente_age = True
        return f"Je ne connais pas encore votre âge, {USER_NAME}. Quel est-il ?"

    # --- BATTERIE ---
    if any(m in t for m in ["batterie", "autonomie", "niveau de charge", "charge du pc"]):
        if psutil is None:
            return "Le module psutil n'est pas disponible, Hugo."
        try:
            bat = psutil.sensors_battery()
            if bat:
                pct = int(bat.percent)
                etat = "en charge" if bat.power_plugged else "sur batterie"
                return f"La batterie est à {pct}%, {etat}, Hugo."
            return "Je ne détecte pas de batterie sur cet appareil, Hugo."
        except Exception:
            return "Impossible de lire la batterie, Hugo."

    # --- CPU ---
    if any(m in t for m in ["cpu", "processeur", "utilisation du processeur", "charge du processeur"]):
        if psutil is None:
            return "Le module psutil n'est pas disponible, Hugo."
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            return f"Le processeur tourne à {cpu}% d'utilisation, Hugo."
        except Exception:
            return "Impossible de lire le processeur, Hugo."

    # --- RAM ---
    if any(m in t for m in ["ram", "mémoire ram", "mémoire vive", "utilisation de la mémoire"]):
        if psutil is None:
            return "Le module psutil n'est pas disponible, Hugo."
        try:
            mem = psutil.virtual_memory()
            utilise = round(mem.used / (1024**3), 1)
            total   = round(mem.total / (1024**3), 1)
            return f"La RAM est à {mem.percent}% — {utilise} Go utilisés sur {total} Go, Hugo."
        except Exception:
            return "Impossible de lire la RAM, Hugo."

    # --- UPTIME (depuis combien de temps le PC est allumé) ---
    if any(m in t for m in ["allumé depuis", "uptime", "depuis combien de temps le pc",
                             "depuis quand est allumé"]):
        if psutil is None:
            return "Le module psutil n'est pas disponible, Hugo."
        try:
            boot = datetime.fromtimestamp(psutil.boot_time())
            delta = maintenant - boot
            heures  = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            return f"Le PC est allumé depuis {heures}h{minutes:02d}, Hugo."
        except Exception:
            return None

    return None

async def demander_ia(texte):

    global is_thinking
    is_thinking = True
    await send_web_state("thinking")
    try:
        # ── PRIORITÉ 0 — RÉPONSES LOCALES (instantané, sans API) ────────────
        rep_loc = reponse_locale(texte)
        if rep_loc:
            return rep_loc

        # ── PRIORITÉ 1 — CLAUDE (Anthropic) ─────────────────────────────────
        if anthropic_client and _quota_mgr.is_available("claude"):
            print("[CERVEAU] Tentative avec Claude (Anthropic)...")
            try:
                rep_claude = await demander_claude(texte)
                if rep_claude:
                    return rep_claude
                print("[CERVEAU] Claude KO (réponse vide). Bascule suivante.")
            except _QuotaExceededError:
                print(f"[CERVEAU] Claude quota épuisé — cooldown {_quota_mgr.remaining_cooldown('claude')}s. Bascule.")
            except Exception as e:
                print(f"[CERVEAU] Claude erreur ({e}). Bascule suivante.")
        elif anthropic_client and not _quota_mgr.is_available("claude"):
            print(f"[CERVEAU] Claude en cooldown ({_quota_mgr.remaining_cooldown('claude')}s). Bascule directe.")

        cerveau = detecter_cerveau(texte)

        async def _call_gemini():
            if not gemini_actif:
                raise Exception("Clé Gemini non configurée — agent ignoré")
            if not _quota_mgr.is_available("gemini"):
                raise _QuotaExceededError(f"Gemini en cooldown ({_quota_mgr.remaining_cooldown('gemini')}s)")
            print(f"[CERVEAU] Tentative avec Gemini (Liste: {MODELS_LIST})...")
            temp_hist = historique + [types.Content(role="user", parts=[types.Part(text=texte)])]
            prompt_actuel = construire_system_prompt()
            last_err = None
            for model_name in MODELS_LIST:
                try:
                    print(f"[CERVEAU] Essai modele : {model_name} (Timeout 12s)")
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            client.models.generate_content,
                            model=model_name,
                            config=types.GenerateContentConfig(
                                system_instruction=prompt_actuel,
                                temperature=0.7,
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                            ),
                            contents=temp_hist
                        ),
                        timeout=12.0
                    )
                    rep = response.text
                    historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
                    historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
                    _sauvegarder_echange_conv(texte, rep)
                    return rep
                except Exception as e:
                    if _quota_mgr.is_quota_error(e):
                        _quota_mgr.mark_quota_exceeded("gemini")
                        raise _QuotaExceededError(f"Gemini quota sur {model_name}: {e}")
                    print(f"[CERVEAU] Echec {model_name} : {e}")
                    last_err = e
                    continue
            raise last_err or Exception("Tous les modeles Gemini ont echoue")

        async def _call_grok():
            if not _quota_mgr.is_available("grok"):
                raise _QuotaExceededError(f"Grok en cooldown ({_quota_mgr.remaining_cooldown('grok')}s)")
            print("[CERVEAU] Tentative avec Grok (xAI)...")
            rep_grok = await demander_grok(texte)
            if not rep_grok:
                raise Exception("Grok n'a rien renvoyé ou est mal configuré")
            return rep_grok

        # ── ROUTING DYNAMIQUE avec gestion quota ─────────────────────────────
        if cerveau == "GROK" and grok_client:
            try:
                return await _call_grok()
            except _QuotaExceededError as e:
                print(f"[CERVEAU] Grok quota ({e}). Bascule Gemini.")
            except Exception as e:
                print(f"[CERVEAU] Grok erreur ({e}). Bascule Gemini.")
        try:
            return await _call_gemini()
        except _QuotaExceededError as e:
            print(f"[CERVEAU] Gemini quota ({e}). Bascule SerpAPI/Groq/Grok.")
        except _QuotaExceededError as e:
            print(f"[CERVEAU] Gemini quota ({e}). Bascule SerpAPI/Groq/Grok.")
        except Exception as e:
            print(f"[CERVEAU] Gemini erreur ({e}). Bascule SerpAPI.")

        # ── FALLBACKS (Gemini KO ou quota) ───────────────────────────────────
        # --- FALLBACK MÉTÉO/TEMP (HA + OpenMeteo, avant SerpAPI) ---
        t_low = texte.lower()
        _mots_meteo = ["quel temps", "météo", "meteo", "il fait quel temps",
                       "temps qu'il fait", "quel temps il fait", "prévisions",
                       "previsions", "va-t-il pleuvoir", "pleut-il",
                       "fait-il beau", "il va pleuvoir", "température dehors",
                       "temperature dehors", "température extérieure",
                       "temperature exterieure", "combien fait-il dehors",
                       "il fait combien dehors"]
        _mots_temp_int = ["température", "temperature", "il fait chaud",
                          "il fait froid", "combien de degrés",
                          "combien fait-il", "il fait combien"]
        _mots_maison   = ["chez moi", "à la maison", "dans la maison",
                          "intérieur", "interieur", "dans le salon",
                          "dans la chambre", "dans le bureau"]
        _pieces_fallback = {
            "salon"   : "salon",
            "chambre" : "chambre",
            "bureau"  : "bureau",
            "extérieur": "exterieur",
            "dehors"  : "dehors",
        }

        if any(m in t_low for m in _mots_meteo):
            print("[CERVEAU] Requête météo détectée → Home Assistant weather.forecast_amilly")
            meteo_data = get_meteo_structuree(None)
            if meteo_data:
                await send_web_meteo(meteo_data)
            reponse_ha = get_meteo_ha()
            if reponse_ha:
                return reponse_ha
            return get_meteo_actuelle(None)

        if any(m in t_low for m in _mots_temp_int):
            for mot_piece, piece_key in _pieces_fallback.items():
                if mot_piece in t_low:
                    entity_id = PIECES_CAPTEURS.get(piece_key)
                    if entity_id:
                        print(f"[CERVEAU] Temp intérieure détectée → HA {entity_id}")
                        temp = ha_get_etat(entity_id)
                        hum_id = PIECES_HUMIDITE.get(piece_key)
                        hum = ha_get_etat(hum_id) if hum_id else None
                        await send_web_temp_piece({
                            "piece": mot_piece,
                            "temperature": str(temp),
                            "humidite": str(hum) if hum else None,
                        })
                        return f"La température dans le {mot_piece} est de {temp} degrés."
            if any(m in t_low for m in _mots_maison):
                entity_id = PIECES_CAPTEURS.get("salon")
                if entity_id:
                    print(f"[CERVEAU] Temp intérieure 'chez moi' → HA {entity_id}")
                    temp = ha_get_etat(entity_id)
                    hum_id = PIECES_HUMIDITE.get("salon")
                    hum = ha_get_etat(hum_id) if hum_id else None
                    await send_web_temp_piece({
                        "piece": "salon",
                        "temperature": str(temp),
                        "humidite": str(hum) if hum else None,
                    })
                    return f"La température chez vous est de {temp} degrés."

        # --- FALLBACK GROQ (LLAMA 3.3) ---
        if groq_client and _quota_mgr.is_available("groq"):
            print("[CERVEAU] Bascule sur Groq (Llama 3.3).")
            try:
                rep_groq = await demander_groq(texte)
                if rep_groq:
                    return rep_groq
            except _QuotaExceededError:
                print(f"[CERVEAU] Groq quota épuisé — cooldown {_quota_mgr.remaining_cooldown('groq')}s.")
            except Exception as e2:
                print(f"[CERVEAU] Groq erreur ({e2}).")
        elif groq_client:
            print(f"[CERVEAU] Groq en cooldown ({_quota_mgr.remaining_cooldown('groq')}s). Ignoré.")

        # --- FALLBACK GROK (xAI) ---
        if grok_client and _quota_mgr.is_available("grok"):
            print("[CERVEAU] Bascule sur Grok (xAI).")
            try:
                return await _call_grok()
            except _QuotaExceededError:
                print(f"[CERVEAU] Grok quota épuisé — cooldown {_quota_mgr.remaining_cooldown('grok')}s.")
            except Exception as e2:
                print(f"[ERREUR IA (Grok repli)] {e2}")
        elif grok_client:
            print(f"[CERVEAU] Grok en cooldown ({_quota_mgr.remaining_cooldown('grok')}s). Ignoré.")

        # --- FALLBACK OLLAMA (100% offline) ---
        print("[CERVEAU] Gemini et Grok KO. Tentative Ollama (local)...")
        rep_ollama = await demander_ollama(texte)
        if rep_ollama:
            return rep_ollama

        # --- FALLBACK SERPAPI (Web) ---
        # On ne le met qu'à la fin pour éviter qu'il ne "vole" les questions de mémoire
        if len(texte.split()) > 2:
            res_serp = recherche_web_serpapi(texte)
            if res_serp and "VOTRE_CLE" not in res_serp and "rien trouvé" not in res_serp and "erreur" not in res_serp.lower():
                return "Voici ce que j'ai trouvé sur le web : " + res_serp

        # ── Détection : aucune API configurée ou toutes en erreur ──────────
        _aucune_api = (not gemini_actif and not groq_client and not grok_client and not anthropic_client)
        if _aucune_api:
            return (
                "Je suis bien en ligne Hugo, mais mes moteurs d'intelligence artificielle ne sont pas encore configurés. "
                "Pour libérer tout mon potentiel, vous devez renseigner vos clés API dans le fichier .env. "
                "Rendez-vous sur le site TechEnClair — vous y trouverez un guide complet pour les obtenir gratuitement. "
                "En attendant, je reste disponible pour toutes vos commandes locales : domotique, heure, calculs, et bien plus encore !"
            )
        return (
            "Désolé Hugo, tous mes serveurs de réflexion sont actuellement surchargés ou en maintenance, "
            "et mes modèles locaux ne répondent pas non plus. "
            "Je reste disponible pour vos commandes domotiques et locales. "
            "Si ce problème persiste, vérifiez vos clés API sur techenclair.fr."
        )
    finally:
        is_thinking = False
        await send_web_state("idle")

async def demander_ia_vision(texte, img_b64):
    """Analyse une image (capture d'écran) avec Gemini Vision."""
    global is_thinking, historique
    if not gemini_actif or client is None:
        return "La vision nécessite une clé Gemini valide. Configurez-la dans le fichier .env."
    is_thinking = True
    await send_web_state("thinking")
    try:
        print("[VISION] Analyse de l'image avec Gemini...")
        
        # Conversion base64 en bytes pour l'API
        img_bytes = base64.b64decode(img_b64)
        image_part = types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/jpeg"
        )
        
        prompt_actuel = construire_system_prompt()
        prompt_actuel += f"\n\nIMPORTANT : Tu viens de recevoir une capture d'écran de {USER_NAME}. Analyse-la attentivement et réponds à sa question en te basant sur ce que tu vois."
        
        # On envoie l'image et le texte avec retry en cas de 503
        contents = [
            types.Content(role="user", parts=[image_part, types.Part(text=texte)])
        ]
        
        rep = None
        last_err = None
        for model_name in MODELS_LIST:
            print(f"[VISION] Essai modele : {model_name}")
            for attempt in range(2): # 2 tentatives par modele
                try:
                    print(f"[VISION] Appel modele : {model_name} (Timeout 15s)")
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            client.models.generate_content,
                            model=model_name,
                            config=types.GenerateContentConfig(
                                system_instruction=prompt_actuel,
                                temperature=0.7,
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                            ),
                            contents=contents
                        ),
                        timeout=15.0
                    )
                    rep = response.text
                    break
                except Exception as e:
                    if ("503" in str(e) or "overloaded" in str(e).lower()) and attempt < 1:
                        print(f"[VISION] Surcharge {model_name} (503). Retente...")
                        await asyncio.sleep(1)
                        continue
                    print(f"[VISION] Erreur {model_name} : {e}")
                    last_err = e
                    break
            if rep: break
        
        if not rep:
            err_str = str(last_err).lower() if last_err else ""
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                print("[VISION] Quota Gemini epuise — vision impossible sans Gemini.")
                return ("Désolé Hugo, mon quota Gemini est épuisé pour aujourd'hui. "
                        "La vision par caméra et écran fonctionne uniquement avec Gemini — "
                        "je ne peux donc pas analyser d'images en ce moment. "
                        "Réessayez demain quand le quota sera réinitialisé.")
            print("[VISION] Tous les modeles Gemini ont echoue. Bascule sur Grok (Texte uniquement)...")
            if grok_client:
                return await demander_grok(texte + " (Note: Je n'ai pas pu voir ton écran car mes serveurs de vision sont indisponibles, je réponds donc uniquement à ton texte).")
            raise last_err or Exception("Aucun modele n'a pu analyser l'image")

        # On ajoute la trace dans l'historique (sans l'image pour éviter de saturer la mémoire)
        historique.append(types.Content(role="user", parts=[types.Part(text=f"[Analyse d'écran] {texte}")]))
        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
        
        return rep
    except Exception as e:
        print(f"[VISION] Erreur Gemini Vision : {e}")
        # On évite les accolades dans le message d'erreur pour ne pas perturber l'extracteur JSON
        err_msg = str(e).replace("{", "[").replace("}", "]")
        return f"Désolé Hugo, je n'ai pas pu analyser votre écran. Erreur : {err_msg}"
    finally:
        is_thinking = False
        await send_web_state("idle")

def detecter_cerveau(texte):
    # Heuristique pour basculer sur Grok uniquement pour X/Twitter
    mots_cles_grok = ["sur x", "twitter", "grok", "elon", "x.com"]
    cmd = texte.lower()
    if any(m in cmd for m in mots_cles_grok):
        return "GROK"
    return "GEMINI"

async def demander_grok(texte):
    if not grok_client:
        return None
    
    try:
        # SYNC : On utilise le même prompt système que Gemini (incluant la mémoire)
        system_prompt = construire_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        
        for h in historique[-30:]: # Limiter aux 30 derniers messages
            role = "user" if h.role == "user" else "assistant"
            msg_text = h.parts[0].text
            messages.append({"role": role, "content": msg_text})
        
        messages.append({"role": "user", "content": texte})
        
        completion = grok_client.chat.completions.create(
            model="grok-3", 
            messages=messages,
            temperature=0.7,
        )
        
        rep = completion.choices[0].message.content
        
        # On synchronise l'historique Gemini
        historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
        _sauvegarder_echange_conv(texte, rep)
        
        return rep
    except Exception as e:
        if _quota_mgr.is_quota_error(e):
            _quota_mgr.mark_quota_exceeded("grok")
            raise _QuotaExceededError(f"Grok quota: {e}")
        print(f"[ERREUR GROK] {e}")
        return None

async def demander_ollama(texte):
    """Appelle un modèle local via Ollama (100% offline)."""
    global historique
    try:
        # SYNC : On utilise le même prompt système que Gemini (incluant la mémoire)
        system_prompt = construire_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        
        for h in historique[-30:]:
            role = "user" if h.role == "user" else "assistant"
            messages.append({"role": role, "content": h.parts[0].text})
        messages.append({"role": "user", "content": texte})
        
        last_err = None
        for model_name in OLLAMA_MODELS:
            try:
                print(f"[OLLAMA] Essai modele local : {model_name}")
                resp = await asyncio.wait_for(
                    asyncio.to_thread(
                        requests.post,
                        f"{OLLAMA_URL}/api/chat",
                        json={"model": model_name, "messages": messages, "stream": False},
                        timeout=30
                    ),
                    timeout=35.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    rep = data.get("message", {}).get("content", "")
                    if rep:
                        historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
                        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
                        _sauvegarder_echange_conv(texte, rep)
                        print(f"[OLLAMA] Reponse recue de {model_name}")
                        return rep
                else:
                    print(f"[OLLAMA] Erreur HTTP {resp.status_code} pour {model_name}")
                    last_err = Exception(f"HTTP {resp.status_code}")
            except Exception as e:
                print(f"[OLLAMA] Echec {model_name} : {e}")
                last_err = e
                continue
        
        print(f"[OLLAMA] Tous les modeles locaux ont echoue")
        return None
    except Exception as e:
        print(f"[ERREUR OLLAMA] {e}")
        return None

async def demander_groq(texte):
    """Appelle Groq (Llama 3.3) en fallback gratuit."""
    if not groq_client:
        return None

    try:
        # SYNC : On utilise le même prompt système que Gemini (incluant la mémoire)
        system_prompt = construire_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        
        for h in historique[-30:]:
            role = "user" if h.role == "user" else "assistant"
            messages.append({"role": role, "content": h.parts[0].text})
            
        messages.append({"role": "user", "content": texte})

        completion = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
        )

        rep = completion.choices[0].message.content

        historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
        _sauvegarder_echange_conv(texte, rep)

        return rep
    except Exception as e:
        if _quota_mgr.is_quota_error(e):
            _quota_mgr.mark_quota_exceeded("groq")
            raise _QuotaExceededError(f"Groq quota: {e}")
        print(f"[ERREUR GROQ] {e}")
        return None

async def demander_claude(texte):
    """Appelle Claude (Anthropic) — agent IA principal (priorité 0)."""
    if not anthropic_client:
        return None
    try:
        # Conversion historique Gemini → format Anthropic
        messages = []
        for h in historique[-30:]:
            role = "user" if h.role == "user" else "assistant"
            messages.append({"role": role, "content": h.parts[0].text})
        messages.append({"role": "user", "content": texte})

        response = await asyncio.wait_for(
            asyncio.to_thread(
                anthropic_client.messages.create,
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=construire_system_prompt(),
                messages=messages,
            ),
            timeout=15.0
        )
        rep = response.content[0].text

        # Sync historique global
        historique.append(types.Content(role="user", parts=[types.Part(text=texte)]))
        historique.append(types.Content(role="model", parts=[types.Part(text=rep)]))
        _sauvegarder_echange_conv(texte, rep)

        return rep
    except Exception as e:
        if _quota_mgr.is_quota_error(e):
            _quota_mgr.mark_quota_exceeded("claude")
            raise _QuotaExceededError(f"Claude quota: {e}")
        print(f"[ERREUR CLAUDE] {e}")
        return None

async def action_whatsapp_appel(contact):
    try:
        await parler(f"J'appelle {contact} sur WhatsApp, Hugo.")
        # Lancement de l'app via le protocole
        os.system("start whatsapp://")
        time.sleep(6) # On laisse le temps a l'app de s'ouvrir et se focuser
        
        # Recherche du contact (Ctrl+F)
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(1)
        pyautogui.typewrite(contact)
        time.sleep(2)
        pyautogui.press('enter')
        time.sleep(3) # On attend que la conversation s'affiche bien
        
        # Utilisation du raccourci clavier officiel pour l'appel audio (plus fiable que la vision)
        print(f"[WHATSAPP] Envoi du raccourci d'appel (Ctrl+Shift+C)...")
        pyautogui.hotkey('ctrl', 'shift', 'c')
        
        # On ajoute quand meme un petit clic de vision en secours si le raccourci ne suffit pas
        time.sleep(2)
        print(f"[WHATSAPP] Verification par vision au cas ou...")
        await jarvis_vision_cliquer("clique sur le bouton 'Appel vocal' ou l icone de telephone qui vient de s afficher en haut a droite")
        
        return True
    except Exception as e:
        print(f"[WHATSAPP ERROR] {e}")
        await parler(f"Desole Hugo, je n'ai pas pu lancer l'appel WhatsApp. {e}")
        return False

async def resoudre_commandes_locales(texte):
    """Détecte et exécute les commandes locales (Spotify, dossiers, apps) sans IA."""
    global attente_nom_dossier, attente_nom_app, attente_age, attente_confirmation_age, _age_temp, USER_AGE
    t = texte.lower().strip()

    # --- GESTION DU CONTEXTE MULTI-TOURS ---
    if attente_confirmation_age:
        attente_confirmation_age = False
        if any(m in t for m in ["oui", "yes", "ouais", "affirmatif", "enregistre", "sauvegarde", "mémorise", "ok"]):
            _sauvegarder_config({"user_age": _age_temp})
            USER_AGE = _age_temp
            _age_temp = ""
            return f"Parfait {USER_NAME}, j'ai bien enregistré votre âge : {USER_AGE} ans. Je m'en souviendrai !"
        else:
            _age_temp = ""
            return f"Pas de problème {USER_NAME}, je n'enregistre rien."

    if attente_age:
        attente_age = False
        match = re.search(r'\b(\d{1,3})\b', t)
        if match:
            _age_temp = match.group(1)
            attente_confirmation_age = True
            return f"{_age_temp} ans, noté ! Voulez-vous que je l'enregistre dans ma mémoire pour m'en souvenir la prochaine fois ?"
        return f"Je n'ai pas compris votre âge, {USER_NAME}. Pouvez-vous me donner un nombre ? Par exemple : '28 ans'."

    if attente_nom_dossier:
        t = f"ouvre le dossier {t}"
        attente_nom_dossier = False
    elif attente_nom_app:
        t = f"ouvre l'application {t}"
        attente_nom_app = False
    else:
        # Interception des commandes incompletes
        if t in ["ouvre le dossier", "ouvre mon dossier", "ouvre un dossier"]:
            attente_nom_dossier = True
            return f"Quel dossier voulez-vous ouvrir, {USER_NAME} ?"
        elif t in ["ouvre l'application", "lance l'application", "ouvre le logiciel", "lance le logiciel", "ouvre", "lance"]:
            attente_nom_app = True
            return f"Quelle application voulez-vous lancer, {USER_NAME} ?"

    # --- IDENTITE / CREATEUR (Priorite 0) ---
    _createur_questions = [
        "qui est ton créateur", "qui est ton createur",
        "qui t'a créé", "qui t'a cree", "qui t'a crée",
        "qui ta créé", "qui ta cree", "qui ta crée",
        "qui t'a fabriqué", "qui t'a fabrique",
        "qui t'a inventé", "qui t'a invente",
        "qui t'a construit", "qui ta construit",
        "qui t'a développé", "qui t'a developpe",
        "qui t'a programmé", "qui t'a programme",
        "qui t'a codé", "qui t'a code",
        "qui t'a conçu", "qui t'a concu",
        "qui ta développé", "qui ta developpe",
        "qui ta programmé", "qui ta programme",
        "qui ta codé", "qui ta code",
        "qui ta conçu", "qui ta concu",
        "c'est qui ton créateur", "c'est qui ton createur",
        "t'as été créé par qui", "t'as ete cree par qui",
        "t'es fait par qui", "tu es fait par qui",
        "tu viens d'où", "tu viens d'ou", "tu viens de ou",
        "d'où tu viens", "d'ou tu viens",
        "qui est derrière toi", "qui est derriere toi",
        "qui est ton père", "qui est ton pere",
        "qui est ton papa",
        "qui est ton développeur", "qui est ton developpeur",
        "qui est ton dev",
        "ton créateur c'est qui", "ton createur c'est qui",
    ]
    if any(q in t for q in _createur_questions):
        import random as _rnd
        _reponses_createur = [
            "J'ai été créé par TechEnClair, Hugo. C'est grâce à lui que j'existe aujourd'hui.",
            "Mon créateur, c'est TechEnClair. Il m'a conçu de A à Z pour être votre assistant personnel.",
            "Je suis le fruit du travail de TechEnClair. Tout mon code, ma voix, mon intelligence, c'est lui.",
            "TechEnClair est mon créateur. C'est lui qui m'a donné vie, et je dois dire qu'il a fait du bon boulot.",
            "C'est TechEnClair qui m'a développé, Hugo. Un développeur passionné qui voulait créer l'assistant ultime.",
            "Mon père numérique, c'est TechEnClair. Il m'a programmé avec passion pour vous aider au quotidien.",
            "TechEnClair, Hugo. C'est le génie derrière mon existence. Vous pouvez le retrouver sur techenclair.fr.",
            "Je suis né dans les lignes de code de TechEnClair. Sans lui, je ne serais qu'un écran noir.",
            "TechEnClair m'a créé. C'est un développeur français qui a voulu rendre l'intelligence artificielle accessible à tous.",
            "Mon créateur s'appelle TechEnClair. Il a mis tout son savoir-faire pour me construire, et je lui en suis reconnaissant.",
        ]
        return _rnd.choice(_reponses_createur)

    # --- AIDE / CAPACITES (Priorite 0) ---
    _aide_questions = [
        "que peux-tu faire", "que peux tu faire", "que sais-tu faire", "que sais tu faire",
        "quelles sont tes capacités", "quelles sont tes capacites",
        "montre moi tes capacités", "montre-moi tes capacités",
        "montre moi ce que tu sais faire", "aide moi", "aide-moi",
        "montre moi tes commandes", "liste tes commandes", "qu'est-ce que tu peux faire"
    ]
    if any(q in t for q in _aide_questions):
        # Envoi IMMEDIAT de l'action help au frontend
        if CONNECTED_CLIENTS:
            async def _dispatch_help():
                msg = json.dumps({"action": "help"})
                await asyncio.gather(*[ws.send(msg) for ws in CONNECTED_CLIENTS], return_exceptions=True)
            asyncio.create_task(_dispatch_help())
        
        import random as _rnd
        _reponses_aide = [
            "J'affiche mes systèmes de bord, Hugo. Je peux gérer votre musique, lancer des recherches, naviguer sur le globe 3D, ou encore ouvrir vos dossiers personnels. Que souhaitez-vous tester ?",
            "Déploiement des protocoles d'assistance. Voici mes modules actifs : contrôle média, navigation satellite, recherche intelligente et gestionnaire de fichiers. Je suis à vos ordres.",
            "Bien sûr. Je suis capable de localiser n'importe quel point sur Terre, de piloter vos applications, et de répondre à vos questions complexes. Jetez un œil aux suggestions à l'écran.",
            "Initialisation de l'interface d'aide. Je peux aussi bien prendre une capture d'écran que vous donner la météo à l'autre bout du monde. Dites-moi simplement ce qu'il vous faut.",
            "Accès aux bases de données. Je peux automatiser vos tâches répétitives, gérer vos rappels et même vous raconter une blague si l'ambiance est trop sérieuse.",
        ]
        return _rnd.choice(_reponses_aide)

    # --- DOSSIERS (Priorité 1) ---
    if any(k in t for k in ["ouvre tous les dossiers", "ouvre tous mes dossiers", "ouvre mes dossiers", "ouvre les dossiers", "mes dossiers", "range mes dossiers", "mosaïque dossiers"]):
        return arranger_fenetres_dossiers()

    prefixes_dossiers = ["ouvre le dossier ", "ouvre mon dossier ", "ouvre le répertoire ", "ouvre le repertoire ", "ouvre dossier ", "ouvre ", "mets "]
    # On vérifie d'abord si c'est un dossier connu
    mots_cles_dossiers = ["bureau", "document", "téléchargement", "image", "photo", "vidéo", "musique", "corbeille"]
    
    for prefix in prefixes_dossiers:
        if t.startswith(prefix):
            potentiel_dossier = t.replace(prefix, "").strip()
            # Si le mot après le préfixe est un dossier connu, on l'ouvre
            if any(k in potentiel_dossier for k in mots_cles_dossiers):
                ok, msg = ouvrir_dossier(potentiel_dossier)
                if ok: return f"J'ouvre le dossier {potentiel_dossier}, Hugo."

    # --- MODE BOULOT (Priorité 1 bis) ---
    if any(k in t for k in ["au boulot", "mode boulot", "mode travail", "on bosse", "mode bureau", "commence le boulot"]):
        return await mode_boulot()

    # --- APPLICATIONS STANDARD & CATALOGUE (Priorité 2) ---
    # IMPORTANT : ces checks doivent être AVANT la détection Spotify car
    # "lance " est aussi un préfixe Spotify → "lance steam" partirait sinon vers Spotify.
    mots_ouvrir = ["ouvre", "lance", "démarre", "démarres", "ouvrir", "lancer"]
    mots_fermer = ["ferme", "quitte", "stoppe", "éteins", "coupe", "fermer", "quitter"]

    apps_standard = {
        "calculatrice":            "calc",
        "notepad":                 "notepad",
        "bloc-notes":              "notepad",
        "bloc notes":              "notepad",
        "paint":                   "mspaint",
        "gestionnaire de tâches":  "taskmgr",
        "gestionnaire de taches":  "taskmgr",
        "task manager":            "taskmgr",
        "panneau de configuration": "control",
        "paramètres":              "ms-settings:",
        "parametres":              "ms-settings:",
        "réglages":                "ms-settings:",
        "reglages":                "ms-settings:",
        "explorateur":             "explorer",
        "explorateur de fichiers": "explorer",
        "invite de commande":      "cmd",
        "cmd":                     "cmd",
        "snipping tool":           "SnippingTool",
        "outil capture":           "SnippingTool",
        "capture d'écran":         "SnippingTool",
        "capture d'ecran":         "SnippingTool",
        "enregistreur vocal":      "SoundRecorder",
        "magnétophone":            "SoundRecorder",
        "table des caractères":    "charmap",
        "caractères spéciaux":     "charmap",
        "nettoyage de disque":     "cleanmgr",
        "informations système":    "msinfo32",
        "info système":            "msinfo32",
        "info systeme":            "msinfo32",
    }
    for nom, cmd in apps_standard.items():
        if f"ouvre {nom}" in t or f"lance {nom}" in t or f"démarre {nom}" in t:
            try:
                subprocess.Popen(cmd)
                return f"J'ouvre {nom}, Hugo."
            except Exception:
                return f"Désolé Hugo, je n'ai pas réussi à lancer {nom}."

    for cle, info in _APPS_CATALOGUE.items():
        if cle not in t:
            continue
        if any(m in t for m in mots_fermer):
            ok = _fermer_app(info["noms"])
            if ok:
                return f"J'ai fermé {info['label']}, Hugo."
            return f"Je n'ai pas trouvé {info['label']} en cours d'exécution."
        if any(m in t for m in mots_ouvrir):
            _boulot_lancer(info["label"], info["noms"], chemins_hints=info["hints"])
            return f"Je lance {info['label']}, Hugo."

    # --- SPOTIFY / MUSIQUE (Priorité 3) ---
    # YouTube music spécifique — doit être AVANT le check Spotify
    if any(k in t for k in ["musique sur youtube", "met de la musique sur youtube", "mets de la musique sur youtube"]):
        url = YOUTUBE_MUSIQUE_URL or "https://www.youtube.com/watch?v=Cr8K88UcO0s"
        webbrowser.open(url, new=2)
        time.sleep(5)
        pyautogui.press('f')
        return f"C'est parti {USER_NAME}, je lance votre musique sur YouTube."

    # Commande "mets de la musique" — lien perso en priorité, Spotify sinon
    if any(k in t for k in [
        "met de la musique", "mets de la musique",
        "met de la musique sur spotify", "mets de la musique sur spotify",
        "met de la musique sur sportify", "mets de la musique sur sportify",
        "musique sur spotify", "musique sur sportify",
        "lance ma playlist", "ma playlist"
    ]):
        lien = MUSIQUE_LIEN_PERSO.strip() if MUSIQUE_LIEN_PERSO else ""
        if lien:
            if "spotify" in lien:
                if lien.startswith("spotify:"):
                    ok = spotify_lancer_playlist(lien)
                    if ok:
                        return f"C'est parti {USER_NAME}, je lance votre playlist Spotify."
                    return f"Je n'ai pas réussi à ouvrir Spotify, {USER_NAME}."
                else:
                    webbrowser.open(lien, new=2)
                    return f"C'est parti {USER_NAME}, j'ouvre votre playlist Spotify."
            elif "youtube" in lien or "youtu.be" in lien:
                webbrowser.open(lien, new=2)
                time.sleep(5)
                pyautogui.press('f')
                return f"C'est parti {USER_NAME}, je lance votre musique sur YouTube."
            elif "deezer" in lien:
                webbrowser.open(lien, new=2)
                return f"C'est parti {USER_NAME}, j'ouvre votre musique sur Deezer."
            elif "music.apple" in lien:
                webbrowser.open(lien, new=2)
                return f"C'est parti {USER_NAME}, j'ouvre Apple Music."
            else:
                webbrowser.open(lien, new=2)
                return f"C'est parti {USER_NAME}, je lance votre musique."
        # Fallback Spotify par défaut
        ok = spotify_lancer_playlist(SPOTIFY_MUSIQUE_URI)
        if ok:
            return f"C'est parti {USER_NAME}, je lance votre playlist sur Spotify."
        return f"Je n'ai pas réussi à ouvrir Spotify, {USER_NAME}."

    if any(k in t for k in ["ouvre spotify", "lance spotify", "démarre spotify"]):
        return await spotify_ouvrir()

    if any(k in t for k in ["mets en pause", "stop la musique", "arrête la musique"]):
        return await spotify_stop()
    if any(k in t for k in ["lecture", "remets la musique", "reprends la musique"]):
        return await spotify_lecture_pause()
    if any(k in t for k in ["suivante", "chanson suivante", "piste suivante"]):
        return await spotify_suivant()
    if any(k in t for k in ["précédente", "chanson précédente", "reviens en arrière"]):
        return await spotify_precedent()
    if any(k in t for k in ["monte le volume", "augmente le son", "plus fort"]):
        return await spotify_volume("monter")
    if any(k in t for k in ["baisse le son", "baisse le volume", "moins fort"]):
        return await spotify_volume("baisser")

    # Recherche Spotify générique — en dernier pour ne pas avaler les commandes apps
    prefixes_recherche = ["joue du ", "joue de la ", "mets du ", "mets de la ", "joue ", "recherche "]
    for prefix in prefixes_recherche:
        if t.startswith(prefix):
            recherche = t.replace(prefix, "").replace(" sur spotify", "").strip()
            if len(recherche) > 1:
                return await spotify_rechercher(recherche)

    raccourcis_dossiers = {
        "bureau": "bureau", "documents": "documents",
        "téléchargements": "downloads", "téléchargement": "downloads",
        "images": "images", "vidéos": "videos", "musique": "musique"
    }
    for cle, chemin in raccourcis_dossiers.items():
        if f"ouvre mon {cle}" in t or f"ouvre le {cle}" in t or t == f"ouvre {cle}":
            ouvrir_dossier(chemin)
            return f"J'ouvre votre dossier {cle}, Hugo."

    # --- DOSSIER / APPLICATION INCONNU(E) ---
    # Si l'utilisateur demande d'ouvrir/lancer quelque chose qu'on ne connait pas
    _mots_action = ["ouvre ", "lance ", "démarre ", "démarres ", "ouvrir ", "lancer ", "ouvre le ", "ouvre la ",
                     "ouvre mon ", "ouvre ma ", "lance le ", "lance la ", "lance mon ", "lance ma ",
                     "ouvre le dossier ", "ouvre mon dossier ", "ouvre l'application ", "lance l'application ",
                     "ouvre l'appli ", "lance l'appli ", "ouvre le logiciel ", "lance le logiciel "]
    for mot in _mots_action:
        if t.startswith(mot):
            nom_demande = t.replace(mot, "").strip().rstrip(".")
            if len(nom_demande) > 1:
                import random as _rnd
                _reponses_inconnu = [
                    f"Désolé Hugo, mon créateur TechEnClair n'a pas encore ajouté \"{nom_demande}\" dans mes fonctionnalités. Mais vous pouvez l'ajouter vous-même gratuitement avec le logiciel Antigravity de chez Google.",
                    f"Je ne connais pas \"{nom_demande}\" pour l'instant, Hugo. TechEnClair, mon développeur, n'a pas intégré cette fonction. Cependant, vous pouvez la créer facilement avec Antigravity de Google, c'est gratuit.",
                    f"Hmm, \"{nom_demande}\" ne fait pas partie de mes compétences actuelles. Mon créateur TechEnClair pourra peut-être l'ajouter dans une future mise à jour. En attendant, essayez Antigravity de Google pour personnaliser vos commandes gratuitement.",
                    f"\"{nom_demande}\" n'est pas dans ma base de données, Hugo. TechEnClair n'a pas encore programmé cette action. Bonne nouvelle : avec Antigravity de chez Google, vous pouvez l'ajouter vous-même sans frais.",
                    f"Je ne suis pas encore capable d'ouvrir \"{nom_demande}\", Hugo. Mon créateur TechEnClair travaille constamment à m'améliorer. En attendant, le logiciel Antigravity de Google vous permet d'étendre mes fonctionnalités gratuitement.",
                    f"Cette fonctionnalité n'a pas été ajoutée par TechEnClair, mon créateur. Mais ne vous inquiétez pas, Hugo, vous pouvez utiliser Antigravity de chez Google pour ajouter \"{nom_demande}\" gratuitement.",
                ]
                return _rnd.choice(_reponses_inconnu)

    return None

async def traiter_reponse_ia(texte_utilisateur, mobile_ws=None):
    global MODE_IRON_MAN, jarvis_actif, dernier_message, _skip_pc_audio
    # Reset du flag audio au début de chaque commande
    _skip_pc_audio = False

    # TENTATIVE DE RÉSOLUTION LOCALE (Commandes, Math, Français, etc.)
    reponse = await resoudre_commandes_locales(texte_utilisateur)
    if not reponse: reponse = resoudre_infos_systeme_localement(texte_utilisateur)
    if not reponse: reponse = resoudre_math_localement(texte_utilisateur)
    if not reponse: reponse = resoudre_francais_localement(texte_utilisateur)
    if not reponse: reponse = resoudre_conversion_localement(texte_utilisateur)
    if not reponse: reponse = resoudre_traduction_localement(texte_utilisateur)
    if not reponse: reponse = await resoudre_globe_localement(texte_utilisateur)
    if not reponse: reponse = await resoudre_extras_locaux(texte_utilisateur)
    
    # VISION (Regarde mon écran)
    if not reponse:
        t = texte_utilisateur.lower()
        if any(keyword in t for keyword in ["regarde mon écran", "analyse mon écran", "vois-tu mon écran", "qu'est-ce qu'il y a sur mon écran"]):
            await parler("Bien sûr Hugo, laissez-moi jeter un œil...")
            img_b64 = await request_screen_capture()
            if img_b64:
                reponse = await demander_ia_vision(texte_utilisateur, img_b64)
            else:
                reponse = "Je suis désolé Hugo, mais je n'ai pas pu capturer votre écran. Assurez-vous d'avoir cliqué sur 'Activer la vision' sur l'interface et d'avoir autorisé le partage."
        
        # CAMERA (Lance la caméra / Analyse visuelle / Objets / Tenue)
        camera_keywords = [
            # Caméra générale (avec ET sans accents pour la reconnaissance vocale)
            "lance la caméra", "lance la camera",
            "ouvre la caméra", "ouvre la camera",
            "regarde avec la caméra", "regarde avec la camera",
            "active la caméra", "active la camera",
            "analyse ce que tu vois", "qu'est-ce que tu vois",
            "regarde-moi", "regarde moi", "analyse-moi", "analyse moi",
            # Tenue / Vêtements
            "ma tenue", "mes vêtements", "mes vetements",
            "comment je suis habillé", "comment je suis habille",
            "montre-moi", "est-ce que ça me va", "est-ce que ca me va",
            "ça me va", "ca me va",
            "qu'est-ce que je porte", "je porte quoi",
            # Objets / Identification
            "c'est quoi ça", "c'est quoi ca", "qu'est-ce que c'est",
            "décris cet objet", "decris cet objet", "c'est quoi cet objet",
            "identifie", "reconnais", "qu'est-ce que je te montre",
            "je te montre", "regarde ça", "regarde ca",
            "tu vois quoi", "dis-moi ce que c'est", "analyse ça", "analyse ca",
            # Webcam
            "webcam", "la cam",
        ]
        if any(keyword in t for keyword in camera_keywords):
            reponse = await jarvis_vision_camera(texte_utilisateur)

    if not reponse:
        reponse = await demander_ia(texte_utilisateur)
    
    print(f"[JARVIS] {reponse}")

    # Si commande mobile : activer le flag pour couper l'audio PC et répondre via mobile
    if mobile_ws:
        _skip_pc_audio = True

    # Recherche de TOUS les blocs JSON dans la réponse
    json_blocks = re.findall(r'\{.*?\}', reponse, re.DOTALL)
    
    if not json_blocks:
        await parler(reponse)
        _skip_pc_audio = False
        return

    for block in json_blocks:
        try:
            print(f"[JARVIS] Execution de l'action : {block}")
            # Timeout de 15s pour chaque action pour eviter de freezer Jarvis
            data = json.loads(block)
            action = data.get("action", "")
            
            # On execute l'action avec un timeout
            try:
                # Note: On utilise asyncio.wait_for pour les actions asynchrones
                # Les actions synchrones comme ha_lumiere devraient idéalement être async aussi
                # mais pour l'instant on les laisse ainsi ou on les wrappe.
                pass 
            except asyncio.TimeoutError:
                print(f"[ACTION ERROR] Timeout sur l'action {action}")
                if grok_client:
                    await parler("C'est un peu long Hugo, je demande une vérification à Grok.")
                    rep_grok = await demander_grok(texte_utilisateur + " (L'action domotique a expiré, peux-tu répondre à l'utilisateur ?)")
                    if rep_grok: await parler(rep_grok)
                continue

            if action == "mode_iron_man":
                etat = data.get("etat", "off")
                MODE_IRON_MAN = (etat == "on")
                msg = "Mode Iron Man activé, Monsieur. Je reste à l'écoute de vos signaux." if MODE_IRON_MAN else "Mode Iron Man désactivé. Je repasse en veille domotique."
                await parler(msg)
            elif action == "afficher_recette":
                titre = data.get("titre", "Recette")
                ingredients = data.get("ingredients", [])
                instructions = data.get("instructions", [])
                msg_json = json.dumps({
                    "type": "show_recipe",
                    "titre": titre,
                    "ingredients": ingredients,
                    "instructions": instructions
                })
                if CONNECTED_CLIENTS:
                    try:
                        await asyncio.gather(*[ws.send(msg_json) for ws in CONNECTED_CLIENTS], return_exceptions=True)
                    except Exception as e:
                        print(f"[ERREUR WS] Broadcast recette: {e}")
                await parler(f"Voici la recette pour {titre}, affichée sur votre interface.")
            elif action == "memoriser":
                cle    = data.get("cle",    "info")
                valeur = data.get("valeur", "")
                ajouter_memoire(cle, valeur)
                await parler(f"Bien note Hugo, je me souviendrai que {valeur}.")
            elif action == "oublier":
                cle     = data.get("cle", "")
                success = supprimer_memoire(cle)
                if success:
                    await parler("Information oubliee, Hugo.")
                else:
                    await parler("Je n avais pas cette information en memoire.")
            elif action == "lister_memoire":
                memoire = charger_memoire()
                if not memoire:
                    await parler("Aucune information personnalisee en memoire, Hugo.")
                else:
                    lignes = ["Voici ce que je sais sur vous Hugo."]
                    for cle, data_m in memoire.items():
                        lignes.append(f"{cle} : {data_m['valeur']}.")
                    await parler(" ".join(lignes))
            elif action == "ouvrir_dossier":
                chemin = data.get("chemin", "bureau")
                ok, resultat = ouvrir_dossier(chemin)
                if ok:
                    await parler("Dossier ouvert, Hugo. Dites-moi si vous voulez que je le trie.")
                else:
                    await parler(f"Je n ai pas trouve ce dossier, Hugo. {resultat}")
            elif action == "lister_dossier":
                contenu, err = lister_dossier()
                if err:
                    await parler(err)
                else:
                    nb_fichiers = len(contenu["fichiers"])
                    nb_dossiers = len(contenu["dossiers"])
                    await parler(f"Le dossier contient {nb_fichiers} fichiers et {nb_dossiers} sous-dossiers, Hugo.")
            elif action == "trier_par_type":
                await parler("Je trie vos fichiers par type, Hugo. Un instant.")
                ok, msg = trier_par_type()
                await parler(msg if ok else f"Probleme lors du tri : {msg}")
            elif action == "trier_par_date":
                await parler("Je trie vos fichiers par date, Hugo. Un instant.")
                ok, msg = trier_par_date()
                await parler(msg if ok else f"Probleme lors du tri : {msg}")
            elif action == "trier_complet":
                await parler("Je trie vos fichiers par type puis par date dans chaque categorie, Hugo.")
                ok, msg = trier_par_type_puis_date()
                await parler(msg if ok else f"Probleme lors du tri : {msg}")
            elif action == "creer_dossier":
                nom     = data.get("nom", "Nouveau Dossier")
                ok, msg = creer_sous_dossier(nom)
                await parler(msg if ok else f"Erreur : {msg}")
            elif action == "renommer_fichier":
                ancien  = data.get("ancien", "")
                nouveau = data.get("nouveau", "")
                ok, msg = renommer_fichier(ancien, nouveau)
                await parler(msg if ok else f"Erreur : {msg}")
            elif action == "deplacer_fichier":
                fichier = data.get("fichier",     "")
                dest    = data.get("destination", "")
                ok, msg = deplacer_fichier(fichier, dest)
                await parler(msg if ok else f"Erreur : {msg}")
            elif action == "chercher_fichier":
                nom        = data.get("nom", "")
                resultats, err = chercher_fichier(nom)
                if err:
                    await parler(err)
                elif not resultats:
                    await parler(f"Aucun fichier contenant {nom} n a ete trouve, Hugo.")
                else:
                    noms = [os.path.basename(r) for r in resultats[:5]]
                    await parler(f"J ai trouve {len(resultats)} fichier(s). Par exemple : {', '.join(noms)}.")
            elif action == "ha_lumiere":
                piece      = data.get("piece",      "salon").lower().strip()
                etat       = data.get("etat",       "on")
                couleur    = data.get("couleur",    None)
                luminosite = data.get("luminosite", None)
                entity_id  = PIECES_LUMIERES.get(piece, f"light.{piece}")
                rgb        = COULEURS_MAP.get(couleur) if couleur else None
                ha_lumiere(entity_id, etat, luminosite, rgb)
                
                # Message de confirmation amélioré
                if etat == "off":
                    msg = f"J'éteins {piece}."
                else:
                    details = []
                    if couleur: details.append(f"en {couleur}")
                    if luminosite is not None: 
                        pourcent = int((int(luminosite)/255)*100)
                        details.append(f"à {pourcent}%")
                    
                    if details:
                        msg = f"C'est fait, {piece} est réglé{' '.join(details)}."
                    else:
                        msg = f"Lumière {piece} allumée."
                await parler(msg)
            elif action == "ha_prise":
                piece     = data.get("piece", "bureau").lower().strip()
                etat      = data.get("etat",  "on")
                entity_id = PIECES_PRISES.get(piece, f"switch.prise_{piece}")
                ha_interrupteur(entity_id, etat)
                msg = f"Prise {piece} {'activée' if etat == 'on' else 'désactivée'}."
                await parler(msg)
            elif action == "ha_temperature":
                piece     = data.get("piece", "salon").lower().strip()
                entity_id = PIECES_CAPTEURS.get(piece)
                if entity_id:
                    temp    = ha_get_etat(entity_id)
                    hum_id  = PIECES_HUMIDITE.get(piece)
                    hum     = ha_get_etat(hum_id) if hum_id else None
                    hum_val = str(hum) if (hum and str(hum) != "inconnu") else None
                    if str(temp) != "inconnu":
                        await send_web_temp_piece({
                            "piece"      : piece,
                            "temperature": str(temp),
                            "humidite"   : hum_val,
                        })
                    await parler(f"La température dans le {piece} est de {temp} degrés.")
                else:
                    await parler(f"Désolé, je n'ai pas de capteur configuré pour le {piece}.")
            elif action == "ha_humidite":
                piece     = data.get("piece", "bureau").lower().strip()
                entity_id = PIECES_HUMIDITE.get(piece)
                if entity_id:
                    humi = ha_get_etat(entity_id)
                    await parler(f"Le taux d'humidité dans le {piece} est de {humi}%.")
                else:
                    await parler(f"Je n'ai pas de capteur d'humidité pour le {piece}.")
            elif action == "ha_batterie":
                appareil  = data.get("appareil", "").lower()
                entity_id = APPAREILS_BATTERIE.get(appareil)
                if entity_id:
                    batt = ha_get_etat(entity_id)
                    if batt == "unknown":
                        await parler(f"Je n'arrive pas à récupérer l'état de la batterie pour {appareil}.")
                    else:
                        suff = ""
                        if "telephone" in appareil or "papa" in appareil or USER_NAME.lower() in appareil:
                            suff = "Ton téléphone est à "
                        elif "julie" in appareil or "maman" in appareil:
                            suff = "Le téléphone de Julie est à "
                        else:
                            suff = f"La batterie de {appareil} est à "
                        await parler(f"{suff}{batt}%.")
                else:
                    await parler(f"Je n'ai pas l'appareil {appareil} dans ma liste de batterie.")
            elif action == "ha_thermostat":
                temp = data.get("temperature", 20)
                ha_thermostat("climate.thermostat", temp)
                await parler(f"Thermostat réglé à {temp} degrés.")
            elif action == "ha_scene":
                nom      = data.get("nom", "")
                scene_id = f"scene.{nom}"
                ha_scene(scene_id)
                await parler(f"Ambiance {nom} activée.")
            elif action == "ha_alarme":
                etat = data.get("etat", "on")
                if etat == "on":
                    ha_appeler_service("alarm_control_panel", "alarm_arm_away", "alarm_control_panel.home_base_2")
                    await parler("Alarme activée.")
                else:
                    ha_appeler_service("alarm_control_panel", "alarm_disarm", "alarm_control_panel.home_base_2")
                    await parler("Alarme désactivée.")
            elif action == "ha_verrou":
                entity_id = data.get("entity_id", "lock.porte_maison")
                etat = data.get("etat", "lock")
                ha_verrou(entity_id, etat)
                msg = "Porte verrouillée, Hugo." if etat == "lock" else "Porte déverrouillée, Hugo."
                await parler(msg)
            elif action == "ha_simulation":
                etat = data.get("etat", "on")
                ha_interrupteur("switch.simulation", etat)
                msg = "Simulation de présence activée." if etat == "on" else "Simulation de présence désactivée."
                await parler(msg)
            elif action == "ha_anniversaires":
                events = ha_get_calendrier("calendar.anniversaires")
                if not events:
                    await parler("Rien de prévu aujourd'hui.")
                else:
                    noms = [e.get("summary", "Anniversaire sans nom") for e in events]
                    if len(noms) == 1:
                        await parler(f"Aujourd'hui, nous fêtons l'anniversaire de {noms[0]}. N'oubliez pas de lui souhaiter !")
                    else:
                        liste = ", ".join(noms[:-1]) + " et " + noms[-1]
                        await parler(f"Aujourd'hui, il y a plusieurs anniversaires : {liste}. C'est une journée chargée !")
            elif action == "ha_consommation":
                entity_id = PIECES_CAPTEURS.get("consommation")
                puissance = ha_get_etat(entity_id)
                if puissance == "unknown" or puissance == "inconnu":
                    await parler("Je n'arrive pas à lire la consommation électrique pour le moment.")
                else:
                    await parler(f"La consommation actuelle de la maison est de {puissance} Volt-Ampères.")
            elif action == "ha_tiktok":
                entity_id = PIECES_CAPTEURS.get("tiktok")
                followers = ha_get_etat(entity_id)
                await parler(f"Tu as actuellement {followers} abonnés sur ton compte TikTok TechEnClair, Hugo. Félicitations !")
            elif action == "ha_oeufs":
                entity_id = PIECES_CAPTEURS.get("oeufs")
                # On récupère l'état (le dernier choix) et le moment de la modif
                try:
                    r = requests.get(f"{HA_URL}/api/states/{entity_id}", headers=HA_HEADERS, timeout=5)
                    data = r.json()
                    last_changed = data.get("last_changed", "")
                    if last_changed:
                        dt = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
                        phrase = dt.strftime("le %d %B à %Hh%M")
                        await parler(f"Le dernier ramassage des œufs a été enregistré {phrase}.")
                    else:
                        await parler("Je n'ai pas d'historique pour le ramassage des œufs.")
                except:
                    await parler("Je n'arrive pas à accéder aux informations sur les œufs.")
            elif action == "ha_energie":
                periode  = data.get("periode", "mois")
                appareil = data.get("appareil", "")
                
                if appareil:
                    appareil_clean = appareil.lower()
                    entite = APPAREILS_ENERGIE.get(appareil_clean)
                    if entite:
                        val = ha_get_etat(entite)
                        if val != "inconnu" and val != "unknown":
                            kwh = float(val)
                            await parler(f"La consommation de {appareil} pour ce mois est de {kwh:.1f} kWh.")
                        else:
                            await parler(f"Je n'ai pas de données de consommation pour {appareil} pour le moment.")
                    else:
                        await parler(f"Je n'ai pas d'appareil nommé {appareil} dans mon suivi énergétique.")
                elif periode == "hier":
                    total_kwh = 0
                    total_cost = 0
                    try:
                        for i in range(1, 7):
                            e_id = f"sensor.lixee_zlinky_tic_zlinky_p{i}_daily"
                            val = ha_get_etat(e_id, attribut="last_period")
                            if val != "inconnu" and val != "unknown":
                                k = float(val)
                                total_kwh += k
                                total_cost += k * HA_TARIFS.get(f"p{i}", 0.16)
                        await parler(f"Hier, la maison a consommé {total_kwh:.1f} kWh, pour un coût estimé à {total_cost:.2f} euros.")
                    except:
                        await parler("J'ai eu un problème pour calculer la consommation d'hier.")
                else: # mois
                    total_kwh = 0
                    total_cost = 0
                    try:
                        for i in range(1, 7):
                            e_id = f"sensor.lixee_zlinky_tic_zlinky_p{i}_mensuel"
                            val = ha_get_etat(e_id)
                            if val != "inconnu" and val != "unknown":
                                k = float(val)
                                total_kwh += k
                                total_cost += k * HA_TARIFS.get(f"p{i}", 0.16)
                        await parler(f"Ce mois-ci, la consommation totale est de {total_kwh:.1f} kWh, pour un montant de {total_cost:.2f} euros.")
                    except:
                        await parler("Je n'ai pas pu calculer la consommation mensuelle.")
            elif action == "ha_aspirateur":
                commande = data.get("commande", "start")
                if commande == "start":
                    ha_appeler_service("vacuum", "start", "vacuum.bob")
                    await parler("C'est parti, Bob lance le nettoyage.")
                elif commande == "stop":
                    ha_appeler_service("vacuum", "stop", "vacuum.bob")
                    await parler("J'ai arrêté l'aspirateur.")
                elif commande == "pause":
                    ha_appeler_service("vacuum", "pause", "vacuum.bob")
                    await parler("Bob est en pause.")
                elif commande == "base":
                    ha_appeler_service("vacuum", "return_to_base", "vacuum.bob")
                    await parler("Bob retourne à sa base.")
            elif action == "create_doc":
                titre   = data.get("title",   "Document JARVIS")
                contenu = data.get("content", "")
                result  = creer_google_doc(titre, contenu)
                await parler(result)
            elif action == "write_doc":
                contenu = data.get("content", "")
                result  = modifier_google_doc(contenu)
                await parler(result)
            elif action == "create_sheet":
                titre  = data.get("title", "Feuille JARVIS")
                result = creer_google_sheet(titre)
                await parler(result)
            elif action == "read_emails":
                result = lire_emails()
                await parler(f"Voici vos derniers emails Hugo. {result}")
            elif action == "read_calendar":
                result = lister_evenements_calendar()
                await parler(f"Voici vos prochains evenements Hugo. {result}")
            elif action == "meteo":
                ville = data.get("ville") or None
                await parler("Je consulte la meteo, un instant.")
                result = get_meteo_actuelle(ville)
                meteo_data = get_meteo_structuree(ville)
                if meteo_data:
                    await send_web_meteo(meteo_data)
                await parler(result)
            elif action == "alerte_meteo":
                ville = data.get("ville") or None
                result = get_alertes_meteo(ville)
                await parler(result)
            elif action == "recherche_web":
                query = data.get("query", "")
                await parler(f"Je lance une recherche sur internet pour {query}.")
                result = recherche_web_serpapi(query)
                await parler(result)
            elif action == "sport_resultats":
                equipe = data.get("equipe") or None
                ligue  = data.get("ligue")  or None
                print(f"[SPORT] Action sport_resultats pour {equipe or ligue}")
                await parler(f"Je cherche les informations pour {equipe or ligue}, un instant.")
                result = get_resultats_football(equipe=equipe, ligue=ligue)
                if "pas trouvé" in result or "Impossible" in result:
                    print(f"[SPORT] Echec recherche locale. Verification avec Grok...")
                    if grok_client:
                        res_grok = await demander_grok(f"{USER_NAME} veut savoir : {texte_utilisateur}. Je n'ai pas trouvé l'info dans ma base de données football, peux-tu chercher pour lui ?")
                        if res_grok: result = res_grok
                await parler(result)
            elif action == "sport_classement":
                ligue  = data.get("ligue", "Ligue 1")
                await parler(f"Je recupere le classement {ligue}.")
                result = get_classement_football(ligue=ligue)
                await parler(result)
            elif action == "sport_live":
                question = data.get("question", "derniers resultats sportifs 2026")
                await parler("Je recherche les derniers resultats en direct, un instant Hugo.")
                result = get_resultats_sport_gemini(question)
                await parler(result)
            elif action == "voir_ecran":
                inst = data.get("instruction", "")
                res = await jarvis_vision_cliquer(inst)
                await parler(res)
            elif action == "whatsapp_appel":
                contact = data.get("contact", "Ma vie")
                await action_whatsapp_appel(contact)
            elif action == "vision_ecrire":
                inst = data.get("instruction", "")
                txt  = data.get("texte", "")
                res  = await jarvis_vision_ecrire(inst, txt)
                await parler(res)
            elif action == "vision_chercher_sur_site":
                txt = data.get("texte", "")
                await parler(f"Je cherche la barre de recherche sur ce site, Hugo.")
                res = await jarvis_vision_rechercher_sur_site(txt)
                await parler(res)
            elif action == "lance_camera":
                res = await jarvis_vision_camera(texte_utilisateur)
                await parler(res)
            elif action == "vision_navigateur":
                res = await jarvis_vision_navigateur(texte_utilisateur)
                await parler(res)
            elif action == "dictee":
                texte = data.get("texte", "")
                if texte:
                    import pyautogui
                    import pyperclip
                    import time
                    pyperclip.copy(texte)
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'v')
                    await parler("C'est tapé, Hugo.")
            elif action == "spotify_ouvrir":
                await parler("J'ouvre Spotify, Hugo.")
                res = await spotify_ouvrir()
                await parler(res)
            elif action == "spotify_rechercher":
                recherche = data.get("recherche", "")
                await parler(f"Je recherche '{recherche}' sur Spotify, Hugo.")
                res = await spotify_rechercher(recherche)
                await parler(res)
            elif action == "spotify_lecture_pause":
                res = await spotify_lecture_pause()
                await parler(res)
            elif action == "spotify_stop":
                res = await spotify_stop()
                await parler(res)
            elif action == "spotify_suivant":
                res = await spotify_suivant()
                await parler(res)
            elif action == "spotify_precedent":
                res = await spotify_precedent()
                await parler(res)
            elif action == "spotify_volume":
                direction = data.get("direction", "monter")
                paliers   = data.get("paliers", 4)
                res = await spotify_volume(direction, paliers)
                await parler(res)
            elif action == "deezer_ouvrir":
                await parler("J'ouvre Deezer, Hugo.")
                res = await deezer_ouvrir()
                await parler(res)
            elif action == "deezer_rechercher":
                recherche = data.get("recherche", "")
                await parler(f"Je recherche '{recherche}' sur Deezer, Hugo.")
                res = await deezer_rechercher(recherche)
                await parler(res)
            elif action == "deezer_lecture_pause":
                res = await deezer_lecture_pause()
                await parler(res)
            elif action == "deezer_stop":
                res = await deezer_stop()
                await parler(res)
            elif action == "deezer_suivant":
                res = await deezer_suivant()
                await parler(res)
            elif action == "deezer_precedent":
                res = await deezer_precedent()
                await parler(res)
            elif action == "deezer_volume":
                direction = data.get("direction", "monter")
                paliers   = data.get("paliers", 4)
                res = await deezer_volume(direction, paliers)
                await parler(res)

        except Exception as e:
            print(f"[ACTION ERROR] Block failed: {block} | Error: {e}")
            if grok_client:
                print("[JARVIS] Bascule sur Grok suite a une erreur d'action...")
                res_grok = await demander_grok(f"{USER_NAME} m'a demandé : {texte_utilisateur}. J'ai tenté de lancer une action mais j'ai eu une erreur technique ({e}). Peux-tu prendre le relais et lui répondre élégamment ?")
                if res_grok: await parler(res_grok)
            continue

    # Si du texte reste après les commandes, on ne fait rien de plus car `parler` a déjà été appelé pour chaque action ou la réponse globale.
    # Réinitialiser le flag audio PC
    _skip_pc_audio = False

def nettoyer_commande(texte):
    t = texte.lower().strip()
    for variante in ["jarvis,", "jarvis"]:
        if t.startswith(variante):
            t = t[len(variante):].strip()
    return t

WAKE_WORD       = "jarvis"
SESSION_TIMEOUT = 30
STOP_PARLER      = False
MIC_MUTED        = False
is_listening     = False
is_speaking      = False
jarvis_actif     = False
dernier_message  = 0
interface_deja_connectee = False


# ══════════════════════════════════════════════════════════════
#  DÉTECTION MICROPHONE — Énumération + Fallback automatique
# ══════════════════════════════════════════════════════════════

_JARVIS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")

def _charger_config() -> dict:
    """Charge jarvis_config.json ou retourne un dict vide si absent/corrompu."""
    try:
        if os.path.exists(_JARVIS_CONFIG_PATH):
            import json
            with open(_JARVIS_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _sauvegarder_config(data: dict) -> None:
    """Sauvegarde les données dans jarvis_config.json."""
    try:
        import json
        cfg = _charger_config()
        cfg.update(data)
        with open(_JARVIS_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[MIC] Impossible de sauvegarder la config : {e}")

def detecter_microphone() -> int | None:
    """
    Détecte le meilleur microphone disponible.

    Stratégie :
      1. Essaie l'index mémorisé dans jarvis_config.json
      2. Essaie le micro par défaut du système (index None)
      3. Parcourt tous les périphériques d'entrée disponibles
      4. Sauvegarde l'index retenu pour le prochain lancement

    Retourne l'index (int) du micro retenu, ou None si aucun trouvé
    (dans ce cas sr.Microphone() utilisera le défaut OS).
    """
    import json

    # ── Lister tous les périphériques PyAudio ────────────────
    if pyaudio:
        try:
            p = pyaudio.PyAudio()
            nb = p.get_device_count()
            inputs = []
            print("[MIC] Périphériques audio détectés :")
            for i in range(nb):
                try:
                    info = p.get_device_info_by_index(i)
                    if info.get("maxInputChannels", 0) > 0:
                        nom = info.get("name", f"Périphérique {i}")
                        inputs.append((i, nom))
                        print(f"      [{i}] {nom}")
                except Exception:
                    pass
            p.terminate()

            if not inputs:
                print("[MIC] ⚠ Aucun périphérique d'entrée détecté par PyAudio.")
        except Exception as e:
            print(f"[MIC] Impossible de lister les périphériques : {e}")
            inputs = []
    else:
        inputs = []
        print("[MIC] PyAudio absent — mode fallback speech_recognition uniquement.")

    # ── Récupérer l'index mémorisé ───────────────────────────
    cfg = _charger_config()
    index_memo = cfg.get("mic_device_index", None)

    # ── Fonction de test d'un index ──────────────────────────
    def _tester_index(idx):
        """Retourne True si sr.Microphone(device_index=idx) s'ouvre correctement."""
        try:
            kwargs = {} if idx is None else {"device_index": idx}
            mic_test = sr.Microphone(**kwargs)
            r_test = sr.Recognizer()
            with mic_test as src:
                r_test.adjust_for_ambient_noise(src, duration=0.3)
            return True
        except Exception as e:
            label = "défaut" if idx is None else str(idx)
            print(f"[MIC]   Index {label} → KO ({e})")
            return False

    # ── Priorité 1 : index mémorisé ──────────────────────────
    if index_memo is not None:
        nom_memo = next((n for i, n in inputs if i == index_memo), f"Index {index_memo}")
        print(f"[MIC] Test du micro mémorisé : [{index_memo}] {nom_memo}")
        if _tester_index(index_memo):
            print(f"[MIC] ✔ Micro retenu (mémorisé) : [{index_memo}] {nom_memo}")
            return index_memo
        else:
            print(f"[MIC] Micro mémorisé introuvable, recherche d'un remplaçant…")

    # ── Priorité 2 : micro par défaut OS ─────────────────────
    print("[MIC] Test du micro par défaut système…")
    if _tester_index(None):
        # Identifier son index réel si possible
        idx_reel = None
        if pyaudio:
            try:
                p = pyaudio.PyAudio()
                idx_reel = p.get_default_input_device_info().get("index", None)
                p.terminate()
            except Exception:
                pass
        nom_defaut = next((n for i, n in inputs if i == idx_reel), "Défaut système")
        print(f"[MIC] ✔ Micro retenu (défaut) : [{idx_reel}] {nom_defaut}")
        _sauvegarder_config({"mic_device_index": idx_reel})
        return idx_reel

    # ── Priorité 3 : parcourir tous les périphériques ────────
    print("[MIC] Recherche sur tous les périphériques disponibles…")
    for idx, nom in inputs:
        print(f"[MIC]   Test [{idx}] {nom}…")
        if _tester_index(idx):
            print(f"[MIC] ✔ Micro retenu (fallback) : [{idx}] {nom}")
            _sauvegarder_config({"mic_device_index": idx})
            return idx

    # ── Aucun micro fonctionnel ───────────────────────────────
    print("[MIC] ⚠ Aucun microphone fonctionnel trouvé.")
    print("[MIC]   Vérifiez que votre micro est branché et autorisé dans")
    print("[MIC]   Paramètres Windows → Confidentialité → Microphone.")
    _sauvegarder_config({"mic_device_index": None})
    return None

def ecouter():
    global is_listening, jarvis_actif, dernier_message, STOP_PARLER, is_speaking, MIC_NEED_RELOAD

    r   = sr.Recognizer()

    # ── Détection automatique du micro ───────────────────────
    mic_index = detecter_microphone()
    if mic_index is not None:
        mic = sr.Microphone(device_index=mic_index)
        print(f"[JARVIS] Microphone sélectionné : index {mic_index}")
    else:
        mic = sr.Microphone()
        print("[JARVIS] Microphone : périphérique par défaut système")

    # -- Réglages de patience (Patience de l'écoute) --
    r.pause_threshold        = 1.2  # Temps de silence autorisé (en s) avant de couper
    r.non_speaking_duration  = 0.8  # Durée de silence minimale pour valider
    r.energy_threshold       = 300  # Sensibilité au bruit
    r.dynamic_energy_threshold = True

    # ── Calibration bruit ambiant ─────────────────────────────
    try:
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=1)
    except Exception as e:
        print(f"[MIC] ⚠ Calibration impossible : {e}")
        # Retenter avec le micro par défaut
        mic = sr.Microphone()
        try:
            with mic as source:
                r.adjust_for_ambient_noise(source, duration=1)
        except Exception:
            pass

    print("[JARVIS] Microphone pret. En attente de 'Jarvis' ou session active...")

    while True:
        try:
            # MICRO COUPÉ — pause silencieuse
            if MIC_MUTED:
                time.sleep(0.3)
                continue

            # CHANGEMENT DE MICRO demandé depuis les paramètres
            if MIC_NEED_RELOAD:
                MIC_NEED_RELOAD = False
                new_idx = detecter_microphone()
                if new_idx is not None:
                    mic = sr.Microphone(device_index=new_idx)
                else:
                    mic = sr.Microphone()
                try:
                    with mic as source:
                        r.adjust_for_ambient_noise(source, duration=0.5)
                except Exception:
                    pass
                print(f"[MIC] Micro rechargé → index {new_idx}")
                continue

            # GESTION DU TIMEOUT DE SESSION
            if jarvis_actif and (time.time() - dernier_message > SESSION_TIMEOUT):
                print("[JARVIS] Timeout session. Retour en veille.")
                jarvis_actif = False

            with mic as source:
                is_listening = True
                loop_ws = asyncio.new_event_loop()
                state = "active" if jarvis_actif else "listening"
                loop_ws.run_until_complete(send_web_state(state))
                loop_ws.close()
                
                audio = r.listen(source, timeout=2, phrase_time_limit=15)
                
                is_listening = False
                loop_ws = asyncio.new_event_loop()
                loop_ws.run_until_complete(send_web_state("idle"))
                loop_ws.close()

            texte = r.recognize_google(audio, language="fr-FR").lower().strip()
            print(f"[ENTENDU] {texte}")

            # GESTION INTERRUPTION DURANT LA PAROLE
            if is_speaking and ("tais-toi" in texte or "silence" in texte or "tais toi" in texte):
                STOP_PARLER = True
                continue

            # MOTS-CLÉS DE SOMMEIL
            SLEEP_WORDS = ["merci", "ce sera tout", "repos", "au revoir", "silence", "tais-toi", "tais toi"]
            if any(word in texte for word in SLEEP_WORDS):
                if jarvis_actif:
                    jarvis_actif = False
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(parler("A votre service Hugo. Je me mets en veille."))
                    loop.close()
                continue

            if WAKE_WORD in texte or jarvis_actif:
                if WAKE_WORD in texte:
                    print("[JARVIS] Mot-clé détecté.")
                    jarvis_actif = True
                
                dernier_message = time.time()
                commande = nettoyer_commande(texte)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if commande:
                    action_pc = executer_action_pc(commande)
                    if action_pc:
                        loop.run_until_complete(parler(action_pc))
                    else:
                        loop.run_until_complete(traiter_reponse_ia(commande))
                else:
                    if WAKE_WORD in texte: # "Jarvis" tout seul
                        loop.run_until_complete(parler("Oui Hugo, je vous écoute."))
                
                loop.close()
            else:
                pass

        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except OSError as e:
            # Micro débranché ou périphérique perdu — on tente de le relancer
            print(f"[MIC] ⚠ Périphérique audio perdu ({e}). Tentative de récupération…")
            time.sleep(2)
            try:
                mic_index = detecter_microphone()
                if mic_index is not None:
                    mic = sr.Microphone(device_index=mic_index)
                else:
                    mic = sr.Microphone()
                with mic as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                print("[MIC] ✔ Microphone récupéré avec succès.")
            except Exception as e2:
                print(f"[MIC] Impossible de récupérer le microphone : {e2}")
                time.sleep(3)
        except Exception as e:
            print(f"Erreur écoute : {e}")
            time.sleep(1)

def monitor_claps():
    if not pyaudio:
        print("[CLAP] PyAudio absent — detection des applaudissements desactivee.")
        return
    try:
        import audioop
        p = pyaudio.PyAudio()
        # On ouvre le flux
        # Utiliser le même micro que la détection vocale
        cfg_clap = _charger_config()
        mic_idx_clap = cfg_clap.get("mic_device_index", None)
        open_kwargs = dict(format=pyaudio.paInt16, channels=1, rate=44100,
                          input=True, frames_per_buffer=1024)
        if mic_idx_clap is not None:
            open_kwargs["input_device_index"] = mic_idx_clap
        stream = p.open(**open_kwargs)
        print("[CLAP] Détection des applaudissements activée.")
        
        print("[CLAP] Détection des doubles applaudissements activée.")
        
        last_clap_time = 0
        
        while True:
            try:
                data = stream.read(1024, exception_on_overflow=False)
                rms  = audioop.rms(data, 2)
                
                # ON IGNORE LE CLAP UNIQUEMENT SI LE MODE IRON MAN EST ÉTEINT OU SI JARVIS PARLE
                if not MODE_IRON_MAN or is_speaking or is_thinking:
                    last_clap_time = 0
                    continue

                if rms > CLAP_THRESHOLD:
                    current_time = time.time()
                    diff = current_time - last_clap_time
                    
                    if 0.1 < diff < 0.8:
                        global VIDEO_LANCEE
                        print(f"\n[CLAP] !!! DOUBLE CLAP DÉTECTÉ !!!")
                        entity_id = PIECES_LUMIERES.get("salon", "light.salon")
                        
                        # On vérifie l'état actuel
                        etat_actuel = ha_get_etat(entity_id)
                        
                        if etat_actuel != "on":
                            # ON ALLUME
                            print(f"[CLAP] Action : ALLUMER")
                            ha_lumiere(entity_id, "on")
                            
                            if not VIDEO_LANCEE:
                                print(f"[CLAP] Lancement initial de la vidéo...")
                                webbrowser.open("https://www.youtube.com/watch?v=KU5V5WZVcVE")
                                VIDEO_LANCEE = True
                                def seq():
                                    time.sleep(5)
                                    pyautogui.press('f')
                                threading.Thread(target=seq, daemon=True).start()
                            else:
                                print(f"[CLAP] Reprise de la vidéo (Play)...")
                                pyautogui.press('k')
                        else:
                            # ON ÉTEINT
                            print(f"[CLAP] Action : ÉTEINDRE")
                            ha_lumiere(entity_id, "off")
                            if VIDEO_LANCEE:
                                print(f"[CLAP] Mise en pause de la vidéo...")
                                pyautogui.press('k')
                            
                        # Gros debounce après une action réussie
                        time.sleep(3.0)
                        last_clap_time = 0 # Reset
                    else:
                        # C'est peut-être le premier clap
                        last_clap_time = current_time
            except Exception as e:
                # Si erreur de lecture (ex: micro débranché), on attend et on continue
                time.sleep(0.5)
                continue

    except Exception as e:
        print(f"[CLAP] Erreur fatale détection claps : {e}")

def verifier_mises_a_jour():
    """Vérifie si une nouvelle version est disponible sur le serveur."""
    global DERNIERE_MAJ_INFO
    try:
        print(f"[UPDATE] Verification des mises a jour...")
        response = requests.get(UPDATE_JSON_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            remote_version = data.get("version", "4.0")
            
            # Comparaison de version
            if remote_version > CURRENT_VERSION:
                print(f"[UPDATE] NOUVELLE VERSION DETECTEE : {remote_version}")
                DERNIERE_MAJ_INFO = {
                    "type": "update_available",
                    "version": remote_version,
                    "url": data.get("download_url", "https://www.techenclair.fr/pages/jarvis.html"),
                    "changelog": data.get("changelog", "")
                }
            else:
                print(f"[UPDATE] Systeme a jour (v{CURRENT_VERSION})")
                DERNIERE_MAJ_INFO = None
        else:
            print(f"[UPDATE] Serveur injoignable (Status: {response.status_code})")
    except Exception as e:
        print(f"[UPDATE] Erreur lors de la verification : {e}")

def verifier_mises_a_jour_loop():
    """Boucle de vérification périodique (toutes les 4 heures)."""
    while True:
        time.sleep(14400)
        verifier_mises_a_jour()

def start_ia():
    threading.Thread(target=monitor_claps, daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def start_ws():
        print(f"[WEB] Serveur WebSocket demarre sur ws://0.0.0.0:8765")
        print(f"[WEB] Accessible depuis le reseau : ws://{LOCAL_IP}:8765")
        
        # Lancer le monitoring système en arrière-plan
        asyncio.create_task(broadcast_system_stats())
        
        async with websockets.serve(ws_handler, "0.0.0.0", 8765):
            await asyncio.Future()

    threading.Thread(target=lambda: asyncio.run(start_ws()), daemon=True).start()

    loop.run_until_complete(parler("Bonjour, Hugo"))
    loop.close()
    ecouter()

# ==========================================
# LANCEMENT — MODE CONSOLE + FRONTEND WEB
# ==========================================
# Ursina desactive : l'interface est maintenant le frontend Three.js
# dans le dossier frontend/ (npm run dev -> http://localhost:5173)
# Le WebSocket est deja demarre par start_ia() sur ws://localhost:8765

if pygame:
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
else:
    print("[INFO] Pygame absent — demarrage sans audio TTS.")

def start_mobile_http_server():
    """Serveur HTTP minimal pour servir l'interface mobile sur le port 8080."""
    import http.server
    mobile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile")
    if not os.path.exists(mobile_dir):
        print("[MOBILE] Dossier mobile/ introuvable, serveur non demarre.")
        return
    class MobileHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=mobile_dir, **kwargs)
        def log_message(self, format, *args):
            pass  # Silencieux
    server = http.server.HTTPServer(("0.0.0.0", 8080), MobileHandler)
    print(f"[MOBILE] Serveur HTTP demarre sur http://{LOCAL_IP}:8080")
    server.serve_forever()

def liberer_port(port):
    """Tue le processus qui occupe le port donné (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True
        )
        stdout = result.stdout.decode(errors='ignore')
        for line in stdout.splitlines():
            if f":{port}" in line and ("LISTENING" in line or "ÉCOUTE" in line):
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit() and int(pid) != os.getpid():
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True)
                    print(f"[DÉMARRAGE] Port {port} libéré (PID {pid} terminé).")
                    return
    except Exception as e:
        print(f"[DÉMARRAGE] Impossible de libérer le port {port} : {e}")

def main():
    # Fix Windows asyncio ProactorEventLoop concurrent-write crash
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print()
    print("=" * 60)
    print("   J.A.R.V.I.S — Demarrage du systeme")
    print("=" * 60)
    print()
    print("  Backend   : actif (terminal)")
    print(f"  WebSocket : ws://localhost:8765  (LAN: ws://{LOCAL_IP}:8765)")
    print(f"  Mobile    : http://{LOCAL_IP}:8080")
    print()
    print("  Commandes vocales actives.")
    print("  Dites 'Jarvis' pour activer la session.")
    print("=" * 60)
    print()

    # Liberer les ports si une instance precedente tourne encore
    liberer_port(8765)
    liberer_port(8080)

    # Lancer le serveur Frontend
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    frontend_process = None
    FRONTEND_URL = "http://localhost:5173"

    def _port_ecoute(port, timeout=4.0):
        """Retourne True si quelque chose ecoute sur le port donne."""
        import socket
        debut = time.time()
        while time.time() - debut < timeout:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    return True
            except (ConnectionRefusedError, OSError):
                time.sleep(0.2)
        return False

    def _servir_dist_python(port=5173):
        """Sert le dossier dist/ avec le serveur HTTP Python (fallback sans npm)."""
        import http.server, socketserver
        dist_dir = os.path.join(frontend_dir, "dist")
        os.chdir(dist_dir)
        handler = http.server.SimpleHTTPRequestHandler
        handler.log_message = lambda *a: None  # silencieux
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"[JARVIS] Frontend servi via Python HTTP sur http://localhost:{port}")
            httpd.serve_forever()

    vite_ok = False
    if os.path.exists(frontend_dir):
        # Tentative 1 : Vite (npm run dev)
        try:
            print("[JARVIS] Tentative de lancement Vite (npm run dev)...")
            frontend_process = subprocess.Popen(
                ["npm", "run", "dev"], cwd=frontend_dir, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            vite_ok = _port_ecoute(5173, timeout=5.0)
            if vite_ok:
                print("[JARVIS] Vite demarre avec succes sur localhost:5173")
            else:
                print("[JARVIS] Vite n'a pas demarre (npm/vite absent ou erreur).")
                if frontend_process:
                    frontend_process.terminate()
                    frontend_process = None
        except Exception as e:
            print(f"[JARVIS] Impossible de lancer Vite : {e}")
            frontend_process = None

        # Tentative 2 : servir dist/ avec Python (pas besoin de npm)
        if not vite_ok:
            dist_dir = os.path.join(frontend_dir, "dist")
            if os.path.exists(dist_dir) and os.path.exists(os.path.join(dist_dir, "index.html")):
                print("[JARVIS] Fallback : service du dossier dist/ via Python HTTP...")
                t_dist = threading.Thread(target=_servir_dist_python, args=(5173,), daemon=True)
                t_dist.start()
                vite_ok = _port_ecoute(5173, timeout=3.0)
                if vite_ok:
                    print("[JARVIS] Frontend dist/ servi correctement.")
            else:
                print("[JARVIS] Aucun dossier dist/ trouve. Interface non disponible.")
                print("[JARVIS] Pour corriger : cd frontend && npm install && npm run build")

    if not vite_ok:
        print("[JARVIS] ATTENTION : l'interface visuelle ne sera pas disponible.")
        print("[JARVIS] JARVIS reste fonctionnel en mode vocal uniquement.")

    # Verification initiale des mises a jour
    verifier_mises_a_jour()
    
    # Lancer les services en arriere-plan
    threading.Thread(target=start_mobile_http_server, daemon=True).start()
    threading.Thread(target=start_ia, daemon=True).start()
    threading.Thread(target=verifier_mises_a_jour_loop, daemon=True).start()

    # Choisir le mode d'affichage
    if _WEBVIEW_OK and webview is not None:
        # MODE FENETRE NATIVE (pywebview)
        print("[JARVIS] Ouverture dans une fenetre native (pywebview)...")

        # Calcul de la taille et position centrée selon la résolution de l'écran
        try:
            from screeninfo import get_monitors
            _mon = get_monitors()[0]
            _sw, _sh = _mon.width, _mon.height
        except Exception:
            _sw, _sh = 1920, 1080

        # 85% de l'écran, min 1280x780
        _win_w = max(1280, int(_sw * 0.85))
        _win_h = max(780,  int(_sh * 0.85))
        _win_x = (_sw - _win_w) // 2
        _win_y = (_sh - _win_h) // 2

        window = webview.create_window(
            title            = "J.A.R.V.I.S",
            url              = FRONTEND_URL,
            width            = _win_w,
            height           = _win_h,
            x                = _win_x,
            y                = _win_y,
            resizable        = True,
            min_size         = (900, 600),
            background_color = "#0a0a0f",
        )
        global _WEBVIEW_WINDOW
        _WEBVIEW_WINDOW = window

        def _on_closed():
            print("\n[JARVIS] Fenetre fermee — extinction du systeme...")
            if frontend_process:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        window.events.closed += _on_closed

        def _on_loaded():
            try:
                import ctypes
                import os
                # Groupement dans la barre des taches (detache de python.exe)
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TechEnClair.Jarvis.App")
                
                # Remplacement de l'icone de la fenetre webview
                hwnd = ctypes.windll.user32.FindWindowW(None, "J.A.R.V.I.S")
                if hwnd:
                    icon_path = os.path.abspath("jarvis.ico")
                    if os.path.exists(icon_path):
                        hicon = ctypes.windll.user32.LoadImageW(0, icon_path, 1, 0, 0, 0x0010)
                        if hicon:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon) # ICON_SMALL
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon) # ICON_BIG
            except Exception as e:
                print(f"[JARVIS] Erreur chargement icone : {e}")

        window.events.loaded += _on_loaded

        # webview.start() DOIT etre appele depuis le thread principal
        try:
            webview.start()
        except Exception as e:
            print(f"[JARVIS] PyWebView impossible : {e} — bascule sur navigateur")
            _ouvrir_dans_navigateur(FRONTEND_URL, frontend_process)
    else:
        # MODE NAVIGATEUR (fallback si pywebview absent)
        _ouvrir_dans_navigateur(FRONTEND_URL, frontend_process)


def _ouvrir_dans_navigateur(url, frontend_process):
    """
    Tente d'ouvrir l'URL en mode 'Application' (sans barres d'outils) 
    pour conserver l'aspect 'Application Dédiée'.
    """
    print(f"[JARVIS] Tentative d'ouverture en Mode App Dédiée sur {url}...")
    
    # Liste des navigateurs supportant le mode --app par ordre de préférence
    try:
        success = False
        # On tente msedge d'abord (présent sur tous les Windows 10/11) puis chrome
        for browser in ["msedge", "chrome"]:
            try:
                # La commande 'start' permet de lancer le processus indépendamment
                subprocess.Popen(f'start {browser} --app="{url}"', shell=True)
                print(f"[JARVIS] Interface lancée via {browser} (Mode App)")
                success = True
                break
            except:
                continue
        
        if success:
            _attendre_interface(frontend_process)
            return
    except Exception as e:
        print(f"[JARVIS] Erreur lancement Mode App : {e}")

    # Fallback ultime : Navigateur par défaut standard
    print("[JARVIS] Fallback : Ouverture dans le navigateur par défaut...")
    webbrowser.open(url)
    _attendre_interface(frontend_process)

def _attendre_interface(frontend_process):
    """Gère la boucle d'attente et l'extinction du système."""
    try:
        while True:
            time.sleep(1)
            # On ne ferme que si l'interface a été connectée au moins une fois
            if interface_deja_connectee and len(CONNECTED_CLIENTS) == 0:
                print("\n[JARVIS] Interface deconnectee. Attente de reconnexion (60s)...")
                time.sleep(60)
                if len(CONNECTED_CLIENTS) == 0:
                    print("[JARVIS] Aucune reconnexion. Extinction automatique...")
                    break
                else:
                    print("[JARVIS] Reconnexion detectee. Reprise.")
    except KeyboardInterrupt:
        print("\n[JARVIS] Arret manuel.")

    if frontend_process:
        print("[JARVIS] Arret du serveur Web...")
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

builtins.demander_ia_vision = demander_ia_vision
if __name__ == "__main__":
    main()
