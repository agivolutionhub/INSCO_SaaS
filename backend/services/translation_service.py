#!/usr/bin/env python3
import re, sys, time, zipfile, tempfile, os, json, random, tiktoken, shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from pptx import Presentation

# Cargar variables de entorno desde múltiples ubicaciones posibles
env_paths = [
    Path(__file__).parent.parent / "config" / ".env",  # Ruta original
    Path("/app/.env"),                                 # Ruta alternativa en el contenedor
    Path("/app/config/.env"),                          # Ruta del volumen montado
]

# Intentar cargar de cada ubicación
for env_path in env_paths:
    if env_path.exists():
        print(f"[translation_service] Cargando variables desde: {env_path}")
        load_dotenv(env_path)
        break

# Constantes
CACHE_FILE = Path(__file__).parent.parent / "config" / "cache" / "translations.json"
MAX_RETRIES = 3
BASE_WAIT = 2.0
MAX_WAIT = 30.0
BACKOFF = 2.0
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID", "asst_mBShBt93TIVI0PKE7zsNO0eZ")
OPENAI_BETA_HEADER = {"OpenAI-Beta": "assistants=v2"}

class TranslationCache:
    def __init__(self):
        self.cache, self.modified = {}, False
        self.hits = self.misses = 0
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            if CACHE_FILE.exists():
                self.cache = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
                print(f"Caché cargada: {len(self.cache)} traducciones")
            else:
                print("Creando nueva caché")
        except Exception as e:
            print(f"Error de caché: {e}")
    
    def get(self, text):
        if not text or not text.strip(): return None
        if text in self.cache:
            self.hits += 1
            return self.cache[text]
        self.misses += 1
        return None
    
    def set(self, text, translation):
        if text and text.strip() and translation:
            self.cache[text] = translation
            self.modified = True
    
    def save(self):
        if not self.modified: return
        try:
            CACHE_FILE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"Caché guardada: {len(self.cache)} traducciones")
            self.modified = False
        except Exception as e:
            print(f"Error al guardar caché: {e}")
    
    @property
    def stats(self):
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total * 100 if total > 0 else 0
        }

class Translator:
    def __init__(self, target_language="en", use_cache=True):
        self.target_language = target_language
        self._configure_proxy()
        
        self.client = OpenAI(api_key=self._get_api_key())
        self.current_thread = None
        self.cache = TranslationCache() if use_cache else None
        self.stats = {"texts": 0, "calls": 0, "duplicate_texts": 0, "retries": 0, "retry_success": 0, "errors": 0}
        self.token_stats = {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
        self._test_connection()
    
    def _configure_proxy(self):
        """Configurar proxy para la conexión API"""
        os.environ["no_proxy"] = "*"
        if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
        if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]
    
    def _get_api_key(self):
        if not (key := os.environ.get("OPENAI_API_KEY")):
            raise ValueError("API key no encontrada en variables de entorno")
        return key
    
    def _test_connection(self):
        try:
            self.current_thread = self.client.beta.threads.create(
                extra_headers=OPENAI_BETA_HEADER
            )
            
            # Comprobación usando el asistente
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Traduce el siguiente texto del español al {self.target_language}:"},
                    {"role": "user", "content": "Hola mundo"}
                ],
                temperature=0.3
            )
            if response and response.choices:
                print(f"✓ Prueba de traducción exitosa: '{response.choices[0].message.content}'")
                return True
            print("⚠️ Prueba de conexión fallida: Respuesta vacía")
        except Exception as e:
            print(f"❌ Error de conexión: {str(e)}")
        return False
    
    def translate(self, texts):
        """Traduce textos individuales o en lote con caché y optimización"""
        if isinstance(texts, str):
            if self.cache and (cached := self.cache.get(texts)):
                self.stats["texts"] += 1
                self.token_stats["cached_input_tokens"] += self._estimate_tokens(texts)
                return cached
            return self._translate_batch([texts]).get(texts, texts)
        
        # Procesar una lista de textos
        return self._process_text_list(texts)
    
    def _process_text_list(self, texts):
        """Procesa una lista de textos para traducción"""
        result, to_translate, cached_texts = {}, [], []
        for text in texts:
            if not text or not text.strip():
                result[text] = text
            elif self.cache and (cached := self.cache.get(text)):
                result[text] = cached
                cached_texts.append(text)
            else:
                to_translate.append(text)
        
        if cached_texts and self.cache:
            print(f"Obtenidos {len(cached_texts)} textos desde caché")
            self.token_stats["cached_input_tokens"] += sum(self._estimate_tokens(t) for t in cached_texts)
        
        if not to_translate: return result
        
        unique_texts = list(dict.fromkeys(to_translate))
        self.stats["duplicate_texts"] += len(to_translate) - len(unique_texts)
        translations = self._translate_batch(unique_texts)
        
        if translations and self.token_stats["input_tokens"] == 0:
            self.token_stats["input_tokens"] = max(1000, len(unique_texts) * 25)
            self.token_stats["output_tokens"] = max(1000, len(unique_texts) * 30)
        
        for text in to_translate:
            result[text] = translations.get(text, text)
        
        return result
    
    def _translate_batch(self, texts):
        if not texts: return {}
        
        # Configuración de lotes
        batch_config = self._plan_batch_processing(texts)
        
        all_translations = {}
        total_processed = 0
        
        for i, batch in enumerate(batch_config["batches"], 1):
            print(f"Procesando lote {i}/{len(batch_config['batches'])} ({len(batch)} textos)...")
            all_translations.update(self._translate_single_batch(batch))
            total_processed += len(batch)
            
            if len(batch_config["batches"]) > 1:
                print(f"Progreso: {(total_processed/len(texts))*100:.1f}% ({total_processed}/{len(texts)})")
            
            if i < len(batch_config["batches"]):
                pause = 3.0 if len(batch_config["batches"]) > 5 else 2.0
                print(f"Pausa de {pause}s antes del siguiente lote...")
                time.sleep(pause)
        
        return all_translations
    
    def _plan_batch_processing(self, texts):
        """Planifica cómo dividir los textos en lotes para procesamiento eficiente"""
        MAX_TOKENS, MAX_TEXTS, MIN_TEXTS = 2500, 50, 20
        print(f"Preparando traducción de {len(texts)} textos únicos...")
        
        if len(texts) <= MIN_TEXTS:
            return {"batches": [texts], "batch_size": len(texts)}
        
        # Estimar tokens promedio por texto
        sample_size = min(20, len(texts))
        sample_texts = random.sample(texts, sample_size)
        avg_tokens = sum(self._estimate_tokens(t) for t in sample_texts) / sample_size
        
        # Calcular tamaño de lote óptimo
        batch_size = min(MAX_TEXTS, max(MIN_TEXTS, int(MAX_TOKENS / avg_tokens * 0.7)))
        batch_size = min(batch_size, 30)
        
        # Dividir en lotes
        batches = [texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]
        print(f"Dividiendo en {len(batches)} lotes de ~{batch_size} textos/lote")
        
        return {"batches": batches, "batch_size": batch_size}
    
    def _translate_single_batch(self, texts):
        if not texts: return {}
        
        # Preparar la instrucción y el contenido
        instructions = self._get_translation_prompt()
        user_content = "TEXTOS:\n" + "\n".join(f"[{i}] {text}" for i, text in enumerate(texts, 1))
        
        retries, wait_time = 0, BASE_WAIT
        
        while retries <= MAX_RETRIES:
            try:
                # Crear un thread nuevo
                thread = self.client.beta.threads.create(
                    extra_headers=OPENAI_BETA_HEADER
                )
                print(f"Thread creado: {thread.id}")
                
                # Añadir mensaje al thread
                self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"{instructions}\n\n{user_content}",
                    extra_headers=OPENAI_BETA_HEADER
                )
                
                # Ejecutar el asistente
                run = self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=ASSISTANT_ID,
                    extra_headers=OPENAI_BETA_HEADER
                )
                print(f"Ejecución iniciada: {run.id}")
                
                # Esperar a que termine la ejecución
                while run.status in ["queued", "in_progress"]:
                    print(f"Estado: {run.status}")
                    time.sleep(1)
                    run = self.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id,
                        extra_headers=OPENAI_BETA_HEADER
                    )
                
                # Verificar si se completó correctamente
                if run.status != "completed":
                    error_msg = f"Error en la traducción. Estado final: {run.status}"
                    if hasattr(run, "last_error"):
                        error_msg += f" - Detalle: {run.last_error}"
                    print(error_msg)
                    raise RuntimeError(error_msg)
                
                # Obtener mensajes
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id,
                    extra_headers=OPENAI_BETA_HEADER
                )
                
                # Encontrar la respuesta del asistente
                response_text = ""
                for msg in messages.data:
                    if msg.role == "assistant":
                        for content in msg.content:
                            if content.type == "text":
                                response_text += content.text.value
                
                if not response_text:
                    raise RuntimeError("No se recibió traducción del asistente")
                
                # Gestionar reintentos exitosos
                if retries > 0:
                    self.stats["retry_success"] += 1
                    print(f"✓ Reintento exitoso después de {retries} intentos")
                
                # Parsear la respuesta
                translations = self._parse_translation_response(response_text, texts)
                
                # Actualizar estadísticas
                self.stats["texts"] += len(texts)
                self.stats["calls"] += 1
                
                # Estimar tokens (no podemos obtenerlos directamente)
                input_tokens = self._estimate_tokens(instructions) + self._estimate_tokens(user_content)
                output_tokens = self._estimate_tokens(response_text)
                self.token_stats["input_tokens"] += input_tokens
                self.token_stats["output_tokens"] += output_tokens
                
                return translations
                
            except Exception as e:
                error_message = str(e)
                rate_limit = any(msg in error_message.lower() for msg in ["rate limit", "rate_limit", "too_many_requests"])
                
                if rate_limit and retries < MAX_RETRIES:
                    retries += 1
                    self.stats["retries"] += 1
                    wait_time = min(wait_time * BACKOFF, MAX_WAIT)
                    print(f"⚠️ Rate limit detectado. Reintentando en {wait_time:.2f}s ({retries}/{MAX_RETRIES})...")
                    time.sleep(wait_time)
                    continue
                
                self.stats["errors"] += 1
                print(f"Error de traducción: {error_message}")
                return {}
    
    def _get_translation_prompt(self):
        """Obtiene el prompt de sistema para la traducción"""
        return f"""Eres un traductor profesional especializado en la industria del cartón ondulado.
Traduce los siguientes textos del español al {self.target_language}.
Responde solo con la traducción de cada texto, manteniendo la numeración original en formato [número] texto_traducido.
No expliques ni comentes tus traducciones. No añadas información adicional.
Respeta el formato y la estructura del texto original."""
    
    def _parse_translation_response(self, response_text, original_texts):
        """Parsea la respuesta del traductor y extrae las traducciones"""
        translations = {}
        print(f"Respuesta recibida: {len(response_text)} caracteres")
        
        for line in response_text.split('\n'):
            if match := re.match(r'\s*\[(\d+)\]\s*(.*)', line):
                if current_index := int(match.group(1)):
                    translations[current_index] = self._clean_response(match.group(2).strip())
        
        result = {}
        if not translations:
            print(f"⚠️ No se obtuvieron traducciones: {response_text[:100]}...")
            return result
        
        print(f"✓ Obtenidas {len(translations)} traducciones")
        
        # Asignar traducciones a textos originales
        for i, text in enumerate(original_texts, 1):
            if i in translations:
                traduccion = translations[i]
                if traduccion.strip().lower() != text.strip().lower():
                    result[text] = traduccion
                    if self.cache:
                        self.cache.set(text, traduccion)
                else:
                    print(f"⚠️ Texto {i} no traducido correctamente")
                    result[text] = text
            else:
                print(f"⚠️ No se encontró traducción para texto {i}")
                result[text] = text
        
        return result
    
    def _estimate_tokens(self, text: str) -> int:
        if not text: return 0
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            return int((len(text) / 4 + len(text.split()) / 0.75) / 2)
    
    def _clean_response(self, text):
        text = text.replace('"', '').replace('"', '').replace('"', '')
        
        if "\n\n" in text:
            text = text.split("\n\n")[0].strip()
        
        phrases = ["important instructions", "translate all", "keep technical", 
                  "maintain the", "do not add", "do not include"]
        
        for phrase in phrases:
            if phrase.lower() in text.lower():
                text = text[:text.lower().find(phrase.lower())].strip()
        
        if "o vertido" in text.lower():
            text = text.lower().replace("o vertido", "OR DISCHARGE").upper()
        
        return text.replace('```', '').strip()
    
    def get_cost_summary(self):
        input_cost = (self.token_stats["input_tokens"] / 1_000_000) * 3.75
        cached_cost = (self.token_stats["cached_input_tokens"] / 1_000_000) * 1.875
        output_cost = (self.token_stats["output_tokens"] / 1_000_000) * 15.0
        total_cost = input_cost + cached_cost + output_cost
        
        total_tokens = sum(self.token_stats.values())
        cost_per_1k = (total_cost * 1000) / total_tokens if total_tokens > 0 else 0
        
        cache_total = self.cache_hits + self.cache_misses if self.cache else 0
        cache_hit_rate = (self.cache_hits / cache_total * 100) if cache_total > 0 else 0
        
        return {
            "input_tokens": self.token_stats["input_tokens"],
            "cached_tokens": self.token_stats["cached_input_tokens"],
            "output_tokens": self.token_stats["output_tokens"],
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "cost_per_1k_tokens": cost_per_1k,
            "cache_hit_rate": cache_hit_rate,
            "api_calls": self.stats.get("calls", 0),
            "texts_processed": self.stats.get("texts", 0)
        }
    
    def __del__(self):
        if self.cache:
            self.cache.save()

    @property
    def total_texts(self): return self.stats.get("texts", 0)
    @property
    def api_calls(self): return self.stats.get("calls", 0)
    @property
    def rate_limit_retries(self): return self.stats.get("retries", 0)
    @property
    def successful_retries(self): return self.stats.get("retry_success", 0)
    @property
    def duplicates_avoided(self): return self.stats.get("duplicate_texts", 0)
    @property
    def errors(self): return self.stats.get("errors", 0)
    @property
    def cache_hits(self): return self.cache.hits if self.cache else 0
    @property
    def cache_misses(self): return self.cache.misses if self.cache else 0
    @property
    def total_input_tokens(self): return self.token_stats.get("input_tokens", 0)
    @property
    def total_output_tokens(self): return self.token_stats.get("output_tokens", 0)
    @property
    def cached_tokens(self): return self.token_stats.get("cached_input_tokens", 0)

class PPTXEditor:
    def __init__(self, translator):
        self.translator = translator
        self.total_texts = self.total_slides = self.errors = 0
        self.namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
        }
        
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)
    
    def process_pptx(self, input_path, output_path=None):
        """Procesa un archivo PPTX para traducir su contenido"""
        input_path = Path(input_path)
        output_path = Path(output_path or input_path.parent / f"{input_path.stem}_translated{input_path.suffix}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        start_time = time.time()
        
        try:
            prs = Presentation(input_path)
            print(f"Presentación con {len(prs.slides)} diapositivas")
            
            result = self._process_pptx(input_path, output_path)
            
            elapsed = time.time() - start_time
            self._print_summary(elapsed, output_path)
            
            if hasattr(self.translator, 'cache') and self.translator.cache:
                self.translator.cache.save()
            
            return output_path
            
        except Exception as e:
            print(f"Error al procesar presentación: {e}")
            self.errors += 1
            
            if hasattr(self.translator, 'cache') and self.translator.cache:
                self.translator.cache.save()
                
            return None
    
    def _collect_texts(self, root):
        """Recopila textos de una diapositiva PPTX"""
        parrafos_info = []
        
        for parrafo in root.findall('.//a:p', self.namespaces):
            runs_texto = []
            texto_completo = ""
            
            for run in parrafo.findall('.//a:t', self.namespaces):
                if run.text and run.text.strip():
                    texto_original = run.text
                    texto_limpio = texto_original.strip()
                    tiene_espacio = texto_original.endswith(" ")
                    
                    runs_texto.append({
                        "elemento": run,
                        "texto": texto_limpio,
                        "longitud": len(texto_limpio),
                        "tiene_espacio_final": tiene_espacio
                    })
                    
                    texto_completo += texto_limpio
                    if tiene_espacio or len(runs_texto) < parrafo.findall('.//a:t', self.namespaces).count(run) + 1:
                        texto_completo += " "
            
            texto_completo = texto_completo.strip()
            
            if runs_texto and texto_completo:
                parrafos_info.append({
                    "texto_completo": texto_completo,
                    "runs": runs_texto,
                    "longitud_total": sum(r["longitud"] for r in runs_texto)
                })
        
        total_parrafos = len(parrafos_info)
        total_runs = sum(len(p["runs"]) for p in parrafos_info)
        print(f" ({total_parrafos} párrafos, {total_runs} fragmentos)", end="", flush=True)
        
        return parrafos_info
    
    def _update_texts(self, parrafos_info, translations):
        """Actualiza los textos en la diapositiva con sus traducciones"""
        textos_traducidos = 0
        
        for parrafo in parrafos_info:
            texto_original = parrafo["texto_completo"]
            texto_traducido = translations.get(texto_original)
            
            if not texto_traducido:
                continue
            
            if len(parrafo["runs"]) == 1:
                # Caso simple: un solo run
                parrafo["runs"][0]["elemento"].text = texto_traducido
                textos_traducidos += 1
            else:
                # Distribución proporcional en múltiples runs
                textos_traducidos += self._update_multi_run_text(parrafo, texto_traducido)
        
        self.total_texts += textos_traducidos
        return textos_traducidos
    
    def _update_multi_run_text(self, parrafo, texto_traducido):
        """Actualiza un párrafo con múltiples runs de texto"""
        palabras_traducidas = texto_traducido.split()
        runs = parrafo["runs"]
        longitud_total = parrafo["longitud_total"]
        palabras_asignadas = 0
        
        for i, run in enumerate(runs):
            elemento = run["elemento"]
            longitud_original = run["longitud"]
            proporcion = longitud_original / longitud_total if longitud_total > 0 else 0
            
            palabras_para_run = max(1, round(proporcion * len(palabras_traducidas)))
            palabras_para_run = min(palabras_para_run, len(palabras_traducidas) - palabras_asignadas)
            
            if palabras_para_run <= 0:
                continue
            
            segmento = palabras_traducidas[palabras_asignadas:palabras_asignadas + palabras_para_run]
            texto_parcial = " ".join(segmento)
            
            if i == len(runs) - 1 and palabras_asignadas + palabras_para_run < len(palabras_traducidas):
                palabras_restantes = palabras_traducidas[palabras_asignadas + palabras_para_run:]
                texto_parcial += " " + " ".join(palabras_restantes)
            
            if run.get("tiene_espacio_final", False) or i < len(runs) - 1:
                texto_parcial += " "
            
            elemento.text = texto_parcial
            palabras_asignadas += palabras_para_run
        
        return 1  # Un párrafo traducido
    
    def _print_summary(self, elapsed, output_path):
        """Muestra un resumen del proceso de traducción"""
        print("\n" + "="*50)
        print("RESUMEN DE TRADUCCIÓN")
        print("="*50)
        
        if self.total_texts > 0:
            print(f"✅ TRADUCCIÓN COMPLETADA EXITOSAMENTE")
        else:
            print(f"❌ NO SE REALIZARON TRADUCCIONES")
        
        print(f"\n- Diapositivas: {self.total_slides}")
        print(f"- Textos traducidos: {self.total_texts}")
        print(f"- Tiempo total: {elapsed:.2f}s")
        
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"- Archivo generado: {output_path} ({size_mb:.2f} MB)")
        else:
            print(f"❌ ERROR: Archivo no generado correctamente")
        
        print("="*50)

    def _process_pptx(self, input_path, output_path=None):
        """Implementación del procesamiento de archivos PPTX para traducción"""
        input_path = Path(input_path)
        output_path = Path(output_path or input_path.parent / f"{input_path.stem}_translated{input_path.suffix}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Procesando: {input_path.name}")
        temp_output = output_path.with_suffix('.tmp')
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                
                # Extraer archivo PPTX
                with zipfile.ZipFile(input_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Verificar estructura
                slides_dir = temp_dir / 'ppt' / 'slides'
                if not slides_dir.exists():
                    raise Exception(f"Estructura PPTX inválida: no existe {slides_dir}")
                    
                slide_files = list(slides_dir.glob('slide*.xml'))
                if not slide_files:
                    raise Exception(f"No hay diapositivas en {slides_dir}")
                
                # Ordenar diapositivas
                slide_files = sorted(slide_files, 
                    key=lambda f: int(re.search(r'slide(\d+)\.xml', f.name).group(1))
                )
                
                # Proceso en dos fases: 1) Extracción de textos, 2) Traducción y actualización
                return self._process_slides(slide_files, temp_dir, temp_output, output_path)
                
        except Exception as e:
            print(f"Error en procesamiento: {e}")
            if temp_output.exists():
                temp_output.unlink()
            
            self.errors += 1
            return None
    
    def _process_slides(self, slide_files, temp_dir, temp_output, output_path):
        """Procesa las diapositivas en dos fases: extracción y actualización"""
        # Fase 1: Extraer todos los textos
        print(f"Extrayendo textos de {len(slide_files)} diapositivas...")
        todos_los_textos = []
        mapa_diapositivas = {}
        
        for i, slide_file in enumerate(slide_files, 1):
            print(f"Analizando diapositiva {i}/{len(slide_files)}...", end="", flush=True)
            
            try:
                parser = ET.XMLParser(encoding="utf-8")
                tree = ET.parse(slide_file, parser=parser)
                root = tree.getroot()
                
                parrafos_info = self._collect_texts(root)
                
                textos_diapositiva = [info["texto_completo"] for info in parrafos_info]
                textos_unicos = set(textos_diapositiva)
                
                mapa_diapositivas[slide_file] = {
                    "tree": tree,
                    "root": root,
                    "parrafos": parrafos_info,
                    "textos": textos_diapositiva
                }
                
                for texto in textos_unicos:
                    if texto not in todos_los_textos:
                        todos_los_textos.append(texto)
                
                print(f" {len(textos_diapositiva)} textos")
                self.total_slides += 1
                
            except Exception as e:
                print(f" ERROR: {e}")
                self.errors += 1
        
        # Fase 2: Traducir todos los textos de una vez
        print(f"Traduciendo {len(todos_los_textos)} textos únicos...")
        todas_traducciones = self.translator.translate(todos_los_textos)
        
        # Fase 3: Actualizar cada diapositiva con las traducciones
        print("Aplicando traducciones a las diapositivas...")
        self._update_slides_with_translations(slide_files, mapa_diapositivas, todas_traducciones)
        
        # Fase 4: Recomprimir el archivo PPTX
        return self._repack_pptx(temp_dir, temp_output, output_path)
    
    def _update_slides_with_translations(self, slide_files, mapa_diapositivas, traducciones):
        """Actualiza las diapositivas con las traducciones"""
        for i, slide_file in enumerate(slide_files, 1):
            if slide_file not in mapa_diapositivas:
                continue
                
            info = mapa_diapositivas[slide_file]
            print(f"Actualizando diapositiva {i}/{len(slide_files)}...", end="", flush=True)
            
            try:
                textos_traducidos = self._update_texts(info["parrafos"], traducciones)
                
                if textos_traducidos:
                    xml_string = ET.tostring(info["root"], encoding='UTF-8', method='xml')
                    if not xml_string.startswith(b'<?xml'):
                        xml_string = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_string
                    
                    with open(slide_file, 'wb') as f:
                        f.write(xml_string)
                    
                    print(f" {textos_traducidos} textos traducidos")
                else:
                    print(" No se encontraron textos para traducir")
                    
            except Exception as e:
                print(f" ERROR: {e}")
                self.errors += 1
    
    def _repack_pptx(self, temp_dir, temp_output, output_path):
        """Recomprime el PPTX con los cambios aplicados"""
        # Crear archivo ZIP
        with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
        
        # Verificar integridad
        with zipfile.ZipFile(temp_output, 'r') as check_zip:
            if check_zip.testzip() is not None:
                raise Exception("ZIP corrupto")
        
        # Mover a la ubicación final
        if output_path.exists():
            output_path.unlink()
        shutil.move(temp_output, output_path)
        print(f"✓ Archivo generado: {output_path}")
        
        return output_path

    @property
    def slides_processed(self):
        return self.total_slides 