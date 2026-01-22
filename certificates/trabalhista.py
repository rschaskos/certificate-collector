"""
Trabalhista Certificate implementation - Certidão Negativa de Débitos Trabalhistas
"""

from datetime import datetime
from certificates.base import BaseCertificate


class TrabalhistaCertificate(BaseCertificate):
    """Generates Trabalhista (TST - Labour Court) certificate with CAPTCHA."""

    def _get_cert_type(self) -> str:
        return 'trabalhista'

    def generate(self) -> bool:
        """
        Generate Trabalhista certificate.

        Returns:
            True if successful, False otherwise
        """
        max_retries = self.config.get_setting('max_captcha_retries', 3)

        for attempt in range(1, max_retries + 1):
            self.logger.info(f'[Attempt {attempt}/{max_retries}] Starting Trabalhista certificate generation for CNPJ: {self.cnpj}')

            try:
                # Navigate directly to certificate generation page
                direct_url = self.config.get_url('trabalhista_direct')
                self.logger.info(f'Navigating to {direct_url}')
                self.page.goto(direct_url, wait_until='domcontentloaded')

                # Wait for form to load
                if not self.wait_for_selector(self.selectors['cnpj_input'], timeout=10000):
                    return False

                # Fill CNPJ
                if not self.fill_input(self.selectors['cnpj_input'], self.cnpj):
                    return False

                # Get CAPTCHA from user (will be provided by GUI)
                captcha = self.extra_data.get('captcha')
                if not captcha:
                    self.logger.error('CAPTCHA not provided')
                    return False

                # Fill CAPTCHA
                if not self.fill_input(self.selectors['captcha_input'], captcha):
                    return False

                # Submit form
                if not self.click_element(self.selectors['submit_button']):
                    return False

                # Wait for response
                self.page.wait_for_load_state('networkidle', timeout=10000)

                # Check for CAPTCHA error
                error_msg = self.check_error_message(self.selectors['error_message'])
                if error_msg:
                    self.logger.warning(f'CAPTCHA validation failed: {error_msg}')
                    if attempt < max_retries:
                        self.logger.info('Retrying with new CAPTCHA...')
                        self.extra_data['captcha_retry'] = True
                        continue
                    else:
                        self.logger.error('Max CAPTCHA retries reached')
                        return False

                # Success - wait for PDF to appear
                if self.wait_for_selector(self.selectors['success_indicator'], timeout=10000):
                    self.logger.info('Certificate generated successfully')

                    # Save the page as PDF
                    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                    filename = f'Trabalhista_{self.cnpj}_{timestamp}.pdf'
                    filepath = self.config.get_path('downloads') / filename

                    self.page.pdf(path=str(filepath))
                    self.logger.info(f'Trabalhista certificate downloaded successfully: {filename}')
                    return True
                else:
                    self.logger.error('Certificate not generated (PDF embed not found)')
                    self.take_screenshot('trabalhista_no_pdf')
                    return False

            except Exception as e:
                self.logger.error(f'Error generating Trabalhista certificate: {e}', exc_info=True)
                self.take_screenshot(f'trabalhista_error_attempt_{attempt}')

                if attempt < max_retries:
                    continue
                return False

        return False
