# -*- coding: utf-8 -*-
import json
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window

# ==== iOS palette ====
BG    = (0.949, 0.949, 0.969, 1)
CARD  = (1, 1, 1, 1)
BLUE  = (0.0, 0.478, 1.0, 1)
GREEN = (0.204, 0.780, 0.349, 1)
TEXT  = (0.110, 0.110, 0.118, 1)
SUB   = (0.557, 0.557, 0.576, 1)
WHITE = (1, 1, 1, 1)

Window.clearcolor = BG

class Card(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*CARD)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self.rect.pos = self.pos
        self.rect.size = self.size

class IOSButton(Button):
    def __init__(self, bg_color=BLUE, **kw):
        super().__init__(**kw)
        self.background_normal = ''
        self.background_color = bg_color
        self.color = WHITE
        self.font_size = sp(16)
        self.bold = True

class WifiInspectorApp(App):
    def build(self):
        self.title = "Wi-Fi Inspector"
        root = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))

        title = Label(text="Wi-Fi", font_size=sp(34), bold=True, color=TEXT, halign='left', valign='middle', size_hint_y=None, height=dp(60))
        title.bind(size=lambda l, s: setattr(l, 'text_size', s))
        root.add_widget(title)

        self.status = Label(text="اضغط فحص للبدء", size_hint_y=None, height=dp(28), color=SUB, font_size=sp(13))
        root.add_widget(self.status)

        self.scroll = ScrollView()
        self.results = GridLayout(cols=1, spacing=dp(8), size_hint_y=None, padding=dp(2))
        self.results.bind(minimum_height=self.results.setter('height'))
        self.scroll.add_widget(self.results)
        root.add_widget(self.scroll)

        btns = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        scan = IOSButton(text="فحص الشبكات", bg_color=BLUE)
        scan.bind(on_press=self.start_scan)
        btns.add_widget(scan)

        save = IOSButton(text="حفظ التقرير", bg_color=GREEN)
        save.bind(on_press=self.save_report)
        btns.add_widget(save)
        root.add_widget(btns)

        if platform == "android":
            Clock.schedule_once(self._request_perms, 0.5)

        return root

    def _request_perms(self, dt):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.NEARBY_WIFI_DEVICES, Permission.ACCESS_FINE_LOCATION])
        except Exception as e:
            print(f"perm error: {e}")

    def start_scan(self, *a):
        if platform != "android":
            self.status.text = "يعمل على أندرويد فقط"
            return
        self.status.text = "جارٍ الفحص..."
        Clock.schedule_once(lambda dt: self._scan(), 0.1)

    def _scan(self):
        try:
            from jnius import autoclass, cast
            Context = autoclass('android.content.Context')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WifiManager = autoclass('android.net.wifi.WifiManager')

            act = PythonActivity.mActivity
            wm = cast(WifiManager, act.getSystemService(Context.WIFI_SERVICE))

            try:
                wm.startScan()
            except Exception:
                pass

            results = wm.getScanResults()
            if results is None or results.size() == 0:
                Clock.schedule_once(lambda dt: self._error("لم يتم العثور على شبكات\nتأكد من تشغيل الواي فاي و GPS"), 0)
                return

            nets = []
            for i in range(results.size()):
                r = results.get(i)
                nets.append({
                    'ssid':  str(r.SSID) if r.SSID else '(مخفية)',
                    'level': int(r.level),
                    'cap':   str(r.capabilities),
                })

            Clock.schedule_once(lambda dt: self._show(nets), 0)

        except Exception as e:
            msg = f"خطأ: {e}"
            Clock.schedule_once(lambda dt: self._error(msg), 0)

    def _error(self, msg):
        self.results.clear_widgets()
        self.status.text = msg

    def _show(self, nets):
        self.results.clear_widgets()
        self.status.text = f"تم العثور على {len(nets)} شبكة"
        nets.sort(key=lambda x: x['level'], reverse=True)
        for n in nets:
            self.results.add_widget(self._make_card(n))

    def _make_card(self, n):
        card = Card(orientation='vertical', size_hint_y=None, height=dp(84), padding=dp(14), spacing=dp(4))
        cap = n['cap']
        secured = ('WPA' in cap) or ('WEP' in cap)
        lock = "🔒" if secured else "🔓"

        t = Label(text=f"{lock}  {n['ssid']}", font_size=sp(16), bold=True, color=TEXT, halign='left', valign='middle', size_hint_y=None, height=dp(28))
        t.bind(size=lambda l, s: setattr(l, 'text_size', s))
        card.add_widget(t)

        lvl = n['level']
        if lvl > -50:   bars = "▂▄▆█"
        elif lvl > -65: bars = "▂▄▆ "
        elif lvl > -75: bars = "▂▄  "
        else:           bars = "▂   "

        if 'SAE' in cap:       enc = 'WPA3'
        elif 'WPA2' in cap:    enc = 'WPA2'
        elif 'WPA' in cap:     enc = 'WPA'
        elif 'WEP' in cap:     enc = 'WEP'
        else:                  enc = 'مفتوح'

        info = Label(text=f"{bars}   {lvl} dBm   ·   {enc}", font_size=sp(12), color=SUB, halign='left', valign='middle', size_hint_y=None, height=dp(24))
        info.bind(size=lambda l, s: setattr(l, 'text_size', s))
        card.add_widget(info)
        return card

    def save_report(self, *a):
        if platform != "android": return
        try:
            from jnius import autoclass, cast
            Context = autoclass('android.content.Context')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WifiManager = autoclass('android.net.wifi.WifiManager')
            act = PythonActivity.mActivity
            wm = cast(WifiManager, act.getSystemService(Context.WIFI_SERVICE))
            results = wm.getScanResults()

            data = []
            if results:
                for i in range(results.size()):
                    r = results.get(i)
                    data.append({'ssid': str(r.SSID), 'bssid': str(r.BSSID), 'level': int(r.level), 'cap': str(r.capabilities)})

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"/sdcard/wifi_scan_{ts}.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status.text = f"تم الحفظ في {path}"
        except Exception as e:
            self.status.text = f"فشل الحفظ: {e}"

if __name__ == "__main__":
    WifiInspectorApp().run()
