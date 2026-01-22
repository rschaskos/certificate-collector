"""
Simples Nacional Certificate implementation - Consulta Optantes pelo Simples Nacional
"""

from datetime import datetime
from certificates.base import BaseCertificate


class SimplesNacionalCertificate(BaseCertificate):
    """Generates Simples Nacional certificate."""

    def _get_cert_type(self) -> str:
        return 'simples'

    def generate(self) -> bool:
        """
        Generate Simples Nacional certificate.

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting Simples Nacional certificate generation for CNPJ: {self.cnpj}')

        try:
            # Navigate to page
            if not self.navigate():
                return False

            # Wait for form to load
            if not self.wait_for_selector(self.selectors['cnpj_input'], timeout=10000):
                return False

            # Fill CNPJ
            if not self.fill_input(self.selectors['cnpj_input'], self.cnpj):
                return False

            # Click consultar button
            if not self.click_element(self.selectors['consultar_button']):
                return False

            # Wait for result page
            self.page.wait_for_load_state('networkidle', timeout=10000)

            # Check if print button exists
            if not self.wait_for_selector(self.selectors['imprimir_button'], timeout=5000):
                self.logger.error('Print button not found - certificate may not have been generated')
                self.take_screenshot('simples_no_print_button')
                return False

            # Click print button (opens print dialog, but we'll capture the page)
            self.logger.info('Certificate generated, saving as PDF')

            # Save the page as PDF before clicking print
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'SimplesNacional_{self.cnpj}_{timestamp}.pdf'
            filepath = self.config.get_path('downloads') / filename

            self.page.pdf(path=str(filepath))
            self.logger.info(f'Simples Nacional certificate downloaded successfully: {filename}')
            return True

        except Exception as e:
            self.logger.error(f'Error generating Simples Nacional certificate: {e}', exc_info=True)
            self.take_screenshot('simples_error')
            return False
