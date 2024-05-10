import sys
from PySide6.QtCore import QStandardPaths, Qt, Slot, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow, QStyle, QToolBar, QPushButton, QSlider, QLabel, QListWidget, QListWidgetItem)
from PySide6.QtMultimedia import (QAudioOutput, QMediaFormat, QMediaPlayer)
from PySide6.QtMultimediaWidgets import QVideoWidget
import time

def getSupportedFormats():
    result = []
    for f in QMediaFormat().supportedFileFormats(QMediaFormat.Decode):
        mime_type = QMediaFormat(f).mimeType()
        result.append(mime_type.name())
    return result


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._playlist = []
        self._playlist_index = -1
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)

        self._player.errorOccurred.connect(self.playerError)


        #bars

        tool_bar = QToolBar()
        self.addToolBar(Qt.BottomToolBarArea, tool_bar)

        right_bar = QToolBar()
        right_bar.setMaximumWidth(180)
        self.addToolBar(Qt.RightToolBarArea, right_bar)

        #toolbars


        file_menu = self.menuBar().addMenu("File")
        icon = QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen)
        open_action = QAction(icon, "Open", self, shortcut="O", triggered=self.openFile)
        file_menu.addAction(open_action)
        
        icon = QIcon.fromTheme(QIcon.ThemeIcon.ApplicationExit)
        exit_action = QAction(icon, "Exit", self, shortcut="Q", triggered=self.close)
        file_menu.addAction(exit_action)



        control_menu = self.menuBar().addMenu("Control")
        icon = QIcon.fromTheme(QIcon.ThemeIcon.AudioVolumeMuted)
        mute_action = QAction(icon, "Mute/Unmute", self, shortcut="M", triggered=self.mute)
        control_menu.addAction(mute_action)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause)
        pause_action = QAction(icon, "Pause", self, shortcut="P", triggered=self._player.pause)
        control_menu.addAction(pause_action)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart)
        play_action = QAction(icon, "Play", self, shortcut="W", triggered=self._player.play)
        control_menu.addAction(play_action)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.GoNext)
        next_action = QAction(icon, "Next", self, shortcut="D", triggered=self.nextClicked)
        control_menu.addAction(next_action)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.GoPrevious)
        previous_action = QAction(icon, "Previous", self, shortcut="A", triggered=self.previousClicked)
        control_menu.addAction(previous_action)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStop)
        stop_action = QAction(icon, "Stop", self, shortcut="S", triggered=self.stop)
        control_menu.addAction(stop_action)




        #downbar

        style = self.style()
        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStart, style.standardIcon(QStyle.SP_MediaPlay))
        self._play_action = tool_bar.addAction(icon, "Play")
        self._play_action.triggered.connect(self._player.play)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaSkipBackward, style.standardIcon(QStyle.SP_MediaSkipBackward))
        self._previous_action = tool_bar.addAction(icon, "Previous")
        self._previous_action.triggered.connect(self.previousClicked)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackPause, style.standardIcon(QStyle.SP_MediaPause))
        self._pause_action = tool_bar.addAction(icon, "Pause")
        self._pause_action.triggered.connect(self._player.pause)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaSkipForward, style.standardIcon(QStyle.SP_MediaSkipForward))
        self._next_action = tool_bar.addAction(icon, "Next")
        self._next_action.triggered.connect(self.nextClicked)

        icon = QIcon.fromTheme(QIcon.ThemeIcon.MediaPlaybackStop, style.standardIcon(QStyle.SP_MediaStop))
        self._stop_action = tool_bar.addAction(icon, "Stop")
        self._stop_action.triggered.connect(self.stop)

        self._position_slider = QSlider(Qt.Horizontal)
        self._position_slider.setRange(0, 0)
        self._position_slider.sliderMoved.connect(self.setPosition)
        tool_bar.addWidget(self._position_slider)

        self._current_time_label = QLabel("0:00")
        tool_bar.addWidget(self._current_time_label)
        
        tool_bar.addSeparator()
        
        self._total_time_label = QLabel("0:00")
        tool_bar.addWidget(self._total_time_label)

        self.update_position_timer = QTimer(self)
        self.update_position_timer.timeout.connect(self.updatePosition)
        self.update_position_timer.start(1000)




        #video
        
        self._video_widget = QVideoWidget()
        self.setCentralWidget(self._video_widget)
        self._player.playbackStateChanged.connect(self.updateButtons)
        self._player.setVideoOutput(self._video_widget)

        self.updateButtons(self._player.playbackState())
        self._mime_types = []



        #playlist

        speed_label = QLabel("Playlist")
        right_bar.addWidget(speed_label)

        self.playlist_widget = QListWidget()
        self.playlist_widget.itemDoubleClicked.connect(self.playSelectedItem)  
        right_bar.addWidget(self.playlist_widget)



        volume_label = QLabel("Volume")
        right_bar.addWidget(volume_label)


        self._volume_slider = QSlider(Qt.Horizontal)
        self._volume_slider.setRange(0, 1000)
        self._volume_slider.setValue(500)
        self._volume_slider.sliderMoved.connect(self.setVolume)
        right_bar.addWidget(self._volume_slider)

        self._mute_button = QPushButton("Mute")
        self._mute_button.clicked.connect(self.mute)
        right_bar.addWidget(self._mute_button)

        speed_label = QLabel("Speed")
        right_bar.addWidget(speed_label)

        self._speed_buttons = {}
        speed_values = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]
        for speed in speed_values:
            button = QPushButton(f"{speed}x")
            button.clicked.connect(lambda _, s=speed: self.setPlaybackRate(s))
            self._speed_buttons[speed] = button
            right_bar.addWidget(button)

    def closeEvent(self, event):
        self.stop()
        event.accept()


    #methods

    @Slot()
    def openFile(self):
        self.stop()
        file_dialog = QFileDialog(self)

        mime_types = getSupportedFormats() 
        file_dialog.setMimeTypeFilters(mime_types)
        file_dialog.selectMimeTypeFilter("video/mp4") 

        movies_location = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)
        file_dialog.setDirectory(movies_location)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)

        if file_dialog.exec() == QDialog.Accepted:
            urls = file_dialog.selectedUrls()
            for url in urls:
                self._playlist.append(url)
                item = QListWidgetItem(url.fileName())
                self.playlist_widget.addItem(item)
            self._playlist_index = 0
            self._player.setSource(self._playlist[self._playlist_index])
            self._player.play()


    @Slot()
    def stop(self):
        if self._player.playbackState() != QMediaPlayer.StoppedState:
            self._player.stop()

    @Slot()
    def previousClicked(self):
        if self._player.position() <= 2000 and self._playlist_index > 0:
            self._playlist_index -= 1
            self._player.setSource(self._playlist[self._playlist_index])
            self._player.play()
            self.playlist_widget.setCurrentRow(self._playlist_index)
        else:
            self._player.setPosition(0)

    @Slot()
    def nextClicked(self):
        if self._playlist_index < len(self._playlist) - 1:
            self._player.stop()
            self._playlist_index += 1
            time.sleep(.01)
            self._player.setSource(self._playlist[self._playlist_index])
            self._player.play()
            self.playlist_widget.setCurrentRow(self._playlist_index)

    @Slot("QMediaPlayer::PlaybackState")
    def updateButtons(self, state):
        media_count = len(self._playlist)
        self._play_action.setEnabled(media_count > 0 and state != QMediaPlayer.PlayingState)
        self._pause_action.setEnabled(state == QMediaPlayer.PlayingState)
        self._stop_action.setEnabled(state != QMediaPlayer.StoppedState)
        self._previous_action.setEnabled(self._player.position() > 0 or self._playlist_index > 0)
        self._next_action.setEnabled(media_count > 1 and self._playlist_index < media_count - 1)

    def showStatusMessage(self, message):
        self.statusBar().showMessage(message, 5000)

    @Slot("QMediaPlayer::Error", str)
    def playerError(self, error, error_string):
        print(error_string, file=sys.stderr)
        self.showStatusMessage(error_string)

    @Slot()
    def updatePosition(self):
        if self._player.duration() > 0:
            duration_secs = self._player.duration() // 1000
            position_secs = self._player.position() // 1000

            duration_str = f"{duration_secs // 60}:{duration_secs % 60:02}"
            position_str = f"{position_secs // 60}:{position_secs % 60:02}"

            self._position_slider.setMaximum(duration_secs)
            self._position_slider.setValue(position_secs)

            self._current_time_label.setText(position_str)
            self._total_time_label.setText(duration_str)
        else:
            self._current_time_label.setText("0:00")
            self._total_time_label.setText("0:00")

    @Slot(int)
    def setPosition(self, position):
        self._player.setPosition(position * 1000)

    @Slot()
    def mute(self):
        if self._audio_output.volume() == 0:
            self._audio_output.setVolume(50)
            self._volume_slider.setValue(500)
            self._mute_button.setText("Mute")
        else:
            self._audio_output.setVolume(0)
            self._volume_slider.setValue(0)
            self._mute_button.setText("Unmute")

    @Slot()
    def playSelectedItem(self):
        selected_item = self.playlist_widget.currentItem()
        if selected_item:
            index = self.playlist_widget.row(selected_item)
            self._playlist_index = index
            self._player.stop()
            time.sleep(.01)
            self._player.setSource(self._playlist[self._playlist_index])
            self._player.play()
            volume = self._audio_output.volume() * 1000
            self._volume_slider.setValue(volume)


    @Slot(int)
    def setVolume(self, value):
        volume = value / 1000
        self._audio_output.setVolume(volume)

    @Slot(float)
    def setPlaybackRate(self, rate):
        self._player.setPlaybackRate(rate)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() / 2, available_geometry.height() / 1.5)
    main_win.setWindowTitle("SM - odtwarzacz video") 
    main_win.show()
    sys.exit(app.exec())
