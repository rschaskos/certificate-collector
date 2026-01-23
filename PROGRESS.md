# Progresso do Projeto - Certificate Collector

**Última atualização:** 23/01/2026

---

## Status das Certidões

| Certidão | Status | Observações |
|----------|--------|-------------|
| FGTS | ✅ Funcionando | Sem CAPTCHA, usa `page.pdf()` |
| ESTADUAL | ✅ Funcionando | Modal com tabela, download via ícone `file_save` |
| RECEITA FEDERAL | ⏳ Pendente | Testar (pede data inicial) |
| TRABALHISTA | ⏳ Pendente | Testar (tem CAPTCHA) |
| SIMPLES NACIONAL | ⏳ Pendente | Testar |
| TCE-PR | ⏳ Pendente | Testar |

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

## Decisões Técnicas

### 1. Remoção do CAPTCHA do FGTS
- O site do FGTS não exige mais CAPTCHA
- Removido callback de CAPTCHA para FGTS
- Apenas TRABALHISTA ainda usa CAPTCHA

### 2. Estratégia de Download PDF
- **Não clicar no botão "Imprimir"** (evita diálogo do sistema)
- Usar `page.pdf()` diretamente na página do certificado
- Mais confiável e funciona em modo headless

### 3. Espera pela Página
- `wait_for_load_state('networkidle')` não é suficiente
- Solução: esperar elemento específico aparecer (botão Imprimir)
- Adicionar `wait_for_timeout(2000)` para garantir renderização

### 4. Conversão de Seletores (Playwright Codegen → config.json)
| Codegen | config.json |
|---------|-------------|
| `get_by_role("button", name="X")` | `role=button[name='X']` |
| `get_by_text("X")` | `text=X` |
| `get_by_label("X")` | `label=X` |

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
│   ├── base.py             # Classe base abstrata
│   ├── fgts.py             # ✅ Funcionando
│   ├── estadual.py         # ⏳ Testar
│   ├── federal.py          # ⏳ Testar
│   ├── trabalhista.py      # ⏳ Testar
│   ├── simples.py          # ⏳ Testar
│   └── tce.py              # ⏳ Testar
├── core/
│   ├── browser.py          # Gerenciador do Playwright
│   ├── config.py           # Carrega config.json
│   └── logger.py           # Sistema de logs
└── downloads/              # PDFs salvos aqui
```

---

## Próximos Passos

1. [ ] Testar certidão ESTADUAL
2. [ ] Testar certidão RECEITA FEDERAL
3. [ ] Testar certidão TRABALHISTA (com CAPTCHA)
4. [ ] Testar certidão SIMPLES NACIONAL
5. [ ] Testar certidão TCE-PR
6. [ ] Ajustar seletores conforme necessário (usar `playwright codegen`)

---

## Comandos Úteis

```bash
# Executar o programa
cd /mnt/c/Users/roney.gabinete/Documents/certificate-collector
python main.py

# Descobrir seletores com Playwright Codegen
playwright codegen https://URL_DO_SITE

# Exemplo FGTS:
playwright codegen https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf
```

---

## Observações

- O projeto usa **PySide6** para interface gráfica
- O projeto usa **Playwright** para automação web
- PDFs são salvos na pasta `downloads/`
- Logs ficam na pasta `logs/`
- Modo headless está **desativado** (browser_headless: false)
