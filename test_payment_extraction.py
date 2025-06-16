#!/usr/bin/env python3
"""
Script simplificado para extrair métodos de pagamento de 5 restaurantes.
"""

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from pathlib import Path
import os
from datetime import datetime


def setup_browser():
    """Inicializa navegador."""
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    browser.set_page_load_timeout(30)
    return browser


def find_latest_csv():
    """Encontra o CSV mais recente."""
    reports_dir = Path("reports")
    csv_files = list(reports_dir.glob("bd_scrap_ifood_*.csv"))
    
    if not csv_files:
        raise FileNotFoundError("Nenhum arquivo CSV encontrado")
    
    latest_file = max(csv_files, key=os.path.getmtime)
    return latest_file


def extract_minimum_order(soup):
    """Extrai pedido mínimo."""
    try:
        min_order_div = soup.find('div', class_='merchant-info__minimum-order')
        if min_order_div:
            text = min_order_div.get_text()
            match = re.search(r'R\$\s*([\d,]+\.?\d*)', text)
            if match:
                value = match.group(1).replace(',', '.')
                return float(value)
    except:
        pass
    return 0.0


def extract_payment_methods(soup):
    """Extrai métodos de pagamento."""
    payment_data = {
        'pag_site_debito': False,
        'pag_site_credito': False,
        'pag_site_pix': False,
        'pag_site_vale_refeicao': False,
        'pag_entrega_debito': False,
        'pag_entrega_credito': False,
        'pag_entrega_pix': False,
        'pag_entrega_vale_refeicao': False,
        'pag_entrega_dinheiro': False
    }
    
    try:
        payment_div = soup.find('div', class_='merchant-details-payment')
        if not payment_div:
            return payment_data
        
        payment_sections = payment_div.find_all('div', class_='merchant-details-payment__payment')
        
        for section in payment_sections:
            title_elem = section.find('p', class_='merchant-details-payment__payment-type-title')
            if not title_elem:
                continue
                
            section_title = title_elem.get_text().strip()
            
            if 'pagamento pelo site' in section_title.lower():
                prefix = 'pag_site_'
            elif 'pagamento na entrega' in section_title.lower():
                prefix = 'pag_entrega_'
            else:
                continue
            
            section_elements = section.find_all(['p', 'span'])
            current_subtype = None
            
            for element in section_elements:
                if element.name == 'p' and 'merchant-details-payment__payment-subtype' in element.get('class', []):
                    current_subtype = element.get_text().strip().lower()
                
                elif element.name == 'span' and 'payment-tag' in element.get('class', []) and current_subtype:
                    if 'débito' in current_subtype:
                        payment_data[f'{prefix}debito'] = True
                    elif 'crédito' in current_subtype:
                        payment_data[f'{prefix}credito'] = True
                    elif 'pix' in current_subtype:
                        payment_data[f'{prefix}pix'] = True
                    elif 'vale-refeição' in current_subtype:
                        payment_data[f'{prefix}vale_refeicao'] = True
                    elif 'dinheiro' in current_subtype:
                        payment_data[f'{prefix}dinheiro'] = True
    
    except Exception:
        pass
    
    return payment_data


def test_restaurant(browser, url, name):
    """Testa extração para um restaurante."""
    try:
        browser.get(url)
        time.sleep(7)
        
        # Clicar "Ver mais"
        try:
            wait = WebDriverWait(browser, 10)
            ver_mais_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@class="merchant-details-about__description-see-more-button"]'))
            )
            browser.execute_script("arguments[0].click();", ver_mais_btn)
            time.sleep(4)
        except:
            try:
                ver_mais_btn = browser.find_element(By.XPATH, '//button[contains(text(), "Ver mais")]')
                browser.execute_script("arguments[0].click();", ver_mais_btn)
                time.sleep(4)
            except:
                pass
        
        # Clicar aba "Pagamento"
        try:
            wait = WebDriverWait(browser, 10)
            payment_tab = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Pagamento")]'))
            )
            browser.execute_script("arguments[0].click();", payment_tab)
            time.sleep(4)
        except:
            try:
                payment_tab = browser.find_element(By.XPATH, '//button[@role="tab" and contains(text(), "Pagamento")]')
                browser.execute_script("arguments[0].click();", payment_tab)
                time.sleep(4)
            except:
                try:
                    payment_tab = browser.find_element(By.XPATH, '//button[contains(@class, "marmita-tab") and contains(text(), "Pagamento")]')
                    browser.execute_script("arguments[0].click();", payment_tab)
                    time.sleep(4)
                except:
                    pass
        
        time.sleep(3)
        
        # Extrair dados
        html_content = browser.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        pedido_minimo = extract_minimum_order(soup)
        payment_methods = extract_payment_methods(soup)
        
        return {
            'nome': name,
            'pedido_minimo': pedido_minimo,
            **payment_methods,
            'status': 'sucesso'
        }
        
    except Exception:
        return {
            'nome': name,
            'pedido_minimo': 0.0,
            'pag_site_debito': False,
            'pag_site_credito': False,
            'pag_site_pix': False,
            'pag_site_vale_refeicao': False,
            'pag_entrega_debito': False,
            'pag_entrega_credito': False,
            'pag_entrega_pix': False,
            'pag_entrega_vale_refeicao': False,
            'pag_entrega_dinheiro': False,
            'status': 'erro'
        }


def main():
    """Função principal."""
    print("🧪 TESTE DE EXTRAÇÃO - MÉTODOS DE PAGAMENTO")
    
    try:
        # Carregar CSV
        csv_path = find_latest_csv()
        df = pd.read_csv(csv_path)
        test_restaurants = df.head(5)
        print(f"📂 CSV carregado: {csv_path.name}")
        
        # Inicializar navegador
        print("🌐 Inicializando navegador...")
        browser = setup_browser()
        
        resultados = []
        
        try:
            print(f"🔄 Processando {len(test_restaurants)} restaurantes...\n")
            
            for i, row in test_restaurants.iterrows():
                nome_curto = row['Restaurante'][:35]
                print(f"[{i+1}/5] {nome_curto}...", end=" ")
                
                resultado = test_restaurant(browser, row['URL'], row['Restaurante'])
                resultados.append(resultado)
                
                if resultado['status'] == 'sucesso':
                    print("✅")
                else:
                    print("❌")
        
        finally:
            browser.quit()
        
        # Criar DataFrame
        df_data = []
        sucessos = 0
        
        for resultado in resultados:
            if resultado['status'] == 'sucesso':
                sucessos += 1
                df_data.append({
                    'Restaurante': resultado['nome'],
                    'Pedido_Minimo': resultado['pedido_minimo'],
                    'Pag_Site_Debito': resultado['pag_site_debito'],
                    'Pag_Site_Credito': resultado['pag_site_credito'],
                    'Pag_Site_PIX': resultado['pag_site_pix'],
                    'Pag_Site_Vale_Refeicao': resultado['pag_site_vale_refeicao'],
                    'Pag_Entrega_Debito': resultado['pag_entrega_debito'],
                    'Pag_Entrega_Credito': resultado['pag_entrega_credito'],
                    'Pag_Entrega_PIX': resultado['pag_entrega_pix'],
                    'Pag_Entrega_Vale_Refeicao': resultado['pag_entrega_vale_refeicao'],
                    'Pag_Entrega_Dinheiro': resultado['pag_entrega_dinheiro']
                })
        
        print(f"\n✅ Resultado: {sucessos}/5 restaurantes processados com sucesso")
        
        # Exibir DataFrame
        if df_data:
            df_final = pd.DataFrame(df_data)
            print(f"\n📊 DATAFRAME FINAL:")
            print("=" * 120)
            print(df_final.to_string(index=False))
            print("=" * 120)
            
            # Salvar
            output_path = Path("reports") / f"teste_pagamentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"💾 Salvo em: {output_path.name}")
        else:
            print("❌ Nenhum dado válido coletado")
    
    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()