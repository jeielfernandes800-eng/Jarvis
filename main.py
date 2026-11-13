import math
import os
import threading
import time

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, Line, PopMatrix, PushMatrix,
                           Rectangle, Rotate, RoundedRectangle)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import escape_markup

# 🎨 Cores
FUNDO = (0.005, 0.012, 0.035, 1)
CIANO = (0.15, 0.85, 1, 1)
CIANO_CLARO = (0.6, 0.96, 1, 1)
AZUL = (0.1, 0.55, 1, 1)
TEXTO = (0.75, 0.9, 1, 1)

Window.clearcolor = FUNDO
Window.softinput_mode = 'resize'  # teclado empurra a tela pra cima

# 🔑 CHAVE DA GROQ
# Opção 1: variável de ambiente GROQ_API_KEY (PC)
# Opção 2: arquivo chave.txt na mesma pasta do código (PC)
# Opção 3: colar a chave aqui entre as aspas (celular / APK)
CHAVE_NO_CODIGO = "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"


def carrega_chave():
    k = os.environ.get("GROQ_API_KEY", "").strip()
    if k:
        return k
    pasta = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(pasta, "chave.txt"), encoding="utf-8") as f:
            k = f.read().strip()
            if k:
                return k
    except Exception:
        pass
    return CHAVE_NO_CODIGO.strip()


CHAVE = carrega_chave()
URL = "https://api.groq.com/openai/v1/chat/completions"
URL_MODELOS = "https://api.groq.com/openai/v1/models"

# Modelos em ordem de preferência. O app consulta a Groq e usa o 1º que existir.
PREFERIDOS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant",
              "openai/gpt-oss-20b", "openai/gpt-oss-120b"]
IGNORAR = ("whisper", "guard", "tts", "playai", "orpheus", "embed", "safeguard")
MODELO = None
historico = []


def escolhe_modelo(headers):
    try:
        r = requests.get(URL_MODELOS, headers=headers, timeout=10)
        ids = [m["id"] for m in r.json().get("data", [])]
        for p in PREFERIDOS:
            if p in ids:
                return p
        for i in ids:
            if not any(x in i for x in IGNORAR):
                return i
    except Exception:
        pass
    return PREFERIDOS[0]


# 🧠 IA
def conversa_ia(mensagem):
    global MODELO
    if not CHAVE:
        return "⚠️ Chave da Groq não encontrada. Coloque em CHAVE_NO_CODIGO, chave.txt ou GROQ_API_KEY."

    historico.append({"role": "user", "content": mensagem})
    del historico[:-20]
    contexto = [
        {"role": "system", "content": "Você é J.A.R.V.I.S., assistente do Homem de Ferro. "
                                      "Seja elegante, sarcástico, curto e direto. Responda sempre em português."}
    ] + historico[-8:]
    headers = {"Authorization": f"Bearer {CHAVE}", "Content-Type": "application/json"}

    r = None
    motivo = ""
    for _ in range(2):  # 2ª tentativa só se o modelo tiver sido desativado
        try:
            if not MODELO:
                MODELO = escolhe_modelo(headers)
            r = requests.post(
                URL, headers=headers, timeout=30,
                json={"model": MODELO, "messages": contexto,
                      "temperature": 0.7, "max_tokens": 400},
            )
        except Exception as e:
            historico.pop()
            return f"⚠️ Sem conexão: {str(e)[:80]}"

        if r.status_code == 200:
            try:
                texto = (r.json()["choices"][0]["message"]["content"] or "").strip()
            except Exception:
                texto = ""
            if not texto:
                texto = "Sem resposta, senhor. Tente de novo."
            historico.append({"role": "assistant", "content": texto})
            return texto

        try:
            motivo = r.json().get("error", {}).get("message", r.text)
        except Exception:
            motivo = r.text
        if r.status_code in (400, 404) and "model" in motivo.lower():
            MODELO = None  # força nova escolha na próxima volta
            continue
        break

    historico.pop()
    dicas = {401: "Chave inválida ou revogada.", 429: "Limite de uso atingido, aguarde.",
             404: "Modelo não encontrado.", 400: "Requisição inválida."}
    return f"⚠️ Erro {r.status_code}: {dicas.get(r.status_code, '')} {motivo[:120]}"


# 🪟 Painel de vidro com cantos brilhantes
class Painel(BoxLayout):
    def __init__(self, raio=18, fundo=(0.02, 0.08, 0.14, 0.8),
                 borda=(0.15, 0.85, 1, 0.45), **kwargs):
        super().__init__(**kwargs)
        self._raio = raio
        with self.canvas.before:
            Color(*fundo)
            self._fundo = RoundedRectangle(radius=[raio])
            Color(*borda)
            self._borda = Line(width=1.1)
            Color(*CIANO_CLARO)
            self._c1 = Line(width=2)
            self._c2 = Line(width=2)
        self.bind(pos=self._atualiza, size=self._atualiza)

    def _atualiza(self, *a):
        x, y = self.pos
        w, h = self.size
        c = 14
        self._fundo.pos, self._fundo.size = self.pos, self.size
        self._borda.rounded_rectangle = (x, y, w, h, self._raio)
        self._c1.points = [x, y + h - c, x, y + h, x + c, y + h]
        self._c2.points = [x + w - c, y, x + w, y, x + w, y + c]


# 🔘 Botão
class BotaoHUD(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = CIANO_CLARO
        self.bold = True
        with self.canvas.before:
            self._cor_fundo = Color(0.03, 0.13, 0.2, 0.9)
            self._fundo = RoundedRectangle(radius=[22])
            Color(*CIANO[:3], 0.8)
            self._borda = Line(width=1.2)
        self.bind(pos=self._atualiza, size=self._atualiza, state=self._estado)

    def _atualiza(self, *a):
        self._fundo.pos, self._fundo.size = self.pos, self.size
        x, y = self.pos
        w, h = self.size
        self._borda.rounded_rectangle = (x, y, w, h, 22)

    def _estado(self, *a):
        self._cor_fundo.rgba = (0.1, 0.45, 0.6, 1) if self.state == 'down' else (0.03, 0.13, 0.2, 0.9)


# 💠 Campo de texto
class CampoHUD(Painel):
    def __init__(self, **kwargs):
        super().__init__(raio=22, padding=[16, 0, 16, 0], **kwargs)
        self.input = TextInput(
            hint_text='Digite seu comando...', multiline=False, font_size=16,
            background_normal='', background_active='',
            background_color=(0, 0, 0, 0),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.65, 0.75, 1),
            cursor_color=CIANO, padding=[0, 15, 0, 0], write_tab=False,
        )
        self.add_widget(self.input)


# ⚛️ Reator animado (anéis concêntricos com brilho)
class Reator(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rots = []      # (Rotate, velocidade graus/seg; negativo = horário)
        self.pulsos = []    # (Color, alpha base)
        self.mult = 1.0
        self.alvo = 1.0
        self.t = 0.0
        self.titulo = Label(text='J.A.R.V.I.S', bold=True, color=(0.88, 0.98, 1, 1),
                            size_hint=(None, None), size=(10, 10),
                            pos_hint={'center_x': .5, 'center_y': .5})
        self.add_widget(self.titulo)
        self.bind(pos=self.desenha, size=self.desenha)
        Clock.schedule_interval(self.anima, 1 / 30)

    def ocupado(self, flag):
        self.alvo = 4.0 if flag else 1.0

    def anima(self, dt):
        self.t += dt
        self.mult += (self.alvo - self.mult) * min(1, dt * 4)
        for rot, v in self.rots:
            rot.angle += v * self.mult * dt
        freq = 7 if self.alvo > 1 else 2.2
        for cor, base in self.pulsos:
            cor.a = base * (0.65 + 0.35 * math.sin(self.t * freq))

    # --- helpers de desenho (usados dentro de canvas.before) ---
    def _gira(self, cx, cy, vel):
        PushMatrix()
        rot = Rotate(angle=0, origin=(cx, cy))
        self.rots.append((rot, vel))

    def _arco(self, cx, cy, r, ini, fim, w, cor=CIANO, alfa=1.0, pulso=False):
        for k, a in ((3.4, 0.06), (2.2, 0.11), (1.4, 0.2)):   # brilho
            c = Color(cor[0], cor[1], cor[2], alfa * a)
            if pulso:
                self.pulsos.append((c, alfa * a))
            Line(circle=(cx, cy, r, ini, fim), width=w * k, cap='round')
        c = Color(cor[0], cor[1], cor[2], alfa)
        if pulso:
            self.pulsos.append((c, alfa))
        Line(circle=(cx, cy, r, ini, fim), width=w, cap='round')

    def _anel(self, cx, cy, r, w, cor=CIANO, alfa=1.0, pulso=False):
        for k, a in ((3.4, 0.06), (2.2, 0.11), (1.4, 0.2)):
            c = Color(cor[0], cor[1], cor[2], alfa * a)
            if pulso:
                self.pulsos.append((c, alfa * a))
            Line(circle=(cx, cy, r), width=w * k)
        c = Color(cor[0], cor[1], cor[2], alfa)
        if pulso:
            self.pulsos.append((c, alfa))
        Line(circle=(cx, cy, r), width=w)

    def _cometa(self, cx, cy, r, ini, comp, w, n=14):
        passo = comp / n
        for i in range(n):
            a = (i + 1) / n
            Color(CIANO_CLARO[0], CIANO_CLARO[1], CIANO_CLARO[2], a * a)
            Line(circle=(cx, cy, r, ini + i * passo, ini + (i + 1) * passo + 1),
                 width=w * (0.4 + 0.6 * a), cap='round')
        ang = math.radians(ini + comp)   # ângulo do kivy: 0 = topo, sentido horário
        hx, hy = cx + r * math.sin(ang), cy + r * math.cos(ang)
        d = w * 1.4
        Color(1, 1, 1, 1)
        Ellipse(pos=(hx - d, hy - d), size=(2 * d, 2 * d))
        Color(0.3, 0.9, 1, 0.25)
        Ellipse(pos=(hx - d * 2.5, hy - d * 2.5), size=(5 * d, 5 * d))

    def desenha(self, *a):
        self.canvas.before.clear()
        self.rots = []
        self.pulsos = []
        cx, cy = self.center
        R = min(self.width, self.height) * 0.46
        if R <= 0:
            return

        self.titulo.font_size = max(11, R * 0.105)
        self.titulo.size = (R, R * 0.3)

        with self.canvas.before:
            # halo
            for rf, al in ((1.3, 0.02), (1.2, 0.03), (1.1, 0.045), (1.02, 0.06)):
                Color(0, 0.5, 1, al)
                r = R * rf
                Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))

            # disco escuro de fundo
            Color(0, 0.025, 0.06, 0.92)
            r = R * 0.98
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
            Color(*CIANO[:3], 0.3)
            Line(circle=(cx, cy, R), width=1)

            # 1) arcos externos grossos
            self._gira(cx, cy, 9)
            self._arco(cx, cy, R * 0.97, 8, 105, 4.5)
            self._arco(cx, cy, R * 0.97, 135, 205, 4.5, alfa=0.55)
            self._arco(cx, cy, R * 0.97, 235, 335, 4.5)
            PopMatrix()

            # 2) régua de marcações
            self._gira(cx, cy, -16)
            for i in range(90):
                ang = math.radians(i * 4)
                maior = i % 5 == 0
                r0 = R * 0.86
                r1 = R * (0.93 if maior else 0.895)
                Color(*CIANO[:3], 0.85 if maior else 0.5)
                Line(points=[cx + r0 * math.cos(ang), cy + r0 * math.sin(ang),
                             cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)],
                     width=1.6 if maior else 1)
            PopMatrix()

            # 3) arcos azuis grossos
            self._gira(cx, cy, 28)
            Color(*AZUL[:3], 0.25)
            Line(circle=(cx, cy, R * 0.78), width=1)
            self._arco(cx, cy, R * 0.78, 20, 150, 7, cor=AZUL)
            self._arco(cx, cy, R * 0.78, 190, 300, 7, cor=AZUL, alfa=0.8)
            PopMatrix()

            # 4) anel tracejado + nós orbitais
            self._gira(cx, cy, -35)
            Color(*CIANO[:3], 0.7)
            Line(circle=(cx, cy, R * 0.68), width=1.2, dash_length=5, dash_offset=5)
            d = max(3, R * 0.025)
            for ang_g in (0, 120, 240):
                ang = math.radians(ang_g)
                px, py = cx + R * 0.68 * math.cos(ang), cy + R * 0.68 * math.sin(ang)
                Color(*CIANO_CLARO[:3], 1)
                Ellipse(pos=(px - d, py - d), size=(2 * d, 2 * d))
            PopMatrix()

            # 5) cometa
            self._gira(cx, cy, -75)
            Color(*CIANO[:3], 0.2)
            Line(circle=(cx, cy, R * 0.58), width=1)
            self._cometa(cx, cy, R * 0.58, 0, 200, max(3, R * 0.03))
            PopMatrix()

            # 6) anel pulsante em volta do texto
            self._anel(cx, cy, R * 0.44, 3, pulso=True)
            Color(*CIANO[:3], 0.4)
            Line(circle=(cx, cy, R * 0.40), width=1)

            # núcleo escuro
            Color(0.0, 0.07, 0.12, 0.95)
            r = R * 0.42
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))

            # marcas fixas N/L/S/O
            Color(*CIANO_CLARO[:3], 0.9)
            for ang_g in (0, 90, 180, 270):
                ang = math.radians(ang_g)
                Line(points=[cx + R * 0.46 * math.cos(ang), cy + R * 0.46 * math.sin(ang),
                             cx + R * 0.51 * math.cos(ang), cy + R * 0.51 * math.sin(ang)],
                     width=1.6)


# 🖥️ Interface
class JarvisTela(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.aguardando = False
        self.linhas = ['[color=66ccff][SISTEMA][/color] Bem‑vindo, senhor. Estou à sua disposição.']
        self.bind(pos=self._fundo, size=self._fundo)

        coluna = BoxLayout(orientation='vertical', padding=[14, 30, 14, 14], spacing=6)
        self.add_widget(coluna)

        self.reator = Reator(size_hint_y=0.5)
        coluna.add_widget(self.reator)

        coluna.add_widget(Label(text='O N L I N E', font_size=20, bold=True,
                                color=CIANO, size_hint_y=None, height=28))
        self.status = Label(text='N U V E M', font_size=13, color=AZUL,
                            size_hint_y=None, height=18)
        coluna.add_widget(self.status)
        if not CHAVE:
            self.status.text = 'S E M   C H A V E'
            self.status.color = (1, 0.4, 0.3, 1)

        painel = Painel(size_hint_y=0.32, padding=6)
        self.scroll = ScrollView(bar_color=CIANO, bar_width=3)
        self.chat = Label(text=self.linhas[0], markup=True, font_size=15, color=TEXTO,
                          halign='left', valign='top', size_hint_y=None, padding=(8, 8))
        self.chat.bind(width=lambda w, v: setattr(w, 'text_size', (v, None)))
        self.chat.bind(texture_size=lambda w, v: setattr(w, 'height', v[1] + 16))
        self.scroll.add_widget(self.chat)
        painel.add_widget(self.scroll)
        coluna.add_widget(painel)

        barra = BoxLayout(size_hint_y=None, height=52, spacing=8)
        self.btn_mais = BotaoHUD(text='+', size_hint_x=None, width=52, on_press=self.mais)
        self.btn_img = BotaoHUD(text='IMG', font_size=12, size_hint_x=None, width=52, on_press=self.mais)
        self.campo = CampoHUD()
        self.campo.input.bind(on_text_validate=self.enviar)
        self.btn_enviar = BotaoHUD(text='Enviar', font_size=14, size_hint_x=None, width=78,
                                   on_press=self.enviar)
        self.btn_mic = BotaoHUD(text='Mic', font_size=14, size_hint_x=None, width=60,
                                on_press=self.mic)
        for w in (self.btn_mais, self.btn_img, self.campo, self.btn_enviar, self.btn_mic):
            barra.add_widget(w)
        coluna.add_widget(barra)

        # clima (esquerda) e hora (direita)
        self.clima = Label(text='', markup=True, font_size=22, color=(1, 1, 1, 1), halign='left',
                           size_hint=(None, None), size=(200, 50),
                           pos_hint={'x': 0.02, 'top': 0.985})
        self.clima.bind(size=lambda w, v: setattr(w, 'text_size', v))
        self.add_widget(self.clima)

        self.hora = Label(text='', font_size=22, color=CIANO_CLARO, halign='right',
                          size_hint=(None, None), size=(140, 50),
                          pos_hint={'right': 0.98, 'top': 0.985})
        self.hora.bind(size=lambda w, v: setattr(w, 'text_size', v))
        self.add_widget(self.hora)
        Clock.schedule_interval(self._relogio, 1)
        self._relogio()

        threading.Thread(target=self.busca_clima, daemon=True).start()

    def _fundo(self, *a):
        """Fundo escuro com grade sutil e cantos de HUD."""
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*FUNDO)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.1, 0.5, 0.9, 0.05)
            x = self.x
            while x < self.right:
                Line(points=[x, self.y, x, self.top], width=1)
                x += 48
            y = self.y
            while y < self.top:
                Line(points=[self.x, y, self.right, y], width=1)
                y += 48
            Color(*CIANO[:3], 0.7)
            m, c = 8, 28
            x0, y0, x1, y1 = self.x + m, self.y + m, self.right - m, self.top - m
            Line(points=[x0, y0 + c, x0, y0, x0 + c, y0], width=1.6)
            Line(points=[x1 - c, y0, x1, y0, x1, y0 + c], width=1.6)
            Line(points=[x0, y1 - c, x0, y1, x0 + c, y1], width=1.6)
            Line(points=[x1 - c, y1, x1, y1, x1, y1 - c], width=1.6)

    def _relogio(self, *a):
        self.hora.text = time.strftime('%H:%M')

    def busca_clima(self):
        try:
            r = requests.get('https://wttr.in/?format=%t|%C&lang=pt', timeout=8)
            temp, desc = r.text.strip().split('|')
            texto = f'{temp.replace("+", "")}\n[size=12]{escape_markup(desc.lower())}[/size]'
        except Exception:
            texto = ''
        Clock.schedule_once(lambda dt: setattr(self.clima, 'text', texto))

    def mais(self, *a):
        self.adiciona('[color=66ccff][SISTEMA][/color] Função ainda não implementada.')

    def mic(self, *a):
        self.adiciona('[color=66ccff][SISTEMA][/color] Microfone ainda não implementado.')

    def adiciona(self, texto):
        self.linhas.append(texto)
        self.linhas = self.linhas[-60:]   # evita o chat crescer sem limite
        self.chat.text = '\n'.join(self.linhas)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def enviar(self, *a):
        if self.aguardando:
            return
        texto = self.campo.input.text.strip()
        if not texto:
            return
        self.aguardando = True
        self.adiciona(f'[color=ffffff][b]Você:[/b][/color] {escape_markup(texto)}')
        self.campo.input.text = ''
        self.btn_enviar.text = '...'
        self.status.text = 'P R O C E S S A N D O'
        self.reator.ocupado(True)
        threading.Thread(target=self._processa, args=(texto,), daemon=True).start()

    def _processa(self, texto):
        resposta = conversa_ia(texto)
        Clock.schedule_once(lambda dt: self._mostra(resposta))

    def _mostra(self, resposta):
        self.adiciona(f'[color=26d9f2][b]Jarvis:[/b][/color] {escape_markup(resposta)}')
        self.btn_enviar.text = 'Enviar'
        self.status.text = 'N U V E M'
        self.reator.ocupado(False)
        self.aguardando = False
        Clock.schedule_once(lambda dt: setattr(self.campo.input, 'focus', True), 0.1)


class JarvisApp(App):
    def build(self):
        return JarvisTela()


if __name__ == '__main__':
    JarvisApp().run()
