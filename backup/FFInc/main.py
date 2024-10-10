if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(style_sheet)
    font_id = QFontDatabase.addApplicationFont("Rena-Regular.ttf")
    if font_id != -1:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            font = QFont(font_families[0], 12)
            app.setFont(font)
    window = AppUI()
    window.show()
    sys.exit(app.exec())