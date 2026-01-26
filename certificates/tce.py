"""
TCE-PR Certificate implementation - Certidão Liberatória do TCE-PR
"""

from datetime import datetime
from playwright.sync_api import FrameLocator
from certificates.base import BaseCertificate


class TCECertificate(BaseCertificate):
    """Generates TCE-PR (Tribunal de Contas do Paraná) certificate."""

    def _get_cert_type(self) -> str:
        return 'tce'

    def _get_frame_or_page(self):
        """
        Check if form is inside an iframe and return appropriate locator.
        Returns the iframe frame_locator if found, otherwise the page itself.
        """
        # Check for iframes
        iframes = self.page.locator('iframe')
        iframe_count = iframes.count()

        if iframe_count > 0:
            self.logger.info(f'Found {iframe_count} iframe(s), checking for form...')
            for i in range(iframe_count):
                frame = self.page.frame_locator(f'iframe >> nth={i}')
                # Check if CNPJ input exists in this frame
                try:
                    cnpj_in_frame = frame.locator('input').first
                    if cnpj_in_frame.count() > 0:
                        self.logger.info(f'Form found in iframe {i}')
                        return frame
                except Exception:
                    continue

        return None

    def generate(self) -> bool:
        """
        Generate TCE-PR certificate.

        Flow:
        1. Navigate to page
        2. Find CNPJ input (may be in iframe)
        3. Fill CNPJ (slow_type for human-like behavior)
        4. Click Consultar
        5. Wait for "Clique aqui para visualizar" link
        6. Click link (opens new tab)
        7. Handle print dialog popup
        8. Save page as PDF

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f'Starting TCE-PR certificate generation for CNPJ: {self.cnpj}')

        try:
            # Navigate to page
            if not self.navigate():
                return False

            # Wait longer for page to fully load
            self.page.wait_for_load_state('networkidle', timeout=20000)
            self.human_delay(1000, 2000)

            # Try to find the form - check for iframe first
            frame = self._get_frame_or_page()

            # Define locator based on whether we're in an iframe or not
            if frame:
                self.logger.info('Using iframe for form interaction')
                # In iframe - use text inputs only (not hidden)
                cnpj_input = frame.locator('input[type="text"]').nth(1)  # Second text input (CNPJ)
                consultar_btn = frame.locator('input[value="Consultar"]')
            else:
                self.logger.info('Using main page for form interaction')
                # Try multiple selector strategies
                # Strategy 1: Original ID selector
                cnpj_locator = self.page.locator(self.selectors['cnpj_input'])

                if cnpj_locator.count() == 0:
                    # Strategy 2: Find by label text proximity
                    self.logger.info('Trying alternative selectors...')
                    # Look for input fields - the CNPJ field should be the second one
                    inputs = self.page.locator('input[type="text"]')
                    input_count = inputs.count()
                    self.logger.info(f'Found {input_count} text inputs')

                    if input_count >= 2:
                        cnpj_input = inputs.nth(1)  # Second text input (CNPJ)
                        consultar_btn = self.page.locator('input[value="Consultar"]')
                    else:
                        self.take_screenshot('tce_no_cnpj_input')
                        self.logger.error('Could not find CNPJ input field')
                        return False
                else:
                    cnpj_input = cnpj_locator
                    consultar_btn = self.page.locator(self.selectors['consultar_button'])

            # Wait for CNPJ input to be visible
            self.logger.info('Waiting for CNPJ input...')
            cnpj_input.wait_for(state='visible', timeout=10000)

            self.human_delay(500, 1000)

            # Fill CNPJ
            self.logger.info('Filling CNPJ...')
            cnpj_input.click()
            self.human_delay(300, 500)
            cnpj_input.type(self.cnpj, delay=100)
            self.logger.info('CNPJ filled')

            self.human_delay(500, 1000)

            # Click consultar button
            self.logger.info('Clicking Consultar button...')
            consultar_btn.click()

            # Wait for result - give more time for the link to appear
            self.page.wait_for_load_state('networkidle', timeout=15000)
            self.human_delay(2000, 3000)

            # Look for the certificate link
            self.logger.info('Waiting for certificate link...')

            cert_link = None

            # The link might be inside the iframe, so check both places
            # First try inside the iframe (where the form is)
            if frame:
                self.logger.info('Looking for certificate link inside iframe...')
                iframe_link = frame.locator('a:has-text("Clique aqui")')
                if iframe_link.count() > 0:
                    self.logger.info('Found link inside iframe')
                    cert_link = iframe_link
                else:
                    # Try by href
                    iframe_link = frame.locator('a[href*="srv_certidao"]')
                    if iframe_link.count() > 0:
                        self.logger.info('Found link by href inside iframe')
                        cert_link = iframe_link

            # If not found in iframe, try main page
            if cert_link is None or cert_link.count() == 0:
                self.logger.info('Looking for certificate link in main page...')
                # Try original selector first
                cert_link = self.page.locator(self.selectors['certidao_link'])
                self.logger.info(f'Selector {self.selectors["certidao_link"]}: count={cert_link.count()}')

                if cert_link.count() == 0:
                    cert_link = self.page.locator('a:has-text("Clique aqui para visualizar")')
                    self.logger.info(f'Text selector: count={cert_link.count()}')

                if cert_link.count() == 0:
                    cert_link = self.page.locator('a[style*="Red"]')
                    self.logger.info(f'Style selector: count={cert_link.count()}')

                if cert_link.count() == 0:
                    cert_link = self.page.locator('a[href*="srv_certidao"]')
                    self.logger.info(f'Href selector: count={cert_link.count()}')

            if cert_link is None or cert_link.count() == 0:
                self.logger.error('Certificate link not found - CNPJ may not have certificate')
                self.take_screenshot('tce_no_certidao_link')
                return False

            cert_link.wait_for(state='visible', timeout=10000)
            self.human_delay(500, 1000)

            # Get the href from the link to navigate directly
            cert_url = cert_link.get_attribute('href')
            self.logger.info(f'Certificate link URL: {cert_url}')

            # Build full URL if relative
            if cert_url and not cert_url.startswith('http'):
                # The link points to servicos.tce.pr.gov.br
                cert_url = f'https://servicos.tce.pr.gov.br/TCEPR/Tribunal/CertidaoLiberatoria/{cert_url}'

            self.logger.info(f'Full certificate URL: {cert_url}')

            # Set up handler for the print dialog (JavaScript confirm/alert)
            def handle_dialog(dialog):
                self.logger.info(f'Dialog appeared: {dialog.message}')
                dialog.dismiss()  # Click "Não" / Cancel to not print

            # Create a new page and navigate directly
            self.logger.info('Opening certificate page...')
            new_page = self.page.context.new_page()

            # Set up dialog handler BEFORE navigating
            new_page.on('dialog', handle_dialog)

            # Navigate to certificate URL
            new_page.goto(cert_url, wait_until='domcontentloaded', timeout=30000)
            self.logger.info('Certificate page opened')

            # Give time for dialog to appear and be handled
            self.human_delay(2000, 3000)

            # Wait for page to fully render
            new_page.wait_for_load_state('networkidle', timeout=15000)

            # Save page as PDF
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'TCE_PR_{self.cnpj}_{timestamp}.pdf'
            filepath = self.config.get_path('downloads') / filename

            new_page.pdf(path=str(filepath))
            self.logger.info(f'TCE-PR certificate saved: {filename}')

            # Close the new tab
            new_page.close()

            return True

        except Exception as e:
            self.logger.error(f'Error generating TCE-PR certificate: {e}', exc_info=True)
            self.take_screenshot('tce_error')
            return False
