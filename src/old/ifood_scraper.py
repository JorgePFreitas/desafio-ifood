import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from pathlib import Path
from datetime import datetime


class IFoodScraper:
    """
    Classe para scraping de restaurantes do iFood usando Selenium + Beautiful Soup.
    
    Vantagens da abordagem híbrida:
    - Selenium para navegação e interações dinâmicas
    - Beautiful Soup para parsing limpo e eficiente do HTML
    """
    
    def __init__(self, n_scrolls=10, output_path=None, timeout=10):
        """
        Inicializa o scraper do iFood.
        
        Args:
            n_scrolls (int): Número de cliques no botão "Ver mais"
            output_path (str): Caminho do arquivo de saída
            timeout (int): Timeout em segundos para aguardar elementos
        """
        self.n_scrolls = n_scrolls
        self.timeout = timeout
        self.browser = None
        self.soup = None
        
        # Configurar caminho de saída
        if output_path:
            self.output_path = Path(output_path)
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.output_path = Path(f"bd_scrap_ifood_{n_scrolls}_{timestamp}.csv")
        
        # URLs e seletores
        self.ifood_url = 'https://www.ifood.com.br/restaurantes'
        
        # Dados coletados
        self.restaurants_data = []
    
    def _init_browser(self):
        """Inicializa o navegador Chrome."""
        print("Inicializando navegador...")
        try:
            options = webdriver.ChromeOptions()
            # options.add_argument('--headless')  # Descomente para executar sem interface
            self.browser = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            print("Navegador inicializado com sucesso")
        except Exception as e:
            print(f"Erro ao inicializar navegador: {e}")
            raise
    
    def _accept_location(self):
        """Aceita usar localização atual."""
        print("Configurando localização")
        try:
            wait = WebDriverWait(self.browser, self.timeout)
            use_location_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Usar minha localização"]'))
            )
            use_location_btn.click()
            time.sleep(3)
            print("Localização configurada")
            return True
        except Exception as e:
            print(f"Erro ao configurar localização: {e}")
            return False
    
    def _scroll_and_load_more(self):
        """Executa scroll e clica em 'Ver mais' n_scrolls vezes."""
        print(f"Iniciando {self.n_scrolls} ciclos de carregamento...")
        
        successful_loads = 0
        
        for i in range(self.n_scrolls):
            print(f"Ciclo {i+1}/{self.n_scrolls}")
            
            # Scroll suave até o final
            self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Tentar clicar no botão "Ver mais"
            if self._click_load_more_button():
                successful_loads += 1
                time.sleep(3)  # Aguarda carregar novos restaurantes
            else:
                print("Não foi possível carregar mais restaurantes. Finalizando...")
                break
        
        print(f"Carregamento concluído! {successful_loads} cliques bem-sucedidos")
        return successful_loads > 0
    
    def _click_load_more_button(self):
        """Encontra e clica no botão 'Ver mais' usando JavaScript."""
        selectors = [
            '//button[@aria-label="Ver mais"]',
            '//button[contains(@class, "cardstack-nextcontent__button")]',
            '//button[contains(text(), "Ver mais")]'
        ]
        
        for selector in selectors:
            try:
                wait = WebDriverWait(self.browser, 5)
                button = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                
                # Usar JavaScript para clicar (mais confiável)
                self.browser.execute_script("arguments[0].click();", button)
                return True
                
            except Exception:
                continue
        
        return False
    
    def _get_page_soup(self):
        """Obtém o HTML da página e cria objeto Beautiful Soup."""
        print("Criando Beautiful Soup do HTML atual...")
        try:
            # Aguarda elementos carregarem
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, '//span[@class="merchant-v2__name"]'))
            )
            
            # Pega HTML completo da página
            html_content = self.browser.page_source
            self.soup = BeautifulSoup(html_content, 'html.parser')
            print("Beautiful Soup criado com sucesso")
            return True
            
        except Exception as e:
            print(f"Erro ao criar Beautiful Soup: {e}")
            return False
    
    def _extract_restaurants_bs(self):
        """Extrai nomes dos restaurantes usando Beautiful Soup."""
        print("Extraindo nomes dos restaurantes...")
        try:
            restaurant_elements = self.soup.find_all('span', class_='merchant-v2__name')
            restaurants = [rest.get_text().strip() for rest in restaurant_elements if rest.get_text().strip()]
            print(f"✅ {len(restaurants)} restaurantes encontrados")
            return restaurants
        except Exception as e:
            print(f"Erro ao extrair restaurantes: {e}")
            return []
    
    def _extract_urls_bs(self):
        """Extrai URLs dos restaurantes usando Beautiful Soup."""
        print("Extraindo URLs dos restaurantes...")
        try:
            url_elements = self.soup.find_all('a', class_='merchant-v2__link')
            urls = []
            
            for link in url_elements:
                href = link.get('href')
                if href:
                    # Se a URL é relativa, adicionar o domínio base
                    if href.startswith('/'):
                        full_url = f"https://www.ifood.com.br{href}"
                    else:
                        full_url = href
                    urls.append(full_url)
            
            print(f"{len(urls)} URLs completas encontradas")
            return urls
        except Exception as e:
            print(f" Erro ao extrair URLs: {e}")
            return []
    
    def _extract_restaurant_info_bs(self):
        """Extrai informações dos restaurantes (nota, tipo, distância) usando Beautiful Soup."""
        print("Extraindo informações dos restaurantes...")
        try:
            info_elements = self.soup.find_all('div', class_='merchant-v2__info')
            
            ratings = []
            types = []
            distances = []
            
            for info in info_elements:
                full_text = info.get_text().strip()
                
                if '•' in full_text:
                    parts = full_text.split('•')
                    
                    if len(parts) >= 3:
                        # Rating: limpar e converter para float
                        rating_clean = parts[0].strip().replace('\n', '')
                        try:
                            rating_float = float(rating_clean) if rating_clean.replace('.', '').isdigit() else 0.0
                        except:
                            rating_float = 0.0
                        
                        # Tipo: limpar
                        type_clean = parts[1].strip().replace('\n', '')
                        
                        # Distância: extrair número
                        distance_clean = parts[2].strip().replace('\n', '')
                        try:
                            distance_float = float(distance_clean.replace('km', '').replace(',', '.').strip())
                        except:
                            distance_float = 0.0
                        
                        ratings.append(rating_float)
                        types.append(type_clean)
                        distances.append(distance_float)
            
            print(f"{len(ratings)} informações extraídas")
            return ratings, types, distances
            
        except Exception as e:
            print(f"Erro ao extrair informações: {e}")
            return [], [], []
    
    def _extract_delivery_info_bs(self):
        """Extrai informações de entrega (tempo e frete) usando Beautiful Soup."""
        print("Extraindo informações de entrega...")
        try:
            footer_elements = self.soup.find_all('div', class_='merchant-v2__footer')
            
            times_min = []
            times_max = []
            freight_prices = []
            
            for footer in footer_elements:
                full_text = footer.get_text().strip()
                
                if '•' in full_text:
                    parts = full_text.split('•')
                    
                    if len(parts) >= 2:
                        # Tempo: extrair min e max
                        time_clean = parts[0].replace('\n', '').replace('min', '').strip()
                        try:
                            if '-' in time_clean:
                                tmin, tmax = map(int, time_clean.split('-'))
                            else:
                                tmin = tmax = int(time_clean)
                        except:
                            tmin = tmax = 0
                        
                        # Frete: tratar "grátis" e valores monetários
                        freight_raw = parts[1].strip().replace('\n', '')
                        
                        if 'grátis' in freight_raw.lower() or 'gratis' in freight_raw.lower():
                            freight_float = 0.0
                        else:
                            # Usar regex para extrair apenas números, vírgulas e pontos
                            freight_numbers = re.sub(r'[^\d,.]', '', freight_raw)
                            freight_numbers = freight_numbers.replace(',', '.')
                            try:
                                freight_float = float(freight_numbers) if freight_numbers else 0.0
                            except:
                                freight_float = 0.0
                        
                        times_min.append(tmin)
                        times_max.append(tmax)
                        freight_prices.append(freight_float)
            
            print(f"{len(times_min)} informações de entrega extraídas")
            return times_min, times_max, freight_prices
            
        except Exception as e:
            print(f"Erro ao extrair informações de entrega: {e}")
            return [], [], []
    
    def _normalize_data_lengths(self, *data_lists):
        """Normaliza o tamanho de todas as listas para o menor tamanho."""
        list_names = ['URLs', 'Restaurantes', 'Ratings', 'Types', 'Distances', 'Times Min', 'Times Max', 'Freight']
        
        print("Verificando tamanhos das listas:")
        for name, data_list in zip(list_names, data_lists):
            print(f"{name}: {len(data_list)}")
        
        # Encontrar tamanho mínimo
        min_length = min(len(data_list) for data_list in data_lists)
        print(f"Tamanho mínimo: {min_length}")
        
        # Cortar todas as listas
        normalized_lists = [data_list[:min_length] for data_list in data_lists]
        
        print(f"Todas as listas ajustadas para {min_length} elementos")
        return normalized_lists
    
    def _create_dataframe(self, urls, restaurants, ratings, types, distances, times_min, times_max, freight_prices):
        """Cria DataFrame com os dados coletados."""
        print("Criando DataFrame...")
        
        df = pd.DataFrame({
            'URL': urls,
            'Restaurante': restaurants,
            'Nota': ratings,
            'Tipo de comida': types,
            'Distancia': distances,
            'Tempo Min': times_min,
            'Tempo Max': times_max,
            'Preco do Frete': freight_prices
        })
        
        print(f"DataFrame criado com {len(df)} registros")
        return df
    
    def _save_data(self, df):
        """Salva os dados em CSV."""
        print("Salvando dados...")
        try:
            # Garantir que o diretório existe
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Salvar CSV
            df.to_csv(self.output_path, encoding='utf-8-sig', index=False)
            
            print(f"Arquivo salvo com sucesso em: {self.output_path}")
            print(f"Total de restaurantes salvos: {len(df)}")
            return True
            
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return False
    
    def scrape(self):
        """
        Executa o scraping completo.
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            print("Iniciando scraping do iFood...")
            
            # 1. Inicializar navegador
            self._init_browser()
            
            # 2. Navegar para o iFood
            print(f"Acessando {self.ifood_url}")
            self.browser.get(self.ifood_url)
            
            # 3. Configurar localização
            if not self._accept_location():
                return False
            
            # 4. Carregar mais restaurantes
            if not self._scroll_and_load_more():
                print("Falha no carregamento, mas continuando com dados atuais...")
            
            # 5. Criar Beautiful Soup
            if not self._get_page_soup():
                return False
            
            # 6. Extrair dados usando Beautiful Soup
            restaurants = self._extract_restaurants_bs()
            urls = self._extract_urls_bs()
            ratings, types, distances = self._extract_restaurant_info_bs()
            times_min, times_max, freight_prices = self._extract_delivery_info_bs()
            
            # 7. Verificar se temos dados
            if not restaurants:
                print("Nenhum restaurante encontrado")
                return False
            
            # 8. Normalizar tamanhos das listas
            normalized_data = self._normalize_data_lengths(
                urls, restaurants, ratings, types, distances, times_min, times_max, freight_prices
            )
            
            # 9. Criar DataFrame
            df = self._create_dataframe(*normalized_data)
            
            # 10. Salvar dados
            return self._save_data(df)
            
        except Exception as e:
            print(f"Erro durante o scraping: {e}")
            return False
            
        finally:
            # Fechar navegador
            if self.browser:
                self.browser.quit()
                print("Navegador fechado")
    
    def __enter__(self):
        """Suporte para context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup automático ao sair do context manager."""
        if self.browser:
            self.browser.quit()


# Exemplo de uso
if __name__ == "__main__":
    # Uso básico
    scraper = IFoodScraper(n_scrolls=5)
    success = scraper.scrape()
    
    if success:
        print("Scraping concluído com sucesso!")
    else:
        print("Erro no scraping")
    
    # Ou usando context manager
    # with IFoodScraper(n_scrolls=10) as scraper:
    #     scraper.scrape()