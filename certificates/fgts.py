"""
FGTS Certificate implementation - Consulta Regularidade do Empregador
"""

from datetime import datetime
from pathlib import Path
from certificates.base import BaseCertificate


class FGTSCertificate(BaseCertificate):
    """Generates FGTS (Caixa) certificate - Consulta Regularidade do Empregador."""

    def _get_cert_type(self) -> str:
        return 'fgts'

    def generate(self) -> bool:
        """
        Generate FGTS certificate.

        Note: FGTS no longer requires CAPTCHA validation.

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting FGTS certificate generation for CNPJ: {self.cnpj}')

        try:
            # Navigate to page
            if not self.navigate():
                return False

            # Wait for page to fully load
            self.human_delay(1500, 2500)

            # Wait for form
            if not self.wait_for_selector(self.selectors['cnpj_input'], timeout=10000):
                self.logger.error('CNPJ input not found')
                return False

            # Small delay before typing
            self.human_delay(500, 1000)

            # Fill CNPJ slowly
            self.logger.info('Filling CNPJ...')
            self.slow_type(self.selectors['cnpj_input'], self.cnpj)

            self.human_delay(800, 1200)

            # Submit form (no CAPTCHA needed)
            self.human_delay(500, 1000)
            if not self.click_element(self.selectors['submit_button']):
                return False

            # Wait for response
            self.page.wait_for_load_state('networkidle', timeout=10000)
            self.human_delay(1000, 1500)

            # Check for error message
            error_msg = self.check_error_message(self.selectors['error_message'])
            if error_msg:
                self.logger.error(f'Error: {error_msg}')
                self.take_screenshot('fgts_error')
                return False

            # Success - extract company name
            razao_social = self.get_text(self.selectors['razao_social'])
            if razao_social:
                razao_social = razao_social.strip()
                self.logger.info(f'Company found: {razao_social}')
            else:
                razao_social = self.cnpj

            self.human_delay(500, 1000)

            # Check the acceptance checkbox
            if not self.click_element(self.selectors['checkbox']):
                self.logger.warning('Failed to click checkbox, continuing anyway...')

            self.human_delay(500, 1000)

            # Click "Visualizar" button to load the certificate view
            if not self.click_element(self.selectors['visualizar_button']):
                self.logger.error('Failed to click Visualizar button')
                return False

            # Wait for the certificate page to be fully loaded
            self.page.wait_for_load_state('networkidle', timeout=15000)

            # Wait for the print button to appear (indicates certificate is ready)
            self.logger.info('Waiting for certificate page to fully render...')
            if not self.wait_for_selector(self.selectors['print_button'], timeout=15000):
                self.logger.warning('Print button not found, but continuing...')

            # Additional wait to ensure page is fully rendered
            self.human_delay(2000, 3000)

            # Save certificate page as PDF (avoids print dialog)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            # Sanitize razao_social for filename (remove invalid chars)
            safe_name = "".join(c for c in razao_social if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name[:50]  # Limit length
            filename = f'FGTS_{safe_name}_{timestamp}.pdf'
            filepath = self.config.get_path('downloads') / filename

            # Save current page as PDF using Playwright
            self.page.pdf(path=str(filepath), format='A4', print_background=True)

            self.logger.info(f'FGTS certificate saved successfully: {filename}')
            return True

        except Exception as e:
            self.logger.error(f'Error generating FGTS certificate: {e}', exc_info=True)
            self.take_screenshot('fgts_error')
            return False
