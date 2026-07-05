import asyncio
import aiohttp
import logging
import re
import random
import csv
import threading
import webbrowser
from tkinter import filedialog
from typing import Any
from bs4 import BeautifulSoup
import customtkinter as ctk

# Additional imports for Superpower Tier
from PIL import Image, ExifTags

# Configure global logger
logger = logging.getLogger("NexusV2")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(console_handler)

# ==========================================
# TASK 1-5 BACKEND CORE
# ==========================================

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b')

class StealthManager:
    USER_AGENTS =[
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
    ]

    @staticmethod
    def get_random_headers() -> dict[str, str]:
        return {
            "User-Agent": random.choice(StealthManager.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

class DataExtractor:
    EXCLUDED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.woff'}
    DUMMY_DOMAINS = {'example.com', 'email.com', 'domain.com', 'test.com', 'yourdomain.com'}

    @classmethod
    def extract_contact_info(cls, html: str) -> dict[str, list[str]]:
        if not html:
            return {"emails":[], "phones":[]}

        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "noscript", "meta"]):
            element.decompose()

        cleaned_text = soup.get_text(separator=" ")
        
        raw_emails = set(EMAIL_REGEX.findall(cleaned_text))
        valid_emails = {
            e.lower() for e in raw_emails 
            if not any(e.lower().endswith(ext) for ext in cls.EXCLUDED_EXTENSIONS)
            and e.lower().split('@')[1] not in cls.DUMMY_DOMAINS
        }

        raw_phones = set(PHONE_REGEX.findall(cleaned_text))
        valid_phones = {
            re.sub(r'\s+', ' ', p).strip() for p in raw_phones 
            if 7 <= sum(c.isdigit() for c in p) <= 15
        }

        return {"emails": list(valid_emails), "phones": list(valid_phones)}

class AsyncEngine:
    def __init__(self, concurrency_limit: int = 50, timeout_seconds: int = 15):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def _fetch_url(self, session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
        async with self.semaphore:
            await asyncio.sleep(random.uniform(0.1, 0.5))
            try:
                async with session.get(url, headers=StealthManager.get_random_headers(), allow_redirects=True) as response:
                    status = response.status
                    html = await response.text() if status == 200 else ""
                    forensics = DataExtractor.extract_contact_info(html)
                    return {"url": url, "status": status, "emails": forensics["emails"], "phones": forensics["phones"], "error": None}
            except asyncio.TimeoutError:
                return {"url": url, "status": None, "emails": [], "phones":[], "error": "TimeoutError"}
            except aiohttp.ClientError as e:
                return {"url": url, "status": None, "emails": [], "phones":[], "error": f"ClientError: {str(e)}"}

    async def _check_status(self, session: aiohttp.ClientSession, platform: str, url: str) -> dict[str, Any]:
        async with self.semaphore:
            await asyncio.sleep(random.uniform(0.05, 0.2))
            headers = StealthManager.get_random_headers()
            try:
                async with session.head(url, headers=headers, allow_redirects=True) as response:
                    status = response.status
                if status in [400, 403, 405]:
                    async with session.get(url, headers=headers, allow_redirects=True) as response:
                        status = response.status
                        await response.release()
                return {"platform": platform, "url": url, "status": status, "error": None}
            except asyncio.TimeoutError:
                return {"platform": platform, "url": url, "status": None, "error": "TimeoutError"}
            except aiohttp.ClientError as e:
                return {"platform": platform, "url": url, "status": None, "error": f"ClientError: {str(e)}"}

    async def execute_batch(self, urls: list[str]) -> list[dict[str, Any]]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            tasks =[self._fetch_url(session, url) for url in urls]
            return await asyncio.gather(*tasks, return_exceptions=False)

    async def execute_status_batch(self, targets: dict[str, str]) -> list[dict[str, Any]]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            tasks =[self._check_status(session, platform, url) for platform, url in targets.items()]
            return await asyncio.gather(*tasks, return_exceptions=False)

class PayloadExporter:
    @staticmethod
    def export_to_csv(results: list[dict[str, Any]], filename: str) -> None:
        headers =["Target_URL", "HTTP_Status", "Error", "Emails_Found", "Phones_Found"]
        try:
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in results:
                    writer.writerow([
                        row.get("url", ""), row.get("status", ""), row.get("error", "") or "None",
                        " | ".join(row.get("emails", [])), " | ".join(row.get("phones",[]))
                    ])
            logger.info(f"Payload exported successfully: {filename}")
        except IOError as e:
            logger.error(f"IO Error during export: {str(e)}")

class IdentityMatrix:
    PLATFORMS = {
        "GitHub": "https://github.com/{}", "Twitter": "https://twitter.com/{}", "Reddit": "https://www.reddit.com/user/{}",
        "Instagram": "https://www.instagram.com/{}/", "Pinterest": "https://www.pinterest.com/{}/", "GitLab": "https://gitlab.com/{}",
        "Medium": "https://medium.com/@{}", "SoundCloud": "https://soundcloud.com/{}", "Twitch": "https://www.twitch.tv/{}"
    }

    @classmethod
    async def scan_username(cls, username: str) -> dict[str, list[str]]:
        engine = AsyncEngine(concurrency_limit=500, timeout_seconds=10)
        targets = {platform: url.format(username) for platform, url in cls.PLATFORMS.items()}
        logger.info(f"Identity Matrix mapping: '{username}' across {len(targets)} vectors.")
        results = await engine.execute_status_batch(targets)
        
        report = {"Found": [], "Not Found": [], "Error":[]}
        for res in results:
            if res["status"] == 200: report["Found"].append(res["platform"])
            elif res["status"] == 404: report["Not Found"].append(res["platform"])
            else: report["Error"].append(f"{res['platform']} ({res['status'] or res['error']})")
        return report

# ==========================================
# SUPERPOWER TIER: NEW FORENSIC MODULES
# ==========================================

class ExifForensics:
    """Extracts deeply embedded EXIF metadata from local images and correlates GPS coordinates."""
    
    @staticmethod
    def extract_metadata(image_path: str) -> dict[str, Any]:
        result = {"error": None, "maps_link": None, "raw_data": {}}
        try:
            img = Image.open(image_path)
            exif_data = img._getexif()
            
            if not exif_data:
                result["error"] = "No EXIF data found in this image."
                return result

            gps_info = {}
            for tag_id, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                if tag_name == "GPSInfo":
                    for key in value:
                        decode = ExifTags.GPSTAGS.get(key, key)
                        gps_info[decode] = value[key]
                else:
                    # Clean up bytes for UI rendering
                    if isinstance(value, bytes):
                        try:
                            value = value.decode(errors="ignore")
                        except Exception:
                            value = "<binary_data>"
                    result["raw_data"][tag_name] = value

            if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
                lat = ExifForensics._convert_to_degrees(gps_info["GPSLatitude"])
                lon = ExifForensics._convert_to_degrees(gps_info["GPSLongitude"])
                
                if gps_info.get("GPSLatitudeRef", "N") != "N": lat = -lat
                if gps_info.get("GPSLongitudeRef", "E") != "E": lon = -lon
                
                result["maps_link"] = f"https://www.google.com/maps?q={lat},{lon}"
                result["raw_data"]["[+] Extracted Location"] = f"{lat}, {lon}"
                
            return result
            
        except FileNotFoundError:
            result["error"] = "Target file not found."
        except Exception as e:
            result["error"] = f"EXIF parsing error: {str(e)}"
        return result

    @staticmethod
    def _convert_to_degrees(value) -> float:
        try:
            d, m, s = float(value[0]), float(value[1]), float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        except (IndexError, TypeError, ValueError):
            return 0.0

class ArchiveRecon:
    """Interrogates the Internet Archive CDX API for historical timeline mapping."""
    
    @staticmethod
    async def fetch_history(url: str) -> dict[str, str]:
        results = {"oldest": "", "newest": "", "error": None}
        
        # CDX endpoints for exact boundaries
        cdx_oldest = f"http://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=1"
        cdx_newest = f"http://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=-1"
        
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # Concurrent requests to hit oldest and newest simultaneously
                old_task = session.get(cdx_oldest)
                new_task = session.get(cdx_newest)
                
                resp_old, resp_new = await asyncio.gather(old_task, new_task, return_exceptions=True)
                
                if isinstance(resp_old, aiohttp.ClientResponse) and resp_old.status == 200:
                    data_old = await resp_old.json()
                    if len(data_old) > 1:
                        timestamp, original = data_old[1][1], data_old[1][2]
                        results["oldest"] = f"http://web.archive.org/web/{timestamp}/{original}"

                if isinstance(resp_new, aiohttp.ClientResponse) and resp_new.status == 200:
                    data_new = await resp_new.json()
                    if len(data_new) > 1:
                        timestamp, original = data_new[1][1], data_new[1][2]
                        results["newest"] = f"http://web.archive.org/web/{timestamp}/{original}"

                if not results["oldest"] and not results["newest"]:
                    results["error"] = "No historical snapshots found in the archive."
                    
            except asyncio.TimeoutError:
                results["error"] = "Connection to Archive API timed out."
            except aiohttp.ClientError as e:
                results["error"] = f"Archive API Client Error: {str(e)}"
            except Exception as e:
                results["error"] = f"Archive API Error: {str(e)}"
                
        return results

# ==========================================
# ADVANCED WINDOWS 11 / HTML UI (UPDATED)
# ==========================================

class TextboxLogHandler(logging.Handler):
    def __init__(self, textbox: ctk.CTkTextbox, update_func):
        super().__init__()
        self.textbox = textbox
        self.update_func = update_func

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n")
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        self.update_func(0, append)


class NexusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("NEXUS V2 - Superpower Edition")
        self.geometry("1200x850")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.font_h1 = ctk.CTkFont(family="Segoe UI Variable Display", size=32, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI Variable Display", size=20, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=14)
        
        self.scraper_results =[]
        self.selected_image_path = ""
        self.current_maps_link = ""
        
        self._build_sidebar()
        self._build_workspace()
        self._build_console()
        
        # Link python logger output to UI Console box
        logger.handlers =[h for h in logger.handlers if not isinstance(h, TextboxLogHandler)]
        self.log_handler = TextboxLogHandler(self.console_text, self.after)
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s[%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(self.log_handler)
        
        logger.info("NEXUS V2 OSINT Engine initialized with Deep Intel Modules.")
        self.select_frame_by_name("scraper")

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#181818")
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        ctk.CTkLabel(self.sidebar_frame, text="NEXUS V2", font=self.font_h2, text_color="#0078D4").grid(row=0, column=0, padx=20, pady=(30, 30))
        
        # We maintain the modern HTML Sidebar approach which functions as our advanced TabView
        self.btn_nav_scraper = self._create_nav_btn("Lead Harvester", "scraper", 1)
        self.btn_nav_identity = self._create_nav_btn("Identity Matrix", "identity", 2)
        self.btn_nav_deepintel = self._create_nav_btn("Deep Intel", "deepintel", 3)

    def _create_nav_btn(self, text, view_name, row):
        btn = ctk.CTkButton(
            self.sidebar_frame, corner_radius=8, height=40, border_spacing=10, 
            text=text, fg_color="transparent", text_color=("gray10", "gray90"), 
            hover_color=("gray70", "gray30"), anchor="w",
            command=lambda: self.select_frame_by_name(view_name)
        )
        btn.grid(row=row, column=0, sticky="ew", padx=15, pady=5)
        return btn

    def _build_workspace(self):
        self.workspace_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace_frame.grid(row=0, column=1, sticky="nsew")
        self.workspace_frame.grid_rowconfigure(0, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)
        
        self._build_scraper_view()
        self._build_identity_view()
        self._build_deepintel_view()

    def _build_scraper_view(self):
        self.view_scraper = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.view_scraper.grid_columnconfigure(0, weight=1)
        self.view_scraper.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.view_scraper, text="Domain Lead Harvester", font=self.font_h1, anchor="w").grid(row=0, column=0, padx=30, pady=(30, 20), sticky="ew")
        
        body = ctk.CTkFrame(self.view_scraper, fg_color="transparent")
        body.grid(row=1, column=0, padx=30, pady=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        
        card_in = ctk.CTkFrame(body, fg_color="#202020", corner_radius=12)
        card_in.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card_in.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(card_in, text="Target Domains (One per line)", font=self.font_body, text_color="gray70").grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        self.url_textbox = ctk.CTkTextbox(card_in, fg_color="#121212", border_width=1, border_color="#333333", corner_radius=6)
        self.url_textbox.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.url_textbox.insert("0.0", "https://www.w3.org\n")
        
        card_stat = ctk.CTkFrame(body, fg_color="#202020", corner_radius=12)
        card_stat.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(card_stat, text="Actions & Metrics", font=self.font_body, text_color="gray70").pack(padx=20, pady=(15, 20), anchor="w")
        
        self.btn_harvest = ctk.CTkButton(card_stat, text="Execute Harvesting", height=45, fg_color="#0078D4", hover_color="#005A9E", font=ctk.CTkFont(weight="bold"), command=self.start_harvester_thread)
        self.btn_harvest.pack(padx=20, pady=(0, 10), fill="x")
        
        self.btn_export = ctk.CTkButton(card_stat, text="Export CSV Payload", height=45, fg_color="#333333", hover_color="#444444", font=ctk.CTkFont(weight="bold"), command=self.export_csv, state="disabled")
        self.btn_export.pack(padx=20, pady=(0, 30), fill="x")
        
        self.lbl_stat_targets = ctk.CTkLabel(card_stat, text="Targets Processed: 0", font=self.font_body, anchor="w")
        self.lbl_stat_targets.pack(padx=20, pady=5, fill="x")

    def _build_identity_view(self):
        self.view_identity = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.view_identity.grid_columnconfigure(0, weight=1)
        self.view_identity.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.view_identity, text="Identity Matrix OSINT", font=self.font_h1, anchor="w").grid(row=0, column=0, padx=30, pady=(30, 20), sticky="ew")
        
        card_in = ctk.CTkFrame(self.view_identity, fg_color="#202020", corner_radius=12)
        card_in.grid(row=1, column=0, padx=30, pady=(0, 15), sticky="new")
        card_in.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(card_in, text="Target Username", font=self.font_body, text_color="gray70").grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")
        self.entry_username = ctk.CTkEntry(card_in, height=45, placeholder_text="e.g., zeros-codexd", fg_color="#121212")
        self.entry_username.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="ew")
        
        self.btn_hunt = ctk.CTkButton(card_in, text="Launch Scan", width=180, height=45, fg_color="#8A2BE2", hover_color="#6A1B9A", font=ctk.CTkFont(weight="bold"), command=self.start_hunter_thread)
        self.btn_hunt.grid(row=1, column=1, padx=20, pady=(5, 20), sticky="e")

        self.scroll_results = ctk.CTkScrollableFrame(self.view_identity, fg_color="#202020", corner_radius=12)
        self.scroll_results.grid(row=2, column=0, padx=30, pady=(0, 0), sticky="nsew")
        self.view_identity.grid_rowconfigure(2, weight=1)

    def _build_deepintel_view(self):
        self.view_deepintel = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.view_deepintel.grid_columnconfigure(0, weight=1)
        self.view_deepintel.grid_columnconfigure(1, weight=1)
        self.view_deepintel.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.view_deepintel, text="Deep Intel Forensics", font=self.font_h1, anchor="w").grid(row=0, column=0, columnspan=2, padx=30, pady=(30, 20), sticky="ew")

        # ---------------------------------------------
        # MODULE 1: EXIF Forensics (Left Card)
        # ---------------------------------------------
        card_exif = ctk.CTkFrame(self.view_deepintel, fg_color="#202020", corner_radius=12)
        card_exif.grid(row=1, column=0, padx=(30, 15), pady=(0, 0), sticky="nsew")
        card_exif.grid_rowconfigure(3, weight=1)
        
        ctk.CTkLabel(card_exif, text="Image Metadata Stripper", font=self.font_h2).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        # EXIF Controls
        exif_controls = ctk.CTkFrame(card_exif, fg_color="transparent")
        exif_controls.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        exif_controls.grid_columnconfigure(0, weight=1)
        
        self.lbl_img_path = ctk.CTkEntry(exif_controls, placeholder_text="No image selected...", fg_color="#121212", state="disabled")
        self.lbl_img_path.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.btn_sel_img = ctk.CTkButton(exif_controls, text="Select Image", width=100, command=self.select_image_file)
        self.btn_sel_img.grid(row=0, column=1)

        self.btn_exif_scan = ctk.CTkButton(card_exif, text="Extract EXIF Data", fg_color="#D84315", hover_color="#BF360C", command=self.run_exif_scan)
        self.btn_exif_scan.grid(row=2, column=0, padx=20, pady=(10, 15), sticky="ew")
        
        self.txt_exif_out = ctk.CTkTextbox(card_exif, fg_color="#121212", border_color="#333", border_width=1)
        self.txt_exif_out.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="nsew")
        
        self.btn_open_map = ctk.CTkButton(card_exif, text="Open Embedded GPS in Maps", fg_color="#008A00", hover_color="#006A00", state="disabled", command=lambda: webbrowser.open(self.current_maps_link))
        self.btn_open_map.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        # ---------------------------------------------
        # MODULE 2: Archive Recon (Right Card)
        # ---------------------------------------------
        card_arc = ctk.CTkFrame(self.view_deepintel, fg_color="#202020", corner_radius=12)
        card_arc.grid(row=1, column=1, padx=(15, 30), pady=(0, 0), sticky="nsew")
        card_arc.grid_rowconfigure(4, weight=1)
        
        ctk.CTkLabel(card_arc, text="Wayback Machine Recon", font=self.font_h2).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.entry_arc_url = ctk.CTkEntry(card_arc, placeholder_text="Enter target URL (e.g., example.com)", fg_color="#121212")
        self.entry_arc_url.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="ew")
        
        self.btn_arc_scan = ctk.CTkButton(card_arc, text="Fetch History", fg_color="#006064", hover_color="#004D40", command=self.start_wayback_thread)
        self.btn_arc_scan.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.txt_arc_out = ctk.CTkTextbox(card_arc, fg_color="#121212", border_color="#333", border_width=1)
        self.txt_arc_out.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="nsew")

        # Buttons to launch the links in browser
        arc_links_frame = ctk.CTkFrame(card_arc, fg_color="transparent")
        arc_links_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="s ew")
        arc_links_frame.grid_columnconfigure(0, weight=1)
        arc_links_frame.grid_columnconfigure(1, weight=1)
        
        self.btn_arc_old = ctk.CTkButton(arc_links_frame, text="View Oldest", state="disabled")
        self.btn_arc_old.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.btn_arc_new = ctk.CTkButton(arc_links_frame, text="View Newest", state="disabled")
        self.btn_arc_new.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def _build_console(self):
        self.console_frame = ctk.CTkFrame(self, height=180, fg_color="#181818", corner_radius=0)
        self.console_frame.grid(row=1, column=1, sticky="nsew")
        self.console_frame.grid_rowconfigure(1, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)
        
        hdr = ctk.CTkFrame(self.console_frame, fg_color="#101010", height=30, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="  SYSTEM LOGS / STDOUT", text_color="gray50", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", pady=2)
        
        self.console_text = ctk.CTkTextbox(self.console_frame, fg_color="#0C0C0C", text_color="#00FF00", font=ctk.CTkFont(family="Consolas", size=12), border_width=0, corner_radius=0)
        self.console_text.grid(row=1, column=0, sticky="nsew")
        self.console_text.configure(state="disabled")

    def select_frame_by_name(self, name):
        self.btn_nav_scraper.configure(fg_color=("gray75", "gray25") if name == "scraper" else "transparent")
        self.btn_nav_identity.configure(fg_color=("gray75", "gray25") if name == "identity" else "transparent")
        self.btn_nav_deepintel.configure(fg_color=("gray75", "gray25") if name == "deepintel" else "transparent")
        
        for view in[self.view_scraper, self.view_identity, self.view_deepintel]:
            view.grid_forget()
            
        if name == "scraper": self.view_scraper.grid(row=0, column=0, sticky="nsew")
        elif name == "identity": self.view_identity.grid(row=0, column=0, sticky="nsew")
        elif name == "deepintel": self.view_deepintel.grid(row=0, column=0, sticky="nsew")

    # ==========================================
    # ACTION HANDLERS
    # ==========================================

    def start_harvester_thread(self):
        urls =[u.strip() for u in self.url_textbox.get("0.0", "end").strip().split('\n') if u.strip()]
        if not urls: return
        self.btn_harvest.configure(state="disabled")
        threading.Thread(target=self._run_async_harvester, args=(urls,), daemon=True).start()

    def _run_async_harvester(self, urls):
        engine = AsyncEngine()
        results = asyncio.run(engine.execute_batch(urls))
        self.scraper_results = results
        self.after(0, lambda: self.btn_harvest.configure(state="normal"))
        self.after(0, lambda: self.btn_export.configure(state="normal"))
        self.after(0, lambda: self.lbl_stat_targets.configure(text=f"Targets Processed: {len(results)}"))

    def export_csv(self):
        if self.scraper_results:
            PayloadExporter.export_to_csv(self.scraper_results, "nexus_output.csv")

    def start_hunter_thread(self):
        username = self.entry_username.get().strip()
        if not username: return
        self.btn_hunt.configure(state="disabled")
        for w in self.scroll_results.winfo_children(): w.destroy()
        threading.Thread(target=self._run_async_hunter, args=(username,), daemon=True).start()

    def _run_async_hunter(self, username):
        results = asyncio.run(IdentityMatrix.scan_username(username))
        
        def update_ui():
            for p in results["Found"]: self._create_id_row(p, "FOUND")
            for p in results["Not Found"]: self._create_id_row(p, "NOT FOUND")
            for p in results["Error"]: self._create_id_row(p, "ERROR")
            self.btn_hunt.configure(state="normal")
        self.after(0, update_ui)

    def _create_id_row(self, platform, status):
        card = ctk.CTkFrame(self.scroll_results, fg_color="#2A2A2A", corner_radius=8, height=40)
        card.pack(fill="x", padx=10, pady=5)
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=platform, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15)
        
        colors = {"FOUND": ("#004D00", "#00FF00"), "NOT FOUND": ("#4D0000", "#FF4C4C"), "ERROR": ("#4D4D00", "#FFFF00")}
        bg, fg = colors.get(status)
        ctk.CTkLabel(card, text=f" {status} ", fg_color=bg, text_color=fg, corner_radius=6).pack(side="right", padx=15, pady=5)

    # --- DEEP INTEL HANDLERS ---
    
    def select_image_file(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tiff")])
        if path:
            self.selected_image_path = path
            self.lbl_img_path.configure(state="normal")
            self.lbl_img_path.delete(0, "end")
            self.lbl_img_path.insert(0, path)
            self.lbl_img_path.configure(state="disabled")

    def run_exif_scan(self):
        if not self.selected_image_path:
            logger.warning("No image selected for EXIF parsing.")
            return
            
        logger.info(f"Stripping EXIF data from: {self.selected_image_path}")
        result = ExifForensics.extract_metadata(self.selected_image_path)
        
        self.txt_exif_out.configure(state="normal")
        self.txt_exif_out.delete("0.0", "end")
        
        if result["error"]:
            self.txt_exif_out.insert("end", f"[!] {result['error']}\n")
            self.current_maps_link = None
            self.btn_open_map.configure(state="disabled")
        else:
            self.txt_exif_out.insert("end", "--- RAW METADATA STRIPPED ---\n\n")
            for k, v in result["raw_data"].items():
                self.txt_exif_out.insert("end", f"{k}: {v}\n")
                
            self.current_maps_link = result["maps_link"]
            if self.current_maps_link:
                self.btn_open_map.configure(state="normal")
                logger.info("GPS Location embedded in image. Map link prepared.")
            else:
                self.btn_open_map.configure(state="disabled")
                
        self.txt_exif_out.configure(state="disabled")

    def start_wayback_thread(self):
        url = self.entry_arc_url.get().strip()
        if not url: return
        
        self.btn_arc_scan.configure(state="disabled")
        self.btn_arc_old.configure(state="disabled")
        self.btn_arc_new.configure(state="disabled")
        
        self.txt_arc_out.configure(state="normal")
        self.txt_arc_out.delete("0.0", "end")
        self.txt_arc_out.insert("end", f"Scanning Internet Archive for: {url}...\n\n")
        self.txt_arc_out.configure(state="disabled")
        
        threading.Thread(target=self._run_async_wayback, args=(url,), daemon=True).start()

    def _run_async_wayback(self, url):
        logger.info(f"Initiating Wayback Recon for {url}")
        results = asyncio.run(ArchiveRecon.fetch_history(url))
        
        def update_ui():
            self.txt_arc_out.configure(state="normal")
            self.txt_arc_out.delete("0.0", "end")
            
            if results["error"]:
                self.txt_arc_out.insert("end", f"[!] {results['error']}\n")
            else:
                self.txt_arc_out.insert("end", "[+] ARCHIVE SNAPSHOTS FOUND\n\n")
                self.txt_arc_out.insert("end", f"Oldest Record:\n{results['oldest']}\n\n")
                self.txt_arc_out.insert("end", f"Newest Record:\n{results['newest']}\n")
                
                if results['oldest']:
                    self.btn_arc_old.configure(state="normal", command=lambda: webbrowser.open(results['oldest']))
                if results['newest']:
                    self.btn_arc_new.configure(state="normal", command=lambda: webbrowser.open(results['newest']))
                    
            self.txt_arc_out.configure(state="disabled")
            self.btn_arc_scan.configure(state="normal")
            logger.info("Wayback Recon cycle completed.")
            
        self.after(0, update_ui)

if __name__ == "__main__":
    app = NexusApp()
    app.mainloop()