import os
import subprocess
import yt_dlp as youtube_dl
import re
import threading

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QCheckBox, QComboBox, QLineEdit, QVBoxLayout, QHBoxLayout, QTabWidget, QFileDialog, QMessageBox, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread




class DownloadThread(QThread):
	progress_signal = pyqtSignal(str)

	def __init__(self, url, ydl_opts, combo_box1, combo_box2, destination, format_options, quality_options, format_to_extension, playlist, parent=None):
		super().__init__(parent)
		self.url = url
		self.ydl_opts = ydl_opts
		self.combo_box1 = combo_box1
		self.combo_box2 = combo_box2
		self.destination = destination
		self.format_options = format_options
		self.quality_options = quality_options
		self.format_to_extension = format_to_extension
		self.playlist_checkbox = playlist
		self.conversion_thread = None  


	def run(self):
		try:
			self.download_video()
		except Exception as e:
			self.progress_signal.emit(f"Error: {str(e)}")


	def download_video(self):
		def progress_hook(d):
			if d['status'] == 'downloading':
				percent = d['_percent_str'].replace('\x1b[0;94m', '').replace('\x1b[0m', '')
				speed = d['_speed_str'].replace('\x1b[0;32m', '').replace('\x1b[0m', '')
				eta = d['_eta_str'].replace('\x1b[0;33m', '').replace('\x1b[0m', '')
				message = f"Downloading: {percent} ({speed}, ETA: {eta})"
				self.progress_signal.emit(message)

		self.ydl_opts['progress_hooks'] = [progress_hook]

		with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
			info_dict = ydl.extract_info(self.url, download=False)
			video_title = info_dict.get('title', 'video')
			video_title_safe = re.sub(r'[\/:*?"<>|&%@]', '_', video_title)
			input_media = os.path.join(self.destination, f'{video_title_safe}.mp4')

			if self.playlist_checkbox.isChecked():
				self.progress_signal.emit("Fetching a playlist data...")
				ydl.download([self.url])
				self.progress_signal.emit("Download completed successfully.")
			else:
				ydl.download([self.url])
				self.progress_signal.emit("Download completed successfully.")
				self.progress_signal.emit("Converting...")
				self.convert_video(input_media, video_title)


	def convert_video(self, input_media, video_title):
		selected_format = self.combo_box1.currentText()
		selected_quality_index = self.combo_box2.currentIndex()

		if selected_quality_index < 0:
			self.show_error("Invalid quality option selected")
			return

		selected_quality_options = self.quality_options.get(selected_format, [])

		if selected_quality_index >= len(selected_quality_options):
			self.show_error("Invalid quality option selected")
			return

		selected_quality_option = selected_quality_options[selected_quality_index]
		selected_quality_name = selected_quality_option["name"]
		selected_quality_ffmpeg_args = selected_quality_option["ffmpeg_args"]

		output_extension = self.format_to_extension.get(selected_format, 'mp4')
		output_media = os.path.join(self.destination, f'{video_title}.{selected_quality_name}.{output_extension}')

		conversion = ConversionThread(input_media, selected_quality_name, selected_quality_ffmpeg_args, output_media)
		self.conversion_thread = conversion
		if self.conversion_thread:
			self.conversion_thread.finished.connect(self.handle_conversion_finished)
			conversion.start()
			self.progress_signal.emit("Successfully converted")


	def handle_conversion_finished(self):
		if self.conversion_thread:
			self.conversion_thread.finished.disconnect(self.handle_conversion_finished)
			self.conversion_thread = None


""" Download thread is end here """





class ConversionThread(QThread):
	def __init__(self, input_media, selected_quality_name, selected_quality_ffmpeg_args, output_media, parent=None):
		super().__init__(parent)
		self.input_media = input_media
		self.selected_quality_name = selected_quality_name
		self.selected_quality_ffmpeg_args = selected_quality_ffmpeg_args
		self.output_media = output_media

	def run(self):
		ffmpeg_command = [
			'ffmpeg',
			'-i', self.input_media,
			*self.selected_quality_ffmpeg_args.split(),
			'-y',
			self.output_media
		]

		subprocess.run(ffmpeg_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
		self.remove_input_media()


	def remove_input_media(self):
		try:
			os.remove(self.input_media)
		except Exception as e:
			print(f"Error removing input media: {str(e)}")


""" Convertion thread is end here """




class DownloadTab(QWidget):
	update_progress_signal = pyqtSignal(str)

	def __init__(self, format_options, quality_options, format_to_extension):
		super().__init__()
		self.format_options = format_options
		self.quality_options = quality_options
		self.format_to_extension = format_to_extension
		self.initUI()
		self.download_thread = None


	def initUI(self):
        # Create a layout for the download tab
		tab1_layout = QVBoxLayout()


    # Create a horizontal layout for the URL input layout
		url_layout = QHBoxLayout()
		url_label = QLabel("URL:", self)
		url_layout.addWidget(url_label)
		self.url_edit = QLineEdit(self)
		self.url_edit.setAccessibleName("Enter the URL here")
		self.url_edit.setToolTip("Enter the URL here")
		url_layout.addWidget(self.url_edit)
		clear_button = QPushButton("Clear", self)
		clear_button.setAccessibleName("Clear")
		clear_button.setToolTip("Clear the URL input")
		clear_button.clicked.connect(self.clear_url)
		url_layout.addWidget(clear_button)


    # Create the horizontal destination layout
		dest_layout = QHBoxLayout()
		dest_label = QLabel("Destination:", self)
		dest_layout.addWidget(dest_label)

		default_directory = os.getcwd()
		default_download = os.path.join(default_directory, "download")

		if not os.path.exists(default_download):
			os.makedirs(default_download)

		self.dest_edit = QLineEdit(default_download, self)
		self.dest_edit.setAccessibleName("Enter the destination here")
		self.dest_edit.setToolTip("Enter the destination here")
		dest_layout.addWidget(self.dest_edit)
		browse_button = QPushButton("Browse...", self)
		browse_button.setAccessibleName("Browse...")
		browse_button.setToolTip("Browse for a destination folder")
		browse_button.clicked.connect(self.browse_destination)
		dest_layout.addWidget(browse_button)


        # Create a horizontal layout for the two combo boxes and download options
		options_layout = QHBoxLayout()
		self.single_file_checkbox = QCheckBox("Download and Convert a Single File", self)
		self.single_file_checkbox.setChecked(True)  
		self.single_file_checkbox.toggled.connect(self.handle_single_file_checkbox)
		self.playlist_checkbox = QCheckBox("Playlist download (No conversion process)", self)
		self.playlist_checkbox.toggled.connect(self.handle_playlist_checkbox)
		options_layout.addWidget(self.single_file_checkbox)
		options_layout.addWidget(self.playlist_checkbox)

		combo_layout = QHBoxLayout()
		combo_label1 = QLabel("Format:", self)
		combo_layout.addWidget(combo_label1)
		self.combo_box1 = QComboBox(self)
		self.combo_box1.setAccessibleName("Format: ")
		self.combo_box1.addItems(self.format_options)
		self.combo_box1.currentIndexChanged.connect(self.update_combo_box2)
		combo_layout.addWidget(self.combo_box1)

		combo_label2 = QLabel("Quality:", self)
		combo_layout.addWidget(combo_label2)
		self.combo_box2 = QComboBox(self)
		self.combo_box2.setAccessibleName("Quality: ")
		self.update_combo_box2()
		combo_layout.addWidget(self.combo_box2)


        # Create a horizontal layout for the download button and progress bar
		button_layout = QHBoxLayout()
		download_button = QPushButton("Download", self)
		download_button.setAccessibleName("Download")
		download_button.setToolTip("Download the selected content")
		download_button.clicked.connect(self.download)
		button_layout.addWidget(download_button)
		button_layout.setAlignment(Qt.AlignCenter)

		self.progress_text = QTextEdit(self)
		self.progress_text.setAccessibleName("Progress Info")
		self.progress_text.setReadOnly(True)
		button_layout.addWidget(self.progress_text)


        # Add layouts and widgets to the first tab layout
		tab1_layout.addLayout(url_layout)
		tab1_layout.addLayout(dest_layout)
		tab1_layout.addLayout(options_layout)
		tab1_layout.addLayout(combo_layout)
		tab1_layout.addLayout(button_layout)
		tab1_layout.addWidget(self.progress_text)
		self.setLayout(tab1_layout)



     # Functions for download tab
	def clear_url(self):
		self.url_edit.clear()


	def browse_destination(self):
		options = QFileDialog.Options()
		options |= QFileDialog.ShowDirsOnly
		folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder", options=options)
		if folder_path:
			folder_path = folder_path.replace('/', '\\')
			self.dest_edit.setText(folder_path)


	def handle_single_file_checkbox(self, checked):
		if checked:
			self.playlist_checkbox.setChecked(False)
			self.combo_box1.clear()
			self.combo_box1.addItems(self.format_options)
			self.combo_box2.clear()
			self.update_combo_box2()


	def handle_playlist_checkbox(self, checked):
		if checked:
			self.single_file_checkbox.setChecked(False)
			self.combo_box1.clear()
			self.combo_box1.addItem(".mp4")
			self.combo_box2.clear()
			self.combo_box2.addItem("best")


	def update_combo_box2(self):
		selected_option = self.combo_box1.currentText()
		self.combo_box2.clear()
		self.combo_box2.addItems([q["name"] for q in self.quality_options.get(selected_option, [])])


	def stop_download_thread(self):
		if self.download_thread and self.download_thread.isRunning():
			self.download_thread.finished.connect(self.handle_thread_finished)
			self.download_thread.terminate()  # Terminate the thread to ensure it exits
			self.download_thread.wait()


	def handle_thread_finished(self):
		self.download_thread.finished.disconnect(self.handle_thread_finished)
		self.download_thread.wait()


	def download(self):
		url = self.url_edit.text()
		if not url:
			return

		destination = self.dest_edit.text()
		if not destination:
			return

		self.stop_download_thread()

		ydl_opts = {
			'format': 'best',
			'outtmpl': os.path.join(destination, '%(title)s.%(ext)s'),
			'yes-playlist': self.playlist_checkbox.isChecked(),
		}


		self.download_thread = DownloadThread(
			url, ydl_opts, self.combo_box1, self.combo_box2, destination, self.format_options, self.quality_options, self.format_to_extension, self.playlist_checkbox, self)
		self.download_thread.progress_signal.connect(self.update_progress_text)
		self.download_thread.start()


	@pyqtSlot(str)
	def update_progress_text(self, message):
		if "Error" in message:
			self.progress_text.clear()
		self.progress_text.append(message)


	def show_error(self, message):
		error_box = QMessageBox()
		error_box.setIcon(QMessageBox.Critical)
		error_box.setWindowTitle("Error")
		error_box.setText(message)
		error_box.exec_()


""" The class end here """




