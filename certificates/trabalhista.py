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

        Flow:
        1. Navigate to direct URL
        2. Fill CNPJ
        3. Request CAPTCHA from user (page is visible)
        4. Fill CAPTCHA
        5. Click submit and wait for PDF download

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

                # Fill CAPTCHA slowly (lowercase as indicated by the input style)
                self.logger.info('Filling CAPTCHA...')
                self.slow_type(self.selectors['captcha_input'], captcha.lower())

                self.human_delay(800, 1200)

                # Click submit and wait for PDF download
                self.logger.info('Clicking submit and waiting for PDF download...')

                with self.page.expect_download(timeout=self.config.get_timeout('download_wait')) as download_info:
                    self.page.click(self.selectors['submit_button'])

                download = download_info.value

                # Check if download started (no error)
                # If there's a CAPTCHA error, the download won't happen and we'll catch the timeout

                # Save the PDF
                timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                filename = f'Trabalhista_{self.cnpj}_{timestamp}.pdf'
                filepath = self.config.get_path('downloads') / filename

                download.save_as(str(filepath))
                self.logger.info(f'Trabalhista certificate downloaded successfully: {filename}')
                return True

            except Exception as e:
                error_str = str(e)

                # Check if it's a timeout (likely CAPTCHA error)
                if 'Timeout' in error_str or 'timeout' in error_str:
                    # Check for error message on page
                    error_msg = self.check_error_message(self.selectors['error_message'])
                    if error_msg:
                        self.logger.warning(f'CAPTCHA validation failed: {error_msg}')
                    else:
                        self.logger.warning('Download timeout - possibly wrong CAPTCHA')

                    if attempt < max_retries:
                        self.logger.info('Retrying with new CAPTCHA...')
                        self.extra_data['captcha_retry'] = True
                        continue
                    else:
                        self.logger.error('Max CAPTCHA retries reached')
                        self.take_screenshot('trabalhista_max_retries')
                        return False
                else:
                    self.logger.error(f'Error generating Trabalhista certificate: {e}', exc_info=True)
                    self.take_screenshot(f'trabalhista_error_attempt_{attempt}')

                    if attempt < max_retries:
                        continue
                    return False

        return False
