import os
import yaml
import json
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import click

class RAGPipeline:
    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        self.embedder = None
        self.index = None
        self.chunks = None
        self._initialize()
    
    def _load_config(self, config_path):
        """설정 파일 로드"""
        if config_path is None:
            # 기본 설정 경로들 시도
            config_paths = [
                os.path.expanduser("~/.whspider.yaml"),
                "config.yaml",
                "data/config.yaml"
            ]
            for path in config_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            else:
                # 기본 설정 반환
                return {
                    "rag": {
                        "index": "data/kb.index",
                        "chunks": "data/kb_chunks.pkl",
                        "top_k": 3,
                        "model": "all-MiniLM-L6-v2"
                    },
                    "model": {
                        "name": "webspider-mistral"
                    }
                }
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            click.secho(f"[!] 설정 파일 로드 실패: {e}", fg="red")
            return {}
    
    def _initialize(self):
        """RAG 파이프라인 초기화"""
        try:
            # 임베딩 모델 로드
            model_name = self.config.get("rag", {}).get("model", "all-MiniLM-L6-v2")
            click.secho(f"[+] 임베딩 모델 로드 중: {model_name}", fg="cyan")
            self.embedder = SentenceTransformer(model_name)
            
            # FAISS 인덱스 로드
            index_path = self.config.get("rag", {}).get("index", "data/kb.index")
            if os.path.exists(index_path):
                click.secho(f"[+] FAISS 인덱스 로드 중: {index_path}", fg="cyan")
                self.index = faiss.read_index(index_path)
            else:
                click.secho(f"[!] FAISS 인덱스 파일을 찾을 수 없습니다: {index_path}", fg="yellow")
                click.secho(f"[!] 구글 드라이브에서 kb.index 파일을 다운로드하여 {index_path}에 배치하세요", fg="yellow")
            
            # 청크 데이터 로드
            chunks_path = self.config.get("rag", {}).get("chunks", "data/kb_chunks.pkl")
            if os.path.exists(chunks_path):
                click.secho(f"[+] 청크 데이터 로드 중: {chunks_path}", fg="cyan")
                with open(chunks_path, 'rb') as f:
                    self.chunks = pickle.load(f)
            else:
                click.secho(f"[!] 청크 데이터 파일을 찾을 수 없습니다: {chunks_path}", fg="yellow")
                click.secho(f"[!] 구글 드라이브에서 kb_chunks.pkl 파일을 다운로드하여 {chunks_path}에 배치하세요", fg="yellow")
                
        except Exception as e:
            click.secho(f"[!] RAG 파이프라인 초기화 실패: {e}", fg="red")
    
    def is_ready(self):
        """RAG 파이프라인이 사용 가능한지 확인"""
        return self.embedder is not None and self.index is not None and self.chunks is not None
    
    def search(self, query, top_k=None):
        """쿼리에 대한 관련 청크 검색"""
        if not self.is_ready():
            return []
        
        if top_k is None:
            top_k = self.config.get("rag", {}).get("top_k", 3)
        
        try:
            # 쿼리 임베딩
            query_vector = self.embedder.encode([query])
            
            # FAISS 검색
            scores, indices = self.index.search(query_vector.astype('float32'), top_k)
            
            # 결과 조합
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.chunks):
                    chunk = self.chunks[idx]
                    # 청크가 딕셔너리인 경우 텍스트 추출
                    if isinstance(chunk, dict):
                        text = chunk.get('text', str(chunk))
                    else:
                        text = str(chunk)
                    
                    results.append({
                        "text": text,
                        "score": float(score),
                        "index": int(idx)
                    })
            
            return results
            
        except Exception as e:
            click.secho(f"[!] RAG 검색 실패: {e}", fg="red")
            return []
    
    def get_context(self, query, max_context_length=2000):
        """쿼리에 대한 컨텍스트 생성"""
        results = self.search(query)
        
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for result in results:
            text = result["text"]
            if isinstance(text, str):
                if current_length + len(text) > max_context_length:
                    break
                context_parts.append(text)
                current_length += len(text)
        
        return "\n\n".join(context_parts)
    
    def get_context_with_sources(self, query, max_context_length=2000):
        """쿼리에 대한 출처 정보가 포함된 컨텍스트 생성"""
        results = self.search(query)
        
        if not results:
            return "", []
        
        context_parts = []
        sources = []
        current_length = 0
        
        for i, result in enumerate(results):
            text = result["text"]
            score = result["score"]
            idx = result["index"]
            
            if isinstance(text, str):
                if current_length + len(text) > max_context_length:
                    break
                
                # 출처 정보 추가
                source_info = f"[Source {i+1}] (Relevance: {score:.3f}, Doc ID: {idx})"
                context_with_source = f"{source_info}\n{text}"
                
                context_parts.append(context_with_source)
                sources.append({
                    "source_id": i+1,
                    "doc_id": idx,
                    "relevance_score": score,
                    "text_preview": text[:100] + "..." if len(text) > 100 else text
                })
                current_length += len(context_with_source)
        
        full_context = "\n\n".join(context_parts)
        return full_context, sources

def create_default_config():
    """기본 설정 파일 생성"""
    config = {
        "rag": {
            "index": "data/kb.index",
            "chunks": "data/kb_chunks.pkl", 
            "top_k": 3,
            "model": "all-MiniLM-L6-v2"
        },
        "model": {
            "name": "webspider-mistral"
        }
    }
    
    config_path = os.path.expanduser("~/.whspider.yaml")
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    click.secho(f"[+] 기본 설정 파일 생성: {config_path}", fg="green")
    return config_path

# 전역 RAG 파이프라인 인스턴스
_rag_pipeline = None

def get_rag_pipeline():
    """RAG 파이프라인 싱글톤 인스턴스 반환"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline 