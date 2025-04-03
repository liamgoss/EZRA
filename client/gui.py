
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from download import download_file

class EzraApp(toga.App):
    def startup(self):
        # Main container
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10, spacing=10))

        # Input: base64 secret
        self.secret_input = toga.TextInput(placeholder="Paste your EZRA secret here", style=Pack(flex=1))

        # Status output
        self.status_label = toga.Label("", style=Pack(padding_top=5))

        # Buttons
        download_button = toga.Button("Download", on_press=self.handle_download, style=Pack(padding_top=5))

        # Widgets
        main_box.add(self.secret_input)
        main_box.add(download_button)
        main_box.add(self.status_label)

        self.main_window = toga.MainWindow(title="EZRA Client")
        self.main_window.content = main_box
        self.main_window.show()

    def handle_download(self, widget):
        secret = self.secret_input.value.strip()
        if not secret:
            self.status_label.text = "[!] No secret provided."
            return

        try:
            download_file(secret)
            self.status_label.text = "[✓] File downloaded successfully."
        except Exception as e:
            self.status_label.text = f"[!] Error: {str(e)}"

def main():
    return EzraApp("EZRA", "org.ezra.client")