
import toga, platform, subprocess, os
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from download import download_file


class EzraApp(toga.App):

    def startup(self):
        # Main container with outer padding
        self.main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))

        # Input Section
        input_section = toga.Box(style=Pack(direction=COLUMN, padding_bottom=10))
        input_section.add(toga.Label("Paste your EZRA secret:", style=Pack(padding_bottom=5)))

        self.secret_input = toga.TextInput(
            placeholder="Paste your EZRA secret here",
            style=Pack(padding_bottom=10)
        )
        input_section.add(self.secret_input)

        # Folder selection
        folder_section = toga.Box(style=Pack(direction=ROW, padding_bottom=10))
        self.destination_label = toga.Label("Selected folder: None", style=Pack(flex=1, padding_right=10))
        folder_button = toga.Button("Select Folder", on_press=self.choose_save_folder)
        folder_section.add(self.destination_label)
        folder_section.add(folder_button)

        input_section.add(folder_section)

        # Download button
        download_button = toga.Button("Download", on_press=self.handle_download, style=Pack(padding_bottom=10))
        input_section.add(download_button)

        # Status output
        self.status_label = toga.Label("", style=Pack(padding_bottom=5, font_weight="bold"))
        input_section.add(self.status_label)

        # Output Section
        self.log_output = toga.MultilineTextInput(style=Pack(height=120), readonly=True)
        self.log_output.visible = True

        self.toggle_button = toga.Button(
            "Hide Details",
            on_press=self.toggle_details,
            style=Pack(padding_top=5)
        )

        # Assemble everything
        self.main_box.add(input_section)
        self.main_box.add(self.toggle_button)
        self.main_box.add(self.log_output)

        # Set up main window
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
            self.destination_label.text = f"Selected folder: {folder}"


    def log_to_output(self, msg: str):
        self.log_output.value += msg + "\n"

    
    def handle_download(self, widget):
        secret = self.secret_input.value.strip()
        
        if not secret:
            self.status_label.text = "[!] No secret provided."
            return

        if not hasattr(self, "save_folder") or self.save_folder is None:
            self.status_label.text = "[!] Please select a destination folder before downloading."
            return

        try:
            filename = download_file(secret, self.save_folder, logger=self.log_to_output)
            if filename:
                self.status_label.text = f"[✓] File downloaded successfully to: {filename}"
                self.open_folder(filename)
            else:
                self.status_label.text = "[!] Failed to download or decrypt file."
                self.main_window.error_dialog(
                    "Download Failed",
                    "The file could not be downloaded. This might mean:\n\n"
                    "- The secret is incorrect\n"
                    "- The file has expired\n"
                    "- The file was already downloaded (and erased)\n\n"
                    "Please verify the secret and try again."
                )
        except Exception as e:
            self.status_label.text = f"[!] Unexpected error: {str(e)}"
            self.main_window.error_dialog(
                "Unexpected Error",
                f"An unexpected error occurred during download:\n\n{e}"
            )


def main():
    return EzraApp("EZRA", "org.ezra.client")

if __name__ == "__main__":
    main().main_loop()