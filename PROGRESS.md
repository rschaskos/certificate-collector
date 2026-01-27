# Progresso do Projeto - Certificate Collector

**Última atualização:** 26/01/2026

---

## Status das Certidões

| Certidão | Status | Observações |
|----------|--------|-------------|
| FGTS | ✅ Funcionando | Sem CAPTCHA, usa `page.pdf()` |
| ESTADUAL | ✅ Funcionando | Modal com tabela, download via ícone `file_save` |
| RECEITA FEDERAL | 🔄 Em andamento | Site detecta automação - testar com Selenium/undetected-chromedriver |
| TRABALHISTA | ✅ Funcionando | CAPTCHA manual + download automático |
| SIMPLES NACIONAL | ❌ Bloqueado | Site detecta automação - "Comportamento de Robô" |
| TCE-PR | ✅ Funcionando | Formulário em iframe, link abre nova aba, salva via `page.pdf()` |

---

## Problema: Certidão Federal (Receita Federal)

**Status:** 🔄 Em investigação - Site detecta QUALQUER automação

**URL:** `https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj`

**Erro:** "Não foi possível concluir a ação para o contribuinte informado. Por favor, tente novamente dentro de alguns minutos. 023"

### Descoberta importante (26/01/2026):
✅ **Funciona manualmente** - Quando o usuário abre o Chrome real com perfil real e interage manualmente, a certidão é emitida sem problemas.

❌ **Falha com automação** - Mesmo usando:
- Perfil real do Chrome
- PyAutoGUI (controle nativo de mouse/teclado do SO)
- undetected-chromedriver

O site ainda detecta e bloqueia.

### O que foi tentado (em ordem):

| # | Técnica | Resultado |
|---|---------|-----------|
| 1 | Playwright padrão | ❌ Detectado |
| 2 | Playwright + Chrome real | ❌ Detectado |
| 3 | Playwright + Edge real | ❌ Detectado |
| 4 | Playwright + perfil persistente | ❌ Detectado |
| 5 | Scripts anti-detecção (webdriver, plugins) | ❌ Detectado |
| 6 | undetected-chromedriver | ❌ Detectado |
| 7 | undetected-chromedriver + perfil novo | ❌ Detectado |
| 8 | PyAutoGUI (input nativo) + perfil novo | ❌ Detectado |
| 9 | Chrome manual + perfil real + interação manual | ✅ **FUNCIONA** |

### Análise técnica:

O site da Receita Federal utiliza **múltiplas camadas de detecção**:

1. **hCaptcha invisível** - Carregado em background (`hcaptcha.html` no console)
2. **Análise comportamental** - Mesmo com input nativo (PyAutoGUI), detecta padrões
3. **Fingerprinting do navegador** - Possivelmente detecta características do WebDriver
4. **Verificação de sessão/cookies** - Perfil novo sem histórico é suspeito

### Arquivos criados para testes:
- `core/browser_undetected.py` - Gerenciador do undetected-chromedriver
- `certificates/federal_undetected.py` - Múltiplos modos de teste (7 opções)

### Próximos passos para resolver:
- [ ] Investigar se o hCaptcha pode ser resolvido com serviço externo (2captcha, anti-captcha)
- [ ] Testar com browser real via extensão (não WebDriver)
- [ ] Investigar API pública da Receita Federal (se existir)
- [ ] Considerar abordagem semi-manual (usuário resolve hCaptcha, automação continua)
- [ ] Pesquisar técnicas de bypass de hCaptcha invisível

**Seletores (config.json):**
```json
"federal": {
  "cnpj_input": "br-input[placeholder='Informe o CNPJ'] input",
  "consultar_button": "button.secondary:has-text('Consultar Certidão')",
  "data_input": "input[placeholder='Selecione a data']",
  "submit_button": "button[type='submit']:has-text('Consultar Certidão')"
}
```

---

## Fluxo FGTS (Completo)

```
1. Preenche CNPJ
2. Clica "Consultar"
3. Extrai razão social da empresa
4. Marca checkbox de aceite
5. Clica "Visualizar"
6. Aguarda botão "Imprimir" aparecer (indica certidão pronta)
7. Aguarda 2s extra (renderização completa)
8. Salva página como PDF via page.pdf()
```

### Seletores FGTS (config.json)
```json
"fgts": {
  "cnpj_input": "[id='mainForm:txtInscricao1']",
  "submit_button": "role=button[name='Consultar']",
  "error_message": "#mainForm > div.ui-messages-error",
  "razao_social": "#mainForm > div:nth-of-type(3) > p > span:nth-of-type(2)",
  "checkbox": "[id='mainForm:j_id51']",
  "visualizar_button": "[id='mainForm:btnVisualizar']",
  "print_button": "[id='mainForm:btImprimir4']"
}
```

---

## Fluxo Estadual PR (Completo)

```
1. Preenche CNPJ
2. Clica "EMITIR CERTIDÃO"
3. Aguarda modal com tabela de certidões aparecer
4. Clica no ícone de download (file_save) da primeira linha
5. Salva PDF baixado
```

### Seletores Estadual (config.json)
```json
"estadual": {
  "cnpj_input": "role=textbox[name='CPF ou CNPJ do requerente']",
  "submit_button": "button:has-text('EMITIR CERTIDÃO')",
  "modal_table": "table tbody tr",
  "download_button": "i:has-text('file_save')"
}
```

---

## Fluxo Trabalhista (Completo)

```
1. Navega para URL direta: cndt-certidao.tst.jus.br/gerarCertidao.faces
2. Preenche CNPJ (slow_type)
3. Abre diálogo para usuário digitar CAPTCHA
4. Preenche CAPTCHA (lowercase)
5. Clica "Emitir Certidão" e aguarda download
6. Salva PDF baixado
```

### Seletores Trabalhista (config.json)
```json
"trabalhista": {
  "cnpj_input": "[id='gerarCertidaoForm:cpfCnpj']",
  "captcha_input": "#idCampoResposta",
  "submit_button": "[id='gerarCertidaoForm:btnEmitirCertidao']",
  "error_message": "#mensagens li"
}
```

---

## Fluxo TCE-PR (Completo)

```
1. Navega para página (formulário está dentro de iframe)
2. Detecta iframe e localiza campos
3. Preenche CNPJ (segundo input de texto no iframe)
4. Clica "Consultar"
5. Aguarda link "Clique aqui para visualizar a certidão." aparecer (dentro do iframe)
6. Extrai URL do link (srv_certidao_emissao.aspx?nrCNPJ=...)
7. Abre nova página com a URL da certidão
8. Lida com dialog "Deseja imprimir?" (dismiss)
9. Salva página como PDF via page.pdf()
```

### Seletores TCE-PR (config.json)
```json
"tce": {
  "cnpj_input": "#ctl00_ContentPlaceHolder2_tbCNPJ",
  "consultar_button": "#ctl00_ContentPlaceHolder2_btnVerificar",
  "certidao_link": "#ctl00_ContentPlaceHolder2_lkCertidao"
}
```

**Observações:**
- Formulário está dentro de um **iframe**
- O link da certidão aparece **dentro do iframe** após consulta
- URL da certidão: `https://servicos.tce.pr.gov.br/TCEPR/Tribunal/CertidaoLiberatoria/srv_certidao_emissao.aspx?nrCNPJ={cnpj}`

---

## Problema: Simples Nacional

**Status:** Bloqueado por detecção de bot (hCaptcha)

**URL:** `https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21`

**Erro:** "Impedido por proteção Captcha. Comportamento de Robô."

**O que já foi tentado:**
1. ✅ Seletores funcionando (CNPJ preenchido)
2. ❌ Edge com perfil persistente - detectado
3. ❌ Scripts anti-detecção - detectado

**Fluxo implementado (funciona até ser bloqueado):**
```
1. Navega para página
2. Preenche CNPJ
3. Clica "Consultar" → BLOQUEADO (hCaptcha detecta robô)
```

### Seletores Simples Nacional (config.json)
```json
"simples": {
  "cnpj_input": "#Cnpj",
  "consultar_button": "button:has-text('Consultar')",
  "gerar_pdf_button": "#GerarPDF"
}
```

---

## Decisões Técnicas

### 1. Métodos anti-detecção na classe base
- `human_delay(min_ms, max_ms)` - Delays aleatórios entre ações
- `slow_type(selector, text)` - Digitação lenta caractere por caractere
- Disponíveis para todas as certidões via `BaseCertificate`

### 2. Browser com perfil persistente
- Usa `launch_persistent_context` para manter cookies/histórico
- Pasta `./browser_profile`
- Scripts anti-detecção (webdriver, plugins, languages, etc.)

### 3. Conversão de Seletores (Playwright Codegen → config.json)
| Codegen | config.json |
|---------|-------------|
| `get_by_role("button", name="X")` | `role=button[name='X']` |
| `get_by_text("X")` | `text=X` |
| `get_by_label("X")` | `label=X` |
| `get_by_placeholder("X")` | `[placeholder='X']` |

---

## Arquivos Principais

```
certificate-collector/
├── main.py                 # Ponto de entrada
├── config.json             # URLs e seletores
├── gui/
│   ├── main_window.py      # Interface principal
│   └── dialogs.py          # Diálogos (CNPJ, CAPTCHA, Data)
├── certificates/
│   ├── base.py             # Classe base (human_delay, slow_type)
│   ├── fgts.py             # ✅ Funcionando
│   ├── estadual.py         # ✅ Funcionando
│   ├── federal.py          # 🔄 Bloqueado por detecção
│   ├── trabalhista.py      # ✅ Funcionando
│   ├── simples.py          # ❌ Bloqueado por detecção
│   └── tce.py              # ✅ Funcionando
├── core/
│   ├── browser.py          # Gerenciador do Playwright (anti-detecção)
│   ├── config.py           # Carrega config.json
│   └── logger.py           # Sistema de logs
├── browser_profile/        # Perfil persistente do navegador
├── downloads/              # PDFs salvos aqui
├── logs/                   # Logs diários
└── screenshots/            # Screenshots de debug
```

---

## Próximos Passos

1. [x] Testar certidão ESTADUAL - ✅ Funcionando
2. [x] Testar certidão TRABALHISTA (com CAPTCHA) - ✅ Funcionando
3. [x] Testar certidão TCE-PR - ✅ Funcionando
4. [x] Testar undetected-chromedriver para FEDERAL - ❌ Ainda detectado
5. [x] Testar PyAutoGUI (input nativo) para FEDERAL - ❌ Ainda detectado
6. [ ] **EM ANÁLISE** - Certidão RECEITA FEDERAL (precisa solução mais robusta)
7. [ ] **PAUSADO** - Certidão SIMPLES NACIONAL (mesmo problema - hCaptcha)

### Ideias para solução profissional da Certidão Federal:
- [ ] Usar serviço de resolução de CAPTCHA (2captcha, anti-captcha, capsolver)
- [ ] Criar extensão do Chrome que injeta automação (não usa WebDriver)
- [ ] Puppeteer com stealth plugin (alternativa ao Playwright)
- [ ] Abordagem híbrida: automação prepara, usuário clica no botão crítico

---

## Comandos Úteis

```bash
# Executar o programa
cd /mnt/c/Users/roney.gabinete/Documents/certificate-collector
python main.py

# Descobrir seletores com Playwright Codegen
playwright codegen https://URL_DO_SITE
```

---

## Observações

- O projeto usa **PySide6** para interface gráfica
- O projeto usa **Playwright** para automação web
- PDFs são salvos na pasta `downloads/`
- Logs ficam na pasta `logs/`
- Modo headless está **desativado** (browser_headless: false)
- Browser usa **Microsoft Edge** com perfil persistente
