import sys
import os
import json
import threading

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QComboBox, QLineEdit, QVBoxLayout, QHBoxLayout, QShortcut, QTabWidget, QFileDialog, QProgressBar, QMessageBox, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread
from download import DownloadTab
from convert import MediaConversionTab



class CustomWindow(QWidget):
	def __init__(self):
		super().__init__()
		self.initUI()

	def initUI(self):
        # Set window size
		self.setGeometry(100, 100, 400, 300)
		self.setWindowTitle("Oni-ESAMEDAV | The Essential and Accessible Tool for Downloading and Converting Media Files")

        # Create a layout for the main window
		main_layout = QVBoxLayout()
		self.setLayout(main_layout)

        # Create tabs
		tab_widget = QTabWidget()
		main_layout.addWidget(tab_widget)


		with open('options.json', 'r') as file:
			options = json.load(file)
			format_options = options["format_options"]
			quality_options = options["quality_options"]
			format_to_extension = options["format_to_extension"]


        # Add Tab
		tab1 = DownloadTab(format_options, quality_options, format_to_extension)
		tab_widget.addTab(tab1, "Download")
		tab2 = MediaConversionTab(format_options, quality_options, format_to_extension)
		tab_widget.addTab(tab2, "Media Conversion")


		def closeEvent(self, event):
        # Stop any running threads in each tab
			tab_widget = self.findChild(QTabWidget)
			for index in range(tab_widget.count()):
				current_tab_widget = tab_widget.widget(index)
				if hasattr(current_tab_widget, "stop_download_thread"):
					current_tab_widget.stop_download_thread()
					current_tab_widget.download_thread.finished.connect(self.handle_thread_finished)
				if hasattr(current_tab_widget, "stop_convert_thread"):
					current_tab_widget.stop_convert_thread()
					current_tab_widget.convert_thread.finished.connect(self.handle_thread_finished)
			event.accept()


	def handle_thread_finished(self):
		event = getattr(self, "_close_event", None)
		if event:
			event.accept()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()
    sys.exit(app.exec_())
