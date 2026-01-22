"""
Main window for Certificate Collector v4.0
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QTextEdit, QLabel, QProgressBar,
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QTextCursor
from core.logger import get_logger
from core.config import get_config
from core.browser import BrowserManager
from gui.dialogs import CNPJDialog, CaptchaDialog, DateDialog
from certificates.fgts import FGTSCertificate
from certificates.estadual import EstadualCertificate
from certificates.federal import FederalCertificate
from certificates.trabalhista import TrabalhistaCertificate
from certificates.simples import SimplesNacionalCertificate
from certificates.tce import TCECertificate


class CertificateWorker(QThread):
    """Worker thread for certificate generation to avoid blocking UI."""

    finished = Signal(bool, str)  # success, message
    progress = Signal(int, str)  # progress percentage, status message
    log_message = Signal(str, str)  # message, level (INFO, ERROR, etc.)
    captcha_needed = Signal(str)  # certificate type

    def __init__(self, cert_type, cnpj, extra_data=None):
        super().__init__()
        self.cert_type = cert_type
        self.cnpj = cnpj
        self.extra_data = extra_data or {}
        self.logger = get_logger('CertificateWorker')
        self.browser_manager = None
        self._captcha_response = None

    def set_captcha(self, captcha: str):
        """Set CAPTCHA from main thread."""
        self._captcha_response = captcha

    def run(self):
        """Execute certificate generation in background thread."""
        try:
            self.log_message.emit(f'Iniciando geração: {self.cert_type}', 'INFO')

            # Start browser
            self.browser_manager = BrowserManager()
            page = self.browser_manager.start()

            # Create certificate instance
            cert_class = self._get_certificate_class()
            if not cert_class:
                self.finished.emit(False, f'Tipo de certidão inválido: {self.cert_type}')
                return

            certificate = cert_class(self.cnpj, page, self.extra_data)

            # Generate certificate
            success = certificate.generate()

            if success:
                self.log_message.emit(f'Certidão {self.cert_type} gerada com sucesso!', 'SUCCESS')
                self.finished.emit(True, f'Certidão {self.cert_type} gerada com sucesso!')
            else:
                self.log_message.emit(f'Falha ao gerar certidão {self.cert_type}', 'ERROR')
                self.finished.emit(False, f'Falha ao gerar certidão {self.cert_type}')

        except Exception as e:
            self.logger.error(f'Error in worker thread: {e}', exc_info=True)
            self.log_message.emit(f'Erro: {str(e)}', 'ERROR')
            self.finished.emit(False, f'Erro: {str(e)}')

        finally:
            if self.browser_manager:
                self.browser_manager.close()

    def _get_certificate_class(self):
        """Get certificate class based on type."""
        classes = {
            'FGTS': FGTSCertificate,
            'ESTADUAL': EstadualCertificate,
            'RECEITA FEDERAL': FederalCertificate,
            'TRABALHISTA': TrabalhistaCertificate,
            'SIMPLES NACIONAL': SimplesNacionalCertificate,
            'TCE-PR': TCECertificate
        }
        return classes.get(self.cert_type)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger('MainWindow')
        self.config = get_config()
        self.cnpj = None
        self.worker = None
        self._setup_ui()

        # Get CNPJ on startup
        self._get_cnpj()

    def _setup_ui(self):
        """Setup main window UI."""
        self.setWindowTitle('Automatiza Certidões - Python v4.0')
        self.setMinimumSize(800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Title
        title = QLabel('Sistema de Automação de Certidões')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # CNPJ display
        self.cnpj_label = QLabel('CNPJ: Não informado')
        cnpj_font = QFont()
        cnpj_font.setPointSize(11)
        self.cnpj_label.setFont(cnpj_font)
        self.cnpj_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.cnpj_label)

        # Control group
        control_group = QGroupBox('Controles')
        control_layout = QHBoxLayout()
        control_group.setLayout(control_layout)

        # Certificate type combobox
        self.cert_combo = QComboBox()
        self.cert_combo.addItems([
            'FGTS',
            'ESTADUAL',
            'RECEITA FEDERAL',
            'TRABALHISTA',
            'SIMPLES NACIONAL',
            'TCE-PR',
            'GERAR TODAS CERTIDÕES'
        ])
        self.cert_combo.setCurrentText('FGTS')
        control_layout.addWidget(QLabel('Tipo:'))
        control_layout.addWidget(self.cert_combo, 1)

        # Start button
        self.start_button = QPushButton('Iniciar Automação')
        self.start_button.clicked.connect(self._start_automation)
        self.start_button.setMinimumHeight(40)
        control_layout.addWidget(self.start_button)

        # Change CNPJ button
        change_cnpj_button = QPushButton('Trocar CNPJ')
        change_cnpj_button.clicked.connect(self._get_cnpj)
        control_layout.addWidget(change_cnpj_button)

        main_layout.addWidget(control_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Console/log output
        console_group = QGroupBox('Console')
        console_layout = QVBoxLayout()
        console_group.setLayout(console_layout)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont('Courier New', 9))
        console_layout.addWidget(self.console)

        main_layout.addWidget(console_group, 1)

        # Status bar
        self.statusBar().showMessage('Pronto')

        # Initialize console
        self._log('Sistema iniciado. Selecione o tipo de certidão e clique em Iniciar Automação.', 'INFO')

    def _get_cnpj(self):
        """Get CNPJ from user."""
        cnpj = CNPJDialog.get_cnpj(self)
        if cnpj:
            self.cnpj = cnpj
            formatted_cnpj = f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}'
            self.cnpj_label.setText(f'CNPJ: {formatted_cnpj}')
            self._log(f'CNPJ definido: {formatted_cnpj}', 'INFO')
        else:
            if not self.cnpj:
                # No CNPJ, close application
                QMessageBox.warning(self, 'Aviso', 'CNPJ é obrigatório para continuar.')
                self.close()

    def _start_automation(self):
        """Start certificate generation."""
        if not self.cnpj:
            QMessageBox.warning(self, 'Aviso', 'Por favor, informe um CNPJ primeiro.')
            self._get_cnpj()
            return

        cert_type = self.cert_combo.currentText()

        if cert_type == 'GERAR TODAS CERTIDÕES':
            self._generate_all()
        else:
            self._generate_single(cert_type)

    def _generate_single(self, cert_type: str):
        """Generate a single certificate."""
        extra_data = {}

        # Check if CAPTCHA is needed
        if cert_type in ['FGTS', 'TRABALHISTA']:
            captcha = CaptchaDialog.get_captcha(self, cert_type)
            if not captcha:
                self._log('Geração cancelada: CAPTCHA não fornecido', 'WARNING')
                return
            extra_data['captcha'] = captcha

        # Check if start date is needed (Federal)
        if cert_type == 'RECEITA FEDERAL':
            start_date = DateDialog.get_start_date(self)
            if not start_date:
                self._log('Geração cancelada: Data inicial não fornecida', 'WARNING')
                return
            extra_data['start_date'] = start_date

        # Disable UI during execution
        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Create and start worker
        self.worker = CertificateWorker(cert_type, self.cnpj, extra_data)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.log_message.connect(self._log)
        self.worker.start()

    def _generate_all(self):
        """Generate all certificates sequentially."""
        self._log('Iniciando geração de todas as certidões...', 'INFO')

        cert_types = [
            'FGTS', 'ESTADUAL', 'RECEITA FEDERAL',
            'TRABALHISTA', 'SIMPLES NACIONAL', 'TCE-PR'
        ]

        # Get all required data upfront
        extra_data_map = {}

        # CAPTCHA for FGTS
        captcha = CaptchaDialog.get_captcha(self, 'FGTS')
        if captcha:
            extra_data_map['FGTS'] = {'captcha': captcha}
        else:
            self._log('FGTS será pulado: CAPTCHA não fornecido', 'WARNING')

        # Start date for Federal
        start_date = DateDialog.get_start_date(self)
        if start_date:
            extra_data_map['RECEITA FEDERAL'] = {'start_date': start_date}
        else:
            self._log('Receita Federal será pulada: Data não fornecida', 'WARNING')

        # CAPTCHA for Trabalhista
        captcha = CaptchaDialog.get_captcha(self, 'TRABALHISTA')
        if captcha:
            extra_data_map['TRABALHISTA'] = {'captcha': captcha}
        else:
            self._log('Trabalhista será pulada: CAPTCHA não fornecido', 'WARNING')

        # Generate each certificate
        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(cert_types))

        success_count = 0
        for i, cert_type in enumerate(cert_types):
            if cert_type not in extra_data_map and cert_type in ['FGTS', 'RECEITA FEDERAL', 'TRABALHISTA']:
                self._log(f'Pulando {cert_type}', 'WARNING')
                continue

            self._log(f'[{i+1}/{len(cert_types)}] Gerando {cert_type}...', 'INFO')
            self.progress_bar.setValue(i)

            extra_data = extra_data_map.get(cert_type, {})

            # Synchronous generation for batch mode
            try:
                browser_manager = BrowserManager()
                page = browser_manager.start()

                cert_class = self._get_certificate_class(cert_type)
                if cert_class:
                    certificate = cert_class(self.cnpj, page, extra_data)
                    if certificate.generate():
                        success_count += 1
                        self._log(f'{cert_type} concluída com sucesso!', 'SUCCESS')
                    else:
                        self._log(f'{cert_type} falhou', 'ERROR')

                browser_manager.close()

            except Exception as e:
                self.logger.error(f'Error generating {cert_type}: {e}', exc_info=True)
                self._log(f'Erro em {cert_type}: {str(e)}', 'ERROR')

        self.progress_bar.setValue(len(cert_types))
        self._log(f'Processo concluído: {success_count}/{len(cert_types)} certidões geradas', 'INFO')

        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)

        QMessageBox.information(
            self,
            'Concluído',
            f'Geração concluída!\n{success_count} de {len(cert_types)} certidões geradas com sucesso.'
        )

    def _get_certificate_class(self, cert_type: str):
        """Get certificate class based on type."""
        classes = {
            'FGTS': FGTSCertificate,
            'ESTADUAL': EstadualCertificate,
            'RECEITA FEDERAL': FederalCertificate,
            'TRABALHISTA': TrabalhistaCertificate,
            'SIMPLES NACIONAL': SimplesNacionalCertificate,
            'TCE-PR': TCECertificate
        }
        return classes.get(cert_type)

    def _on_worker_finished(self, success: bool, message: str):
        """Handle worker thread completion."""
        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)

        if success:
            QMessageBox.information(self, 'Sucesso', message)
        else:
            QMessageBox.warning(self, 'Erro', message)

    def _set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls."""
        self.start_button.setEnabled(enabled)
        self.cert_combo.setEnabled(enabled)
        self.statusBar().showMessage('Pronto' if enabled else 'Processando...')

    def _log(self, message: str, level: str = 'INFO'):
        """Add message to console with color coding."""
        colors = {
            'INFO': 'black',
            'SUCCESS': 'green',
            'WARNING': 'orange',
            'ERROR': 'red',
            'DEBUG': 'gray'
        }

        color = colors.get(level, 'black')
        formatted = f'<span style="color: {color};">[{level}] {message}</span>'

        self.console.append(formatted)
        self.console.moveCursor(QTextCursor.End)

    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                'Confirmação',
                'Uma operação está em andamento. Deseja realmente sair?',
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.worker.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
