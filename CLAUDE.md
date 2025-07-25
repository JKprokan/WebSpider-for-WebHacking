# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhSpider is a defensive web security tool that performs automated vulnerability analysis through web crawling, input field extraction, and AI-powered security assessment. The tool combines static/dynamic crawling with local LLM analysis via Ollama integration.

## Installation and Setup

```bash
# Install dependencies
pip install .

# Install Ollama for LLM functionality
# Mac: brew install ollama
# Ubuntu: curl -fsSL https://ollama.com/install.sh | sh

# Download the security analysis model
ollama pull hf.co/Jin312/WebSpider_Mistral:Q4_K_M
```

## Common Commands

### Running the Tool
```bash
# Basic crawling
whspider -u "https://target.com" --static

# Dynamic crawling with Playwright
whspider -u "https://target.com" --dynamic --depth 2

# LLM security analysis (basic)
whspider -u "https://target.com" --llm

# LLM + RAG deep analysis
whspider -u "https://target.com" --deep

# Generate network graph
whspider -u "https://target.com" --graph

# Export results
whspider -u "https://target.com" --json --csv
```

### Testing
```bash
# Run individual test scripts
python test_simple.py          # Basic RAG pipeline test
python test_llm_only.py        # LLM-only analysis test
python test_deep_vs_llm.py     # Compare deep vs basic analysis
python test_rag_debug.py       # RAG debugging
```

### Development
```bash
# Check database tables after crawling
python check_db_tables.py

# Install in development mode
pip install -e .

# Safe cache cleanup (preserves RAG files)
# Only delete domain-specific databases, NOT kb.index or kb_chunks.pkl
rm -f data/*.db  # Safe: only removes crawl databases
# rm -rf data/    # DANGEROUS: removes RAG files too!
```

## Architecture

### Core Components

**CLI Entry Point (`cli.py`)**
- Uses Click framework for command-line interface
- Orchestrates crawling, analysis, and export operations
- Automatically creates domain-specific databases in `data/` directory

**Crawling Engines**
- `modules/static_crawler.py` - requests/BeautifulSoup-based crawling
- `modules/dynamic_crawler.py` - Playwright-based JavaScript execution
- Both support DFS/BFS traversal, robots.txt compliance, and cookie handling

**Data Processing**
- `modules/parser.py` - Extracts form inputs and security-relevant attributes
- `modules/params.py` - Analyzes URL parameters and query strings
- `modules/db.py` - SQLite persistence with domain-based file naming
- `modules/url_filter.py` - Include/exclude pattern matching

**AI Analysis Stack**
- `modules/local_llm.py` - Ollama integration with caching and optimization
- `modules/rag.py` - Knowledge base search using sentence-transformers and FAISS
- Analysis results are cached to avoid redundant LLM calls

**Output and Visualization**
- `modules/export.py` - JSON/CSV export functionality  
- `modules/visualize.py` - pyvis-based interactive network graphs
- `modules/config.py` - Centralized attribute definitions

### Data Flow

1. **Crawling**: Static or dynamic crawler discovers URLs and extracts input fields
2. **Storage**: Results stored in SQLite database (`data/{domain}.db`)
3. **Analysis**: LLM analyzes input field structures for security vulnerabilities
4. **RAG Enhancement**: Knowledge base provides context for deeper analysis
5. **Output**: Results exported as JSON/CSV or visualized as network graphs

### Key Design Patterns

- **Modular Architecture**: Each functional area is isolated in separate modules
- **Database-Centric**: All crawled data persists in SQLite for repeatability
- **Caching Strategy**: LRU caching prevents redundant LLM analysis
- **Performance Optimization**: Resource blocking, parallel processing, and query optimization

### Configuration

The tool uses domain-based file organization:
- Database: `data/{domain}.db` (e.g., `data/example_com.db`)
- RAG Index: `data/kb.index` and `data/kb_chunks.pkl`
- Config: Optional YAML files at `~/.whspider.yaml` or `config.yaml`

**⚠️ IMPORTANT: Never delete the following critical RAG files:**
- `data/kb.index` - FAISS vector index for security knowledge base
- `data/kb_chunks.pkl` - Text chunks for RAG system
These files are required for `--deep` and `--rag` functionality and are difficult to recreate.

### Security Focus

This is a defensive security tool designed to identify potential vulnerabilities in web applications through:
- Input field enumeration and analysis
- Parameter extraction and assessment
- AI-powered vulnerability pattern recognition
- Link relationship mapping for attack surface analysis