import sys
sys.path.append(r"E:\SEMESTER\Python scrapper\Packages")
import threading
import ssl
from pathlib import Path
import aiofiles
from typing import List, Dict
import time
from bs4 import BeautifulSoup
import random
import os
import csv
import asyncio
import aiohttp
from tkinter import ttk, scrolledtext, messagebox, filedialog
import tkinter as tk
import subprocess
import itertools
from PIL import Image, ImageTk # Import Pillow for icons
import datetime
import concurrent.futures

class NeurIPSScraper(tk.Tk):

    PRIMARY_COLOR = '#2980B9'  # Softer Blue
    SECONDARY_COLOR = '#3498DB' # Slightly lighter Blue
    BACKGROUND_COLOR = '#F0F0F0' # Light Gray Background
    ACCENT_COLOR = '#1ABC9C'   # Teal Accent for buttons/highlights
    TEXT_COLOR = '#000000'     # Dark Text - Changed to Black for visibility
    HEADER_FONT = ('Segoe UI', 24, 'bold') # Modern font
    LABEL_FONT = ('Segoe UI', 11)
    BUTTON_FONT = ('Segoe UI', 12, 'bold')
    ENTRY_FONT = ('Segoe UI', 11)
    TREEVIEW_FONT = ('Segoe UI', 10)
    LOG_FONT = ('Consolas', 10) # Monospace font for logs

    CSV_OUTPUT_FILE = 'pdf_metadata_output.csv'

    def __init__(self):
        super().__init__()
        self.title("NeurIPS Paper Scraper")
        self.configure(bg=self.BACKGROUND_COLOR)
        self.state('zoomed')
        self.metadata_list = []
        self.create_styles()
        self.initialize_gui()

    def create_styles(self):
        style = ttk.Style()
        style.theme_use('vista')

        style.configure('TFrame', background=self.BACKGROUND_COLOR)
        style.configure('TLabelFrame', background=self.BACKGROUND_COLOR,
                        foreground=self.TEXT_COLOR, font=self.LABEL_FONT, borderwidth=2, relief='groove')
        style.configure('TLabel', background=self.BACKGROUND_COLOR,
                        foreground=self.TEXT_COLOR, font=self.LABEL_FONT)
        style.configure('Header.TLabel', font=self.HEADER_FONT,
                        foreground=self.PRIMARY_COLOR, background=self.BACKGROUND_COLOR)
        style.configure('TEntry', fieldbackground='white', foreground=self.TEXT_COLOR, font=self.ENTRY_FONT)
        style.configure('TButton',
                        background=self.ACCENT_COLOR,
                        foreground=self.TEXT_COLOR,
                        font=self.BUTTON_FONT,
                        borderwidth=0,
                        padding=(10, 8),
                        relief='raised')

        style.map('TButton',
                  background=[('active', self.SECONDARY_COLOR), ('pressed', self.PRIMARY_COLOR)])
        style.configure('TCombobox', fieldbackground='white', foreground=self.TEXT_COLOR, font=self.ENTRY_FONT)
        style.configure("Treeview",
                        background="white",
                        foreground=self.TEXT_COLOR,
                        fieldbackground="white",
                        font=self.TREEVIEW_FONT)
        style.configure("Treeview.Heading",
                        background=self.PRIMARY_COLOR,
                        foreground="white",
                        font=self.BUTTON_FONT)
        style.configure('TCheckbutton', background=self.BACKGROUND_COLOR, foreground=self.TEXT_COLOR, font=self.LABEL_FONT)

        style.configure('Vertical.TScrollbar', background=self.BACKGROUND_COLOR, bordercolor=self.BACKGROUND_COLOR, arrowcolor=self.TEXT_COLOR)
        style.configure('Horizontal.TScrollbar', background=self.BACKGROUND_COLOR, bordercolor=self.BACKGROUND_COLOR, arrowcolor=self.TEXT_COLOR)

    def initialize_gui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header_frame = ttk.Frame(self, padding=20)
        header_frame.grid(row=0, column=0, columnspan=2, sticky='ew')
        header_frame.columnconfigure(0, weight=1)
        title_label = ttk.Label(header_frame, text="NeurIPS Paper Scraper", style='Header.TLabel')
        title_label.grid(row=0, column=0, sticky='ew')

        separator = ttk.Separator(header_frame, orient='horizontal')
        separator.grid(row=1, column=0, columnspan=3, sticky='ew', pady=10)

        paned_window = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned_window.grid(row=1, column=0, sticky='nsew', padx=20, pady=10)

        sidebar_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(sidebar_frame, weight=1)

        options_frame = ttk.LabelFrame(sidebar_frame, text="Scraping Options", padding=10)
        options_frame.grid(row=0, column=0, sticky='new', pady=(0, 10), padx=10)

        year_frame = ttk.Frame(options_frame)
        year_frame.pack(fill=tk.X, pady=5)
        ttk.Label(year_frame, text="Year Range:", style='TLabel').pack(side=tk.LEFT, padx=5)
        year_start_frame = ttk.Frame(year_frame)
        year_start_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(year_start_frame, text="Start:", style='TLabel').pack(side=tk.LEFT)
        self.start_year = ttk.Combobox(year_start_frame, values=list(range(1990, time.localtime().tm_year + 1)), width=5, state='readonly', font=self.ENTRY_FONT)
        self.start_year.set("2018")
        self.start_year.pack(side=tk.LEFT)
        year_end_frame = ttk.Frame(year_frame)
        year_end_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(year_end_frame, text="End:", style='TLabel').pack(side=tk.LEFT)
        self.end_year = ttk.Combobox(year_end_frame, values=list(range(1990, time.localtime().tm_year + 1)), width=5, state='readonly', font=self.ENTRY_FONT)
        self.end_year.set("2024")
        self.end_year.pack(side=tk.LEFT)


        dir_frame = ttk.Frame(options_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dir_frame, text="Download Directory:", style='TLabel').grid(row=0, column=0, padx=5, sticky=tk.W)
        self.download_dir = ttk.Entry(dir_frame, font=self.ENTRY_FONT)
        self.download_dir.insert(0, "Scrapped_PDFs")
        self.download_dir.grid(row=0, column=1, padx=5, sticky=tk.EW)
        browse_button = ttk.Button(dir_frame, text="Browse", command=self.browse_directory, style='TButton')
        browse_button.grid(row=0, column=2, padx=5, sticky=tk.E)
        dir_frame.columnconfigure(1, weight=1)


        buttons_frame = ttk.Frame(sidebar_frame, padding=10)
        buttons_frame.grid(row=2, column=0, sticky='ew', pady=(0, 10), padx=10)
        buttons_frame.columnconfigure(0, weight=1)

        self.scrape_button = ttk.Button(buttons_frame, text="Scrape Metadata", command=self.scrape_metadata, style='TButton')
        self.scrape_button.grid(row=0, column=0, sticky='ew', pady=5)
        self.download_button = ttk.Button(buttons_frame, text="Download PDFs", command=self.download_pdfs, style='TButton')
        self.download_button.grid(row=1, column=0, sticky='ew', pady=5)


        content_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(content_frame, weight=3)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        columns = ("Title", "Authors", "Year", "PDF Link")
        self.tree = ttk.Treeview(content_frame, columns=columns, show='headings', style='Treeview')
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "Title":
                self.tree.column(col, width=400)
            elif col == "Authors":
                self.tree.column(col, width=300)
            elif col == "Year":
                self.tree.column(col, width=80, anchor='center')
            else:
                self.tree.column(col, width=250)

        vsb = ttk.Scrollbar(content_frame, orient="vertical", command=self.tree.yview, style='Vertical.TScrollbar')
        hsb = ttk.Scrollbar(content_frame, orient="horizontal", command=self.tree.xview, style='Horizontal.TScrollbar')
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')


        footer_frame = ttk.Frame(self, padding=20)
        footer_frame.grid(row=2, column=0, columnspan=2, sticky='ew')
        footer_frame.columnconfigure(1, weight=1)

        progress_label = ttk.Label(footer_frame, text="Progress:", style='TLabel')
        progress_label.grid(row=0, column=0, sticky='nw', padx=(0, 10), pady=(0, 5))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(footer_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.grid(row=0, column=1, sticky='ew', pady=(0, 5))

        stats_area = ttk.Frame(footer_frame)
        stats_area.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(5, 10))
        self.stats_labels = {}
        stats_columns = [("Total", "total_papers"), ("Downloaded", "downloaded"),
                         ("Failed", "failed_download"), ("Skipped", "skipped")]
        for i, (label_text, var_name) in enumerate(stats_columns):
            ttk.Label(stats_area, text=f"{label_text}:", background=self.BACKGROUND_COLOR, foreground=self.TEXT_COLOR, font=self.LABEL_FONT).grid(row=0, column=i*2, padx=(10,2), sticky='e')
            self.stats_labels[var_name] = ttk.Label(stats_area, text="0", background=self.BACKGROUND_COLOR, foreground=self.TEXT_COLOR, font=self.LABEL_FONT)
            self.stats_labels[var_name].grid(row=0, column=i*2 + 1, padx=(2, 10), sticky='w')

        log_label = ttk.Label(footer_frame, text="Log:", style='TLabel')
        log_label.grid(row=2, column=0, sticky='nw', padx=(0, 10), pady=(0, 0))
        self.log_area = scrolledtext.ScrolledText(footer_frame, height=6, bg='white',
                                                    fg=self.TEXT_COLOR, font=self.LOG_FONT, wrap=tk.WORD, borderwidth=1, relief='solid')
        self.log_area.grid(row=2, column=1, sticky='nsew')


    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=os.getcwd(), title="Select PDF Download Directory")
        if directory:
            self.download_dir.delete(0, tk.END)
            self.download_dir.insert(0, directory)

    def log(self, message: str):
        self.log_area.insert(tk.END, f"{message}\n")
        self.log_area.see(tk.END)

    async def download_pdf(self, session: aiohttp.ClientSession, pdf_url: str, destination_path: str, paper_title: str, paper_year: str):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        ]
        headers = {'User-Agent': random.choice(user_agents)}

        try:
            async with session.get(pdf_url, headers=headers, timeout=60) as response: # Added timeout to session.get
                if response.status == 200:
                    async with aiofiles.open(destination_path, 'wb') as f:
                        await f.write(await response.read())
                    return True
                else:
                    self.log(f"Failed to download {pdf_url}: HTTP {response.status}")
                    return False
        except asyncio.TimeoutError:
            self.log(f"Download timed out: {pdf_url}")
            return False
        except Exception as e:
            self.log(f"Error downloading {pdf_url}: {str(e)}")
            return False

    async def scrape_year(self, session: aiohttp.ClientSession, year: int) -> List[Dict]:
        if year < 2019:
            base_url = f"https://papers.nips.cc/paper/{year}"
            pdf_base = f"https://papers.nips.cc/paper_files/paper/{year}/file"
        else:
            base_url = f"https://proceedings.neurips.cc/paper/{year}"
            pdf_base = f"https://proceedings.neurips.cc/paper/{year}/file"

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        ]
        headers = {'User-Agent': random.choice(user_agents)}
        papers = []
        try:
            async with session.get(base_url, headers=headers, timeout=60) as response: # Added timeout to session.get
                if response.status != 200:
                    self.log(f"Failed to fetch year {year}: HTTP {response.status}")
                    return papers

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                paper_links = soup.select("a[title='paper title']")

                for paper_link in paper_links:
                    try:
                        title = paper_link.text.strip()
                        authors_tag = paper_link.find_next('i')
                        authors = authors_tag.text.strip() if authors_tag else ""
                        abstract_url = paper_link.get('href', '')
                        if 'Abstract' in abstract_url:
                            paper_hash = abstract_url.split('/')[-1].replace('-Abstract.html', '')
                            pdf_link = f"{pdf_base}/{paper_hash}-Paper.pdf"
                            papers.append({
                                'title': title,
                                'authors': authors,
                                'year': str(year),
                                'pdf_link': pdf_link,
                            })
                    except Exception as e:
                        self.log(f"Error processing paper: {str(e)}")
                self.log(f"Year {year}: {len(papers)} papers saved in metadata.")
        except asyncio.TimeoutError:
            self.log(f"Scraping year {year} timed out.")
        except Exception as e:
            self.log(f"Error scraping year {year}: {str(e)}")
        return papers

    async def scrape_metadata_async(self):
        start_year = int(self.start_year.get())
        end_year = int(self.end_year.get())
        years_to_scrape = range(start_year, end_year + 1)

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector, timeout=None) as session: # Removed default timeout from session
            tasks = [self.scrape_year(session, year) for year in years_to_scrape] # Run tasks concurrently with gather
            results = await asyncio.gather(*tasks)
            all_papers = list(itertools.chain.from_iterable(results)) # Flatten list of lists

        csv_path = Path(NeurIPSScraper.CSV_OUTPUT_FILE)
        if not csv_path.exists():
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'authors', 'year', 'pdf_link'])
                writer.writeheader()
                writer.writerows(all_papers)
        return all_papers


    async def download_pdfs_async(self):
        download_dir = Path(self.download_dir.get())
        download_dir.mkdir(exist_ok=True)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            total = len(self.metadata_list)
            self.update_stats(total_papers=total, downloaded=0, failed_download=0, skipped=0)
            skipped_count = 0
            failed_count = 0
            downloaded_count = 0

            for i, paper in enumerate(self.metadata_list, 1):
                title = ''.join(c if c.isalnum() else '_' for c in paper['title'])
                path = download_dir / f"{title}_{paper['year']}.pdf"

                if path.exists():
                    self.log(f"Skipping existing: {title} ({paper['year']})")
                    skipped_count += 1
                    self.update_stats(skipped=skipped_count)
                else:
                    self.log(f"Downloading: {title} ({paper['year']})")
                    success = await self.download_pdf(session, paper['pdf_link'], str(path), paper['title'], paper['year'])
                    if success:
                        downloaded_count += 1
                        self.update_stats(downloaded=downloaded_count)
                    else:
                        failed_count += 1
                        self.update_stats(failed_download=failed_count)
                progress = (i / total) * 100
                self.progress_var.set(progress)

            self.after(0, lambda: self.update_stats(total_papers=total, downloaded=downloaded_count, failed_download=failed_count, skipped=skipped_count))

    def scrape_metadata(self):
        self.scrape_button.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        self.progress_var.set(0)
        self.metadata_list = []
        self.update_stats(total_papers=0)

        def run_scrape():
            start_time = time.time()
            papers = asyncio.run(self.scrape_metadata_async())
            elapsed_time = time.time() - start_time
            self.after(0, self.finish_scrape, papers, elapsed_time)
        threading.Thread(target=run_scrape, daemon=True).start()

    def finish_scrape(self, papers, elapsed_time):
        self.metadata_list = papers
        total_papers_count = len(papers)
        for paper in papers:
            self.tree.insert('', tk.END, values=(paper['title'], paper['authors'], paper['year'], paper['pdf_link']))
        self.update_stats(total_papers=total_papers_count)
        self.scrape_button.config(state=tk.NORMAL)
        messagebox.showinfo("Scraping Complete",
                            f"Scraped {total_papers_count} papers\nTotal time: {elapsed_time:.2f} seconds")

    def download_pdfs(self):
        self.download_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        def run_download():
            if not self.metadata_list:
                csv_path = Path(NeurIPSScraper.CSV_OUTPUT_FILE)
                if csv_path.exists():
                    self.log("Loading metadata from existing CSV...")
                    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        papers = list(reader)
                    self.metadata_list = papers
                    for paper in papers:
                        self.tree.insert('', tk.END, values=(paper['title'], paper['authors'], paper['year'], paper['pdf_link']))
                else:
                    self.log("No metadata found. Scraping metadata now...")
                    start_time = time.time()
                    papers = asyncio.run(self.scrape_metadata_async())
                    elapsed_time = time.time() - start_time
                    self.after(0, self.finish_scrape, papers, elapsed_time)
            asyncio.run(self.download_pdfs_async())
            self.after(0, self.finish_download)
        threading.Thread(target=run_download, daemon=True).start()

    def finish_download(self):
        self.download_button.config(state=tk.NORMAL)
        messagebox.showinfo("Download Complete", "PDF Download Complete")


    def update_stats(self, total_papers=None, downloaded=None, failed_download=None, skipped=None):
        if total_papers is not None:
            self.stats_labels['total_papers'].config(text=str(total_papers))
        if downloaded is not None:
            self.stats_labels['downloaded'].config(text=str(downloaded))
        if failed_download is not None:
            self.stats_labels['failed_download'].config(text=str(failed_download))
        if skipped is not None:
            self.stats_labels['skipped'].config(text=str(skipped))

app = NeurIPSScraper()
app.mainloop()
