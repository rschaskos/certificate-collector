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

        Flow:
        1. Navigate to page
        2. Fill CNPJ
        3. Click Consultar
        4. Wait for "Gerar PDF" button
        5. Click and wait for automatic download

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting Simples Nacional certificate generation for CNPJ: {self.cnpj}')

        try:
            # Navigate to page
            if not self.navigate():
                return False

            # Wait for page to fully load
            self.human_delay(2000, 3000)

            # Log current URL for debugging
            self.logger.info(f'Current URL: {self.page.url}')

            # Check for iframes
            iframes = self.page.frames
            self.logger.info(f'Found {len(iframes)} frames on page')
            for i, frame in enumerate(iframes):
                self.logger.info(f'Frame {i}: {frame.url}')

            # Take screenshot for debugging
            self.take_screenshot('simples_after_navigate')

            # Try to find CNPJ input in main page first
            cnpj_found = False
            target_frame = self.page

            # Check main page
            if self.page.locator('#Cnpj').count() > 0:
                self.logger.info('Found #Cnpj in main page')
                cnpj_found = True
            else:
                # Check each iframe
                for i, frame in enumerate(iframes):
                    if frame != self.page.main_frame:
                        try:
                            if frame.locator('#Cnpj').count() > 0:
                                self.logger.info(f'Found #Cnpj in frame {i}: {frame.url}')
                                target_frame = frame
                                cnpj_found = True
                                break
                        except Exception as e:
                            self.logger.debug(f'Error checking frame {i}: {e}')

            if not cnpj_found:
                self.logger.error(f'CNPJ input #Cnpj not found in any frame')
                self.take_screenshot('simples_no_cnpj_input')
                return False

            # Small delay before typing
            self.human_delay(500, 1000)

            # Fill CNPJ slowly using target frame
            self.logger.info('Filling CNPJ...')
            target_frame.locator('#Cnpj').click()
            self.human_delay(300, 600)
            target_frame.locator('#Cnpj').type(self.cnpj, delay=100)

            self.human_delay(800, 1200)

            # Click consultar button
            self.logger.info('Clicking Consultar...')
            consultar_btn = target_frame.locator('button:has-text("Consultar")')
            if consultar_btn.count() == 0:
                self.logger.error('Consultar button not found')
                self.take_screenshot('simples_no_consultar')
                return False
            consultar_btn.click()

            # Wait for result page
            self.page.wait_for_load_state('networkidle', timeout=30000)
            self.human_delay(2000, 3000)

            # Take screenshot after consultar
            self.take_screenshot('simples_after_consultar')

            # Check if "Gerar PDF" button exists
            gerar_pdf_btn = target_frame.locator('#GerarPDF')
            try:
                gerar_pdf_btn.wait_for(timeout=15000)
            except Exception:
                self.logger.error('Gerar PDF button not found - certificate may not have been generated')
                self.take_screenshot('simples_no_gerar_pdf_button')
                return False

            # Click "Gerar PDF" and wait for download
            self.logger.info('Clicking Gerar PDF and waiting for download...')

            with self.page.expect_download(timeout=self.config.get_timeout('download_wait')) as download_info:
                gerar_pdf_btn.click()

            download = download_info.value

            # Save the PDF
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'SimplesNacional_{self.cnpj}_{timestamp}.pdf'
            filepath = self.config.get_path('downloads') / filename

            download.save_as(str(filepath))
            self.logger.info(f'Simples Nacional certificate downloaded successfully: {filename}')
            return True

        except Exception as e:
            self.logger.error(f'Error generating Simples Nacional certificate: {e}', exc_info=True)
            self.take_screenshot('simples_error')
            return False
