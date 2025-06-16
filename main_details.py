#!/usr/bin/env python3
"""
Script principal simplificado para executar o scraping de detalhes dos restaurantes do iFood.

Uso:
    python main_details.py                   # Usar diretório padrão
    python main_details.py --timeout 15     # Customizar timeout
"""

import argparse
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / 'src'))

try:
    from src.restaurant_details_scraper import RestaurantDetailsScraper
except ImportError:
    print("Erro: Arquivo src\restaurant_details_scraper.py não encontrado.")
    sys.exit(1)


def main():
    """Função principal simplificada."""
    parser = argparse.ArgumentParser(description="Scraper simplificado de detalhes dos restaurantes do iFood")
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=10,
        help='Timeout em segundos (padrão: 10)'
    )
    
    parser.add_argument(
        '--directory', '-d',
        type=str,
        default="reports",
        help='Diretório onde buscar o CSV (padrão: reports)'
    )
    
    args = parser.parse_args()
    
    print("Iniciando scraping de detalhes dos restaurantes...")
    print(f"Diretório de busca: {args.directory}")
    print(f"Timeout configurado: {args.timeout}")
    
    try:
        scraper = RestaurantDetailsScraper(
            csv_directory=args.directory,
            timeout=args.timeout
        )
        
        output_path = scraper.scrape_details()
        
        print("Scraping de detalhes concluído com sucesso!")
        print(f"Arquivo gerado: {Path(output_path).name}")
        print(f"Localização completa: {output_path}")
        return 0
            
    except KeyboardInterrupt:
        print("Scraping interrompido pelo usuário.")
        return 1
    except Exception as e:
        print(f"Erro durante o scraping: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())