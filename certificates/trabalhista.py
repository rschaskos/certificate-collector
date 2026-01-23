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

                # Wait for page to fully load
                self.human_delay(1500, 2500)

                # Wait for form to load
                if not self.wait_for_selector(self.selectors['cnpj_input'], timeout=10000):
                    self.logger.error('CNPJ input not found')
                    return False

                # Small delay before typing
                self.human_delay(500, 1000)

                # Fill CNPJ slowly
                self.logger.info('Filling CNPJ...')
                self.slow_type(self.selectors['cnpj_input'], self.cnpj)

                self.human_delay(800, 1200)

                # Request CAPTCHA from user via callback (page is visible now)
                captcha_callback = self.extra_data.get('captcha_callback')
                if not captcha_callback:
                    self.logger.error('CAPTCHA callback not provided')
                    return False

                self.logger.info('Aguardando CAPTCHA do usuário...')
                captcha = captcha_callback()

                if not captcha:
                    self.logger.warning('CAPTCHA not provided by user')
                    return False

                # Small delay before typing CAPTCHA
                self.human_delay(500, 1000)

                # Fill CAPTCHA slowly
                self.logger.info('Filling CAPTCHA...')
                self.slow_type(self.selectors['captcha_input'], captcha)

                self.human_delay(800, 1200)

                # Submit form
                self.human_delay(500, 1000)
                if not self.click_element(self.selectors['submit_button']):
                    return False

                # Wait for response
                self.page.wait_for_load_state('networkidle', timeout=10000)
                self.human_delay(1500, 2500)

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

                    # Wait for PDF to fully load
                    self.human_delay(2000, 3000)

                    # Save the page as PDF
                    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                    filename = f'Trabalhista_{self.cnpj}_{timestamp}.pdf'
                    filepath = self.config.get_path('downloads') / filename

                    self.page.pdf(path=str(filepath), format='A4', print_background=True)
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
