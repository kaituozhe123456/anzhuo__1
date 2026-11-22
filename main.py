import flet as ft
import json
import uuid
import asyncio
import os
from datetime import datetime

async def get_data_path(filename):
    data_dir = await ft.get_application_documents_directory()
    return os.path.join(data_dir, filename)

def main(page: ft.Page):
    page.title = "尚上签"
    # 强行指定软件左上角的图标（双重保险）
    page.window.icon = "assets/icon.png"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F2F4F7"
    page.padding = 0
    
    state = {"alarms": [], "notes": [], "current_tab": 0}

    async def load_all_data():
        alarms_path = await get_data_path("alarms.json")
        if os.path.exists(alarms_path):
            try:
                with open(alarms_path, "r", encoding="utf-8") as f:
                    state["alarms"] = json.load(f)
            except: pass
        notes_path = await get_data_path("notes.json")
        if os.path.exists(notes_path):
            try:
                with open(notes_path, "r", encoding="utf-8") as f:
                    state["notes"] = json.load(f)
            except: pass
        refresh_views()

    async def save_alarms():
        path = await get_data_path("alarms.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state["alarms"], f, ensure_ascii=False)

    async def save_notes():
        path = await get_data_path("notes.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state["notes"], f, ensure_ascii=False)

    def refresh_views():
        today_list.controls.clear()
        state["alarms"].sort(key=lambda x: x["time"])
        for alarm in state["alarms"]:
            today_list.controls.append(
                ft.Container(bgcolor="white", border_radius=15, padding=15, margin=ft.margin.only(bottom=10),
                    content=ft.Row([
                        ft.Column([ft.Text(alarm["time"], size=28, weight="bold"), ft.Text(alarm.get("period", "早"), size=12, color="grey")], spacing=2),
                        ft.Text(alarm["content"], size=16, weight="bold", expand=True),
                        ft.Switch(value=alarm["active"], active_color="#FF3B30")
                    ])
                )
            )
        note_list.controls.clear()
        for note in state["notes"]:
            note_list.controls.append(
                ft.Container(bgcolor="white", border_radius=15, padding=15, margin=ft.margin.only(bottom=10), on_click=lambda e, n=note: open_note_edit(n),
                    content=ft.Column([ft.Text(note["title"], size=16, weight="bold"), ft.Text(note["content"][:20] + "..." if len(note["content"]) > 20 else note["content"], size=13, color="grey")])
                )
            )
        page.update()

    today_list = ft.ListView(expand=True, spacing=0, padding=15)
    view_today = ft.Column([ft.Container(content=ft.Text("今日提醒", size=28, weight="bold"), padding=ft.padding.only(left=20, top=20, bottom=10)), today_list], expand=True)

    def open_add_alarm(e):
        time_picker = ft.TimePicker(confirm_text="确定", cancel_text="取消")
        def on_time_change(e):
            if time_picker.value:
                selected_time = time_picker.value.strftime("%H:%M")
                hour_int = time_picker.value.hour
                period = "早" if 5<=hour_int<11 else ("午" if 11<=hour_int<18 else "晚")
                state["alarms"].append({"id": str(uuid.uuid4()), "time": selected_time, "period": period, "content": "新提醒", "mode": "alarm", "active": True})
                page.run_task(save_alarms)
                refresh_views()
        time_picker.on_change = on_time_change
        page.open(time_picker)

    timer_text = ft.Text("20:00", size=72, weight="bold", color="#1A1A1A")
    status_text = ft.Text("准备学习", size=32, weight="bold", color="#FF3B30")
    timer_state = {"is_running": False, "time_left": 1200, "mode": "study"}
    
    async def timer_loop():
        while True:
            await asyncio.sleep(1)
            if timer_state["is_running"]:
                if timer_state["time_left"] > 0:
                    timer_state["time_left"] -= 1
                    m, s = divmod(timer_state["time_left"], 60)
                    timer_text.value = f"{m:02d}:{s:02d}"
                    page.update()
                else:
                    if timer_state["mode"] == "study":
                        timer_state["mode"] = "rest"
                        timer_state["time_left"] = 300
                        status_text.value = "休息放松中"
                        status_text.color = "#34C759"
                    else:
                        timer_state["mode"] = "study"
                        timer_state["time_left"] = 1200
                        status_text.value = "专注学习中"
                        status_text.color = "#FF3B30"
                    page.update()

    def toggle_timer(e):
        timer_state["is_running"] = not timer_state["is_running"]
        btn_timer.content.value = "暂停" if timer_state["is_running"] else "继续"
        page.update()

    btn_timer = ft.FilledButton("开始", on_click=toggle_timer, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=25), bgcolor="#FF3B30", color="white"))
    view_study = ft.Column([ft.Container(content=ft.Text("学习循环", size=28, weight="bold"), padding=ft.padding.only(left=20, top=20, bottom=10)), ft.Container(content=ft.Column([status_text, timer_text, ft.Container(height=20), btn_timer], alignment="center", horizontal_alignment="center"), expand=True)], expand=True)

    note_list = ft.ListView(expand=True, spacing=0, padding=15)
    view_note = ft.Column([ft.Container(content=ft.Text("签签", size=28, weight="bold"), padding=ft.padding.only(left=20, top=20, bottom=10)), note_list], expand=True)
    note_text_field = ft.TextField(multiline=True, expand=True, text_size=16)
    
    def open_note_edit(note=None):
        page.views.append(ft.View("/edit", [ft.AppBar(title=ft.Text("编辑签签"), bgcolor="#F2F4F7"), ft.Container(content=note_text_field, padding=15, expand=True), ft.Container(content=ft.FilledButton("保存", on_click=lambda e: save_note_and_back(note), style=ft.ButtonStyle(bgcolor="#FF3B30", color="white")), padding=15)]))
        note_text_field.value = note["content"] if note else ""
        page.update()

    async def save_note_and_back(note=None):
        content = note_text_field.value
        title = content.split('\n')[0] if content else "无标题"
        if note:
            note["content"] = content
            note["title"] = title
        else:
            state["notes"].append({"id": str(uuid.uuid4()), "title": title, "content": content})
        await save_notes()
        page.views.pop()
        page.update()
        refresh_views()

    main_container = ft.Container(content=view_today, expand=True)
    def switch_tab(e):
        idx = e.control.selected_index
        if idx == 0:
            main_container.content = view_today
            fab.content = ft.Icon(ft.Icons.ADD)
            fab.on_click = open_add_alarm
        elif idx == 1:
            main_container.content = view_study
            fab.visible = False
        elif idx == 2:
            main_container.content = view_note
            fab.content = ft.Icon(ft.Icons.CREATE)
            fab.on_click = lambda e: open_note_edit()
        if idx != 1: fab.visible = True
        page.update()

    nav_bar = ft.NavigationBar(selected_index=0, on_change=switch_tab, bgcolor="white", indicator_color="#FFE5E5",
        destinations=[ft.NavigationBarDestination(icon=ft.Icons.ACCESS_ALARM, label="今日"), ft.NavigationBarDestination(icon=ft.Icons.BOOK, label="学习"), ft.NavigationBarDestination(icon=ft.Icons.EDIT, label="签签")]
    )
    fab = ft.FloatingActionButton(icon=ft.Icons.ADD, bgcolor="#FF3B30", on_click=open_add_alarm)
    page.add(ft.Column([main_container], expand=True), nav_bar, fab)
    page.run_task(load_all_data)
    page.run_task(timer_loop)

ft.run(main)
