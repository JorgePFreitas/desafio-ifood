#!/usr/bin/env python3
"""
Script principal simplificado para executar o scraping do iFood.

Uso:
    python main.py                           # Padrão: 10 scrolls
    python main.py --scrolls 15              # Customizar scrolls
    python main.py --timeout 15              # Customizar timeout
"""

import argparse
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / 'src'))
try:
    from src.ifood_scraper import IFoodScraper
except ImportError:
    print("Erro: Arquivo src/ifood_scraper.py não encontrado.")
    sys.exit(1)


def main():
    """Função principal simplificada."""
    parser = argparse.ArgumentParser(description="Scraper simplificado de restaurantes do iFood")
    
    parser.add_argument(
        '--scrolls', '-s',
        type=int,
        default=10,
        help='Número de cliques no botão "Ver mais" (padrão: 10)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=10,
        help='Timeout em segundos (padrão: 10)'
    )
    
    args = parser.parse_args()
    
    print("Iniciando scraping simplificado do iFood...")
    print(f"Configurações: {args.scrolls} scrolls, timeout {args.timeout}s")
    
    try:
        # Criar scraper (ele mesmo gera o nome do arquivo e cria diretórios)
        scraper = IFoodScraper(
            n_scrolls=args.scrolls,
            timeout=args.timeout
            # output_path não especificado = geração automática
        )
        
        # Executar scraping
        success = scraper.scrape()
        
        if success:
            print("Scraping concluído com sucesso!")
            return 0
        else:
            print("Erro durante o scraping.")
            return 1
            
    except KeyboardInterrupt:
        print("\nScraping interrompido pelo usuário.")
        return 1
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())