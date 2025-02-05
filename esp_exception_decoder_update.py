import sys
import re
import subprocess
import os
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, 
                             QPushButton, QFileDialog, QLabel, QHBoxLayout, QMessageBox,
                             QStatusBar, QAction)
from PyQt5.QtGui import QTextCursor, QIcon, QColor, QPalette
from PyQt5.QtCore import Qt, QSize
import qtawesome as qta

DEFAULT_GDB_PATH = r"C:\Users\trion\AppData\Local\Arduino15\packages\esp32\tools\xtensa-esp-elf-gdb\14.2_20240403\bin\xtensa-esp32-elf-gdb.exe" # change your gdb here

class EspExceptionDecoder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.elf_file = None
        self.gdb_path = DEFAULT_GDB_PATH if os.path.exists(DEFAULT_GDB_PATH) else None
        self.dark_mode = False
        self.initUI()

    def initUI(self):
        self.setWindowTitle('FMS ESP Exception Decoder')
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        toolbar = self.addToolBar('Main Toolbar')
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))

        self.add_toolbar_action(toolbar, 'fa5s.file-code', 'Select ELF File', self.select_elf_file)
        self.add_toolbar_action(toolbar, 'fa5s.terminal', 'Select GDB', self.select_gdb)
        self.add_toolbar_action(toolbar, 'fa5s.moon', 'Toggle Dark Mode', self.toggle_dark_mode)

        self.input_area = QTextEdit()
        self.input_area.setPlaceholderText("Paste your stack trace here")
        layout.addWidget(self.input_area)

        self.decode_button = QPushButton('Decode')
        self.decode_button.setIcon(qta.icon('fa5s.bug'))
        self.decode_button.clicked.connect(self.decode_exception)
        layout.addWidget(self.decode_button)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status()

        self.apply_styles()

    def add_toolbar_action(self, toolbar, icon_name, text, slot):
        action = QAction(qta.icon(icon_name), text, self)
        action.triggered.connect(slot)
        toolbar.addAction(action)

    def apply_styles(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow, QTextEdit, QPushButton, QLabel, QStatusBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTextEdit {
                    border: 1px solid #555555;
                    border-radius: 4px;
                }
                QPushButton {
                    background-color: #0d47a1;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QToolBar {
                    background-color: #1e1e1e;
                    border: none;
                }
                .error-card {
                    background-color: #4a0e0e;
                    border: 1px solid #ff6b6b;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 4px 0;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QTextEdit, QPushButton, QLabel, QStatusBar {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QTextEdit {
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                }
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QToolBar {
                    background-color: #e0e0e0;
                    border: none;
                }
                .error-card {
                    background-color: #ffebee;
                    border: 1px solid #ef9a9a;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 4px 0;
                }
            """)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.apply_styles()

    def select_elf_file(self):
        file_dialog = QFileDialog()
        elf_file, _ = file_dialog.getOpenFileName(self, "Select ELF File", "", "ELF Files (*.elf)")
        if elf_file:
            self.elf_file = elf_file
            self.update_status()

    def select_gdb(self):
        file_dialog = QFileDialog()
        gdb_path, _ = file_dialog.getOpenFileName(self, "Select GDB", "", "GDB Executable (*)")
        if gdb_path:
            self.gdb_path = gdb_path
            self.update_status()

    def update_status(self):
        elf_status = os.path.basename(self.elf_file) if self.elf_file else "Not selected"
        gdb_status = os.path.basename(self.gdb_path) if self.gdb_path else "Not selected"
        self.statusBar.showMessage(f"ELF: {elf_status} | GDB: {gdb_status}")

    def decode_exception(self):
        try:
            if not self.elf_file:
                raise ValueError("ELF file not selected")
            if not self.gdb_path:
                raise ValueError("GDB not selected")

            input_text = self.input_area.toPlainText()
            if not input_text.strip():
                raise ValueError("No stack trace provided")

            decoded_text = self.parse_exception(input_text)
            self.output_area.setHtml(decoded_text)
        except Exception as e:
            error_msg = f"Error during decoding: {str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "Decoding Error", error_msg)
            self.output_area.setPlainText(error_msg)

    def parse_exception(self, content):
        output = "<pre>"
        
        if "Stack smashing protect failure!" in content:
            output += "<b><font color=red>Stack smashing protect failure detected!</font></b>\n"
        
        backtrace_match = re.search(r"Backtrace:(.*)", content, re.DOTALL)
        if backtrace_match:
            output += self.parse_backtrace(backtrace_match.group(1))
        else:
            output += "<font color=red>No backtrace found in the input.</font>\n"
        
        sha256_match = re.search(r"ELF file SHA256: (\w+)", content)
        if sha256_match:
            output += f"ELF file SHA256: {sha256_match.group(1)}\n"
        
        output += "</pre>"
        return output

    def parse_backtrace(self, backtrace):
        output = "<i>Decoding backtrace:</i>\n"
        addresses = re.findall(r"0x([0-9a-fA-F]{8})", backtrace)
        if addresses:
            cmd = [
                self.gdb_path,
                "--batch",
                self.elf_file,
                "-ex", "set listsize 1"
            ]
            for addr in addresses:
                cmd.extend(["-ex", f"l *0x{addr}"])
            cmd.extend(["-ex", "q"])
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                gdb_output = result.stdout.strip()
                decoded_lines = self.parse_gdb_output(gdb_output)
                for addr, decoded_line in zip(addresses, decoded_lines):
                    output += f"{decoded_line}\n"
            except subprocess.CalledProcessError as e:
                error_msg = f"GDB command failed: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                raise RuntimeError(error_msg)
            except Exception as e:
                raise RuntimeError(f"Error decoding addresses: {str(e)}")
        else:
            output += "<font color=red>No valid addresses found in the backtrace.</font>\n"
        
        if "CORRUPTED" in backtrace:
            output += "<b><font color=red>WARNING: Backtrace is corrupted!</font></b>\n"
        
        return output

    def parse_gdb_output(self, gdb_output):
        lines = gdb_output.split('\n')
        decoded_lines = []
        for line in lines:
            match = re.search(r"(0x[0-9a-fA-F]+)\s+is\s+in\s+(\w+)\s+$$(.*?):(\d+)$$", line)
            if match:
                addr, func, file, line_num = match.groups()
                decoded_lines.append(f"<font color=green>{addr}: </font><b><font color=blue>{func}</font></b> at {file}:{line_num} (line {line_num})")
            else:
                match = re.search(r"(0x[0-9a-fA-F]+)\s+is\s+in\s+(\w+)", line)
                if match:
                    addr, func = match.groups()
                    decoded_lines.append(f"<font color=green>{addr}: </font><b><font color=blue>{func}</font></b>")
                else:
                    decoded_lines.append(f'<div class="error-card"><font color=red>Unable to decode:check line :{line}</font></div>')
        return decoded_lines

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EspExceptionDecoder()
    ex.show()
    sys.exit(app.exec_())

