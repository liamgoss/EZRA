
import toga, platform, subprocess, os
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from download import download_file


class EzraApp(toga.App):

    def startup(self):
        # Main container
        self.main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Input: base64 secret
        self.secret_input = toga.TextInput(placeholder="Paste your EZRA secret here", style=Pack(flex=1, padding_top=5))

        # Status output
        self.status_label = toga.Label("", style=Pack(padding_top=5))

        # Log output
        # This is a multiline text input that will be used to show logs or output
        self.log_output = toga.MultilineTextInput(style=Pack(flex=1, height=100), readonly=True)
        self.log_output.visible = True

        self.toggle_button = toga.Button(
            "Hide Details",
            on_press=self.toggle_details,
            style=Pack(padding_top=10)
        )

        self.save_folder = None
        

        # Buttons
        output_dir_button = toga.Button("Select Destination Folder", on_press=self.choose_save_folder, style=Pack(padding_top=5))
        download_button = toga.Button("Download", on_press=self.handle_download, style=Pack(padding_top=5))

        # Widgets
        self.main_box.add(self.secret_input)
        self.main_box.add(output_dir_button)
        self.main_box.add(download_button)
        self.main_box.add(self.status_label)
        self.main_box.add(self.toggle_button)
        self.main_box.add(self.log_output)


        self.main_window = toga.MainWindow(title="EZRA Client")
        self.main_window.content = self.main_box
        self.main_window.show()

    # Platform-specific folder selection
    def open_folder(self, path):
        folder = os.path.dirname(path)
        if platform.system() == "Darwin":
            subprocess.run(["open", folder])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", folder])
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", folder])

    def toggle_details(self, widget):
        if self.log_output.visible:
            self.log_output.visible = False
            self.log_output.style.height = 0
            widget.text = "Show Details"
        else:
            self.log_output.visible = True
            self.log_output.style.height = 100  
            widget.text = "Hide Details"
        self.main_box.refresh()

    def choose_save_folder(self, widget):
        self.main_window.select_folder_dialog(
            title="Select Folder",
            on_result=self.folder_selected
        )

    def folder_selected(self, dialog, folder):
        if folder:
            self.save_folder = folder
            self.status_label.text = f"Selected folder: {folder}"


    def log_to_output(self, msg: str):
        self.log_output.value += msg + "\n"

    
    def handle_download(self, widget):
        secret = self.secret_input.value.strip()
        if not secret:
            self.status_label.text = "[!] No secret provided."
            return

        try:
            filename = download_file(secret, self.save_folder, logger=self.log_to_output)
            self.status_label.text = f"[✓] File downloaded successfully to: {filename}"

        except Exception as e:
            self.status_label.text = f"[!] Error: {str(e)}"

def main():
    return EzraApp("EZRA", "org.ezra.client")

if __name__ == "__main__":
    main().main_loop()