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

            # Wait for the form to load
            if not self.wait_for_selector(self.selectors['cnpj_input'], timeout=10000):
                self.logger.error('CNPJ input field not found')
                self.take_screenshot('estadual_no_cnpj_input')
                return False

            # Fill CNPJ
            if not self.fill_input(self.selectors['cnpj_input'], self.cnpj):
                return False

            # Click submit button
            if not self.click_element(self.selectors['submit_button']):
                return False

            # Wait for modal with table to appear
            self.logger.info('Waiting for certificates modal...')
            if not self.wait_for_selector(self.selectors['modal_table'], timeout=15000):
                self.logger.error('Modal with certificates table not found')
                self.take_screenshot('estadual_no_modal')
                return False

            # Take screenshot for debugging
            self.take_screenshot('estadual_after_submit')

            # Wait a moment for table to fully render
            self.page.wait_for_timeout(1000)

            # Click download button of first row (most recent certificate)
            download_button = self.selectors['download_button']
            if not self.wait_for_selector(download_button, timeout=5000):
                self.logger.error('Download button not found')
                self.take_screenshot('estadual_no_download_button')
                return False

            # Download PDF
            self.logger.info('Clicking download button...')
            with self.page.expect_download(timeout=self.config.get_timeout('download_wait')) as download_info:
                self.page.locator(download_button).first.click()

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
