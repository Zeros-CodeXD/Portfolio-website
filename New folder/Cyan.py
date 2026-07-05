import customtkinter as ctk
import threading
import time
import speech_recognition as sr
import ollama
import subprocess
import pygame
import os
import winsound
import psutil
from datetime import datetime
from tkinter import messagebox  # Added for popups

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
PIPER_EXE = os.path.join(BIN_DIR, "piper.exe")

# Define voice paths
VOICE_ENGLISH = os.path.join(BIN_DIR, "en_US-amy-medium.onnx")

# --- THEMES ---
THEMES = {
    "Cyan": {"acc": "#60CDFF", "hov": "#4CC2FF", "bg": "#202020"},
    "Purple": {"acc": "#D0BCFF", "hov": "#E8DEF8", "bg": "#141218"},
    "Green": {"acc": "#66FF7F", "hov": "#8AFF9D", "bg": "#0D110E"},
    "Gold": {"acc": "#FFD700", "hov": "#FFE14D", "bg": "#1C1C10"},
}

ctk.set_appearance_mode("Dark")

class Backend:
    def __init__(self):
        self.history = []
        self.system_prompt = "You are Cyan. Helpful, witty, and concise."
        self.current_voice = VOICE_ENGLISH
        self.temp = 0.7
        self.incognito = False
        self.voice_speed = 100 
        pygame.mixer.init()
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.energy_threshold = 1000
        
        # Check for Ollama on startup
        threading.Thread(target=self.check_ollama).start()

    def check_ollama(self):
        try:
            ollama.list()
        except:
            print("⚠️ Ollama not detected.")

    def generate_stream(self):
        """Generates text in chunks for the typewriter effect"""
        messages = [{'role': 'system', 'content': self.system_prompt}]
        for msg in self.history:
            messages.append({'role': msg['role'], 'content': msg['content']})
        
        try:
            stream = ollama.chat(model='llama3.2:1b', messages=messages, options={'temperature': self.temp}, stream=True)
            full_reply = ""
            for chunk in stream:
                content = chunk['message']['content']
                full_reply += content
                yield content 
            
            if not self.incognito:
                self.history.append({'role': 'assistant', 'content': full_reply, 'timestamp': datetime.now().strftime("%I:%M %p")})
            
            # Speak after full generation
            self.speak(full_reply)
            
        except Exception as e:
            yield f"[System Error: Ollama not running or model missing. {e}]"

    def speak(self, text):
        # SAFETY CHECK: Don't try to speak if files are missing
        if not os.path.exists(PIPER_EXE) or not os.path.exists(self.current_voice):
            print("⚠️ Voice files missing. Skipping audio.")
            return

        threading.Thread(target=self._speak_thread, args=(text,)).start()

    def _speak_thread(self, text):
        out = "temp_voice.wav"
        if os.path.exists(out): os.remove(out)
        
        cmd = [PIPER_EXE, "--model", self.current_voice, "--output_file", out]
        try:
            subprocess.run(cmd, input=text.encode('utf-8'), capture_output=True, check=True)
            if os.path.exists(out):
                pygame.mixer.music.load(out)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy(): time.sleep(0.1)
                pygame.mixer.music.unload()
        except Exception as e:
            print(f"Voice Error: {e}")

class CyanFluent(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.current_theme = "Cyan"
        self.colors = THEMES[self.current_theme]
        
        self.title("Cyan AI (v2.0)")
        self.geometry("1200x800")
        self.configure(fg_color=self.colors["bg"])
        
        self.f_head = ("Segoe UI Variable Display", 20, "bold")
        self.f_body = ("Segoe UI", 14)

        self.backend = Backend()
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_pages()
        self.show_page("chat")
        
        self.update_stats()
        
        # ON STARTUP: Check for voice files
        self.after(1000, self.check_files)

    def check_files(self):
        if not os.path.exists(PIPER_EXE):
            messagebox.showwarning("Missing Files", 
                "⚠️ Voice Engine Not Found!\n\nCyan needs 'piper.exe' in a 'bin' folder to speak.\nChat will work, but voice will be disabled.")

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#2B2B2B")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="💠 Cyan AI", font=self.f_head, text_color=self.colors["acc"])
        self.logo.pack(anchor="w", padx=25, pady=(30, 20))

        self.nav_btn("💬 Chat", "chat")
        self.nav_btn("📂 Vault 2.0", "vault")
        self.nav_btn("⚙️ Settings", "settings")

        self.frame_stats = ctk.CTkFrame(self.sidebar, fg_color="#202020", corner_radius=10)
        self.frame_stats.pack(side="bottom", fill="x", padx=15, pady=20)
        
        self.bar_cpu = ctk.CTkProgressBar(self.frame_stats, height=6, progress_color=self.colors["acc"])
        self.bar_cpu.pack(fill="x", padx=10, pady=(10, 5))
        self.lbl_cpu = ctk.CTkLabel(self.frame_stats, text="CPU: 0%", font=("Segoe UI", 10))
        self.lbl_cpu.pack(anchor="w", padx=10, pady=(0, 10))

    def nav_btn(self, text, page):
        btn = ctk.CTkButton(self.sidebar, text=text, font=self.f_body, fg_color="transparent", 
                            text_color="#FFF", hover_color="#3A3A3A", anchor="w", height=45,
                            command=lambda: self.show_page(page))
        btn.pack(fill="x", padx=10, pady=2)

    def setup_pages(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # --- CHAT PAGE ---
        self.page_chat = ctk.CTkFrame(self.container, fg_color="transparent")
        
        top = ctk.CTkFrame(self.page_chat, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="Assistant", font=("Segoe UI", 18, "bold")).pack(side="left")
        ctk.CTkButton(top, text="📌 Pin", width=60, fg_color="#333", command=self.toggle_pin).pack(side="right")
        
        self.chat_scroll = ctk.CTkScrollableFrame(self.page_chat, fg_color="transparent")
        self.chat_scroll.pack(fill="both", expand=True, pady=10)
        
        chips = ctk.CTkFrame(self.page_chat, fg_color="transparent")
        chips.pack(fill="x", pady=(0, 5))
        for prompt in ["Summarize", "Explain Code", "Joke", "Story"]:
            ctk.CTkButton(chips, text=prompt, width=80, height=25, fg_color="#333", font=("Segoe UI", 11),
                          command=lambda p=prompt: self.quick_prompt(p)).pack(side="left", padx=5)

        inp = ctk.CTkFrame(self.page_chat, height=60, fg_color="#2B2B2B", corner_radius=30)
        inp.pack(fill="x")
        
        self.entry = ctk.CTkEntry(inp, placeholder_text="Ask Cyan...", border_width=0, fg_color="transparent", font=self.f_body)
        self.entry.pack(side="left", fill="x", expand=True, padx=20)
        self.entry.bind("<Return>", self.press_enter)
        
        ctk.CTkButton(inp, text="🎤", width=40, height=40, corner_radius=20, fg_color="#333", 
                      hover_color="red", command=self.listen).pack(side="right", padx=10)

        # --- VAULT PAGE ---
        self.page_vault = ctk.CTkFrame(self.container, fg_color="transparent")
        v_split = ctk.CTkFrame(self.page_vault, fg_color="transparent")
        v_split.pack(fill="both", expand=True)
        
        self.vault_list = ctk.CTkScrollableFrame(v_split, width=250, fg_color="#2B2B2B")
        self.vault_list.pack(side="left", fill="y", padx=(0, 10))
        
        self.vault_content = ctk.CTkTextbox(v_split, fg_color="#1E1E1E", font=("Consolas", 14), corner_radius=10)
        self.vault_content.pack(side="right", fill="both", expand=True)

        # --- SETTINGS PAGE ---
        self.page_settings = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.add_setting_head("🎨 Appearance")
        
        row_theme = ctk.CTkFrame(self.page_settings, fg_color="#2B2B2B")
        row_theme.pack(fill="x", pady=5)
        ctk.CTkLabel(row_theme, text="Accent Color").pack(side="left", padx=20, pady=15)
        ctk.CTkOptionMenu(row_theme, values=list(THEMES.keys()), command=self.change_theme).pack(side="right", padx=20)

        self.add_setting_head("🧠 Brain")
        self.add_setting_toggle("Incognito Mode", self.toggle_incognito)

    def add_setting_head(self, text):
        ctk.CTkLabel(self.page_settings, text=text, font=("Segoe UI", 16, "bold"), text_color=self.colors["acc"]).pack(anchor="w", pady=(20, 5))

    def add_setting_toggle(self, text, cmd):
        fr = ctk.CTkFrame(self.page_settings, fg_color="#2B2B2B")
        fr.pack(fill="x", pady=2)
        ctk.CTkLabel(fr, text=text).pack(side="left", padx=20, pady=15)
        ctk.CTkSwitch(fr, text="", command=cmd, progress_color=self.colors["acc"]).pack(side="right", padx=20)

    # --- LOGIC ---
    def show_page(self, page):
        self.page_chat.pack_forget()
        self.page_vault.pack_forget()
        self.page_settings.pack_forget()
        
        if page == "chat": self.page_chat.pack(fill="both", expand=True)
        if page == "vault": 
            self.page_vault.pack(fill="both", expand=True)
            self.load_vault_list()
        if page == "settings": self.page_settings.pack(fill="both", expand=True)

    def press_enter(self, event=None):
        msg = self.entry.get()
        if not msg.strip(): return
        self.entry.delete(0, "end")
        
        if not self.backend.incognito:
            self.backend.history.append({'role': 'user', 'content': msg, 'timestamp': datetime.now().strftime("%I:%M %p")})
        self.add_bubble(msg, True)
        threading.Thread(target=self.process_stream).start()

    def process_stream(self):
        bubble_label = self.add_bubble("...", False)
        full_text = ""
        for chunk in self.backend.generate_stream():
            full_text += chunk
            bubble_label.configure(text=full_text) 
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        self.add_save_btn(bubble_label.master, full_text)

    def add_bubble(self, text, is_user):
        align = "right" if is_user else "left"
        col = self.colors["acc"] if is_user else "#2B2B2B"
        txt = "#000" if is_user else "#FFF"
        
        wrap = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        wrap.pack(fill="x", pady=5)
        
        bub = ctk.CTkFrame(wrap, fg_color=col, corner_radius=18)
        bub.pack(side=align, padx=20, ipadx=10, ipady=8)
        
        lbl = ctk.CTkLabel(bub, text=text, text_color=txt, font=self.f_body, wraplength=600, justify="left")
        lbl.pack()
        return lbl

    def add_save_btn(self, parent_frame, text):
        btn = ctk.CTkButton(parent_frame, text="💾 Save", width=40, height=20, font=("Arial", 10), 
                            fg_color="transparent", text_color="gray", hover_color="#333",
                            command=lambda: self.save_to_vault(text))
        btn.pack(anchor="w", padx=20)

    def save_to_vault(self, text):
        if not os.path.exists("vault"): os.makedirs("vault")
        fname = f"Note_{int(time.time())}.txt"
        with open(f"vault/{fname}", "w") as f: f.write(text)
        winsound.Beep(1000, 100)

    def load_vault_list(self):
        for w in self.vault_list.winfo_children(): w.destroy()
        if not os.path.exists("vault"): return
        for f in os.listdir("vault"):
            ctk.CTkButton(self.vault_list, text=f, fg_color="transparent", anchor="w",
                          command=lambda n=f: self.load_note_content(n)).pack(fill="x")

    def load_note_content(self, filename):
        with open(f"vault/{filename}", "r") as f:
            self.vault_content.delete("0.0", "end")
            self.vault_content.insert("0.0", f.read())

    def toggle_pin(self): self.attributes('-topmost', not self.attributes('-topmost'))
    
    def change_theme(self, theme):
        self.current_theme = theme
        self.colors = THEMES[theme]
        self.configure(fg_color=self.colors["bg"])
        self.logo.configure(text_color=self.colors["acc"])

    def quick_prompt(self, txt):
        self.entry.insert(0, txt + " ")
        self.entry.focus()

    def update_stats(self):
        c = psutil.cpu_percent()
        self.bar_cpu.set(c/100)
        self.lbl_cpu.configure(text=f"CPU: {c}%")
        self.after(2000, self.update_stats)

    def toggle_incognito(self): self.backend.incognito = not self.backend.incognito
    
    def listen(self):
        threading.Thread(target=self._listen).start()
    def _listen(self):
        r = self.backend.recognizer
        with sr.Microphone() as s:
            r.adjust_for_ambient_noise(s)
            try:
                a = r.listen(s, timeout=5)
                t = r.recognize_google(a)
                self.entry.insert(0, t)
                self.press_enter()
            except: pass

if __name__ == "__main__":
    app = CyanFluent()
    app.mainloop()