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
    """Classe simplificada para extrair detalhes dos restaurantes do iFood."""
    
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
        """Inicializa Chrome com configurações mínimas."""
        print("Inicializando navegador...")
        
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        
        self.browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        self.browser.set_page_load_timeout(30)
        print("Navegador inicializado")
    
    def _find_latest_csv(self):
        """Encontra o CSV mais recente no diretório."""
        print("Procurando CSV mais recente...")
        
        if not self.csv_directory.exists():
            raise FileNotFoundError(f"Diretório não encontrado: {self.csv_directory}")
        
        csv_files = list(self.csv_directory.glob("bd_scrap_ifood_*.csv"))
        
        if not csv_files:
            raise FileNotFoundError("Nenhum arquivo bd_scrap_ifood_*.csv encontrado")
        
        latest_file = max(csv_files, key=os.path.getmtime)
        print(f"CSV encontrado: {latest_file.name}")
        
        # Carregar e validar CSV
        self.df_original = pd.read_csv(latest_file)
        
        if len(self.df_original) == 0:
            raise ValueError("CSV está vazio")
        
        if 'URL' not in self.df_original.columns or 'Restaurante' not in self.df_original.columns:
            raise ValueError("CSV não tem colunas obrigatórias: URL e Restaurante")
        
        print(f"CSV validado. Total de restaurantes: {len(self.df_original)}")
        return latest_file
    
    def _extract_details_with_retry(self, url, name):
        """Extrai detalhes de um restaurante com retry simples."""
        try:
            print(f"Processando: {name}")
            self.browser.get(url)
            time.sleep(7)  # Aumentar delay para evitar rate limiting
            
            # Clicar no botão "Ver mais" - OBRIGATÓRIO para mostrar endereço
            try:
                wait = WebDriverWait(self.browser, 10)  # Aumentar timeout
                ver_mais_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@class="merchant-details-about__description-see-more-button"]'))
                )
                self.browser.execute_script("arguments[0].click();", ver_mais_btn)
                time.sleep(4)  # Mais tempo após clicar
            except:
                # Fallback para outros seletores
                try:
                    ver_mais_btn = self.browser.find_element(By.XPATH, '//button[contains(text(), "Ver mais")]')
                    self.browser.execute_script("arguments[0].click();", ver_mais_btn)
                    time.sleep(4)
                except:
                    print(f"Aviso: Botão 'Ver mais' não encontrado para {name}")
            
            # Criar Beautiful Soup
            html_content = self.browser.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extrair informações de endereço
            address_info = self._get_address_info(soup)
            
            if address_info['endereco'] != 'Não encontrado':
                self.success += 1
                print(f"Sucesso: {address_info['endereco'][:50]}...")
            else:
                self.errors += 1
                print(f"Falha: {name}")
            
            return address_info
            
        except Exception as e:
            # Retry simples
            try:
                print(f"Tentativa extra para: {name}")
                time.sleep(5)  # Delay maior no retry
                self.browser.get(url)
                time.sleep(8)
                
                # Tentar clicar no botão novamente
                try:
                    ver_mais_btn = self.browser.find_element(By.XPATH, '//button[@class="merchant-details-about__description-see-more-button"]')
                    self.browser.execute_script("arguments[0].click();", ver_mais_btn)
                    time.sleep(4)
                except:
                    pass
                
                html_content = self.browser.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                address_info = self._get_address_info(soup)
                
                if address_info['endereco'] != 'Não encontrado':
                    self.success += 1
                else:
                    self.errors += 1
                
                return address_info
                
            except Exception:
                self.errors += 1
                print(f"Falha após retry: {name}")
                return {
                    'endereco': 'Erro na extração',
                    'bairro': 'Erro na extração',
                    'cidade': 'Erro na extração',
                    'uf': 'Erro na extração',
                    'cep': 'Erro na extração'
                }
            
        except Exception as e:
            # Retry simples - uma tentativa extra
            try:
                print(f"Tentativa extra para: {name}")
                time.sleep(2)
                self.browser.get(url)
                time.sleep(3)
                
                html_content = self.browser.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                address_info = self._get_address_info(soup)
                
                if address_info['endereco'] != 'Erro na extração':
                    self.success += 1
                else:
                    self.errors += 1
                
                return address_info
                
            except Exception:
                self.errors += 1
                print(f"Falha após retry: {name}")
                return {
                    'endereco': 'Erro na extração',
                    'bairro': 'Erro na extração',
                    'cidade': 'Erro na extração',
                    'uf': 'Erro na extração',
                    'cep': 'Erro na extração'
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
                
        except Exception as e:
            print(f"Erro ao extrair endereço: {e}")
            return {
                'endereco': 'Erro na extração',
                'bairro': 'Erro na extração',
                'cidade': 'Erro na extração',
                'uf': 'Erro na extração',
                'cep': 'Erro na extração'
            }
    
    def _save_data(self):
        """Salva os dados coletados em CSV."""
        print("Salvando dados...")
        
        if not self.restaurants_data:
            print("Nenhum dado para salvar")
            return None
        
        df_final = pd.DataFrame(self.restaurants_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"details_bd_scrap_ifood_{timestamp}.csv"
        output_path = self.csv_directory / filename
        
        # Garantir que diretório existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"Arquivo salvo: {filename}")
        print(f"Total de registros: {len(df_final)}")
        print(f"Sucessos: {self.success}")
        print(f"Erros: {self.errors}")
        print(f"Localização: {output_path.absolute()}")
        
        return output_path
    
    def scrape_details(self):
        """Executa o scraping completo de detalhes."""
        try:
            print("Iniciando scraping de detalhes...")
            
            # 1. Encontrar e validar CSV
            self._find_latest_csv()
            
            # 2. Inicializar navegador
            self._setup_browser()
            
            # 3. Processar restaurantes
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for i in range(len(self.df_original)):
                url = self.df_original.iloc[i]['URL']
                nome = self.df_original.iloc[i]['Restaurante']
                
                self.processed += 1
                print(f"Processando {self.processed}/{len(self.df_original)}")
                
                # Extrair detalhes
                address_info = self._extract_details_with_retry(url, nome)
                
                # Adicionar aos dados
                self.restaurants_data.append({
                    'URL': url,
                    'Restaurante': nome,
                    'Endereco': address_info['endereco'],
                    'Bairro': address_info['bairro'],
                    'Cidade': address_info['cidade'],
                    'UF': address_info['uf'],
                    'CEP': address_info['cep'],
                    'Data_Scraping': current_time
                })
            
            # 4. Salvar dados
            output_path = self._save_data()
            
            print("Scraping de detalhes concluído!")
            return str(output_path)
            
        except Exception as e:
            print(f"Erro durante o scraping: {e}")
            raise
            
        finally:
            if self.browser:
                self.browser.quit()
                print("Navegador fechado")


# Exemplo de uso
if __name__ == "__main__":
    scraper = RestaurantDetailsScraper(csv_directory="reports")
    output_path = scraper.scrape_details()
    print(f"Arquivo gerado: {output_path}")