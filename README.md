<h1 align="center"> GERADOR DE CERTIDÕES AUTOMATIZADO v4.0 </h1>

Sistema profissional de automação para emissão de Certidões de Regularidade brasileiras.

**Versão 4.0** - Refatorado com PySide6 + Playwright (2026)

## Certidões Suportadas

O sistema gera automaticamente as seguintes certidões:

- **FGTS** - Consulta Regularidade do Empregador (Caixa/CRF)
- **Estadual (PR)** - Certidão de Débitos Tributários Estadual (Fazenda do Paraná)
- **Federal** - Certidão de Débitos Federais (Receita Federal)
- **Trabalhista** - Certidão Negativa de Débitos Trabalhistas (TST)
- **Simples Nacional** - Consulta Optantes pelo Simples Nacional
- **TCE-PR** - Certidão Liberatória do Tribunal de Contas do Paraná

## Melhorias na Versão 4.0

- **Interface moderna** com PySide6 (Qt6)
- **Automação profissional** com Playwright (substitui PyAutoGUI)
- **Arquitetura modular** orientada a objetos
- **Sistema de logging** com arquivos diários
- **Configuração externa** via config.json
- **Tratamento de erros robusto** com retry automático
- **Console em tempo real** na interface
- **Cross-platform** (Windows, Linux, macOS)

## Pré-requisitos

- **Python 3.8+**
- Ambiente virtual (recomendado)

## Instalação

### 1. Clone o repositório
```bash
git clone <repository-url>
cd certificate-collector
```

### 2. Crie e ative o ambiente virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Instale os browsers do Playwright
```bash
python -m playwright install chromium
```

## Como executar

Com o ambiente virtual ativado:

```bash
python main.py
```

## Estrutura do Projeto

```
certificate-collector/
├── main.py                    # Entry point da aplicação
├── config.json                # Configurações (URLs, seletores, timeouts)
├── requirements.txt           # Dependências Python
│
├── core/                      # Módulos principais
│   ├── logger.py             # Sistema de logging
│   ├── config.py             # Carregador de configuração
│   └── browser.py            # Gerenciador Playwright
│
├── gui/                       # Interface gráfica
│   ├── main_window.py        # Janela principal
│   └── dialogs.py            # Diálogos (CNPJ, CAPTCHA, data)
│
├── certificates/              # Implementação de cada certidão
│   ├── base.py               # Classe base abstrata
│   ├── fgts.py
│   ├── estadual.py
│   ├── federal.py
│   ├── trabalhista.py
│   ├── simples.py
│   └── tce.py
│
├── downloads/                 # PDFs gerados (criado automaticamente)
├── logs/                      # Arquivos de log (criado automaticamente)
└── screenshots/               # Screenshots de debug (criado automaticamente)
```

## Como usar

1. **Execute o programa**: `python main.py`
2. **Digite o CNPJ** da empresa na primeira janela
3. **Selecione o tipo de certidão** no menu dropdown
4. **Clique em "Iniciar Automação"**
5. Para certidões com CAPTCHA (FGTS, Trabalhista), digite o código quando solicitado
6. Para certidão Federal, informe a data inicial (data final é sempre hoje)
7. Os PDFs são salvos automaticamente em `downloads/`

### Modo "Gerar Todas"

Selecione "GERAR TODAS CERTIDÕES" para processar todas as 6 certidões em sequência. O sistema solicitará todos os CAPTCHAs e dados necessários no início.

## Logs

Logs detalhados são salvos em `logs/certidoes_YYYY-MM-DD.log` e também exibidos no console da interface em tempo real.

## Configuração

Edite `config.json` para:
- Alterar URLs dos sites governamentais
- Atualizar seletores CSS/XPath quando sites mudarem
- Ajustar timeouts e número de tentativas
- Modificar caminhos de download e logs

## Migração da v3.0

Se você usava a versão anterior (CustomTkinter + Selenium + PyAutoGUI), o código original foi preservado em `main_v3_backup.py`.

**Principais mudanças:**
- PyAutoGUI **removido** completamente
- Selenium **substituído** por Playwright
- CustomTkinter **substituído** por PySide6
- Código monolítico **refatorado** em módulos
- Hardcoded Chrome path **removido**

## Solução de Problemas

### Erro: "playwright not found"
```bash
pip install playwright
python -m playwright install chromium
```

### Erro: "PySide6 not found"
```bash
pip install PySide6
```

### Seletores não funcionam (site mudou)
Edite `config.json` → seção `selectors` → atualize o seletor CSS/XPath correspondente.

### Timeout durante geração
Edite `config.json` → seção `timeouts` → aumente os valores (em milissegundos).

## Contribuição

1. Faça o fork do projeto
2. Crie uma branch para a sua feature (`git checkout -b feature/nome-da-feature`)
3. Faça o commit (`git commit -am 'Adicionando nova funcionalidade'`)
4. Faça o push para a branch (`git push origin feature/nome-da-feature`)
5. Crie um novo Pull Request

## Licença

Desenvolvido por **RSCHASKOS** (2024-2026)

---

**Nota:** Este sistema interage com sites governamentais brasileiros. Certifique-se de que a automação está de acordo com os termos de uso de cada portal.
