"""
Dialog windows for Certificate Collector v4.0
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class CNPJDialog(QDialog):
    """Dialog for CNPJ input with validation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cnpj = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle('Entre com o CNPJ')
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Title label
        title = QLabel('Digite o CNPJ da empresa:')
        title_font = QFont()
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        # CNPJ input
        self.cnpj_input = QLineEdit()
        self.cnpj_input.setPlaceholderText('00.000.000/0000-00')
        self.cnpj_input.setMaxLength(18)
        self.cnpj_input.returnPressed.connect(self._validate_and_accept)
        layout.addWidget(self.cnpj_input)

        # Validation label
        self.validation_label = QLabel('')
        self.validation_label.setStyleSheet('color: red;')
        layout.addWidget(self.validation_label)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton('OK')
        ok_button.clicked.connect(self._validate_and_accept)
        cancel_button = QPushButton('Cancelar')
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.cnpj_input.setFocus()

    def _validate_and_accept(self):
        """Validate CNPJ and accept if valid."""
        cnpj = self.cnpj_input.text().strip()

        # Remove formatting characters
        cnpj_numbers = ''.join(filter(str.isdigit, cnpj))

        if len(cnpj_numbers) < 14:
            self.validation_label.setText('CNPJ deve ter pelo menos 14 dígitos')
            self.cnpj_input.setFocus()
            self.cnpj_input.selectAll()
            return

        self.cnpj = cnpj_numbers
        self.accept()

    @staticmethod
    def get_cnpj(parent=None):
        """
        Show dialog and return CNPJ if accepted.

        Returns:
            CNPJ string or None if cancelled
        """
        dialog = CNPJDialog(parent)
        result = dialog.exec()

        if result == QDialog.Accepted:
            return dialog.cnpj
        return None


class CaptchaDialog(QDialog):
    """Dialog for CAPTCHA input with validation."""

    def __init__(self, parent=None, certificate_type: str = ''):
        super().__init__(parent)
        self.captcha = None
        self.certificate_type = certificate_type
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle(f'CAPTCHA - {self.certificate_type}')
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Title label
        title = QLabel('Digite o CAPTCHA exibido na página do navegador:')
        title_font = QFont()
        title_font.setPointSize(11)
        title.setFont(title_font)
        layout.addWidget(title)

        # Instruction label
        instruction = QLabel('Verifique a janela do navegador e insira o código.')
        instruction.setStyleSheet('color: gray;')
        layout.addWidget(instruction)

        # CAPTCHA input
        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText('Digite o CAPTCHA')
        self.captcha_input.returnPressed.connect(self._validate_and_accept)
        layout.addWidget(self.captcha_input)

        # Validation label
        self.validation_label = QLabel('')
        self.validation_label.setStyleSheet('color: red;')
        layout.addWidget(self.validation_label)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton('OK')
        ok_button.clicked.connect(self._validate_and_accept)
        cancel_button = QPushButton('Cancelar')
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.captcha_input.setFocus()

    def _validate_and_accept(self):
        """Validate CAPTCHA and accept if valid."""
        captcha = self.captcha_input.text().strip()

        if len(captcha) < 4:
            self.validation_label.setText('CAPTCHA deve ter pelo menos 4 caracteres')
            self.captcha_input.setFocus()
            self.captcha_input.selectAll()
            return

        self.captcha = captcha
        self.accept()

    @staticmethod
    def get_captcha(parent=None, certificate_type: str = ''):
        """
        Show dialog and return CAPTCHA if accepted.

        Args:
            parent: Parent widget
            certificate_type: Type of certificate (for title)

        Returns:
            CAPTCHA string or None if cancelled
        """
        dialog = CaptchaDialog(parent, certificate_type)
        result = dialog.exec()

        if result == QDialog.Accepted:
            return dialog.captcha
        return None


class DateDialog(QDialog):
    """Dialog for start date input (Federal certificate)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_date = '01/01/2024'  # Default
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle('Data Inicial - Certidão Federal')
        self.setModal(True)
        self.setMinimumWidth(350)

        layout = QVBoxLayout()

        # Title label
        title = QLabel('Digite a data inicial para consulta:')
        title_font = QFont()
        title_font.setPointSize(11)
        title.setFont(title_font)
        layout.addWidget(title)

        # Date input
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText('DD/MM/AAAA')
        self.date_input.setText('01/01/2024')
        self.date_input.setMaxLength(10)
        self.date_input.returnPressed.connect(self._validate_and_accept)
        layout.addWidget(self.date_input)

        # Info label
        info = QLabel('Data final será automaticamente definida como hoje.')
        info.setStyleSheet('color: gray; font-size: 9pt;')
        layout.addWidget(info)

        # Validation label
        self.validation_label = QLabel('')
        self.validation_label.setStyleSheet('color: red;')
        layout.addWidget(self.validation_label)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton('OK')
        ok_button.clicked.connect(self._validate_and_accept)
        cancel_button = QPushButton('Cancelar')
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.date_input.setFocus()
        self.date_input.selectAll()

    def _validate_and_accept(self):
        """Validate date and accept if valid."""
        date_str = self.date_input.text().strip()

        # Basic validation (DD/MM/YYYY format)
        if len(date_str) != 10 or date_str.count('/') != 2:
            self.validation_label.setText('Formato inválido. Use DD/MM/AAAA')
            self.date_input.setFocus()
            self.date_input.selectAll()
            return

        try:
            parts = date_str.split('/')
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])

            if not (1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100):
                raise ValueError()

            self.start_date = date_str
            self.accept()

        except ValueError:
            self.validation_label.setText('Data inválida')
            self.date_input.setFocus()
            self.date_input.selectAll()

    @staticmethod
    def get_start_date(parent=None):
        """
        Show dialog and return start date if accepted.

        Returns:
            Date string in DD/MM/YYYY format or None if cancelled
        """
        dialog = DateDialog(parent)
        result = dialog.exec()

        if result == QDialog.Accepted:
            return dialog.start_date
        return None
