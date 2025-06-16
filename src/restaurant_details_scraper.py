import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from pathlib import Path
from datetime import datetime
import os
import re


class RestaurantDetailsScraper:
    """Classe para extrair detalhes completos dos restaurantes do iFood."""
    
    def __init__(self, csv_directory="reports", timeout=10):
        self.csv_directory = Path(csv_directory)
        self.timeout = timeout
        self.browser = None
        self.df_original = None
        self.restaurants_data = []
        self.processed = 0
        self.success = 0
        self.errors = 0
    
    def _setup_browser(self):
        """Inicializa Chrome com configurações otimizadas."""
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        self.browser.set_page_load_timeout(30)
    
    def _find_latest_csv(self):
        """Encontra o CSV mais recente no diretório."""
        if not self.csv_directory.exists():
            raise FileNotFoundError(f"Diretório não encontrado: {self.csv_directory}")
        
        csv_files = list(self.csv_directory.glob("bd_scrap_ifood_*.csv"))
        
        if not csv_files:
            raise FileNotFoundError("Nenhum arquivo bd_scrap_ifood_*.csv encontrado")
        
        latest_file = max(csv_files, key=os.path.getmtime)
        
        # Carregar e validar CSV
        self.df_original = pd.read_csv(latest_file)
        
        if len(self.df_original) == 0:
            raise ValueError("CSV está vazio")
        
        if 'URL' not in self.df_original.columns or 'Restaurante' not in self.df_original.columns:
            raise ValueError("CSV não tem colunas obrigatórias: URL e Restaurante")
        
        return latest_file
    
    def _extract_minimum_order(self, soup):
        """Extrai pedido mínimo da página."""
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
    
    def _click_payment_tab(self):
        """Clica na aba de pagamento."""
        try:
            wait = WebDriverWait(self.browser, 10)
            payment_tab = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Pagamento")]'))
            )
            self.browser.execute_script("arguments[0].click();", payment_tab)
            time.sleep(4)
            return True
        except:
            try:
                payment_tab = self.browser.find_element(By.XPATH, '//button[@role="tab" and contains(text(), "Pagamento")]')
                self.browser.execute_script("arguments[0].click();", payment_tab)
                time.sleep(4)
                return True
            except:
                try:
                    payment_tab = self.browser.find_element(By.XPATH, '//button[contains(@class, "marmita-tab") and contains(text(), "Pagamento")]')
                    self.browser.execute_script("arguments[0].click();", payment_tab)
                    time.sleep(4)
                    return True
                except:
                    return False
    
    def _extract_payment_methods(self, soup):
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
    
    def _extract_details_with_retry(self, url, name):
        """Extrai detalhes completos de um restaurante com retry."""
        try:
            # PASSO 1: Entrar no link e extrair pedido mínimo
            self.browser.get(url)
            time.sleep(7)
            
            html_content_initial = self.browser.page_source
            soup_initial = BeautifulSoup(html_content_initial, 'html.parser')
            pedido_minimo = self._extract_minimum_order(soup_initial)
            
            # PASSO 2: Clicar "Ver mais" e extrair endereço
            try:
                wait = WebDriverWait(self.browser, 10)
                ver_mais_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@class="merchant-details-about__description-see-more-button"]'))
                )
                self.browser.execute_script("arguments[0].click();", ver_mais_btn)
                time.sleep(4)
            except:
                try:
                    ver_mais_btn = self.browser.find_element(By.XPATH, '//button[contains(text(), "Ver mais")]')
                    self.browser.execute_script("arguments[0].click();", ver_mais_btn)
                    time.sleep(4)
                except:
                    pass
            
            # Extrair endereço APÓS clicar "Ver mais"
            html_content_address = self.browser.page_source
            soup_address = BeautifulSoup(html_content_address, 'html.parser')
            address_info = self._get_address_info(soup_address)
            
            # PASSO 3: Clicar "Pagamento" e extrair métodos de pagamento
            payment_clicked = self._click_payment_tab()
            
            # Extrair pagamentos APÓS clicar na aba
            if payment_clicked:
                time.sleep(3)  # Aguardar carregamento
                html_content_payment = self.browser.page_source
                soup_payment = BeautifulSoup(html_content_payment, 'html.parser')
                payment_methods = self._extract_payment_methods(soup_payment)
            else:
                payment_methods = {
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
            
            # Combinar todos os dados
            result = {
                'pedido_minimo': pedido_minimo,
                **address_info,
                **payment_methods
            }
            
            if address_info['endereco'] != 'Não encontrado':
                self.success += 1
            else:
                self.errors += 1
            
            return result
            
        except Exception:
            # Retry simples
            try:
                time.sleep(5)
                self.browser.get(url)
                time.sleep(8)
                
                # Tentar extrair pelo menos o básico
                html_content = self.browser.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                
                pedido_minimo = self._extract_minimum_order(soup)
                address_info = self._get_address_info(soup)
                
                result = {
                    'pedido_minimo': pedido_minimo,
                    **address_info,
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
                
                if address_info['endereco'] != 'Não encontrado':
                    self.success += 1
                else:
                    self.errors += 1
                
                return result
                
            except Exception:
                self.errors += 1
                return {
                    'pedido_minimo': 0.0,
                    'endereco': 'Erro na extração',
                    'bairro': 'Erro na extração',
                    'cidade': 'Erro na extração',
                    'uf': 'Erro na extração',
                    'cep': 'Erro na extração',
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
    
    def _get_address_info(self, soup):
        """Extrai informações de endereço usando Beautiful Soup."""
        default_data = {
            'endereco': 'Não encontrado',
            'bairro': 'Não encontrado', 
            'cidade': 'Não encontrado',
            'uf': 'Não encontrado',
            'cep': 'Não encontrado'
        }
        
        try:
            # Buscar a div com informações de endereço
            info_divs = soup.find_all('div', class_='merchant-details-about__info')
            
            # Procurar a div que contém "Endereço"
            address_div = None
            for div in info_divs:
                title = div.find('p', class_='merchant-details-about__info-title')
                if title and 'Endereço' in title.get_text():
                    address_div = div
                    break
            
            if not address_div:
                return default_data
            
            # Extrair os dados do endereço
            data_paragraphs = address_div.find_all('p', class_='merchant-details-about__info-data')
            
            if len(data_paragraphs) >= 3:
                # Primeiro parágrafo: "Avenida Sílvio Rugani, 715 - Tubalina"
                endereco_completo = data_paragraphs[0].get_text().strip()
                
                # Segundo parágrafo: "Uberlandia - MG"
                cidade_uf = data_paragraphs[1].get_text().strip()
                
                # Terceiro parágrafo: "CEP: 38412-026"
                cep_raw = data_paragraphs[2].get_text().strip()
                
                # Processar endereço e bairro
                if ' - ' in endereco_completo:
                    partes = endereco_completo.split(' - ', 1)
                    endereco_limpo = partes[0].strip()
                    bairro_limpo = partes[1].strip()
                else:
                    endereco_limpo = endereco_completo
                    bairro_limpo = "Não identificado"
                
                # Processar cidade e UF
                if ' - ' in cidade_uf:
                    partes = cidade_uf.split(' - ', 1)
                    cidade_limpa = partes[0].strip()
                    uf_limpa = partes[1].strip()
                else:
                    cidade_limpa = cidade_uf
                    uf_limpa = "Não identificado"
                
                # Processar CEP
                cep_limpo = cep_raw.replace('CEP: ', '').strip()
                
                return {
                    'endereco': endereco_limpo,
                    'bairro': bairro_limpo,
                    'cidade': cidade_limpa,
                    'uf': uf_limpa,
                    'cep': cep_limpo
                }
            
            return default_data
                
        except Exception:
            return {
                'endereco': 'Erro na extração',
                'bairro': 'Erro na extração',
                'cidade': 'Erro na extração',
                'uf': 'Erro na extração',
                'cep': 'Erro na extração'
            }
    
    def _save_data(self):
        """Salva os dados coletados em CSV."""
        if not self.restaurants_data:
            return None
        
        df_final = pd.DataFrame(self.restaurants_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"details_bd_scrap_ifood_{timestamp}.csv"
        output_path = self.csv_directory / filename
        
        # Garantir que diretório existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        return output_path
    
    def scrape_details(self):
        """Executa o scraping completo de detalhes."""
        try:
            print("INICIANDO SCRAPING DE DETALHES COMPLETOS")
            
            # 1. Encontrar e validar CSV
            csv_file = self._find_latest_csv()
            print(f"CSV carregado: {csv_file.name} ({len(self.df_original)} restaurantes)")
            
            # 2. Inicializar navegador
            print("Inicializando navegador...")
            self._setup_browser()
            
            # 3. Processar restaurantes
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            total = len(self.df_original)
            
            print(f"🔄 Processando {total} restaurantes...\n")
            
            for i in range(total):
                url = self.df_original.iloc[i]['URL']
                nome = self.df_original.iloc[i]['Restaurante']
                
                self.processed += 1
                nome_curto = nome[:35]
                print(f"[{self.processed}/{total}] {nome_curto}...", end=" ")
                
                # Extrair detalhes
                details = self._extract_details_with_retry(url, nome)
                
                # Adicionar aos dados
                self.restaurants_data.append({
                    'URL': url,
                    'Restaurante': nome,
                    'Pedido_Minimo': details['pedido_minimo'],
                    'Endereco': details['endereco'],
                    'Bairro': details['bairro'],
                    'Cidade': details['cidade'],
                    'UF': details['uf'],
                    'CEP': details['cep'],
                    'Pag_Site_Debito': details['pag_site_debito'],
                    'Pag_Site_Credito': details['pag_site_credito'],
                    'Pag_Site_PIX': details['pag_site_pix'],
                    'Pag_Site_Vale_Refeicao': details['pag_site_vale_refeicao'],
                    'Pag_Entrega_Debito': details['pag_entrega_debito'],
                    'Pag_Entrega_Credito': details['pag_entrega_credito'],
                    'Pag_Entrega_PIX': details['pag_entrega_pix'],
                    'Pag_Entrega_Vale_Refeicao': details['pag_entrega_vale_refeicao'],
                    'Pag_Entrega_Dinheiro': details['pag_entrega_dinheiro'],
                    'Data_Scraping': current_time
                })
                
                # Status visual
                if details['endereco'] not in ['Não encontrado', 'Erro na extração']:
                    print("Sucesso")
                else:
                    print("Erro")
            
            # 4. Salvar dados
            output_path = self._save_data()
            
            print(f"\n SCRAPING CONCLUÍDO!")
            print(f"Sucessos: {self.success}/{total}")
            print(f"Erros: {self.errors}/{total}")
            print(f"Arquivo salvo: {output_path.name}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"Erro durante o scraping: {e}")
            raise
            
        finally:
            if self.browser:
                self.browser.quit()


# Exemplo de uso
if __name__ == "__main__":
    scraper = RestaurantDetailsScraper(csv_directory="reports")
    output_path = scraper.scrape_details()
    print(f"Arquivo gerado: {output_path}")