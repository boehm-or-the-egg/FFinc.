from PyQt6.QtWidgets import QWidget, QMessageBox
from backup.FFInc.subject import Subject
from file_manager import FileManager

CREDITS_PER_SECOND = 3
CREDITS_SAVE_FILE = "../app_data.json"
CHECK_INTERVAL_RUNNING = 5
UNVAULT_FEE = 120000
SIZE_THRESHOLD = 2048 * 1024
TIMESTEP = 1

class Session(QWidget, Subject):

    def __init__(self, flow_cred_system, app_manager):
        super().__init__()

        self.global_remaining_time = None
        self.file_manager = FileManager()
        self.flow_cred_system = flow_cred_system
        self.remaining_time = 0
        self.app_manager = app_manager
        self.is_running = False
        self.is_paused = False
        self.session_completed = False
        self.bonus_multiplier = 1.0
        self.bonus_credits = 0
        self.auto_pause_duration = 0
        self.break_time = 0
        self.in_break = False
        self.completed_intervals = 0

    def trigger_auto_break(self):
        self.in_break = True
        self.break_time = int(self.pomodoro_duration.value() * 60 * 0.2)
        self.update_timer_label()
        self.timer.start(1000)
        QMessageBox.information(self, "Pomodoro Complete",
                                "Good Work! I started a break for you, make sure you use it to your advantage.")
    def end_break(self):
        self.in_break = False
        self.start_next_subsession()

    def start_next_subsession(self):
        if self.completed_intervals < self.pomodoro_count.value():
            self.remaining_time = self.pomodoro_duration.value() * 60
            self.update_timer_label()
        else:
            self.end_session()

    def start_session(self):
        session_duration = self.pomodoro_duration.value() * 60
        total_duration = session_duration * self.pomodoro_count.value()

        if session_duration <= 0:
            QMessageBox.warning(self, "Invalid Input", "Please select a non-zero time.")
            return

        self.auto_pause_duration = session_duration * 0.2
        self.remaining_time = session_duration
        self.global_remaining_time = total_duration
        self.session_completed = False

        self.claim_bonus_button.setEnabled(False)
        self.configure_button.setEnabled(False)
        self.claim_bonus_button.hide()
        self.bonus_label.hide()

        if total_duration > 3600:
            self.bonus_multiplier = self.calculate_bonus(total_duration / 3600)
            self.bonus_credits = (total_duration + (self.auto_pause_duration * (self.pomodoro_count.value() - 1))) * (
                    self.bonus_multiplier - 1)
            self.update_bonus_label()
            self.bonus_label.show()
        else:
            self.bonus_multiplier = 1.0
            self.bonus_credits = 0

        self.update_timer_label()
        self.is_running = True
        self.is_paused = False
        self.pause_resume_button.setEnabled(True)

        self.timer.start(1000)

    def end_session(self, interrupted=False):
        self.timer.stop()
        self.is_running = False
        self.start_button.setText("Start")
        self.pause_resume_button.setEnabled(False)
        self.configure_button.setEnabled(True)

        if interrupted:
            self.bonus_label.hide()
            self.claim_bonus_button.hide()
            QMessageBox.information(self, "Session Interrupted",
                                    "Your session was interrupted. No bonus will be applied.")
        else:
            if self.global_remaining_time <= 0:
                if self.bonus_credits > 0:
                    self.claim_bonus_button.setEnabled(True)
                    self.claim_bonus_button.show()

            QMessageBox.information(self, "Session Complete", "Great job! You completed your study session!")

    def claim_bonus(self):
        self.flow_cred_system.update_credits(self.bonus_credits)
        self.update_credits_display()
        self.bonus_credits = 0
        self.bonus_label.hide()
        self.claim_bonus_button.hide()
        QMessageBox.information(self, "Bonus Claimed", "You have claimed your bonus credits!")

    def interrupt_session(self):
        reply = QMessageBox.question(self, "Interrupt Session",
                                     "Are you sure you want to interrupt the session?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.end_session(interrupted=True)

    def start_cancel_session(self):
        if self.is_running:
            self.is_running = False
            self.start_button.setText("Start")
            self.interrupt_session()
        elif self.pomodoro_duration.value() != 0:
            self.is_running = True
            self.start_button.setText("Cancel")
            self.start_session()
        else:
            QMessageBox.warning(self, "Error", "Session is not properly configured.")

    def pause_resume_session(self):
        if self.is_paused:
            self.is_paused = False
            self.pause_resume_button.setText("Pause")
            self.timer.start(1000)
        else:
            self.is_paused = True
            self.pause_resume_button.setText("Resume")
            self.timer.stop()

    def update_after_rent(self, message):
        QMessageBox.information(self, "App Rented", message)
        self.update_credits_display()

    @staticmethod
    def calculate_bonus(duration):
        if duration > 1:
            return 1 + (2 * duration ** 2) / (100 + 2 * duration ** 2)
        else:
            return 1