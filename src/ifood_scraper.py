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
    def __init__(self, n_scrolls=10, output_path=None, timeout=10):
        """Inicializa o scraper com configurações básicas."""
        self.n_scrolls = n_scrolls
        self.timeout = timeout
        self.browser = None
        self.ifood_url = 'https://www.ifood.com.br/restaurantes'
        
        # Output path
        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = None  
        
    def _setup_browser(self):
        """Inicializa Chrome com configurações mínimas."""
        print("Inicializando navegador.")
        
        options = webdriver.ChromeOptions()
        # Apenas 2-3 opções essenciais
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        
        self.browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
    
    print(" Navegador inicializado.")
        
    def _load_restaurants(self):
        """Navega para iFood e carrega restaurantes com retry simples."""
        print(f"Acessando {self.ifood_url}")
        self.browser.get(self.ifood_url)
        
        # Aceitar localização
        try:
            location_btn = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Usar minha localização"]'))
            )
            location_btn.click()
            time.sleep(3)
            print("Localização configurada")
        except:
            print("Falha na localização, continuando...")
        
        # Carregar mais restaurantes
        print(f"Carregando mais restaurantes ({self.n_scrolls} tentativas)")
        
        for i in range(self.n_scrolls):
            # Scroll
            self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Tentar clicar "Ver mais" - retry simples
            if not self._click_ver_mais():
                print(f"⚠️ Parou no ciclo {i+1} - sem mais botões")
                break
            
            time.sleep(3)
        
        print("Carregamento concluído")
        return self.browser.page_source

    def _click_ver_mais(self):
        """Clica 'Ver mais' com retry simples (apenas 1 tentativa extra)."""
        selectors = [
            '//button[@aria-label="Ver mais"]',
            '//button[contains(@class, "cardstack-nextcontent__button")]'
        ]
        
        for selector in selectors:
            try:
                button = self.browser.find_element(By.XPATH, selector)
                self.browser.execute_script("arguments[0].click();", button)
                return True
            except:
                continue
        
        # Uma tentativa extra (retry simples)
        try:
            time.sleep(1)
            button = self.browser.find_element(By.XPATH, selectors[0])
            self.browser.execute_script("arguments[0].click();", button)
            return True
        except:
            return False
        
    def _get_user_location(self):
        """Extrai coordenadas precisas do localStorage do iFood."""
        print("Extraindo localização do usuário...")
        
        try:
            # JavaScript para extrair dados do localStorage
            location_data = self.browser.execute_script("""
                try {
                    const sessionData = JSON.parse(localStorage.getItem('fstr.session'));
                    return {
                        general_lat: sessionData.geoPoint?.latitude,
                        general_lng: sessionData.geoPoint?.longitude,
                        delivery_lat: sessionData.properties?.delLat,
                        delivery_lng: sessionData.properties?.delLon,
                        geohash: window.geohash || null,
                        full_session: sessionData
                    };
                } catch(e) {
                    return {error: e.message};
                }
            """)
            
            if location_data and not location_data.get('error'):
                print(f"Localização Entrega: {location_data.get('delivery_lat')}, {location_data.get('delivery_lng')}")
                print(f"Geohash: {location_data.get('geohash')}")
                return location_data
            else:
                print(f"Erro ao extrair localização: {location_data.get('error', 'Dados não encontrados')}")
                
        except Exception as e:
            print(f"Erro na extração de localização: {e}")
        
        # Fallback para Uberlândia
        return {
            'general_lat': -18.9187, 'general_lng': -48.2772,
            'delivery_lat': -18.9187, 'delivery_lng': -48.2772,
            'geohash': None, 'error': 'Usando coordenadas padrão'
        }

    def _extract_all_data(self, html):
        """Extrai todos os dados do html"""
        print("Extraindo dados")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar todos os containers de restaurantes
        containers = soup.find_all('div', class_='merchant-list-v2__item-wrapper')
        print(f"Encontrados {len(containers)} restaurantes")
        
        # Dados globais do scraping
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_location = self._get_user_location()

        # Listas para dados
        restaurants_data = []
        
        # LOOP ÚNICO - extrai tudo de uma vez
        for container in containers:
            try:
                # URL
                link = container.find('a', class_='merchant-v2__link')
                url = link.get('href') if link else ''
                if url.startswith('/'):
                    url = f"https://www.ifood.com.br{url}"
                
                # Nome
                name_span = container.find('span', class_='merchant-v2__name')
                nome = name_span.text.strip() if name_span else 'N/A'
                
                # Info (nota • tipo • distância)
                info_div = container.find('div', class_='merchant-v2__info')
                nota, tipo, distancia = self._process_info_text(info_div.text if info_div else '')
                
                # Footer (tempo • frete)
                footer_div = container.find('div', class_='merchant-v2__footer')
                tempo_min, tempo_max, frete = self._process_footer_text(footer_div.text if footer_div else '')
                
                # Adicionar à lista (um restaurante completo)
                restaurants_data.append({
                    'Data' : current_time,
                    'User_Latitude': user_location.get('delivery_lat'),
                    'User_Longitude': user_location.get('delivery_lng'),
                    'Geohash': user_location.get('geohash'),
                    'URL': url,
                    'Restaurante': nome,
                    'Nota': nota,
                    'Tipo de comida': tipo,
                    'Distancia': distancia,
                    'Tempo Min': tempo_min,
                    'Tempo Max': tempo_max,
                    'Preco do Frete': frete
                })
                
            except Exception as e:
                print(f"⚠️ Erro ao processar restaurante: {e}")
                continue
        
        print(f" {len(restaurants_data)} restaurantes processados com sucesso")
        return restaurants_data
    

    def _process_info_text(self, text):
        """
        Processa texto do tipo: '4.6 • Lanches • 2.9 km'
        Retorna: (nota, tipo, distancia)
        """
        if not text or '•' not in text:
            return 0.0, 'N/A', 0.0
        
        parts = [p.strip() for p in text.split('•')]
        
        if len(parts) < 3:
            return 0.0, 'N/A', 0.0
        
        # Nota (primeiro elemento)
        try:
            # Remove rating star e pega só o número
            nota_text = parts[0].replace('\n', '').strip()
            # Pega só números e ponto
            nota_clean = ''.join(c for c in nota_text if c.isdigit() or c == '.')
            nota = float(nota_clean) if nota_clean else 0.0
        except:
            nota = 0.0
        
        # Tipo (segundo elemento)
        tipo = parts[1].strip()
        
        # Distância (terceiro elemento)
        try:
            dist_text = parts[2].replace('km', '').replace(',', '.').strip()
            distancia = float(dist_text) if dist_text else 0.0
        except:
            distancia = 0.0
        
        return nota, tipo, distancia

    def _process_footer_text(self, text):
        """
        Processa texto do tipo: '15-25 min • R$ 9,99' ou '15-25 min • Grátis'
        Retorna: (tempo_min, tempo_max, frete)
        """
        if not text or '•' not in text:
            return 0, 0, 0.0
        
        parts = [p.strip() for p in text.split('•')]
        
        if len(parts) < 2:
            return 0, 0, 0.0
        
        # Tempo (primeiro elemento)
        try:
            tempo_text = parts[0].replace('min', '').strip()
            if '-' in tempo_text:
                tempo_min, tempo_max = map(int, tempo_text.split('-'))
            else:
                tempo_min = tempo_max = int(tempo_text)
        except:
            tempo_min = tempo_max = 0
        
        # Frete (segundo elemento)
        frete_text = parts[1].lower()
        
        if 'grátis' in frete_text or 'gratis' in frete_text:
            frete = 0.0
        else:
            try:
                # Remove tudo exceto números, vírgulas e pontos
                import re
                frete_numbers = re.sub(r'[^\d,.]', '', parts[1])
                frete_numbers = frete_numbers.replace(',', '.')
                frete = float(frete_numbers) if frete_numbers else 0.0
            except:
                frete = 0.0
        
        return tempo_min, tempo_max, frete
        
    def _save_data(self, restaurants_data):
        """Salva dados direto em CSV - sem batches, sem complicação."""
        print("Salvando dados...")
        
        if not restaurants_data:
            print("Nenhum dado para salvar")
            return False
        
        # Criar DataFrame
        df = pd.DataFrame(restaurants_data)
        
        # Gerar nome do arquivo (inline)
        if not self.output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bd_scrap_ifood_{self.n_scrolls}_{timestamp}.csv"
            self.output_path = Path("reports") / filename
        
        # Garantir que diretório existe (uma linha)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Salvar CSV
        try:
            df.to_csv(self.output_path, encoding='utf-8-sig', index=False)
            print(f"Arquivo salvo: {self.output_path}")
            print(f"Total de restaurantes: {len(df)}")
            return True
            
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            return False
        
    def scrape(self):
        """
        Executa o scraping completo de forma simplificada.
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            print("Iniciando scraping do iFood...")
            
            # 1. Setup navegador
            self._setup_browser()
            
            # 2. Carregar restaurantes (navegar + clicar "ver mais")
            html = self._load_restaurants()
            
            # 3. Extrair TODOS os dados com loop único
            restaurants_data = self._extract_all_data(html)
            
            # 4. Validação simples
            if not restaurants_data:
                print("Nenhum restaurante encontrado")
                return False
            
            # 5. Salvar dados
            success = self._save_data(restaurants_data)
            
            if success:
                print("Scraping concluído com sucesso!")
                return True
            else:
                print("Erro ao salvar dados")
                return False
                
        except Exception as e:
            print(f"Erro durante o scraping: {e}")
            return False
            
        finally:
            # Cleanup simples
            if self.browser:
                self.browser.quit()
                print("Navegador fechado")