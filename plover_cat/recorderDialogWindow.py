from PySide6.QtWidgets import QDialog
from PySide6.QtMultimedia import QMediaDevices, QMediaFormat, QMediaRecorder

from plover_cat.recorder_dialog_ui import Ui_recorderDialog

class recorderDialogWindow(QDialog, Ui_recorderDialog):
    """Set QRecorder settings for audio recording.

    :param recorder: a QMediaRecorder instance
    :type recorder: QMediaRecorder
    :return: QDialog status code inherited from the QDialog class.
    :rtype: QDialog.DialogCode, either Accepted or Rejected     
    """
    def __init__(self, recorder):
        super().__init__()
        self.setupUi(self)
        self.recorder = recorder
        self.media_format = recorder.mediaFormat()
        for input in QMediaDevices.audioInputs():
            self.audio_device.addItem(input.description(), input)        
        for container in QMediaFormat().supportedFileFormats(QMediaFormat.Encode):
            self.audio_container.addItem(QMediaFormat.fileFormatName(container), container)
        for codec in QMediaFormat().supportedAudioCodecs(QMediaFormat.Encode):
            self.audio_codec.addItem(QMediaFormat.audioCodecName(codec), codec)
        common_hertz =  [8000, 11025, 12000, 16000, 22050,  24000,  32000,  44100,
        48000, 64000, 88200, 96000, 128000, 176400, 192000]
        self.audio_sample_rate.addItem("Default", -1)
        for sample in common_hertz:
            self.audio_sample_rate.addItem(str(sample), sample)
        self.audio_sample_rate.addItems(common_hertz)
        self.audio_sample_rate.setCurrentIndex(0)
        self.audio_channels.addItem("Default", -1)
        self.audio_channels.addItem("1-channel", 1)
        self.audio_channels.addItem("2-channel", 2)
        self.audio_channels.addItem("4-channel", 4)
        self.audio_bitrate.addItem("Default", -1)
        self.audio_bitrate.addItem("32000", 32000)
        self.audio_bitrate.addItem("64000", 64000)
        self.audio_bitrate.addItem("96000", 96000)
        self.audio_bitrate.addItem("128000", 128000)
        self.audio_encoding.addItem("ConstantQualityEncoding", QMediaRecorder.ConstantQualityEncoding)
        self.audio_encoding.addItem("ConstantBitRateEncoding", QMediaRecorder.ConstantBitRateEncoding)
        self.audio_encoding.addItem("AverageBitRateEncoding", QMediaRecorder.AverageBitRateEncoding)
        self.audio_encoding.addItem("TwoPassEncoding", QMediaRecorder.TwoPassEncoding)
        self.update_codecs()
        self.audio_container.currentIndexChanged.connect(self.update_codecs)
    
    def update_codecs(self):
        current_format = QMediaFormat()
        current_format.setFileFormat(self.audio_container.currentData())
        self.audio_codec.clear()
        for codec in current_format.supportedAudioCodecs(QMediaFormat.Encode):
            self.audio_codec.addItem(QMediaFormat.audioCodecName(codec), codec)

                


