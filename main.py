#########################################
#   DESENVOLVIDO POR RSCHASKOS EM 2024  #
#########################################

import pyautogui as pag
import webbrowser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
from datetime import datetime
from pygetwindow import PyGetWindowException
from selenium.common.exceptions import NoSuchElementException
import customtkinter as ctk
from tkinter.filedialog import askopenfilename

url = ['https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf',
       'http://www.cdw.fazenda.pr.gov.br/cdw/emissao/certidaoAutomatica',
       'https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PJ/Consultar',
       'https://www.tst.jus.br/certidao1',
       'https://www8.receita.fazenda.gov.br/simplesnacional/aplicacoes.aspx?id=21',
       'https://www1.tce.pr.gov.br/conteudo/consultar-certidao-liberatoria/235540/area/54']

__version__ = '3.0'

# Permite que o Chrome fique aberto após encerrar código, descomente p/ usar
chrome_options = Options()
# chrome_options.add_experimental_option('detach', True)


def leia_cnpj():
    global win1
    global cnpj_entry
    win1 = ctk.CTk()
    win1.title('Entre com o CNPJ')
    win1.geometry('400x100')

    # Criação do campo de entrada para a opção
    cnpj_entry = ctk.CTkEntry(win1, placeholder_text='Digite o CNPJ')
    cnpj_entry.pack(pady=30)

    # Configuração para chamar a função quando a tecla "Enter" for pressionada
    cnpj_entry.bind('<Return>', handle_cnpj_entry)

    # Execução da aplicação
    win1.mainloop()


def handle_cnpj_entry(event=None):
    global cnpj
    cnpj = cnpj_entry.get()
    while True:
        try:
            if len(cnpj) < 14:
                # print(f'CNPJ inválido: {cnpj}')
                win1.destroy()
                leia_cnpj()
            else:
                # print(f'A opção inserida foi: {cnpj}')
                win1.destroy()
                break
        except KeyboardInterrupt:
            # print()
            # print('Usuario encerrou')
            exit()
    win2.mainloop()


def captcha():
    global win3
    global cap_entry
    win3 = ctk.CTk()
    win3.title('Entre com Captcha')
    win3.geometry('400x100')

    # Criação do campo de entrada para a opção
    cap_entry = ctk.CTkEntry(win3, placeholder_text='Digite o Captcha')
    cap_entry.pack(pady=30)


    # Configuração para chamar a função quando a tecla "Enter" for pressionada
    cap_entry.bind('<Return>', handle_cap_entry)

    # Execução da aplicação
    win3.mainloop()


def handle_cap_entry(event=None):
    global cap
    cap = cap_entry.get()
    while True:
        try:
            if len(cap) <= 3:
                # print(f'Captcha Inválido: {cap}')
                win3.destroy()
                captcha()
            else:
                # print(f'A opção inserida foi: {cap}')
                win3.quit()
        except KeyboardInterrupt:
            # print()
            # print('Usuario encerrou')
            exit()
        finally:
            win3.quit()
        break
    win3.destroy()

# Função para lidar com o clique no botão
def button_callback():
    selected_option = combobox_1.get()
    if selected_option == 'FGTS':
        fgts()
    elif selected_option == 'ESTADUAL':
        estadual()
    elif selected_option == 'RECEITA FEDERAL':
        federal()
    elif selected_option == 'TRABALHISTA':
        trabalhista()
    elif selected_option == 'SIMPLES NACIONAL':
        simples()
    elif selected_option == 'TCE-PR':
        tce()
    elif selected_option == 'TROCAR CNPJ':
        leia_cnpj()
    elif selected_option == 'GERAR TODAS CERTIDÕES':
        sleep(3)
        fgts()
        sleep(3)
        estadual()
        sleep(3)
        federal()
        sleep(3)
        trabalhista()
        sleep(3)
        simples()
        sleep(3)
        tce()


# Configurações iniciais
ctk.set_appearance_mode('light')
ctk.set_default_color_theme('dark-blue')
win2 = ctk.CTk()
win2.title('Automatiza Certidões - Python')

# Opções do menu
frame_1 = ctk.CTkFrame(master=win2)
frame_1.grid(row=0, pady=50, padx=50)
win2.geometry('400x300')

# Lista suspensa (combobox)
combobox_1 = ctk.CTkComboBox(frame_1, values=['FGTS', 'ESTADUAL', 'RECEITA FEDERAL',
                                              'TRABALHISTA', 'SIMPLES NACIONAL', 'TCE-PR', 'TROCAR CNPJ',
                                              'GERAR TODAS CERTIDÕES'])
combobox_1.grid(row=0, column=0, pady=10, padx=10)
combobox_1.set('Tipo de Certidão')

# Botão para efetivar a escolha
button_1 = ctk.CTkButton(frame_1, text='Iniciar Automação', command=button_callback)
button_1.grid(row=0, column=1, pady=10, padx=0)

# Botão para encerrar
button_encerrar = ctk.CTkButton(frame_1, text='Encerrar', command=win2.destroy)

button_encerrar.grid(row=1, column=0, columnspan=2, pady=10, padx=10)

def fgts():
    global browser
    browser = webdriver.Chrome(options=chrome_options)
    browser.maximize_window()
    browser.get(url[0])
    sleep(3)
    browser.find_element('xpath', '//*[@id="mainForm:txtInscricao1"]').click()
    browser.find_element('xpath', '//*[@id="mainForm:txtInscricao1"]').send_keys(cnpj)
    captcha()
    browser.find_element('xpath', '//*[@id="mainForm:txtCaptcha"]').click()
    sleep(1)
    browser.find_element('xpath', '//*[@id="mainForm:txtCaptcha"]').send_keys(cap)
    sleep(1)
    browser.find_element('xpath', '//*[@id="mainForm:btnConsultar"]').click()
    sleep(2)
    while True:
        try:
            browser.find_element('xpath', '//*[@id="mainForm"]/div[1]/span')
            print('CAPTCHA INVÁLIDO')
            sleep(1)
            browser.get(url[0])
            sleep(3)
            browser.find_element('xpath', '//*[@id="mainForm:txtInscricao1"]').click()
            browser.find_element('xpath', '//*[@id="mainForm:txtInscricao1"]').send_keys(cnpj)
            captcha()
            browser.find_element('xpath', '//*[@id="mainForm:txtCaptcha"]').click()
            sleep(1)
            browser.find_element('xpath', '//*[@id="mainForm:txtCaptcha"]').send_keys(cap)
            sleep(1)
            browser.find_element('xpath', '//*[@id="mainForm:btnConsultar"]').click()
            sleep(2)
        except NoSuchElementException:
            razao = browser.find_element('xpath', '//*[@id="mainForm"]/div[3]/p/span[2]').text
            sleep(1)
            browser.find_element('xpath', '//*[@id="mainForm:j_id51"]').click()
            sleep(1)
            browser.find_element('xpath', '//*[@id="mainForm:btnVisualizar"]').click()
            sleep(2)
            while True:
                try:
                    pag.getWindowsWithTitle('Consulta Regularidade do Empregador')[0].activate()
                    break
                except PyGetWindowException:
                    print('Clique na Janela do FGTS')
                    sleep(1)
            sleep(1)
            pag.keyDown('ctrl')
            pag.press('p')
            pag.keyUp('ctrl')
            sleep(1)
            pag.press('enter')
            sleep(2)
            pag.write('FGTS ' + razao)
            sleep(1)
            pag.press('enter')
            break


def estadual():
    global browser
    browser = webdriver.Chrome(options=chrome_options)
    browser.maximize_window()
    browser.get(url[1])
    browser.find_element('xpath', '//*[@id="EmissaoCnpj"]').click()
    browser.find_element('xpath', '//*[@id="EmissaoCnpj"]').send_keys(cnpj)
    browser.find_element('xpath', '//*[@id="submitBtn"]').click()
    sleep(4)
    while True:
        try:
            pag.getWindowsWithTitle('Secretaria da Fazenda')[0].activate()
            break
        except PyGetWindowException:
            print('Clique na Janela do Certidão')
            sleep(1)
    try:
        browser.find_element('xpath', '//*[@id="msg"]/table/tbody/tr/td[2]/div')
        print('ALGUM PROBLEMA COM O CNPJ. VERIFICAR COM O FORNECEDOR')
        sleep(3)
    except NoSuchElementException:
        sleep(4)
        browser.find_element('xpath', '//*[@id="pdf"]/table/tbody/tr/td[2]/div/b/a').click()


def federal():
    chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
    webbrowser.get(chrome_path).open(url[2])
    sleep(4)
    while True:
        try:
            pag.getWindowsWithTitle('Certidão de Débitos')[0].activate()
            break
        except PyGetWindowException:
            print('Clique na Janela da Certidão')
            sleep(1)
    pag.press('tab')
    sleep(0.5)
    pag.write(cnpj)
    sleep(1)
    hoje = datetime.today()
    hoje_brasil = hoje.strftime('%d%m%Y')
    pag.write('01012024')
    sleep(0.5)
    pag.write(hoje_brasil)
    sleep(0.5)
    pag.press('enter')
    sleep(2)
    for c in range(32):
        pag.press('tab')
    sleep(0.5)
    pag.press('enter')


def trabalhista():
    global browser
    browser = webdriver.Chrome(options=chrome_options)
    browser.maximize_window()
    browser.get(url[3])
    browser.find_element('xpath',
                         '//*[@id="portlet_com_liferay_journal_content_web_portlet_JournalContentPortlet_INSTANCE_Wu3q"]/div/div[2]/div/div/div/p/div/p/a').click()
    sleep(1)
    browser.get(url[3])
    sleep(1)
    browser.get(url[3])
    sleep(1)
    while True:
        try:
            pag.getWindowsWithTitle('Certidão Negativa de Débitos')[0].activate()
            break
        except PyGetWindowException:
            print('Clique na Janela do Certidão')
            sleep(1)
    sleep(1)
    browser.get('https://cndt-certidao.tst.jus.br/gerarCertidao.faces')
    sleep(2)
    browser.find_element('xpath', '//*[@id="gerarCertidaoForm:cpfCnpj"]').click()
    browser.find_element('xpath', '//*[@id="gerarCertidaoForm:cpfCnpj"]').send_keys(cnpj)
    captcha()
    browser.find_element('xpath', '//*[@id="idCampoResposta"]').click()
    browser.find_element('xpath', '//*[@id="idCampoResposta"]').send_keys(cap)
    sleep(2)
    browser.find_element('xpath', '//*[@id="gerarCertidaoForm:btnEmitirCertidao"]').click()
    sleep(1)
    while True:
        try:
            browser.find_element('xpath', '//*[@id="mensagens"]/ul/li')
            print('CAPTCHA INVÁLIDO')
            sleep(1)
            browser.get('https://cndt-certidao.tst.jus.br/gerarCertidao.faces')
            sleep(2)
            browser.find_element('xpath', '//*[@id="gerarCertidaoForm:cpfCnpj"]').click()
            browser.find_element('xpath', '//*[@id="gerarCertidaoForm:cpfCnpj"]').send_keys(cnpj)
            captcha()
            browser.find_element('xpath', '//*[@id="idCampoResposta"]').click()
            browser.find_element('xpath', '//*[@id="idCampoResposta"]').send_keys(cap)
            sleep(2)
            browser.find_element('xpath', '//*[@id="gerarCertidaoForm:btnEmitirCertidao"]').click()
            sleep(1)
        except NoSuchElementException:
            sleep(2)
            print('Certidão geradada com sucesso!')
            break


def simples():
    chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
    webbrowser.get(chrome_path).open(url[4])
    sleep(4)
    while True:
        try:
            pag.getWindowsWithTitle('Simples Nacional')[0].activate()
            break
        except PyGetWindowException:
            print('Clique na Janela do Certidão')
            sleep(1)
        sleep(1)
    for c in range(7):
        pag.press('tab')
        sleep(0.3)
    pag.write(cnpj)
    pag.press('enter')
    sleep(1)
    sleep(1)
    for c in range(3):
        pag.press('tab')
        sleep(0.3)
    pag.press('enter')


def tce():
    chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
    webbrowser.get(chrome_path).open(url[5])
    sleep(4)
    while True:
        try:
            pag.getWindowsWithTitle('Consultar Certidão Liberatória')[0].activate()
            break
        except PyGetWindowException:
            print('	Clique na Janela do TCEPR')
            sleep(1)
    sleep(1)
    for c in range(24):
        pag.press('tab')
    pag.write(cnpj)
    sleep(1)
    for c in range(2):
        pag.press('tab')
    sleep(1)
    pag.press('enter')
    sleep(4)
    for c in range(6):
        pag.press('tab')
    sleep(1)
    pag.press('enter')
    sleep(2)
    pag.press('enter')
    sleep(2)
    pag.press('enter')
    sleep(1)
    pag.press('enter')


if __name__ == '__main__':
    leia_cnpj()

