from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox, QHBoxLayout, QSpinBox, QCheckBox
from backup.FFInc.observer import Observer
from backup.app import CREDITS_PER_SECOND, TIMESTEP


class TimerApp(QWidget, Observer):

    def __init__(self, flow_cred_system, app_manager):
        super().__init__()

        self.credits_label = QLabel()
        self.layout = QVBoxLayout()
        self.timer_label = QLabel("00:00:00")
        self.bonus_label = QLabel("(+0%) Bonus: 0")
        self.claim_bonus_button = QPushButton("Claim Bonus")
        self.start_button = QPushButton("Start")
        self.pause_resume_button = QPushButton("Pause")
        self.configure_button = QPushButton("Configure Session")
        self.pomodoro_duration = QSpinBox()
        self.pomodoro_count = QSpinBox()
        self.timer = QTimer()
        self.skip_break = QCheckBox("Skip Breaks")
        self.init_ui()
        self.app_manager.app_rented_signal.connect(self.update_after_rent)

    def init_ui(self):

        self.credits_label = QLabel(f"Wealth: {self.flow_cred_system.get_total_credits()}")
        self.layout.addWidget(self.credits_label)

        self.credits_label.setStyleSheet("font-size: 24px;")
        timer_layout = QHBoxLayout()
        self.setWindowTitle("Study Timer")
        self.layout.addWidget(self.timer_label)
        self.timer_label.setStyleSheet("font-size: 72px;")
        self.layout.addLayout(timer_layout)
        self.bonus_label.setStyleSheet("font-size: 18px;")
        self.bonus_label.hide()
        self.layout.addWidget(self.bonus_label)

        self.claim_bonus_button.setEnabled(False)
        self.claim_bonus_button.hide()
        self.claim_bonus_button.clicked.connect(self.claim_bonus)
        self.layout.addWidget(self.claim_bonus_button)

        self.pomodoro_duration.setRange(0, 120)
        self.pomodoro_duration.setSingleStep(TIMESTEP)
        self.pomodoro_duration.setPrefix("Pomodoro duration: ")
        self.pomodoro_count.setRange(1, 12)
        self.pomodoro_count.setPrefix("Count: ")
        self.pomodoro_count.setValue(2)
        self.pomodoro_duration.setMinimumWidth(230)
        self.pomodoro_count.setMinimumWidth(130)
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.pomodoro_duration)
        time_layout.addWidget(self.pomodoro_count)

        self.layout.addLayout(time_layout)
        self.hide_time_inputs()

        self.configure_button.clicked.connect(self.show_time_inputs)
        self.layout.addWidget(self.configure_button)

        button_layout = QHBoxLayout()
        self.start_button.clicked.connect(self.start_cancel_session)
        button_layout.addWidget(self.start_button)

        self.pause_resume_button.clicked.connect(self.pause_resume_session)
        self.pause_resume_button.setEnabled(False)
        button_layout.addWidget(self.pause_resume_button)
        self.skip_break.stateChanged.connect(self.is_skip_break)
        button_layout.addWidget(self.skip_break)

        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)

        self.timer.timeout.connect(self.update_timer)

    def is_skip_break(self,state):
        return state == Qt.CheckState.Checked

    def update_credits_display(self):
        self.credits_label.setText(f"Wealth: {self.flow_cred_system.get_total_credits()}")

    def show_time_inputs(self):
        self.pomodoro_duration.show()
        self.pomodoro_count.show()
        self.configure_button.setText("Confirm")
        self.configure_button.clicked.connect(self.confirm_configuration)

    def confirm_configuration(self):
        self.hide_time_inputs()
        self.configure_button.setText("Configure Session")
        self.configure_button.clicked.disconnect()
        self.configure_button.clicked.connect(self.show_time_inputs)

    def hide_time_inputs(self):
        self.pomodoro_duration.hide()
        self.pomodoro_count.hide()

    def update_timer(self):
        if self.is_running:
            if self.in_break:
                self.break_time -= 1
                self.flow_cred_system.update_credits(CREDITS_PER_SECOND)
                self.update_credits_display()
                self.update_timer_label()
                if self.break_time <= 0:
                    self.end_break()
            elif self.remaining_time > 0 and not self.is_paused:
                self.remaining_time -= 1
                self.global_remaining_time -= 1
                self.update_timer_label()
                self.flow_cred_system.update_credits(CREDITS_PER_SECOND)
                self.update_credits_display()

                if self.remaining_time <= 0:
                    self.completed_intervals += 1
                    if self.completed_intervals < self.pomodoro_count.value():
                        self.trigger_auto_break()
                    else:
                        self.end_session()
            else:
                self.end_session()

    def update_bonus_label(self):
        self.bonus_label.setText(f"(+{(self.bonus_multiplier - 1) * 100:.2f}%) Bonus: {int(self.bonus_credits)}")

    def update_timer_label(self):
        if self.in_break:
            self.timer_label.setText(f"Break: {self.break_time // 60:02}:{self.break_time % 60:02}")
        else:
            hours, remainder = divmod(int(self.global_remaining_time), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    def update_after_rent(self, message):
        QMessageBox.information(self, "App Rented", message)
        self.update_credits_display()
