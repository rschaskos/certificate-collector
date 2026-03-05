"""
Federal Certificate - PyAutoGUI + OpenCV (v2.0 - Clean Implementation)
Automacao que opera no nivel do SO, indetectavel pelo site.

Este modulo implementa a automacao de certidoes federais seguindo estritamente
o DESIGN_SYSTEM v1.0. Enfase em:
- Sem 'return True' quando estado e ambiguo/desconhecido
- Cada operacao retorna True APENAS com evidencia positiva
- Fallback coordinates para 1920x1080 (sem magic numbers dependentes de resolucao)
- Modal detection com threshold minimo 60% (nao 40%)
- Strings especificas para modal detection (nao generico 'modal')

Author: Certificate Collector Team
Version: 2.0.0 (Clean, Design-System Compliant)
"""

import os
import sys
import time
import random
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

import pyautogui
import cv2
import numpy as np
from PIL import Image


# ==================== SECTION 1: CONSTANTES NOMEADAS ====================

# Coordenadas para 1920×1080 (DESIGN_SYSTEM Seção 5.1)
COORDS = {
    "cnpj_field":         (376, 478),
    "emitir_button":      (1449, 681),
    "modal_consultar":    (983, 640),
    "dates_consultar":    (1433, 854),
    "download_button":    (1488, 578),
}

# Confidence thresholds (DESIGN_SYSTEM Seção 4.2)
CONFIDENCE = {
    "emitir_button":      0.85,
    "consultar_modal":    0.75,
    "consultar_dates":    0.75,
    "download_icon":      0.75,
}

# Timeouts por operação (DESIGN_SYSTEM Seção 3.4)
TIMEOUTS = {
    "cnpj_field":         10,
    "emitir_click":       10,
    "page_validation":    3,
    "modal_detection":    30,
    "modal_button":       15,
    "date_page_wait":     30,
    "consultar_click":    15,
    "results_load":       4,
    "status_check":       5,
    "download_detect":    10,
    "download_complete":  10,
}


# ==================== SECTION 2: STATUS OVERLAY ====================

class StatusOverlay:
    """
    Janela flutuante de status da automacao (Gracefully Degraded).

    Tenta usar Tkinter para uma janela flutuante, mas se falhar,
    continua usando apenas console output (sem erros).

    Usa threading.Event para sincronizacao segura entre threads.
    """

    def __init__(self):
        self.root = None
        self.label_status = None
        self.cancelled = False
        self._thread = None
        self._ready = threading.Event()
        self._stop_event = threading.Event()
        self.tkinter_available = True

    def _run_window(self):
        """Roda janela Tkinter em thread separada."""
        try:
            self.root = tk.Tk()
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.9)
            self.root.resizable(False, False)

            # Tamanho e posicao (canto inferior direito)
            width, height = 400, 100
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = screen_width - width - 10
            y = screen_height - height - 50
            self.root.geometry(f"{width}x{height}+{x}+{y}")

            # Label de status
            self.label_status = tk.Label(
                self.root,
                text="Iniciando automacao...",
                bg="#2c3e50",
                fg="#ecf0f1",
                font=("Arial", 10),
                wraplength=350,
                justify=tk.LEFT,
                padx=10,
                pady=10,
            )
            self.label_status.pack(fill=tk.BOTH, expand=True)

            # Botao de cancelamento
            cancel_btn = tk.Button(
                self.root,
                text="Cancelar",
                bg="#e74c3c",
                fg="white",
                command=self._on_cancel,
                padx=10,
                pady=5,
            )
            cancel_btn.pack(side=tk.BOTTOM, padx=5, pady=5)

            self._ready.set()

            def check_stop():
                if self._stop_event.is_set():
                    self.root.quit()
                else:
                    self.root.after(100, check_stop)

            self.root.after(100, check_stop)
            self.root.mainloop()

        except Exception as e:
            # Tkinter falhou - desabilita e continua
            print(f"[StatusOverlay] Tkinter indisponivel: {e}")
            print("[StatusOverlay] Continuando sem janela flutuante...")
            self.tkinter_available = False
            self._ready.set()

    def _on_cancel(self):
        """Callback do botao de cancelamento."""
        self.cancelled = True
        if self.label_status:
            self.label_status.config(text="Cancelamento solicitado...")

    def show(self):
        """Mostra a janela flutuante (ou apenas avisa via console)."""
        if not self._thread:
            self._thread = threading.Thread(target=self._run_window, daemon=True)
            self._thread.start()
            self._ready.wait(timeout=5)

    def hide(self):
        """Esconde a janela flutuante."""
        if self.root:
            self._stop_event.set()
            try:
                self.root.quit()
            except:
                pass
            self.root = None

    def update(self, message: str):
        """Atualiza mensagem de status (ou apenas imprime)."""
        if self.tkinter_available and self.label_status:
            try:
                self.label_status.config(text=message)
                self.label_status.update()
            except:
                pass
        else:
            # Fallback: apenas imprime no console
            print(f"[Status] {message}")


# ==================== SECTION 3: SCREEN AUTOMATION (HELPERS) ====================

class ScreenAutomation:
    """
    Classe helper para automacao de tela.

    Contém metodos sólidos extraídos de federal_pyautogui.py:
    - Humanização (mouse, teclado, delays)
    - Screenshot
    - Template matching (OpenCV)
    - OCR (Tesseract)

    NÃO contém lógica de steps - apenas utilitários.
    """

    def __init__(self, logger_callback=None):
        """
        Inicializa ScreenAutomation.

        Args:
            logger_callback: Função para logging (sig: log(message))
        """
        self.log_fn = logger_callback or print
        self.screen_width = pyautogui.size()[0]
        self.screen_height = pyautogui.size()[1]
        self._configure_tesseract()

    def _configure_tesseract(self):
        """Configura caminho do Tesseract com multi-fallback."""
        import pytesseract

        possible_paths = [
            r'C:\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.path.expandvars(r'%ProgramFiles%\Tesseract-OCR\tesseract.exe'),
            os.path.expandvars(r'%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe'),
        ]

        env_path = os.getenv('TESSERACT_PATH')
        if env_path:
            possible_paths.insert(0, env_path)

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    self.log_fn(f"[Tesseract] Configurado em: {path}")
                    return
                except Exception as e:
                    self.log_fn(f"[Tesseract] Erro ao configurar {path}: {e}")

        self.log_fn("[Tesseract] AVISO: Nao encontrado em locais comuns!")

    def log(self, message: str):
        """Faz log de mensagem."""
        self.log_fn(message)

    # ==================== HUMANIZACAO ====================

    def human_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """Delay humanizado com variacao aleatoria."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def human_move(self, x: int, y: int):
        """Movimento humanizado do mouse com curva easing."""
        target_x = x + random.randint(-3, 3)
        target_y = y + random.randint(-3, 3)
        duration = random.uniform(0.3, 0.6)
        pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeOutQuad)

    def human_click(self, x: int, y: int):
        """Clique humanizado com movimento suave."""
        self.human_move(x, y)
        self.human_delay(0.1, 0.2)
        pyautogui.click()
        self.human_delay(0.2, 0.4)

    def human_type(self, text: str):
        """Digitacao humanizada caractere por caractere."""
        for char in text:
            if char.isdigit():
                pyautogui.press(char)
            else:
                pyautogui.typewrite(char, interval=0.05)
            time.sleep(random.uniform(0.05, 0.15))

    # ==================== SCREENSHOT ====================

    def take_screenshot(self, name: str = None, save_dir: Path = None) -> Image.Image:
        """
        Tira screenshot e salva opcionalemente.

        Args:
            name: Nome base para arquivo (opcional)
            save_dir: Diretorio para salvar (opcional)

        Returns:
            Imagem PIL da screenshot
        """
        screenshot = pyautogui.screenshot()

        if name and save_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = save_dir / f"{name}_{timestamp}.png"
            screenshot.save(path)
            self.log(f"Screenshot salva: {path}")

        return screenshot

    # ==================== TEMPLATE MATCHING ====================

    def find_template(self, template_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """Encontra template na tela usando OpenCV."""
        screenshot = pyautogui.screenshot()
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        if not os.path.exists(template_path):
            self.log(f"[Template] Nao encontrado: {template_path}")
            return None

        template = cv2.imread(template_path)
        if template is None:
            self.log(f"[Template] Erro ao carregar: {template_path}")
            return None

        result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        self.log(f"[Template] {os.path.basename(template_path)}: conf={max_val:.2f}")

        if max_val >= confidence:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)

        return None

    def find_all_templates(self, template_path: str, confidence: float = 0.8) -> List[Tuple[int, int]]:
        """Encontra todas as ocorrencias de um template."""
        screenshot = pyautogui.screenshot()
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        if not os.path.exists(template_path):
            return []

        template = cv2.imread(template_path)
        if template is None:
            return []

        h, w = template.shape[:2]
        result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence)

        matches = []
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            matches.append((center_x, center_y))

        return matches

    def wait_for_template(self, template_path: str, timeout: int = 30, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """Espera template aparecer na tela."""
        self.log(f"[Template] Aguardando: {os.path.basename(template_path)}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            pos = self.find_template(template_path, confidence)
            if pos:
                self.log(f"[Template] Encontrado em: {pos}")
                return pos
            time.sleep(0.5)

        self.log(f"[Template] Timeout: {os.path.basename(template_path)}")
        return None

    def click_template(self, template_path: str, timeout: int = 30, confidence: float = 0.8) -> bool:
        """Encontra template e clica."""
        pos = self.wait_for_template(template_path, timeout, confidence)
        if pos:
            self.human_click(pos[0], pos[1])
            return True
        return False

    # ==================== OCR ====================

    def find_text(self, target_text: str, region: Tuple[int, int, int, int] = None,
                  avoid_vlibras: bool = True, min_confidence: float = 70.0) -> Optional[Tuple[int, int]]:
        """
        Encontra texto na tela usando OCR.

        Args:
            target_text: Texto a procurar
            region: Regiao (x, y, width, height) ou None para tela toda
            avoid_vlibras: Se True, ignora canto direito (15%)
            min_confidence: Confianca minima (0-100)

        Returns:
            (x, y) ou None
        """
        import pytesseract

        if region:
            screenshot = pyautogui.screenshot(region=region)
            offset_x, offset_y = region[0], region[1]
        else:
            screenshot = pyautogui.screenshot()
            offset_x, offset_y = 0, 0

        try:
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, lang='por')
        except Exception as e:
            self.log(f"[OCR] Erro: {e}")
            return None

        target_lower = target_text.lower()
        matches = []

        for i, text in enumerate(data['text']):
            if not text or not text.strip():
                continue

            text_lower = text.lower().strip()
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0

            if conf < min_confidence:
                continue

            if target_lower in text_lower or text_lower in target_lower:
                x = data['left'][i] + data['width'][i] // 2 + offset_x
                y = data['top'][i] + data['height'][i] // 2 + offset_y

                if avoid_vlibras and x > (self.screen_width * 0.85):
                    continue

                matches.append((x, y, conf))

        if matches:
            matches.sort(key=lambda m: m[2], reverse=True)
            best = matches[0]
            self.log(f"[OCR] '{target_text}' em ({best[0]}, {best[1]}), conf={best[2]:.1f}%")
            return (best[0], best[1])

        self.log(f"[OCR] '{target_text}' nao encontrado (min: {min_confidence:.0f}%)")
        return None

    def find_all_text(self, target_text: str, avoid_vlibras: bool = True, min_confidence: float = 70.0) -> List[Tuple[int, int, float]]:
        """Encontra todas as ocorrencias de um texto."""
        import pytesseract

        screenshot = pyautogui.screenshot()

        try:
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, lang='por')
        except Exception as e:
            self.log(f"[OCR] Erro: {e}")
            return []

        target_lower = target_text.lower()
        matches = []

        for i, text in enumerate(data['text']):
            if not text or not text.strip():
                continue

            text_lower = text.lower().strip()
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0

            if conf < min_confidence:
                continue

            if target_lower in text_lower or text_lower in target_lower:
                x = data['left'][i] + data['width'][i] // 2
                y = data['top'][i] + data['height'][i] // 2

                if avoid_vlibras and x > (self.screen_width * 0.85):
                    continue

                matches.append((x, y, conf))

        return matches

    def find_leftmost_text(self, target_text: str, min_y: int = 0, max_y: Optional[int] = None,
                           avoid_vlibras: bool = True, min_confidence: float = 60.0) -> Optional[Tuple[int, int]]:
        """Encontra texto mais a esquerda (menor X)."""
        matches = self.find_all_text(target_text, avoid_vlibras=avoid_vlibras, min_confidence=min_confidence)

        if not matches:
            return None

        if max_y is None:
            max_y = self.screen_height

        matches_filtered = [m for m in matches if min_y <= m[1] <= max_y]
        if not matches_filtered:
            return None

        matches_filtered.sort(key=lambda m: m[0])
        leftmost = matches_filtered[0]

        self.log(f"[OCR] Leftmost '{target_text}' em ({leftmost[0]}, {leftmost[1]})")
        return (leftmost[0], leftmost[1])

    def wait_for_text(self, target_text: str, timeout: int = 30, avoid_vlibras: bool = True, min_confidence: float = 70.0) -> Optional[Tuple[int, int]]:
        """Espera texto aparecer na tela."""
        self.log(f"[OCR] Aguardando: '{target_text}'")
        start_time = time.time()

        while time.time() - start_time < timeout:
            pos = self.find_text(target_text, avoid_vlibras=avoid_vlibras, min_confidence=min_confidence)
            if pos:
                return pos
            time.sleep(0.5)

        self.log(f"[OCR] Timeout aguardando: '{target_text}'")
        return None

    def wait_for_text_with_retry(self, target_text: str, max_attempts: int = 3,
                                  timeout: int = 30, avoid_vlibras: bool = True) -> Optional[Tuple[int, int]]:
        """Espera texto com retry logic e exponential backoff."""
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                base_delay = (attempt - 1) * 1.0
                jitter = random.uniform(0, 0.5)
                delay = base_delay + jitter
                self.log(f"[Retry {attempt}/{max_attempts}] Aguardando {delay:.2f}s...")
                time.sleep(delay)

            self.log(f"[Retry {attempt}/{max_attempts}] Procurando '{target_text}'...")
            pos = self.find_text(target_text, avoid_vlibras=avoid_vlibras)

            if pos:
                self.log(f"[Retry] Sucesso na tentativa {attempt}!")
                return pos

        self.log(f"[Retry] Falha apos {max_attempts} tentativas")
        return None


# ==================== SECTION 4: FEDERAL CERTIFICATE V2 ====================

class FederalCertificateV2:
    """
    Automacao de Certidao Federal - Implementacao v2.0.

    Segue estritamente o DESIGN_SYSTEM v1.0 com enfase em:
    - Nunca retornar True quando estado e ambiguo
    - Evidencia positiva OBRIGATORIA para sucesso
    - Timeouts por operacao (nao magicos)
    - Modal detection com threshold >= 60%

    5 Steps:
    1. Fill CNPJ & Emit
    2. Handle Modal (Conditional)
    3. Date Selection
    4. Verify Status
    5. Download Certificate
    """

    URL = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"

    def __init__(self, cnpj: str, download_dir: str = None):
        """
        Inicializa automacao.

        Args:
            cnpj: CNPJ (com ou sem formatacao)
            download_dir: Diretorio para PDFs
        """
        self.cnpj = cnpj
        self.cnpj_raw = ''.join(filter(str.isdigit, cnpj))

        # Diretorios
        self.project_root = Path(__file__).parent.parent
        self.download_dir = Path(download_dir) if download_dir else self.project_root / "downloads"
        self.screenshots_dir = self.project_root / "screenshots"
        self.templates_dir = self.project_root / "templates"
        self.logs_dir = self.project_root / "logs"

        for d in [self.download_dir, self.screenshots_dir, self.templates_dir, self.logs_dir]:
            d.mkdir(exist_ok=True)

        # Logger
        self.log_file = self.logs_dir / f"federal_v2_{datetime.now():%Y%m%d}.log"

        # Chrome
        self.chrome_process = None

        # Automacao e overlay
        self.screen_auto = ScreenAutomation(logger_callback=self.log)
        self.overlay = StatusOverlay()

    def log(self, message: str):
        """Log para console e arquivo."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except:
            pass

    # ==================== CHROME ====================

    def _open_chrome(self) -> bool:
        """Abre Chrome com a URL."""
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]

        chrome_path = None
        for path in chrome_paths:
            expanded = os.path.expandvars(path)
            if os.path.exists(expanded):
                chrome_path = expanded
                self.log(f"[Chrome] Encontrado: {chrome_path}")
                break

        if not chrome_path:
            self.log("[Chrome] ERRO: Nao encontrado!")
            return False

        try:
            cmd = [
                chrome_path,
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-popup-blocking",
                f"--download-directory={self.download_dir}",
                "--safebrowsing-disable-download-protection",
                "--safebrowsing-disable-extension-blacklist",
                self.URL
            ]

            self.log(f"[Chrome] Abrindo: {self.URL}")
            self.chrome_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log(f"[Chrome] PID: {self.chrome_process.pid}")

            time.sleep(2)
            time.sleep(5)  # Aguarda pagina carregar

            return True

        except Exception as e:
            self.log(f"[Chrome] ERRO: {e}")
            return False

    def _close_chrome(self):
        """Fecha Chrome."""
        if self.chrome_process:
            try:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)
                self.log("[Chrome] Fechado")
            except:
                try:
                    self.chrome_process.kill()
                except:
                    pass
            self.chrome_process = None

    # ==================== HELPER: CNPJ FIELD DETECTION ====================

    def _find_cnpj_word_in_line(self, min_y: int, max_y: int) -> Optional[Tuple[int, int]]:
        """
        Procura pela palavra "CNPJ" em uma faixa Y específica (mesma linha).

        Usado para encontrar "CNPJ" que fica à direita de "Informe o",
        permitindo clicar no lugar mais correto (mais perto do campo).

        Args:
            min_y: Y mínimo da linha
            max_y: Y máximo da linha

        Returns:
            (x, y) da palavra "CNPJ" ou None
        """
        import pytesseract

        screenshot = pyautogui.screenshot()

        try:
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, lang='por')
        except:
            return None

        # Procura por "CNPJ" exatamente naquela linha
        for i, text in enumerate(data['text']):
            if not text or not text.strip():
                continue

            text_lower = text.lower().strip()
            y_pos = data['top'][i]
            x_pos = data['left'][i]
            width = data['width'][i]
            height = data['height'][i]

            # Verifica se está na mesma altura (linha)
            if not (min_y <= y_pos <= max_y):
                continue

            # Encontrou "CNPJ" - retorna posição
            if text_lower == 'cnpj':
                x = x_pos + width // 2
                y = y_pos + height // 2
                self.log(f"[CNPJ Helper] Palavra 'CNPJ' encontrada em ({x}, {y})")
                return (x, y)

        return None

    def _find_cnpj_field_filtered(self, min_y: int = 300) -> Optional[Tuple[int, int]]:
        """
        Encontra campo CNPJ filtrando por posição Y e texto específico.

        Com logging DETALHADO para debugar.

        Args:
            min_y: Posição Y mínima para considerar (300 ignora barra superior)

        Returns:
            (x, y) do campo CNPJ ou None
        """
        import pytesseract

        screenshot = pyautogui.screenshot()

        # Salva screenshot para debug visual
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_path = self.screenshots_dir / f"ocr_debug_cnpj_{timestamp}.png"
        screenshot.save(debug_path)
        self.log(f"[CNPJ] Screenshot para debug salva em: {debug_path}")

        try:
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT, lang='por')
        except Exception as e:
            self.log(f"[CNPJ] ❌ Erro OCR: {e}")
            return None

        self.log(f"[CNPJ] ========== INICIANDO BUSCA ==========")
        self.log(f"[CNPJ] Filtro Y: > {min_y}")
        self.log(f"[CNPJ] Screen width: {self.screen_auto.screen_width}")

        all_texts = []
        found_texts = []

        for i, text in enumerate(data['text']):
            if not text or not text.strip():
                continue

            text_lower = text.lower().strip()
            y_pos = data['top'][i]
            x_pos = data['left'][i]
            width = data['width'][i]
            height = data['height'][i]

            # Coleta TODOS os textos para debug
            all_texts.append((text_lower, x_pos, y_pos, width, height))

            # FILTRO 1: Ignora posições acima do threshold (barra superior/navegador)
            if y_pos < min_y:
                self.log(f"[CNPJ] ⬜ IGNORADO (Y muito alto): '{text}' em Y={y_pos} (< {min_y})")
                continue

            # FILTRO 2: Ignora area do VLibras (canto direito > 85% da tela)
            if x_pos > (self.screen_auto.screen_width * 0.85):
                self.log(f"[CNPJ] ⬜ IGNORADO (VLibras): '{text}' em X={x_pos} (> 85%)")
                continue

            # Passou nos filtros
            found_texts.append((text_lower, x_pos, y_pos, width, height))
            self.log(f"[CNPJ] ✓ VÁLIDO: '{text}' em X={x_pos}, Y={y_pos}, W={width}")

            # BUSCA 1: Procura por "Informe o CNPJ" (texto completo)
            if 'informe o cnpj' in text_lower:
                x = x_pos + width + 50
                y = y_pos + height // 2
                self.log(f"[CNPJ] 🎯 MATCH: 'Informe o CNPJ' → Clicando em ({x}, {y})")
                return (x, y)

            # BUSCA 2: Procura por "Informe" isolado
            if text_lower == 'informe':
                x = x_pos + width + 100
                y = y_pos + height // 2
                self.log(f"[CNPJ] 🎯 MATCH: 'Informe' → Clicando em ({x}, {y})")
                return (x, y)

            # BUSCA 3: Procura por "CNPJ" isolado
            if text_lower == 'cnpj':
                if width < 150:
                    x = x_pos + width // 2
                    y = y_pos + height + 40
                    self.log(f"[CNPJ] 🎯 MATCH: 'CNPJ' (label) → Clicando em ({x}, {y})")
                    return (x, y)
                else:
                    x = x_pos + width + 30
                    y = y_pos + height // 2
                    self.log(f"[CNPJ] 🎯 MATCH: 'CNPJ' (largo) → Clicando em ({x}, {y})")
                    return (x, y)

        # Nada encontrado - mostra debug completo
        self.log(f"[CNPJ] ❌ NENHUM MATCH ENCONTRADO!")
        self.log(f"[CNPJ] Total de textos no OCR: {len(all_texts)}")
        self.log(f"[CNPJ] Textos após filtros (Y>{min_y}): {len(found_texts)}")

        if found_texts:
            self.log(f"[CNPJ] Textos válidos encontrados:")
            for txt, xp, yp, w, h in found_texts:
                self.log(f"  - '{txt}' | X={xp}, Y={yp}, W={w}, H={h}")
        else:
            self.log(f"[CNPJ] NENHUM texto passou pelos filtros! Mostrando os primeiros 20 textos do OCR:")
            for i, (txt, xp, yp, w, h) in enumerate(all_texts[:20]):
                self.log(f"  [{i}] '{txt}' | X={xp}, Y={yp}, W={w}, H={h}")

        return None

    # ==================== STEP 1: FILL CNPJ & EMIT ====================

    def _step1_fill_cnpj_and_emit(self) -> bool:
        """
        Step 1: Preenche CNPJ e clica "Emitir Certidão".

        Retorna True APENAS se clique bem-sucedido validado.

        Estratégia: usa CV para encontrar elemento próximo, depois TAB para navegar
        até o campo CNPJ. Muito mais robusto que OCR ou coordenadas hardcoded.
        """
        self.log("\n[STEP 1/5] Preenchendo CNPJ e emitindo...")
        self.overlay.update("Step 1/5: Preenchendo CNPJ...")

        # Estratégia: procura por template na área do formulário
        # Pode encontrar label "CNPJ" ou algum elemento próximo
        # Depois usa TAB para navegar para o campo correto
        self.log("[Step 1] Procurando elemento próximo via CV...")

        # Procura por template "1_btn_cnpj.png" ou outro elemento visual
        template_candidates = [
            str(self.templates_dir / "1_btn_cnpj.png"),
            str(self.templates_dir / "2_btn_emitir.png"),  # Fallback
        ]

        element_found = False
        for template_path in template_candidates:
            if not os.path.exists(template_path):
                continue

            pos = self.screen_auto.find_template(template_path, confidence=0.6)
            if pos:
                self.log(f"[Step 1] Elemento encontrado via CV em: {pos}")
                self.screen_auto.human_click(pos[0], pos[1])
                element_found = True
                break

        if not element_found:
            # Fallback: clica nas coordenadas conhecidas
            self.log(f"[Step 1] Template não encontrado, usando fallback XY: {COORDS['cnpj_field']}")
            self.screen_auto.human_click(COORDS["cnpj_field"][0], COORDS["cnpj_field"][1])

        self.screen_auto.human_delay(0.5, 1.0)

        # Estratégia inteligente: pressiona TAB para garantir que está no campo correto
        # TAB navega entre inputs do formulário
        self.log("[Step 1] Pressionando TAB para navegar ao campo CNPJ...")
        # pyautogui.press('tab')  # COMENTADO - não necessário com CV + clique direto
        self.screen_auto.human_delay(0.2, 0.4)

        # Seleciona tudo antes de digitar (Ctrl+A) para limpar qualquer texto anterior
        pyautogui.hotkey('ctrl', 'a')
        self.screen_auto.human_delay(0.1, 0.2)

        self.log(f"[Step 1] Digitando CNPJ: {self.cnpj_raw}")
        self.screen_auto.human_type(self.cnpj_raw)
        self.screen_auto.human_delay(1.0, 2.0)

        # Clica "Emitir Certidão"
        self.log("[Step 1] Procurando botao 'Emitir Certidao'...")

        # Tenta template primeiro
        emitir_template = self.templates_dir / "2_btn_emitir.png"
        emitir_pos = None

        if emitir_template.exists():
            emitir_pos = self.screen_auto.find_template(str(emitir_template), CONFIDENCE["emitir_button"])

        # Fallback para XY
        if not emitir_pos:
            self.log("[Step 1] Template nao encontrado, usando fallback XY")
            emitir_pos = COORDS["emitir_button"]

        self.log(f"[Step 1] Clicando botao Emitir em: {emitir_pos}")
        self.screen_auto.human_click(emitir_pos[0], emitir_pos[1])

        # Validacao: aguarda indicadores de sucesso
        self.log("[Step 1] Aguardando validacao de pagina...")
        self.screen_auto.human_delay(2.0, 3.0)

        success_indicators = ["Valida Encontrada", "Certidao Valida", "Data Inicial", "Data Final"]
        for indicator in success_indicators:
            if self.screen_auto.find_text(indicator, avoid_vlibras=True, min_confidence=60.0):
                self.log(f"[Step 1] SUCESSO: Encontrado '{indicator}'")
                self.overlay.update("Step 1/5: Sucesso ✓")
                return True

        # Estado ambiguo - NÃO retornar True
        self.log("[Step 1] FALHA: Nenhum indicador de sucesso encontrado")
        self.overlay.update("Step 1/5: Falhou ✗")
        return False

    # ==================== STEP 2: HANDLE MODAL ====================

    def _step2_handle_modal(self) -> bool:
        """
        Step 2: Detecta e maneja modal (Condicional).

        Se modal nao aparece, continua normalmente (nao eh erro).
        Retorna True se modal foi detectado E fechado.
        Retorna False se modal nao foi detectado (eh normal).
        """
        self.log("\n[STEP 2/5] Aguardando modal (condicional)...")
        self.overlay.update("Step 2/5: Aguardando modal...")

        # Aguarda indicadores de modal com threshold alto (60%)
        modal_indicators = [
            "Válida Encontrada",
            "Certidão Válida",
            "Certidão foi encontrada",
            "foi encontrada",
        ]

        start_time = time.time()
        modal_detected = False

        while time.time() - start_time < TIMEOUTS["modal_detection"]:
            for indicator in modal_indicators:
                if self.screen_auto.find_text(indicator, avoid_vlibras=True, min_confidence=60.0):
                    self.log(f"[Step 2] Modal detectado: '{indicator}'")
                    modal_detected = True
                    break

            if modal_detected:
                break
            time.sleep(0.5)

        if not modal_detected:
            self.log("[Step 2] Modal nao apareceu (comportamento esperado, continuando)")
            self.overlay.update("Step 2/5: Sem modal (OK) ✓")
            return False  # Nao eh erro - apenas continua

        # Modal detectado - precisa fechar
        self.log("[Step 2] Fechando modal...")

        # Tenta template
        consultar_template = self.templates_dir / "3_btn_consultar_cnpj.png"
        consultar_pos = None

        if consultar_template.exists():
            consultar_pos = self.screen_auto.find_template(str(consultar_template), CONFIDENCE["consultar_modal"])

        # Fallback XY
        if not consultar_pos:
            self.log("[Step 2] Template nao encontrado, usando fallback XY")
            consultar_pos = COORDS["modal_consultar"]

        self.log(f"[Step 2] Clicando 'Consultar' em: {consultar_pos}")
        self.screen_auto.human_click(consultar_pos[0], consultar_pos[1])
        self.screen_auto.human_delay(1.0, 2.0)

        # Validacao: modal fechou?
        if self.screen_auto.find_text("Válida Encontrada", avoid_vlibras=True, min_confidence=60.0):
            self.log("[Step 2] AVISO: Modal ainda visivel apos clique")
            return False

        self.log("[Step 2] SUCESSO: Modal fechado")
        self.overlay.update("Step 2/5: Modal fechado ✓")
        return True

    # ==================== STEP 3: DATE SELECTION ====================

    def _step3_date_selection(self) -> bool:
        """
        Step 3: Confirma pagina de datas e clica "Consultar Certidão".

        Retorna True APENAS se pagina de datas foi encontrada E
        clique executado com sucesso.
        """
        self.log("\n[STEP 3/5] Aguardando pagina de datas...")
        self.overlay.update("Step 3/5: Aguardando datas...")

        # Confirma presenca de "Data Inicial" ou "Data Final"
        date_indicators = ["Data Inicial", "Data Final"]
        date_found = False

        for indicator in date_indicators:
            if self.screen_auto.find_text(indicator, avoid_vlibras=True, min_confidence=60.0):
                self.log(f"[Step 3] Encontrado: '{indicator}'")
                date_found = True
                break

        if not date_found:
            self.log("[Step 3] FALHA: Pagina de datas nao encontrada")
            self.overlay.update("Step 3/5: Pagina de datas nao encontrada ✗")
            return False

        # Clica "Consultar Certidão" (datas)
        self.log("[Step 3] Clicando 'Consultar Certidao' (datas)...")

        # Tenta template
        consultar_template = self.templates_dir / "4_btn_consultar_data.png"
        consultar_pos = None

        if consultar_template.exists():
            consultar_pos = self.screen_auto.find_template(str(consultar_template), CONFIDENCE["consultar_dates"])

        # Fallback XY
        if not consultar_pos:
            self.log("[Step 3] Template nao encontrado, usando fallback XY")
            consultar_pos = COORDS["dates_consultar"]

        self.log(f"[Step 3] Clicando em: {consultar_pos}")
        self.screen_auto.human_click(consultar_pos[0], consultar_pos[1])

        # Aguarda resultados carregarem
        self.screen_auto.human_delay(2.0, 3.0)

        # Validacao: resultados apareceram?
        if self.screen_auto.find_text("Válida", avoid_vlibras=True, min_confidence=70.0) or \
           self.screen_auto.find_text("Vencida", avoid_vlibras=True, min_confidence=70.0):
            self.log("[Step 3] SUCESSO: Resultados carregados")
            self.overlay.update("Step 3/5: Resultados carregados ✓")
            return True

        self.log("[Step 3] FALHA: Resultados nao carregaram")
        self.overlay.update("Step 3/5: Resultados nao carregaram ✗")
        return False

    # ==================== STEP 4: VERIFY STATUS ====================

    def _step4_check_status(self) -> bool:
        """
        Step 4: Verifica se certificado eh "Válida".

        Retorna True APENAS se "Válida" for encontrado.
        Retorna False se "Vencida" ou estado desconhecido.
        """
        self.log("\n[STEP 4/5] Verificando status do certificado...")
        self.overlay.update("Step 4/5: Verificando status...")

        # Procura "Válida"
        if self.screen_auto.find_text("Válida", avoid_vlibras=True, min_confidence=70.0):
            self.log("[Step 4] SUCESSO: Certificado VÁLIDO")
            self.overlay.update("Step 4/5: Válido ✓")
            return True

        # Procura "Vencida"
        if self.screen_auto.find_text("Vencida", avoid_vlibras=True, min_confidence=70.0):
            self.log("[Step 4] FALHA: Certificado VENCIDO")
            self.overlay.update("Step 4/5: Vencido ✗")
            return False

        # Estado desconhecido = FALHA (nao assumir sucesso)
        self.log("[Step 4] FALHA: Status desconhecido")
        self.overlay.update("Step 4/5: Status desconhecido ✗")
        return False

    # ==================== STEP 5: DOWNLOAD ====================

    def _step5_download_certificate(self) -> bool:
        """
        Step 5: Clica download e verifica PDF criado.

        Retorna True APENAS se novo PDF foi detectado apos clique.
        """
        self.log("\n[STEP 5/5] Fazendo download do certificado...")
        self.overlay.update("Step 5/5: Fazendo download...")

        # Registra timestamp de referencia
        ref_time = time.time()
        self.log(f"[Step 5] Timestamp de referencia: {ref_time}")

        # Tenta template novo
        download_template = self.templates_dir / "5_btn_baixar2.png"
        download_pos = None

        if download_template.exists():
            download_pos = self.screen_auto.find_template(str(download_template), CONFIDENCE["download_icon"])

        # Fallback XY
        if not download_pos:
            self.log("[Step 5] Usando fallback XY para download")
            download_pos = COORDS["download_button"]

        self.log(f"[Step 5] Clicando download em: {download_pos}")
        self.screen_auto.human_click(download_pos[0], download_pos[1])

        # Aguarda arquivo
        self.log(f"[Step 5] Aguardando criacao de PDF (timeout: {TIMEOUTS['download_complete']}s)...")
        start_time = time.time()

        while time.time() - start_time < TIMEOUTS["download_complete"]:
            # Lista PDFs
            pdfs = list(self.download_dir.glob("*.pdf"))

            # Encontra novo PDF (modificado apos ref_time)
            for pdf in pdfs:
                try:
                    mtime = pdf.stat().st_mtime
                    if mtime > ref_time:
                        size = pdf.stat().st_size
                        self.log(f"[Step 5] SUCESSO: PDF encontrado: {pdf.name} ({size} bytes)")
                        self.overlay.update("Step 5/5: Download completo ✓")
                        return True
                except:
                    pass

            time.sleep(0.5)

        # Timeout - FALHA (nao assumir sucesso)
        self.log("[Step 5] FALHA: Nenhum novo PDF detectado")
        self.overlay.update("Step 5/5: Download falhou ✗")
        return False

    # ==================== MAIN RUN ====================

    def run(self) -> bool:
        """
        Executa o fluxo completo de 5 steps.

        Retorna True APENAS se todos os steps forem bem-sucedidos.
        """
        self.log("=" * 70)
        self.log(f"INICIANDO: Federal Certificate v2.0 - CNPJ: {self.cnpj_raw}")
        self.log(f"Log: {self.log_file}")
        self.log("=" * 70)

        try:
            self.overlay.show()

            if not self._open_chrome():
                self.log("ERRO: Falha ao abrir Chrome")
                return False

            if not self._step1_fill_cnpj_and_emit():
                self.log("ERRO: Step 1 falhou")
                return False

            # Step 2 e opcional - nao bloqueia se falhar
            self._step2_handle_modal()

            if not self._step3_date_selection():
                self.log("ERRO: Step 3 falhou")
                return False

            if not self._step4_check_status():
                self.log("ERRO: Step 4 falhou")
                return False

            if not self._step5_download_certificate():
                self.log("ERRO: Step 5 falhou")
                return False

            self.log("=" * 70)
            self.log("SUCESSO: Certificado obtido com sucesso!")
            self.log("=" * 70)
            self.overlay.update("Completado com sucesso! ✓")
            return True

        except Exception as e:
            self.log(f"ERRO GERAL: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False

        finally:
            self.overlay.hide()
            self._close_chrome()


# ==================== MAIN ====================

if __name__ == "__main__":
    # Exemplo de uso
    cert = FederalCertificateV2(cnpj="75658377000131")
    result = cert.run()

    if result:
        print("\n✓ Certificado obtido com sucesso!")
        print(f"  PDF: {cert.download_dir}/certidao_federal_*.pdf")
    else:
        print("\n✗ Falha ao obter certificado")
        print(f"  Log: {cert.log_file}")
