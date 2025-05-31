import click

@click.command()
@click.option('-u', '--url', required=True, help='타겟 URL')
@click.option('--depth', default=1, type=int, help='크롤링 깊이 (기본: 1)')
@click.option('--static', is_flag=True, help='정적 크롤링')
@click.option('--dynamic', is_flag=True, help='동적 크롤링 (Playwright)')
@click.option('--json', is_flag=True, help='JSON 결과 추출')
@click.option('--csv', is_flag=True, help='CSV 파일 추출')
@click.option("--graph", is_flag=True, help="크롤링된 링크 구조를 인터랙티브 그래프로 시각화")
@click.option('--llm', is_flag=True, help='LLM 연계 분석 실행')
@click.option('--include', default="", help='포함할 키워드 (쉼표로 구분)')
@click.option('--exclude', default="", help='제외할 키워드 (쉼표로 구분)')
@click.option('--mode', default='dfs', type=click.Choice(['dfs', 'bfs']), help='탐색 방식 (dfs 또는 bfs)')


def webspider(url, depth, static, dynamic, json, csv, graph, llm, include, exclude, mode):
    click.secho(f"\n [URL] {url}", fg="cyan")
    click.secho(f" [Depth] {depth}", fg="cyan")

    if not any([static, dynamic, json, csv, graph, llm]):
        click.secho(" 실행할 작업을 최소 1개 이상 선택하세요 (예: --static)", fg="yellow")
        return

    if static:
        from modules.static_crawler import run_static_crawl
        click.secho("[+] 정적 크롤링 시작", fg="green")
        run_static_crawl(url, depth, include, exclude, mode)

    if dynamic:
        from modules.dynamic_crawler import run_dynamic_crawl_entry
        click.secho("[+] 동적 크롤링 시작", fg="green")
        run_dynamic_crawl_entry(url, depth, include, exclude, mode)
        
    if json:
        from modules.export import export_json
        click.secho("[+] JSON 파일 추출", fg="green")
        export_json()

    if csv:
        from modules.export import export_csv
        click.secho("[+] CSV 파일 추출", fg="green")
        export_csv()

    if graph:
        from modules.visualize import generate_interactive_graph
        generate_interactive_graph()
        
if __name__ == '__main__':
    from modules.db import create_table
    create_table()
    webspider()
