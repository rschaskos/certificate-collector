"""
FGTS Certificate implementation - Consulta Regularidade do Empregador
"""

from datetime import datetime
from pathlib import Path
from certificates.base import BaseCertificate


class FGTSCertificate(BaseCertificate):
    """Generates FGTS (Caixa) certificate with CAPTCHA handling."""

    def _get_cert_type(self) -> str:
        return 'fgts'

    def generate(self) -> bool:
        """
        Generate FGTS certificate.

        Returns:
            True if successful, False otherwise
        """
        max_retries = self.config.get_setting('max_captcha_retries', 3)

        for attempt in range(1, max_retries + 1):
            self.logger.info(f'[Attempt {attempt}/{max_retries}] Starting FGTS certificate generation for CNPJ: {self.cnpj}')

            try:
                # Navigate to page
                if not self.navigate():
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
                        # Signal GUI to request new CAPTCHA
                        self.extra_data['captcha_retry'] = True
                        continue
                    else:
                        self.logger.error('Max CAPTCHA retries reached')
                        return False

                # Success - extract company name
                razao_social = self.get_text(self.selectors['razao_social'])
                if razao_social:
                    razao_social = razao_social.strip()
                    self.logger.info(f'Company found: {razao_social}')
                else:
                    razao_social = self.cnpj

                # Check the acceptance checkbox
                if not self.click_element(self.selectors['checkbox']):
                    self.logger.warning('Failed to click checkbox, continuing anyway...')

                # Click download/visualize button
                if not self.click_element(self.selectors['download_button']):
                    return False

                # Wait for PDF to load
                self.page.wait_for_load_state('networkidle', timeout=15000)

                # The PDF opens in a new window/tab - switch to it
                pages = self.page.context.pages
                if len(pages) > 1:
                    pdf_page = pages[-1]  # Get the newest page
                    pdf_page.bring_to_front()

                    # Save PDF
                    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                    filename = f'FGTS_{razao_social}_{timestamp}.pdf'
                    filepath = self.config.get_path('downloads') / filename

                    # Download PDF using Playwright
                    pdf_content = pdf_page.pdf()
                    filepath.write_bytes(pdf_content)

                    self.logger.info(f'FGTS certificate downloaded successfully: {filename}')
                    pdf_page.close()
                    return True
                else:
                    self.logger.error('PDF window did not open')
                    self.take_screenshot('fgts_pdf_not_opened')
                    return False

            except Exception as e:
                self.logger.error(f'Error generating FGTS certificate: {e}', exc_info=True)
                self.take_screenshot(f'fgts_error_attempt_{attempt}')

                if attempt < max_retries:
                    continue
                return False

        return False
