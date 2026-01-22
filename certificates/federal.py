"""
Federal Certificate implementation - Certidão de Débitos Federais (Receita Federal)
"""

from datetime import datetime
from certificates.base import BaseCertificate


class FederalCertificate(BaseCertificate):
    """Generates Federal tax certificate (Receita Federal)."""

    def _get_cert_type(self) -> str:
        return 'federal'

    def generate(self) -> bool:
        """
        Generate Federal certificate.

        Requires extra_data with 'start_date' in DD/MM/YYYY format.
        End date is automatically set to today.

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting Federal certificate generation for CNPJ: {self.cnpj}')

        try:
            # Get dates
            start_date = self.extra_data.get('start_date', '01/01/2024')
            end_date = datetime.now().strftime('%d/%m/%Y')

            self.logger.info(f'Date range: {start_date} to {end_date}')

            # Navigate to page
            if not self.navigate():
                return False

            # Wait for form to load
            if not self.wait_for_selector(self.selectors['cnpj_input'], timeout=10000):
                return False

            # Fill CNPJ
            if not self.fill_input(self.selectors['cnpj_input'], self.cnpj):
                return False

            # Fill start date
            if not self.fill_input(self.selectors['data_inicio_input'], start_date):
                return False

            # Fill end date
            if not self.fill_input(self.selectors['data_fim_input'], end_date):
                return False

            # Click emit button
            if not self.click_element(self.selectors['emitir_button']):
                return False

            # Wait for certificate to be generated
            self.page.wait_for_load_state('networkidle', timeout=15000)

            # Look for download link or PDF embed
            if self.wait_for_selector(self.selectors['download_link'], timeout=5000):
                # Download via link
                with self.page.expect_download(timeout=self.config.get_timeout('download_wait')) as download_info:
                    self.page.click(self.selectors['download_link'])

                download = download_info.value
                timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                filename = f'Federal_{self.cnpj}_{timestamp}.pdf'
                filepath = self.config.get_path('downloads') / filename

                download.save_as(str(filepath))
                self.logger.info(f'Federal certificate downloaded successfully: {filename}')
                return True
            else:
                # PDF might be embedded, try to print to PDF
                timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                filename = f'Federal_{self.cnpj}_{timestamp}.pdf'
                filepath = self.config.get_path('downloads') / filename

                self.page.pdf(path=str(filepath))
                self.logger.info(f'Federal certificate saved as PDF: {filename}')
                return True

        except Exception as e:
            self.logger.error(f'Error generating Federal certificate: {e}', exc_info=True)
            self.take_screenshot('federal_error')
            return False
