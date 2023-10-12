import os
import subprocess
import threading

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QComboBox, QLineEdit, QVBoxLayout, QHBoxLayout, QTabWidget, QFileDialog, QMessageBox, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread



class ConversionThread(QThread):
	update_progress_signal = pyqtSignal(str)

	def __init__(self, input_media_files, selected_quality_name, selected_quality_ffmpeg_args, output_media_files, parent=None):
		super().__init__(parent)
		self.input_media_files = input_media_files
		self.selected_quality_name = selected_quality_name
		self.selected_quality_ffmpeg_args = selected_quality_ffmpeg_args
		self.output_media_files = output_media_files

	def run(self):
		for input_media, output_media in zip(self.input_media_files, self.output_media_files):
			ffmpeg_command = [
			'ffmpeg',
			'-i', input_media,
			*self.selected_quality_ffmpeg_args.split(),
			'-y',
			output_media
			]

			self.update_progress_signal.emit("Converting...")  # Emit a progress signal
			subprocess.run(ffmpeg_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
			self.update_progress_signal.emit(f"Conversion finished for {input_media}")


""" convertion thread class is end here"""



class MediaConversionTab(QWidget):
	update_progress_signal = pyqtSignal(str)

	def __init__(self, format_options, quality_options, format_to_extension):
		super().__init__()
		self.format_options = format_options
		self.quality_options = quality_options
		self.format_to_extension = format_to_extension
		self.initUI()
		self.convert_thread = None


	def initUI(self):
        # Create a layout for the download tab
		tab1_layout = QVBoxLayout()


        # Create a horizontal layout for the "Choose Media" button
		choose_media_layout = QHBoxLayout()
		choose_media_button = QPushButton("Choose Media", self)
		choose_media_button.setAccessibleName("Choose Media")
		choose_media_button.setToolTip("Choose media file")
		choose_media_button.clicked.connect(self.choose_media)
		choose_media_layout.addWidget(choose_media_button)
		choose_media_layout.setAlignment(Qt.AlignCenter)


    # Create the horizontal destination layout
		dest_layout = QHBoxLayout()
		dest_label = QLabel("Destination:", self)
		dest_layout.addWidget(dest_label)

		default_directory = os.getcwd()
		default_converted = os.path.join(default_directory, "converted")

		if not os.path.exists(default_converted):
			os.makedirs(default_converted)

		self.dest_edit = QLineEdit(default_converted, self)
		self.dest_edit.setAccessibleName("Enter the destination here")
		self.dest_edit.setToolTip("Enter the destination here")
		dest_layout.addWidget(self.dest_edit)
		browse_button = QPushButton("Browse...", self)
		browse_button.setAccessibleName("Browse...")
		browse_button.setToolTip("Browse for a destination folder")
		browse_button.clicked.connect(self.browse_destination)
		dest_layout.addWidget(browse_button)


        # Create a horizontal layout for the two combo boxes
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


        # Create a horizontal layout for the convert button and progress bar
		button_layout = QHBoxLayout()
		convert_button = QPushButton("Start Conversion", self)
		convert_button.setAccessibleName("Start Conversion")
		convert_button.setToolTip("Convert the selected content")
		convert_button.clicked.connect(self.convert)
		button_layout.addWidget(convert_button)
		button_layout.setAlignment(Qt.AlignCenter)

		self.progress_text = QTextEdit(self)
		self.progress_text.setAccessibleName("Progress Info")
		self.progress_text.setReadOnly(True)
		button_layout.addWidget(self.progress_text)


        # Add layouts and widgets to the first tab layout
		tab1_layout.addLayout(choose_media_layout)
		tab1_layout.addLayout(dest_layout)
		tab1_layout.addLayout(combo_layout)
		tab1_layout.addLayout(button_layout)
		tab1_layout.addWidget(self.progress_text)
		self.setLayout(tab1_layout)



     # Functions for media convertion tab
	def choose_media(self):
		options = QFileDialog.Options()
		options |= QFileDialog.ReadOnly
		media_files, _ = QFileDialog.getOpenFileNames(self, "Choose Media Files", "", "Media Files (*.mp3 *.mp4 *.avi *.mkv);;All Files (*)", options=options)
		if media_files:
			self.selected_media_files = media_files


	def browse_destination(self):
		options = QFileDialog.Options()
		options |= QFileDialog.ShowDirsOnly
		folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder", options=options)
		if folder_path:
			folder_path = folder_path.replace('/', '\\')
			self.dest_edit.setText(folder_path)


	def update_combo_box2(self):
		selected_option = self.combo_box1.currentText()
		self.combo_box2.clear()
		self.combo_box2.addItems([q["name"] for q in self.quality_options.get(selected_option, [])])


	def stop_convert_thread(self):
		if self.convert_thread and self.convert_thread.isRunning():
			self.convert_thread.finished.connect(self.handle_thread_finished)
			self.convert_thread.terminate()  # Terminate the thread to ensure it exits
			self.convert_thread.wait()


	def handle_thread_finished(self):
		self.convert_thread.finished.disconnect(self.handle_thread_finished)
		self.convert_thread.wait()


	def convert(self):
		self.stop_convert_thread()

		selected_format = self.combo_box1.currentText()
		selected_quality_index = self.combo_box2.currentIndex()

		if selected_quality_index < 0:
			self.show_error("Invalid quality option selected")
			return

		selected_quality_options = self.quality_options.get(selected_format, [])

		if selected_quality_index >= len(selected_quality_options):
			self.show_error("Invalid quality option selected")
			return

		self.destination = self.dest_edit.text()

		selected_quality_option = selected_quality_options[selected_quality_index]
		selected_quality_name = selected_quality_option["name"]
		selected_quality_ffmpeg_args = selected_quality_option["ffmpeg_args"]

		input_media_files = self.selected_media_files
		output_extension = self.format_to_extension.get(selected_format, 'mp4')
		output_media_base = f'{selected_quality_name}.{output_extension}'  # Common output base name

		output_media_files = [
			os.path.join(self.destination, f'{os.path.splitext(os.path.basename(media))[0]}_{output_media_base}')
			for media in input_media_files
		]

		conversion_threads = [
			ConversionThread(media, selected_quality_name, selected_quality_ffmpeg_args, output_media)
			for media, output_media in zip(input_media_files, output_media_files)
		]

		conversion = ConversionThread(input_media_files, selected_quality_name, selected_quality_ffmpeg_args, output_media_files)
		self.conversion_thread = conversion
		self.conversion_thread.update_progress_signal.connect(self.update_progress_text)
		if self.conversion_thread:
			self.conversion_thread.finished.connect(self.handle_conversion_finished)
			self.conversion_thread.start()


	def handle_conversion_finished(self):
		if self.conversion_thread:
			self.conversion_thread.finished.disconnect(self.handle_conversion_finished)
			self.conversion_thread = None



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




