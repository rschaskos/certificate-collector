"""
TCE-PR Certificate implementation - Certidão Liberatória do TCE-PR
"""

from datetime import datetime
from certificates.base import BaseCertificate


class TCECertificate(BaseCertificate):
    """Generates TCE-PR (Tribunal de Contas do Paraná) certificate."""

    def _get_cert_type(self) -> str:
        return 'tce'

    def generate(self) -> bool:
        """
        Generate TCE-PR certificate.

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting TCE-PR certificate generation for CNPJ: {self.cnpj}')

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

            # Wait for emit button (certificate found)
            if not self.wait_for_selector(self.selectors['emitir_button'], timeout=5000):
                self.logger.error('Emit button not found - certificate may not be available')
                self.take_screenshot('tce_no_emit_button')
                return False

            # Click emit button
            if not self.click_element(self.selectors['emitir_button']):
                return False

            # Wait for PDF to load
            self.page.wait_for_load_state('networkidle', timeout=10000)

            # The certificate should now be displayed, save as PDF
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'TCE_PR_{self.cnpj}_{timestamp}.pdf'
            filepath = self.config.get_path('downloads') / filename

            # Check if there's a new page/tab with PDF
            pages = self.page.context.pages
            if len(pages) > 1:
                pdf_page = pages[-1]
                pdf_page.bring_to_front()
                pdf_page.pdf(path=str(filepath))
                pdf_page.close()
            else:
                # PDF might be embedded in current page
                self.page.pdf(path=str(filepath))

            self.logger.info(f'TCE-PR certificate downloaded successfully: {filename}')
            return True

        except Exception as e:
            self.logger.error(f'Error generating TCE-PR certificate: {e}', exc_info=True)
            self.take_screenshot('tce_error')
            return False
