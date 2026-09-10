import flet as ft
import flet_audio
import flet_audio as fta
import sqlite3
import random
import urllib.parse
import time
import threading
import os
import tempfile
import shutil

def get_db_path():
    base_dir = os.path.dirname(__file__)
    bundled_db = os.path.join(base_dir, "vocab.db")
    home_dir = os.path.expanduser("~")
    writable_db = os.path.join(home_dir, "vocab.db")
    
    if not os.path.exists(writable_db):
        try:
            shutil.copy2(bundled_db, writable_db)
        except Exception:
            pass
            
    if os.access(writable_db, os.W_OK):
        return writable_db
    return bundled_db

DB_PATH = get_db_path()

def get_words():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, word, meaning, example FROM words ORDER BY id DESC")
    words = cursor.fetchall()
    conn.close()
    return words

def main(page: ft.Page):
    page.title = "Vocab AI Mobile"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400
    page.window_height = 800
    page.padding = 0

    is_mobile_or_web = page.web or page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
    audio_player = None
    if is_mobile_or_web:
        try:
            audio_player = fta.Audio(autoplay=False)
            page.add(audio_player)
        except:
            pass

    def play_sound(text, lang="en"):
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(text)}&tl={lang}&client=tw-ob"
        if audio_player:
            audio_player.src = url
            page.update()
            audio_player.play()
        else:
            # Desktop fallback using pygame
            def _play():
                try:
                    import pygame
                    import urllib.request
                    pygame.mixer.init()
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        data = response.read()
                    temp_path = os.path.join(tempfile.gettempdir(), f"vocab_tts_{random.randint(1,10000)}.mp3")
                    with open(temp_path, "wb") as f:
                        f.write(data)
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                except Exception as e:
                    print("Lỗi phát âm thanh:", e)
            threading.Thread(target=_play, daemon=True).start()

    all_words = get_words()

    # --- 1. VIEW VOCAB ---
    list_view = ft.ListView(expand=True, spacing=10, padding=20)
    def load_list():
        list_view.controls.clear()
        for w in all_words:
            list_view.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=15,
                        content=ft.Row([
                            ft.Column([
                                ft.Text(w[1], size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                                ft.Text(w[2], size=16),
                                ft.Text(f"VD: {w[3]}", size=14, color=ft.Colors.GREY_600, italic=True) if w[3] else ft.Container(),
                            ], expand=True),
                            ft.IconButton(icon=ft.Icons.VOLUME_UP, on_click=lambda e, word=w[1]: play_sound(word, "en"))
                        ])
                    )
                )
            )
    load_list()
    view_vocab = ft.Column([
        ft.Container(content=ft.Text("Danh sách Từ vựng", size=24, weight=ft.FontWeight.BOLD), padding=20),
        list_view
    ], expand=True)

    # --- 2. VIEW FLASHCARD ---
    flashcard_idx = [0]
    is_front = [True]
    
    lbl_card_text = ft.Text(size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    lbl_card_sub = ft.Text(size=16, text_align=ft.TextAlign.CENTER, color=ft.Colors.GREY_700)
    
    def update_card():
        if not all_words: return
        w = all_words[flashcard_idx[0]]
        if is_front[0]:
            lbl_card_text.value = w[1]
            lbl_card_text.color = ft.Colors.BLUE_900
            lbl_card_sub.value = ""
        else:
            lbl_card_text.value = w[2]
            lbl_card_text.color = ft.Colors.PINK_600
            lbl_card_sub.value = w[3]
        page.update()

    def flip_card(e):
        is_front[0] = not is_front[0]
        update_card()

    def next_card(e):
        flashcard_idx[0] = (flashcard_idx[0] + 1) % len(all_words)
        is_front[0] = True
        update_card()

    def prev_card(e):
        flashcard_idx[0] = (flashcard_idx[0] - 1) % len(all_words)
        is_front[0] = True
        update_card()
        
    def play_flashcard_audio(e):
        w = all_words[flashcard_idx[0]]
        if is_front[0]:
            play_sound(w[1], "en")
        else:
            play_sound(w[2], "vi")

    card_container = ft.GestureDetector(
        on_tap=flip_card,
        content=ft.Card(
            elevation=5,
            content=ft.Container(
                width=320, height=250,
                alignment=ft.Alignment(0, 0),
                padding=20,
                content=ft.Column(
                    [lbl_card_text, lbl_card_sub],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
        )
    )

    view_flashcard = ft.Column([
        ft.Container(content=ft.Text("Học Flashcard", size=24, weight=ft.FontWeight.BOLD), padding=20),
        ft.Row([card_container], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=20),
        ft.Row([
            ft.FilledButton(content=ft.Text("⬅"), on_click=prev_card),
            ft.FilledButton(content=ft.Text("🔄"), on_click=flip_card, bgcolor=ft.Colors.ORANGE_400),
            ft.IconButton(icon=ft.Icons.VOLUME_UP, on_click=play_flashcard_audio, bgcolor=ft.Colors.GREEN_100, icon_color=ft.Colors.GREEN_900),
            ft.FilledButton(content=ft.Text("➡"), on_click=next_card),
        ], alignment=ft.MainAxisAlignment.CENTER)
    ], expand=True, visible=False)
    
    update_card()

    # --- 3. VIEW GAMES HUB ---
    view_games = ft.Column(expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
    
    def back_to_menu(e=None):
        build_games_menu()
        page.update()

    # --- QUIZ GAME ---
    quiz_score = [0]
    quiz_current = [None]
    quiz_options = []
    lbl_quiz_question = ft.Text(size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800, text_align=ft.TextAlign.CENTER)
    lbl_quiz_feedback = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    btn_options = [ft.FilledButton(content=ft.Text(""), on_click=lambda e, i=i: check_quiz(i), width=300) for i in range(4)]
    
    def next_quiz():
        if len(all_words) < 4: return
        quiz_current[0] = random.choice(all_words)
        lbl_quiz_question.value = quiz_current[0][1]
        
        wrongs = random.sample([w for w in all_words if w[0] != quiz_current[0][0]], 3)
        options = [quiz_current[0]] + wrongs
        random.shuffle(options)
        
        quiz_options.clear()
        quiz_options.extend(options)
        
        for i, opt in enumerate(options):
            btn_options[i].content.value = opt[2][:40] + "..." if len(opt[2])>40 else opt[2]
            btn_options[i].bgcolor = None
            
        lbl_quiz_feedback.value = f"Điểm: {quiz_score[0]}"
        lbl_quiz_feedback.color = ft.Colors.BLACK
        page.update()

    def check_quiz(idx):
        if not quiz_current[0]: return
        selected = quiz_options[idx]
        if selected[0] == quiz_current[0][0]:
            quiz_score[0] += 10
            lbl_quiz_feedback.value = f"Chính xác! (+10đ) | Tổng: {quiz_score[0]}"
            lbl_quiz_feedback.color = ft.Colors.GREEN
            btn_options[idx].bgcolor = ft.Colors.GREEN_400
            play_sound("Chính xác", "vi")
            page.update()
            def _next():
                time.sleep(0.5)
                next_quiz()
            threading.Thread(target=_next, daemon=True).start()
        else:
            lbl_quiz_feedback.value = "Sai rồi! Hãy thử lại."
            lbl_quiz_feedback.color = ft.Colors.RED
            btn_options[idx].bgcolor = ft.Colors.RED_400
            play_sound("Sai rồi", "vi")
            page.update()

    def start_quiz():
        if len(all_words) < 4: return
        quiz_score[0] = 0
        view_games.controls.clear()
        view_games.controls.append(
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=back_to_menu),
                ft.Text("Trắc Nghiệm", size=20, weight=ft.FontWeight.BOLD)
            ])
        )
        view_games.controls.append(ft.Container(content=lbl_quiz_question, padding=20, alignment=ft.Alignment(0,0)))
        view_games.controls.append(ft.Column(btn_options, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        view_games.controls.append(ft.Container(content=lbl_quiz_feedback, padding=20, alignment=ft.Alignment(0,0)))
        next_quiz()
        page.update()

    # --- MATCH GAME (WORD & AUDIO) ---
    match_state = {"mode": "word", "selected_a": None, "selected_b": None, "completed": 0}

    def start_match_game(mode="word"):
        match_state["mode"] = mode
        match_state["selected_a"] = None
        match_state["selected_b"] = None
        match_state["completed"] = 0
        
        if len(all_words) < 5:
            return
            
        words = random.sample(all_words, 5)
        list_a = [{"id": w[0], "text": w[1], "type": "a", "control": None} for w in words]
        list_b = [{"id": w[0], "text": w[2], "type": "b", "control": None} for w in words]
        
        random.shuffle(list_a)
        random.shuffle(list_b)

        view_games.controls.clear()
        
        lbl_match_feedback = ft.Text(size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
        
        view_games.controls.append(
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=back_to_menu),
                ft.Text("Ghép Từ" if mode=="word" else "Luyện Nghe", size=20, weight=ft.FontWeight.BOLD)
            ])
        )
        view_games.controls.append(ft.Container(content=lbl_match_feedback, padding=5, alignment=ft.Alignment(0,0)))

        col_a = ft.Column(spacing=10, expand=1)
        col_b = ft.Column(spacing=10, expand=1)

        def on_match_click(item, btn):
            if item["type"] == "a":
                if match_state["mode"] == "audio":
                    play_sound(item["text"], "en")
                if match_state["selected_a"]:
                    match_state["selected_a"]["control"].bgcolor = ft.Colors.BLUE_50
                match_state["selected_a"] = item
                btn.bgcolor = ft.Colors.BLUE_200
            else:
                if match_state["selected_b"]:
                    match_state["selected_b"]["control"].bgcolor = ft.Colors.BLUE_50
                match_state["selected_b"] = item
                btn.bgcolor = ft.Colors.BLUE_200
            
            page.update()

            if match_state["selected_a"] and match_state["selected_b"]:
                a = match_state["selected_a"]
                b = match_state["selected_b"]
                
                # Check match
                def resolve_match():
                    if a["id"] == b["id"]:
                        lbl_match_feedback.value = "Chính xác!"
                        lbl_match_feedback.color = ft.Colors.GREEN
                        play_sound("Chính xác", "vi")
                        a["control"].visible = False
                        b["control"].visible = False
                        match_state["completed"] += 1
                        if match_state["completed"] == 5:
                            view_games.controls.append(
                                ft.Column([
                                    ft.Container(height=20),
                                    ft.Text("Tuyệt vời! Bạn đã ghép đúng hết!", color=ft.Colors.GREEN, size=20, weight=ft.FontWeight.BOLD),
                                    ft.FilledButton(content=ft.Text("Chơi ván mới"), on_click=lambda e: start_match_game(match_state["mode"]))
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                            )
                    else:
                        lbl_match_feedback.value = "Sai rồi! Hãy chọn lại."
                        lbl_match_feedback.color = ft.Colors.RED
                        play_sound("Sai rồi", "vi")
                        a["control"].bgcolor = ft.Colors.RED_400
                        b["control"].bgcolor = ft.Colors.RED_400
                        page.update()
                        time.sleep(0.5)
                        lbl_match_feedback.value = ""
                        if a["control"].visible: a["control"].bgcolor = ft.Colors.BLUE_50
                        if b["control"].visible: b["control"].bgcolor = ft.Colors.BLUE_50
                    match_state["selected_a"] = None
                    match_state["selected_b"] = None
                    page.update()
                
                threading.Thread(target=resolve_match, daemon=True).start()

        for item in list_a:
            if mode == "word":
                btn = ft.Container(content=ft.Text(item["text"], text_align=ft.TextAlign.CENTER, size=16), 
                                   bgcolor=ft.Colors.BLUE_50, padding=15, border_radius=10, alignment=ft.Alignment(0,0),
                                   on_click=lambda e, i=item: on_match_click(i, e.control))
            else:
                btn = ft.Container(content=ft.Icon(ft.Icons.VOLUME_UP, size=24, color=ft.Colors.BLUE_900), 
                                   bgcolor=ft.Colors.BLUE_50, padding=15, border_radius=10, alignment=ft.Alignment(0,0),
                                   on_click=lambda e, i=item: on_match_click(i, e.control))
            item["control"] = btn
            col_a.controls.append(btn)

        for item in list_b:
            btn = ft.Container(content=ft.Text(item["text"], text_align=ft.TextAlign.CENTER, size=16), 
                               bgcolor=ft.Colors.BLUE_50, padding=15, border_radius=10, alignment=ft.Alignment(0,0),
                               on_click=lambda e, i=item: on_match_click(i, e.control))
            item["control"] = btn
            col_b.controls.append(btn)

        view_games.controls.append(
            ft.Container(
                content=ft.Row([col_a, col_b], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START),
                padding=20, expand=True
            )
        )
        page.update()

    def build_games_menu():
        view_games.controls.clear()
        view_games.controls.extend([
            ft.Container(content=ft.Text("Khu Vực Trò Chơi", size=24, weight=ft.FontWeight.BOLD), padding=20),
            ft.FilledButton(content=ft.Text("1. Trắc Nghiệm Nhanh"), width=300, on_click=lambda e: start_quiz()),
            ft.Container(height=10),
            ft.FilledButton(content=ft.Text("2. Ghép Từ (Anh - Việt)"), width=300, on_click=lambda e: start_match_game("word")),
            ft.Container(height=10),
            ft.FilledButton(content=ft.Text("3. Luyện Nghe (Âm - Việt)"), width=300, on_click=lambda e: start_match_game("audio")),
        ])

    build_games_menu()

    # --- 4. VIEW DATA (IMPORT/EXPORT) ---
    txt_data = ft.TextField(multiline=True, min_lines=15, max_lines=15, expand=True, label="Dữ liệu CSV (Từ vựng | Nghĩa | Ví dụ)")
    
    def export_data(e):
        lines = []
        for w in all_words:
            lines.append(f"{w[1]} | {w[2]} | {w[3] if w[3] else ''}")
        txt_data.value = chr(10).join(lines)
        page.update()
        
    def import_data(e):
        if not txt_data.value: return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        count = 0
        for line in txt_data.value.split(chr(10)):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                word = parts[0]
                meaning = parts[1]
                example = parts[2] if len(parts) > 2 else ""
                cursor.execute("SELECT id FROM words WHERE word=? COLLATE NOCASE", (word,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO words (word, meaning, example) VALUES (?, ?, ?)", (word, meaning, example))
                    count += 1
        conn.commit()
        conn.close()
        
        # Reload list
        nonlocal all_words
        all_words = get_words()
        load_list()
        txt_data.value = f"Đã nhập thành công {count} từ vựng mới!"
        page.update()

    view_data = ft.Column([
        ft.Container(content=ft.Text("Nhập / Xuất Dữ Liệu", size=24, weight=ft.FontWeight.BOLD), padding=20),
        ft.Row([
            ft.FilledButton(content=ft.Text("Xuất CSV (Copy)"), on_click=export_data, icon=ft.Icons.DOWNLOAD),
            ft.FilledButton(content=ft.Text("Nhập CSV (Paste)"), on_click=import_data, icon=ft.Icons.UPLOAD, bgcolor=ft.Colors.GREEN),
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(content=txt_data, padding=10, expand=True)
    ], expand=True, visible=False)


    # --- CUSTOM TABS ---
    def change_tab(idx):
        view_vocab.visible = (idx == 0)
        view_flashcard.visible = (idx == 1)
        view_games.visible = (idx == 2)
        view_data.visible = (idx == 3)
        btn_tab1.bgcolor = ft.Colors.BLUE_100 if idx == 0 else ft.Colors.TRANSPARENT
        btn_tab2.bgcolor = ft.Colors.BLUE_100 if idx == 1 else ft.Colors.TRANSPARENT
        btn_tab3.bgcolor = ft.Colors.BLUE_100 if idx == 2 else ft.Colors.TRANSPARENT
        btn_tab4.bgcolor = ft.Colors.BLUE_100 if idx == 3 else ft.Colors.TRANSPARENT
        if idx == 2:
            build_games_menu()
        page.update()

    btn_tab1 = ft.TextButton("Từ vựng", icon=ft.Icons.LIST, on_click=lambda e: change_tab(0), expand=1)
    btn_tab2 = ft.TextButton("Thẻ", icon=ft.Icons.STYLE, on_click=lambda e: change_tab(1), expand=1)
    btn_tab3 = ft.TextButton("Game", icon=ft.Icons.VIDEOGAME_ASSET, on_click=lambda e: change_tab(2), expand=1)
    btn_tab4 = ft.TextButton("Data", icon=ft.Icons.SAVE, on_click=lambda e: change_tab(3), expand=1)
    
    top_nav = ft.Row([btn_tab1, btn_tab2, btn_tab3, btn_tab4], alignment=ft.MainAxisAlignment.SPACE_AROUND)
    
    change_tab(0) # Khởi tạo tab 0
    page.add(top_nav, ft.Divider(), view_vocab, view_flashcard, view_games, view_data)

ft.app(main)
