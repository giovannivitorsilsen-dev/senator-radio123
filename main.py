from pathlib import Path
from time import time
from pauses import Pauses, describe, restriction

from threading import Event, Thread

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from engine import StopRun, execute, scan


class Unfollow(App):
    title = "Unfollow"

    def build(self):
        self.pauses = Pauses(Path(self.user_data_dir) / "pause.db")
        self.client = None
        self.snapshot = None
        self.stop = Event()
        self.busy = False
        self.rootbox = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(6))
        self.rootbox.add_widget(Label(text="Unfollow", font_size="28sp"))
        self.username = self.field("Nome utente Instagram")
        self.password = self.field("Password", True)
        self.code = self.field("Codice 2FA, se attivo")
        self.login = self.button("Collega account e analizza", self.analyze)
        self.keep = self.field("Proteggi questi @nomi, separati da virgola")
        self.go = self.button("Avvia unfollow", self.start)
        self.go.disabled = True
        self.button("Ferma dopo l’operazione in corso", lambda *_: self.stop.set())
        self.status = Label(text="Sessione utilizzata solo in memoria.", halign="left")
        self.status.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        self.rootbox.add_widget(self.status)
        self.notice = Label(text="", halign="left", size_hint_y=None, height=0)
        self.notice.bind(size=lambda w, size: setattr(w, "text_size", size))
        self.rootbox.add_widget(self.notice)
        self.verified = self.button("Ho verificato lo sblocco su Instagram", self.clear_pause)
        self.username.bind(text=self.refresh_pause)
        self.refresh_pause()
        Clock.schedule_interval(self.refresh_pause, 2)
        return self.rootbox

    def refresh_pause(self, *_):
        notice = self.pauses.get(self.username.text)
        self.notice.text = describe(notice) if notice else ""
        self.notice.height = dp(54) if notice else 0
        self.verified.disabled = self.busy or not notice or (notice[1] is not None and time() < notice[1])
        self.verified.opacity = 1 if notice else 0
        self.verified.size_hint_y = 1 if notice else None
        if not notice:
            self.verified.height = 0
        self.login.disabled = self.busy or bool(notice)
        self.go.disabled = self.busy or bool(notice) or not (self.snapshot and self.snapshot.targets)

    def clear_pause(self, *_):
        if not self.busy:
            self.pauses.clear_verified(self.username.text, time())
            self.refresh_pause()

    def save_restriction(self, user, error):
        response = getattr(self.client, "last_response", None)
        notice = restriction(error, time(), response)
        if notice:
            self.pauses.record(user, notice)
            return describe(notice)
        return None

    def field(self, hint, password=False):
        field = TextInput(hint_text=hint, password=password, multiline=False)
        self.rootbox.add_widget(field)
        return field

    def button(self, text, callback):
        button = Button(text=text)
        button.bind(on_release=callback)
        self.rootbox.add_widget(button)
        return button

    def work(self, action):
        if self.busy:
            return
        self.active_user = self.username.text.strip()
        self.busy = True
        self.stop.clear()
        for widget in (self.login, self.go, self.username, self.password, self.code, self.keep):
            widget.disabled = True

        def run():
            try:
                message = action()
            except StopRun as err:
                message = str(err)
                self.snapshot = None
            except Exception as err:
                self.snapshot = None
                message = self.save_restriction(self.active_user, err) or f"Interrotto ({type(err).__name__}). Verifica il profilo in Instagram."
            Clock.schedule_once(lambda dt: self.finish(message))
        Thread(target=run, daemon=True).start()

    def finish(self, message):
        self.busy = False
        for widget in (self.login, self.username, self.password, self.code, self.keep):
            widget.disabled = False
        self.go.disabled = not (self.snapshot and self.snapshot.targets)
        self.status.text = message
        self.refresh_pause()

    def analyze(self, *_):
        if self.busy:
            return
        user = self.username.text.strip()
        if self.pauses.get(user):
            self.refresh_pause()
            return
        password = self.password.text
        code = self.code.text.strip()
        if not user or (not password and (not self.client or self.client.username.casefold() != user.casefold())):
            self.snapshot = None
            self.go.disabled = True
            self.status.text = "Inserisci nome utente e password per collegare il profilo."
            return
        self.password.text = self.code.text = ""
        self.snapshot = None
        self.status.text = "Lettura degli elenchi…"

        def action():
            from instagrapi import Client
            if password or not self.client or self.client.username.casefold() != user.casefold():
                self.client = None
                client = Client()
                self.client = client
                try:
                    client.login(user, password, verification_code=code)
                except Exception as err:
                    message = self.save_restriction(user, err)
                    self.client = None
                    if message:
                        raise StopRun(message) from err
                    raise
            result = scan(self.client, self.stop.is_set)
            if self.stop.is_set():
                return "Analisi interrotta."
            self.snapshot = result
            return f"{len(result.targets)} profili non ricambiano. Aggiungi eventuali esclusioni."
        self.work(action)

    def start(self, *_):
        if self.busy or not self.snapshot:
            return
        if self.username.text.strip().casefold() != self.client.username.casefold():
            self.snapshot = None
            self.go.disabled = True
            self.status.text = "Account modificato. Ripeti l’analisi."
            return
        if self.pauses.get(self.username.text):
            self.refresh_pause()
            return
        snapshot, self.snapshot = self.snapshot, None
        protected = {s.strip().lstrip("@").casefold() for s in self.keep.text.split(",")}
        # Resolve protected handles to snapshot IDs before any write.
        protected_ids = {uid for uid, name in snapshot.targets if name.casefold() in protected}
        self.status.text = "Verifica dei rapporti in corso…"

        def action():
            counts = {"rimosso": 0, "saltato": 0}

            def report(name, outcome):
                counts[outcome] += 1
                msg = f"@{name} • {outcome}  |  Rimossi: {counts['rimosso']}"
                Clock.schedule_once(lambda dt: setattr(self.status, "text", msg))
            try:
                execute(self.client, snapshot, protected_ids, self.stop.is_set, report)
            except StopRun as err:
                end = self.save_restriction(self.active_user, err) or str(err)
            except Exception as err:
                end = self.save_restriction(self.active_user, err) or f"Verifica interrotta ({type(err).__name__})."
            else:
                end = "Interrotto." if self.stop.is_set() else "Completato."
            return f"{end} Rimossi confermati: {counts['rimosso']}. Saltati: {counts['saltato']}. Protetti: {len(protected_ids)}."
        self.work(action)

    def on_pause(self):
        self.stop.set()
        return True

    def on_stop(self):
        self.stop.set()


if __name__ == "__main__":
    Unfollow().run()
