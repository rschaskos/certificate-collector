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

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting Federal certificate generation for CNPJ: {self.cnpj}')

        try:
            # Get start date from extra_data
            start_date = self.extra_data.get('start_date', '01/01/2024')
            self.logger.info(f'Using start date: {start_date}')

            # Navigate to page
            if not self.navigate():
                return False

            # Wait for page to fully load
            self.human_delay(2000, 3000)

            # Wait for form to load
            if not self.wait_for_selector(self.selectors['cnpj_input'], timeout=15000):
                self.logger.error('CNPJ input field not found')
                self.take_screenshot('federal_no_cnpj_input')
                return False

            # Small delay before typing
            self.human_delay(500, 1000)

            # Fill CNPJ slowly
            self.logger.info('Filling CNPJ...')
            self.slow_type(self.selectors['cnpj_input'], self.cnpj)

            self.human_delay(800, 1200)
            self.take_screenshot('federal_after_cnpj')

            # Click first consult button (secondary)
            self.human_delay(500, 1000)
            if not self.click_element(self.selectors['consultar_button']):
                return False

            self.logger.info('Waiting for date input form...')
            self.human_delay(1500, 2500)

            # Wait for date input to appear
            if not self.wait_for_selector(self.selectors['data_input'], timeout=15000):
                self.logger.error('Date input field not found')
                self.take_screenshot('federal_no_date_input')
                return False

            # Small delay before typing date
            self.human_delay(500, 1000)

            # Fill start date slowly
            self.logger.info('Filling date...')
            self.slow_type(self.selectors['data_input'], start_date)

            self.human_delay(800, 1200)
            self.take_screenshot('federal_after_date')

            # Click submit button
            self.human_delay(500, 1000)
            if not self.click_element(self.selectors['submit_button']):
                return False

            # Wait for certificate to be generated
            self.logger.info('Waiting for certificate generation...')
            self.page.wait_for_load_state('networkidle', timeout=30000)

            # Wait extra time for rendering
            self.human_delay(3000, 5000)

            self.take_screenshot('federal_after_submit')

            # Save page as PDF
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'Federal_{self.cnpj}_{timestamp}.pdf'
            filepath = self.config.get_path('downloads') / filename

            self.page.pdf(path=str(filepath), format='A4', print_background=True)
            self.logger.info(f'Federal certificate saved successfully: {filename}')
            return True

        except Exception as e:
            self.logger.error(f'Error generating Federal certificate: {e}', exc_info=True)
            self.take_screenshot('federal_error')
            return False
