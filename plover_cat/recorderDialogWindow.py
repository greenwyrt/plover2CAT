from PyQt5.QtWidgets import QDialog

from plover_cat.recorder_dialog_ui import Ui_recorderDialog

class recorderDialogWindow(QDialog, Ui_recorderDialog):
    """Set QRecorder settings for audio recording
    :param recorder: a QAudioRecorder instance
    :type recorder: QAudioRecorder
    :return: QDialog status code inherited from the QDialog class.
        Editor will access ``affix_dict`` from instance.
    :rtype: QDialog.DialogCode, either Accepted or Rejected     
    """
    def __init__(self, recorder):
        super().__init__()
        self.setupUi(self)
        self.recorder = recorder
        self.audio_device.addItems(self.recorder.audioInputs())
        self.audio_codec.addItems(self.recorder.supportedAudioCodecs())
        self.audio_container.addItems(self.recorder.supportedContainers())
        self.audio_sample_rate.addItems([str(rate) for rate in reversed(self.recorder.supportedAudioSampleRates()[0]) if rate < 50000])
        self.audio_channels.addItem("Default", -1)
        self.audio_channels.addItem("1-channel", 1)
        self.audio_channels.addItem("2-channel", 2)
        self.audio_channels.addItem("4-channel", 4)
        self.audio_bitrate.addItem("Default", -1)
        self.audio_bitrate.addItem("32000", 32000)
        self.audio_bitrate.addItem("64000", 64000)
        self.audio_bitrate.addItem("96000", 96000)
        self.audio_bitrate.addItem("128000", 128000)        
    
        