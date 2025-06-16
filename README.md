# 🍕 iFood Restaurant Scraper

Um sistema completo de **web scraping** para coleta de dados de restaurantes do iFood, desenvolvido com **Selenium**, **Beautiful Soup** e **Pandas**. O projeto extrai informações detalhadas incluindo dados básicos dos restaurantes, localização, métodos de pagamento e informações de entrega.

## 🚀 Funcionalidades

### 📊 Dados Básicos dos Restaurantes
- **Nome do restaurante**
- **Nota de avaliação** 
- **Tipo de culinária**
- **Distância do usuário**
- **Tempo de entrega** (mínimo e máximo)
- **Preço do frete**
- **URL do restaurante**

### 📍 Informações de Localização
- **Endereço completo**
- **Bairro**
- **Cidade e UF**
- **CEP**
- **Coordenadas do usuário** (latitude/longitude)
- **Geohash da localização**

### 💳 Métodos de Pagamento
- **Pagamento pelo site**: Débito, Crédito, PIX, Vale-refeição
- **Pagamento na entrega**: Débito, Crédito, PIX, Vale-refeição, Dinheiro
- **Pedido mínimo** do restaurante

## 🛠️ Tecnologias Utilizadas

- **[Selenium](https://selenium-python.readthedocs.io/)** - Automação do navegador
- **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)** - Parsing de HTML
- **[Pandas](https://pandas.pydata.org/)** - Manipulação de dados
- **[WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager)** - Gerenciamento automático do ChromeDriver

## 📦 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/ifood-scraper.git
cd ifood-scraper
```

### 2. Instale as dependências
```bash
pip install pandas selenium beautifulsoup4 webdriver-manager pathlib
```

### 3. Verifique se o Chrome está instalado
O projeto utiliza o Google Chrome como navegador padrão.

## 🎯 Como Usar

### Scraping Básico de Restaurantes

```bash
# Execução padrão (10 scrolls)
python main.py

# Personalizar número de scrolls
python main.py --scrolls 20

# Personalizar timeout
python main.py --timeout 15
```

### Extração de Detalhes Completos

```bash
# Extrair detalhes dos restaurantes (endereços + pagamentos)
python main_details.py

# Com timeout personalizado
python main_details.py --timeout 20

# Especificar diretório do CSV
python main_details.py --directory "meus_dados"
```

### Teste de Funcionalidades

```bash
# Testar extração de métodos de pagamento (5 restaurantes)
python test_payment_extraction.py
```

## 📁 Estrutura do Projeto

```
ifood-scraper/
├── 📄 main.py                          # Script principal simplificado
├── 📄 main_details.py                  # Extração de detalhes completos
├── 📄 test_payment_extraction.py       # Teste de métodos de pagamento
├── 📁 src/
│   ├── 📄 ifood_scraper.py            # Classe principal do scraper
│   ├── 📄 restaurant_details_scraper.py # Extração de detalhes
│   └── 📁 old/                        # Versões anteriores
├── 📁 reports/                        # Arquivos CSV gerados
│   ├── 📄 bd_scrap_ifood_*.csv        # Dados básicos dos restaurantes
│   ├── 📄 details_bd_scrap_ifood_*.csv # Detalhes completos
│   └── 📄 teste_pagamentos_*.csv      # Testes de pagamento
└── 📄 README.md
```

## 📊 Formatos de Saída

### Dados Básicos (`bd_scrap_ifood_*.csv`)
```csv
Data,User_Latitude,User_Longitude,Geohash,URL,Restaurante,Nota,Tipo de comida,Distancia,Tempo Min,Tempo Max,Preco do Frete
2025-06-15 12:52:39,-18.9395041,-48.3059029,6utskb0v3k6t,https://...,McDonald's,4.6,Lanches,2.9,20,30,9.99
```

### Detalhes Completos (`details_bd_scrap_ifood_*.csv`)
```csv
URL,Restaurante,Pedido_Minimo,Endereco,Bairro,Cidade,UF,CEP,Pag_Site_Debito,Pag_Site_Credito,Pag_Site_PIX,Pag_Site_Vale_Refeicao,Pag_Entrega_Debito,Pag_Entrega_Credito,Pag_Entrega_PIX,Pag_Entrega_Vale_Refeicao,Pag_Entrega_Dinheiro,Data_Scraping
https://...,McDonald's,15.0,"Av Rondon Pacheco, 1311",Tabajaras,Uberlandia,MG,38400-242,True,True,True,True,True,True,False,False,True,2025-06-15 19:07:25
```

## ⚙️ Configurações Avançadas

### Personalização do Scraper

```python
from src.ifood_scraper import IFoodScraper

# Criar scraper personalizado
scraper = IFoodScraper(
    n_scrolls=15,           # Número de cliques em "Ver mais"
    timeout=20,             # Timeout em segundos
    output_path="dados.csv" # Caminho personalizado
)

# Executar scraping
success = scraper.scrape()
```

### Configuração de Localização

O scraper detecta automaticamente sua localização através do iFood, mas você pode modificar as coordenadas padrão no código:

```python
# Em ifood_scraper.py, método _get_user_location()
return {
    'general_lat': -18.9187,    # Latitude padrão (Uberlândia)
    'general_lng': -48.2772,    # Longitude padrão
    'delivery_lat': -18.9187,
    'delivery_lng': -48.2772,
    'geohash': None
}
```

## 🔧 Principais Classes

### `IFoodScraper`
Classe principal para scraping de dados básicos dos restaurantes.

**Métodos principais:**
- `scrape()` - Executa o processo completo de scraping
- `_load_restaurants()` - Navega e carrega mais restaurantes
- `_extract_all_data()` - Extrai todos os dados usando Beautiful Soup

### `RestaurantDetailsScraper`
Classe para extração de detalhes completos (endereços + pagamentos).

**Métodos principais:**
- `scrape_details()` - Extrai detalhes de todos os restaurantes
- `_extract_details_with_retry()` - Extrai dados com retry automático
- `_extract_payment_methods()` - Extrai métodos de pagamento

## 📈 Exemplos de Uso

### Análise Básica dos Dados

```python
import pandas as pd

# Carregar dados
df = pd.read_csv('reports/bd_scrap_ifood_10_20250615_125239.csv')

# Estatísticas básicas
print(f"Total de restaurantes: {len(df)}")
print(f"Nota média: {df['Nota'].mean():.2f}")
print(f"Tipos de culinária: {df['Tipo de comida'].nunique()}")

# Top 10 tipos de culinária
print(df['Tipo de comida'].value_counts().head(10))
```

### Análise de Métodos de Pagamento

```python
import pandas as pd

# Carregar dados detalhados
df_details = pd.read_csv('reports/details_bd_scrap_ifood_20250615_192715.csv')

# Análise de pagamentos
pix_aceito = df_details['Pag_Site_PIX'].sum()
print(f"Restaurantes que aceitam PIX: {pix_aceito}")

# Pedido mínimo médio
print(f"Pedido mínimo médio: R$ {df_details['Pedido_Minimo'].mean():.2f}")
```

## ⚠️ Considerações Importantes

### Rate Limiting
- O scraper inclui delays entre requisições para evitar sobrecarga
- Tempos de espera configuráveis para diferentes cenários

### Tratamento de Erros
- Retry automático em caso de falhas
- Logs detalhados de sucessos e erros
- Continuidade do processo mesmo com falhas individuais

### Responsabilidade
- **Use com responsabilidade** e respeite os termos de uso do iFood
- **Não sobrecarregue** os servidores com muitas requisições simultâneas
- **Considere** usar apenas para fins educacionais ou de pesquisa

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🙋‍♂️ Suporte

Se você encontrar problemas ou tiver dúvidas:

1. Verifique os [Issues existentes](https://github.com/seu-usuario/ifood-scraper/issues)
2. Crie um novo Issue descrevendo o problema
3. Inclua logs de erro e detalhes do ambiente

---

**⭐ Se este projeto foi útil para você, considere dar uma estrela no repositório!**