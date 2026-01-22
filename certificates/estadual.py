"""
Estadual (Paraná) Certificate implementation - Certidão de Débitos Tributários Estadual
"""

from datetime import datetime
from certificates.base import BaseCertificate


class EstadualCertificate(BaseCertificate):
    """Generates Paraná State tax certificate."""

    def _get_cert_type(self) -> str:
        return 'estadual'

    def generate(self) -> bool:
        """
        Generate Estadual (PR) certificate.

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting Estadual certificate generation for CNPJ: {self.cnpj}')

        try:
            # Navigate to page
            if not self.navigate():
                return False

            # Fill CNPJ
            if not self.fill_input(self.selectors['cnpj_input'], self.cnpj):
                return False

            # Click submit
            if not self.click_element(self.selectors['submit_button']):
                return False

            # Wait for response
            self.page.wait_for_load_state('networkidle', timeout=10000)

            # Check for error message
            error_msg = self.check_error_message(self.selectors['error_message'])
            if error_msg:
                self.logger.error(f'CNPJ validation error: {error_msg}')
                return False

            # Wait for and click download link
            if not self.wait_for_selector(self.selectors['download_link'], timeout=5000):
                self.logger.error('Download link not found')
                self.take_screenshot('estadual_no_download_link')
                return False

            # Download PDF
            with self.page.expect_download(timeout=self.config.get_timeout('download_wait')) as download_info:
                self.page.click(self.selectors['download_link'])

            download = download_info.value
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'Estadual_PR_{self.cnpj}_{timestamp}.pdf'
            filepath = self.config.get_path('downloads') / filename

            download.save_as(str(filepath))
            self.logger.info(f'Estadual certificate downloaded successfully: {filename}')
            return True

        except Exception as e:
            self.logger.error(f'Error generating Estadual certificate: {e}', exc_info=True)
            self.take_screenshot('estadual_error')
            return False
