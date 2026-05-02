"""
Channel parser — extrai estrutura canônica (curso → módulos → aulas) do conteúdo
bruto de um canal Telegram.

Estratégia:
  Single-shot com GPT-4o (modelo full) sobre TODO o conteúdo do canal:

    1. Construímos um contexto compacto contendo:
         - Mensagens-guia (texto puro, índices, separadores) na íntegra.
         - Lista de vídeos com (msg_id, caption oneline, duração) — caption inteiro
           porque o nome do módulo costuma vir após o '\\n\\n' do título da aula.
    2. Uma única chamada para gpt-4o devolve apenas a ESTRUTURA (módulos com lessonIds);
       títulos das aulas são derivados deterministicamente do caption depois.
       Output enxuto evita o cap de 16k tokens do gpt-4o.
    3. Enriquecemos o JSON com duração e file_size vindos diretamente do Telegram
       (não confiamos no AI para dados numéricos).
    4. Vídeos que o AI tenha omitido caem em "Geral" automaticamente — nunca
       perdemos uma aula.

Para canais com input >280k chars o prompt é dividido em lotes que compartilham
o mesmo blueprint de módulos extraído na primeira chamada.
"""
import json
import logging
import re
import mimetypes
from typing import Callable

logger = logging.getLogger(__name__)

# Modelo: GPT-4o full. Custo é prioridade menor que qualidade conforme requisito.
_MODEL = "gpt-4o"
_MAX_TOKENS_OUT = 16384
_TEMPERATURE = 0

# Heurísticas de tamanho — se o prompt single-shot ultrapassar, vamos para modo lote.
_SAFE_INPUT_CHARS = 280_000  # ~70k tokens — gpt-4o tem 128k de janela
_BATCH_SIZE = 200            # vídeos por lote no modo dividido
_MAX_HEADERS = 80
_MAX_HEADER_CHARS = 30_000   # por mensagem-guia
_MAX_CAPTION_CHARS = 600     # captions são geralmente <300; corte para segurança

_FCODE_RE = re.compile(r"#([A-Z]{1,10}\d{1,10})", re.IGNORECASE)
_WATERMARK_RE = re.compile(r"\s*-\s*-\s*[Bb]y\s+@\w+.*", re.DOTALL)


_SYSTEM_PROMPT = """\
Você é um especialista em organizar catálogos de cursos online a partir de canais do Telegram.
Sua única saída é um objeto JSON válido — sem markdown, sem comentários, sem texto extra.
Seja rigorosamente fiel ao conteúdo do canal: NÃO invente módulos, NÃO omita aulas, NÃO duplique vídeos.
"""

_USER_PROMPT_TEMPLATE = """\
# Tarefa
Recebi todas as mensagens de um canal Telegram que hospeda um curso. Preciso converter
isso em um catálogo estruturado (curso → módulos → aulas).

# Schema de saída obrigatório
{{
  "courseTitle": "Nome canônico do curso (sem '@', sem 'Telegram', sem emojis decorativos)",
  "description": "Descrição curta extraída da guia, ou string vazia",
  "modules": [
    {{
      "moduleTitle": "Nome do módulo, limpo e consistente",
      "lessonIds": ["123", "456", "789"]
    }}
  ]
}}

# Regras (TODAS obrigatórias)

1. **PONTE CÓDIGO → MSG_ID**: O guia lista itens por código (#F0001, #DOC002, #P12, etc.).
   Cada item também costuma ter esse código no caption — exemplo:
       [id=12345] #F0099 03 - Fecha sempre à sua imagem | =13 - ...
   Para classificar, você DEVE:
     a) Ler o guia e listar quais códigos pertencem a cada módulo.
     b) Para cada código listado, encontrar o item cujo caption contenha '#<código>'
        (na linha [id=...] ...).
     c) Pegar o número entre colchetes ('[id=12345]') e colocar em lessonIds.
   NUNCA coloque o código (ex: 'F0099') em lessonIds — sempre o msg_id (o número de [id=...]).
2. Se o canal tiver MENSAGEM-GUIA listando módulos com seus fcodes, ela é a VERDADE
   ABSOLUTA da estrutura. Não reorganize, não junte, não divida módulos do guia.
3. Se NÃO houver guia, infira módulos analisando os captions:
   - Padrões '01 - Tema', 'Módulo X', linhas após '|', prefixos '=Submódulo'.
   - Vídeos sobre o mesmo tema/tecnologia ficam juntos.
4. CADA vídeo da lista DEVE aparecer em EXATAMENTE UM módulo. Antes de finalizar,
   confira: o número de ids únicos em todos os lessonIds = total de vídeos da entrada.
   Vídeos não classificados vão para um módulo "Geral".
5. Mantenha a ordem original (pelo msg_id crescente) dos lessonIds dentro de cada módulo.
6. Nomes dos módulos: use o nome EXATO do guia se existir (ex: '05 - Docker 2.0').
   Senão, escolha o nome mais recorrente entre os captions do grupo.
7. lessonIds é SEMPRE um array de strings com msg_ids puros (ex: "12345"), nunca com
   '#', 'F', ou prefixo de zeros do fcode.
8. NÃO retorne títulos das aulas — serão derivados dos captions automaticamente.
   Você só decide a estrutura: courseTitle, description, módulos e quais ids vão em cada um.

{blueprint_block}# Canal
{channel_name}

# Conteúdo do canal
{channel_content}
"""

_BLUEPRINT_BLOCK_TEMPLATE = """\
# Blueprint pré-acordado
Os módulos do curso já foram identificados em uma chamada anterior. Use EXATAMENTE estes
nomes e a mesma ordem ao classificar os vídeos deste lote:

{blueprint_json}

"""


# --------------------------------------------------------------------------
# Construção do contexto de entrada
# --------------------------------------------------------------------------

def _clean_caption_oneline(text: str, limit: int) -> str:
    """Compacta um caption em uma linha legível, removendo watermark e quebras."""
    text = (text or "").strip()
    text = _WATERMARK_RE.sub("", text)
    # Mantém quebras como '|' para a IA ainda enxergar a estrutura módulo/submódulo
    text = re.sub(r"\s*\n\s*", " | ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def _format_headers(headers: list[dict]) -> str:
    if not headers:
        return ""
    lines = ["## Mensagens-guia (índice / sumário do canal)"]
    for h in headers[:_MAX_HEADERS]:
        text = (h.get("caption") or "").strip()
        if not text:
            continue
        if len(text) > _MAX_HEADER_CHARS:
            text = text[:_MAX_HEADER_CHARS] + "…"
        lines.append(f"\n[GUIA msg_id={h['msg_id']}]\n{text}")
    return "\n".join(lines)


def _format_videos(videos: list[dict]) -> str:
    lines = ["## Vídeos (em ordem cronológica)"]
    for v in videos:
        cap = _clean_caption_oneline(v.get("caption", ""), _MAX_CAPTION_CHARS)
        dur = v.get("duration_seconds") or 0
        dur_str = _fmt_duration(dur) if dur else "?"
        lines.append(f"[id={v['msg_id']} dur={dur_str}] {cap}")
    return "\n".join(lines)


def _build_user_prompt(
    channel_name: str,
    headers: list[dict],
    videos: list[dict],
    blueprint: list[str] | None = None,
) -> str:
    blueprint_block = ""
    if blueprint:
        blueprint_block = _BLUEPRINT_BLOCK_TEMPLATE.format(
            blueprint_json=json.dumps(blueprint, ensure_ascii=False, indent=2)
        )
    headers_text = _format_headers(headers)
    videos_text = _format_videos(videos)
    channel_content = (headers_text + "\n\n" + videos_text).strip()
    return _USER_PROMPT_TEMPLATE.format(
        blueprint_block=blueprint_block,
        channel_name=channel_name,
        channel_content=channel_content,
    )


# --------------------------------------------------------------------------
# Chamada à OpenAI
# --------------------------------------------------------------------------

async def _call_ai(user_prompt: str) -> dict:
    from openai import AsyncOpenAI
    from app.config import settings

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada")

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    logger.info("Chamando %s (prompt=%d chars)...", _MODEL, len(user_prompt))
    response = await client.chat.completions.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS_OUT,
        temperature=_TEMPERATURE,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    usage = response.usage
    logger.info(
        "Resposta %s: in=%d out=%d total=%d tokens",
        _MODEL, usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("JSON inválido retornado por %s: %s\n%s", _MODEL, e, raw[:1000])
        raise RuntimeError(f"AI retornou JSON inválido: {e}") from e


# --------------------------------------------------------------------------
# Pipeline principal
# --------------------------------------------------------------------------

async def extract_channel_structure(
    raw_messages: list[dict],
    channel_name: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Extrai o catálogo completo do canal e devolve o JSON canônico já enriquecido
    com duração e file_size deterministicamente.
    """
    headers = [m for m in raw_messages if m.get("is_header")]
    videos = [m for m in raw_messages if not m.get("is_header")]

    logger.info(
        "Extração de '%s': %d mensagens-guia, %d vídeos.",
        channel_name, len(headers), len(videos),
    )

    if not videos:
        logger.warning("Canal '%s' sem vídeos — devolvendo curso vazio.", channel_name)
        return _empty_course(channel_name)

    # Parser determinístico do guia — rede de segurança para vídeos que o AI errar
    guide_map = _parse_guide_blueprint(headers)
    guide_order = _parse_guide_module_order(headers) if guide_map else []
    if guide_map:
        logger.info(
            "Guia parseado: %d fcodes mapeados para %d módulos.",
            len(guide_map), len(set(guide_map.values())),
        )

    if guide_map:
        mapped = 0
        for v in videos:
            if _lookup_module_in_guide(v, guide_map):
                mapped += 1
        coverage = mapped / max(1, len(videos))
        if coverage >= 0.6:
            logger.info(
                "Guia cobre %.1f%% dos itens (%d/%d) — pulando IA e gerando estrutura determinística.",
                coverage * 100.0, mapped, len(videos),
            )
            return _build_structure_from_guide(
                channel_name=channel_name,
                videos=videos,
                guide_map=guide_map,
                guide_order=guide_order,
                headers=headers,
            )

    # Decide single-shot vs lotes pela estimativa de tamanho
    est_chars = sum(len(h.get("caption", "")) for h in headers[:_MAX_HEADERS])
    est_chars += len(videos) * 120  # ~120 chars por linha de vídeo no prompt

    if est_chars <= _SAFE_INPUT_CHARS:
        total_steps = 4
        if progress_callback:
            progress_callback(1, total_steps)
            progress_callback(2, total_steps)
        ai_json = await _extract_single_shot(headers, videos, channel_name)
        if progress_callback:
            progress_callback(3, total_steps)
    else:
        batch_count = (len(videos) + _BATCH_SIZE - 1) // _BATCH_SIZE
        total_steps = batch_count + 3  # preparar + blueprint + lotes + finalizar
        if progress_callback:
            progress_callback(1, total_steps)
        logger.info(
            "Conteúdo grande (~%d chars) — usando modo lote com blueprint.", est_chars,
        )
        ai_json = await _extract_batched(
            headers,
            videos,
            channel_name,
            progress_callback=progress_callback,
            total_steps=total_steps,
            batch_count=batch_count,
        )

    out = _enrich_and_validate(ai_json, videos, channel_name, guide_map, guide_order)
    if progress_callback:
        progress_callback(total_steps, total_steps)
    return out


def _extract_description_from_headers(headers: list[dict]) -> str:
    for h in headers:
        text = (h.get("caption") or "").strip()
        if not text:
            continue
        out_lines: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if _GUIDE_SECTION_RE.match(line) or line.startswith("#"):
                break
            out_lines.append(line)
        description = "\n".join(out_lines).strip()
        if description:
            return description
    return ""


def _build_structure_from_guide(
    channel_name: str,
    videos: list[dict],
    guide_map: dict[str, str],
    guide_order: list[str],
    headers: list[dict],
) -> dict:
    lessons_by_title: dict[str, list[dict]] = {}
    orphans: list[dict] = []

    for v in videos:
        title = _lookup_module_in_guide(v, guide_map)
        if not title:
            orphans.append(v)
            continue
        lessons_by_title.setdefault(title, []).append(v)

    out_modules: list[dict] = []
    ordered_titles: list[str] = []
    for t in guide_order:
        if t in lessons_by_title and lessons_by_title[t]:
            ordered_titles.append(t)
    for t in lessons_by_title.keys():
        if t not in ordered_titles and lessons_by_title[t]:
            ordered_titles.append(t)

    for t in ordered_titles:
        vids = sorted(lessons_by_title.get(t) or [], key=lambda x: int(x["msg_id"]))
        lessons = [
            _build_lesson_dict(msg_id=str(v["msg_id"]), video=v, order=i + 1)
            for i, v in enumerate(vids)
        ]
        if not lessons:
            continue
        out_modules.append({
            "moduleTitle": t,
            "order": len(out_modules) + 1,
            "lessons": lessons,
        })

    if orphans:
        vids = sorted(orphans, key=lambda x: int(x["msg_id"]))
        lessons = [
            _build_lesson_dict(msg_id=str(v["msg_id"]), video=v, order=i + 1)
            for i, v in enumerate(vids)
        ]
        out_modules.append({
            "moduleTitle": "Geral",
            "order": len(out_modules) + 1,
            "lessons": lessons,
        })

    description = _extract_description_from_headers(headers)
    total_lessons = sum(len(m["lessons"]) for m in out_modules)
    total_duration = sum(
        l["durationSeconds"] for m in out_modules for l in m["lessons"]
    )
    logger.info(
        "JSON final (determinístico): curso='%s', %d módulos, %d aulas, duração total=%s",
        channel_name, len(out_modules), total_lessons, _fmt_duration(total_duration),
    )
    return {
        "sourceName": channel_name,
        "courseTitle": channel_name,
        "description": description,
        "modules": out_modules,
    }


# --------------------------------------------------------------------------
# Parser determinístico do guia (rede de segurança)
# --------------------------------------------------------------------------

_GUIDE_SECTION_RE = re.compile(r"^\s*={1,3}\s*(.+?)\s*$")


def _parse_guide_blueprint(headers: list[dict]) -> dict[str, str]:
    """
    Extrai um mapa {fcode_uppercase: nome_do_módulo} parseando as mensagens-guia.

    Reconhece o formato dominante destes canais:
        = 05 - Docker 2.0
        #F0039 #F0040 #F0041 ...
        #F0047 #F0048 ...

        = 06 - Kubernetes
        #F0215 ...

    Linhas iniciadas com '=' definem o módulo corrente; fcodes nas linhas seguintes
    pertencem a esse módulo até a próxima linha de seção.

    Também suporta seções simples sem '=' (ex.: "Arquivos" seguido de "#Doc001 #Doc002").
    """
    fcode_to_module: dict[str, str] = {}

    current_module: str | None = None
    pending_plain_title: str | None = None

    for h in headers:
        text = (h.get("caption") or "").strip()
        if not text or not _FCODE_RE.search(text):
            continue

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            section_match = _GUIDE_SECTION_RE.match(line)
            if section_match:
                current_module = section_match.group(1).strip()
                pending_plain_title = None
                continue

            if not line.startswith("#"):
                pending_plain_title = line.strip()
                continue

            if pending_plain_title:
                current_module = pending_plain_title
                pending_plain_title = None

            if current_module:
                for fc in _FCODE_RE.findall(line):
                    key = fc.upper()
                    if key not in fcode_to_module:
                        fcode_to_module[key] = current_module

    return fcode_to_module


def _parse_guide_module_order(headers: list[dict]) -> list[str]:
    order: list[str] = []
    pending_plain_title: str | None = None
    for h in headers:
        text = (h.get("caption") or "").strip()
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            section_match = _GUIDE_SECTION_RE.match(line)
            if section_match:
                title = section_match.group(1).strip()
                pending_plain_title = None
                if title and title not in order:
                    order.append(title)
                continue

            if not line.startswith("#"):
                pending_plain_title = line.strip()
                continue

            if pending_plain_title and _FCODE_RE.search(line):
                if pending_plain_title not in order:
                    order.append(pending_plain_title)
                pending_plain_title = None
    return order


async def _extract_single_shot(
    headers: list[dict],
    videos: list[dict],
    channel_name: str,
) -> dict:
    prompt = _build_user_prompt(channel_name, headers, videos)
    return await _call_ai(prompt)


async def _extract_batched(
    headers: list[dict],
    videos: list[dict],
    channel_name: str,
    progress_callback: Callable[[int, int], None] | None = None,
    total_steps: int = 0,
    batch_count: int = 0,
) -> dict:
    """
    Estratégia para canais enormes:
      1) Chamada-blueprint: só os headers + amostra de vídeos → lista canônica de módulos.
      2) Chamadas-lote: cada lote de vídeos é classificado contra o blueprint.
    """
    # Passo 1 — blueprint
    if progress_callback and total_steps:
        progress_callback(2, total_steps)
    sample_size = min(len(videos), 60)
    sample_step = max(1, len(videos) // sample_size)
    sample_videos = videos[::sample_step][:sample_size]

    blueprint_prompt = _build_user_prompt(channel_name, headers, sample_videos)
    blueprint_json = await _call_ai(blueprint_prompt)
    blueprint_titles = [
        m.get("moduleTitle", "").strip()
        for m in blueprint_json.get("modules", [])
        if m.get("moduleTitle")
    ]
    course_title = blueprint_json.get("courseTitle", channel_name)
    description = blueprint_json.get("description", "")

    logger.info(
        "Blueprint: %d módulos identificados → %s",
        len(blueprint_titles), blueprint_titles,
    )

    # Passo 2 — lotes
    merged_modules: dict[str, list[dict]] = {t: [] for t in blueprint_titles}
    module_order = list(blueprint_titles)

    for i in range(0, len(videos), _BATCH_SIZE):
        batch_index = (i // _BATCH_SIZE) + 1
        if progress_callback and total_steps:
            progress_callback(2 + batch_index, total_steps)
        batch = videos[i:i + _BATCH_SIZE]
        logger.info(
            "Lote %d–%d / %d", i + 1, i + len(batch), len(videos),
        )
        batch_prompt = _build_user_prompt(
            channel_name, headers if i == 0 else [], batch, blueprint=blueprint_titles,
        )
        batch_json = await _call_ai(batch_prompt)

        for mod in batch_json.get("modules", []):
            title = mod.get("moduleTitle", "").strip() or "Geral"
            if title not in merged_modules:
                merged_modules[title] = []
                module_order.append(title)
            merged_modules[title].extend(mod.get("lessons", []))

    return {
        "courseTitle": course_title,
        "description": description,
        "modules": [
            {"moduleTitle": t, "lessons": merged_modules[t]}
            for t in module_order
            if merged_modules.get(t)
        ],
    }


# --------------------------------------------------------------------------
# Enriquecimento + validação
# --------------------------------------------------------------------------

def _enrich_and_validate(
    ai_json: dict,
    videos: list[dict],
    channel_name: str,
    guide_map: dict[str, str] | None = None,
    guide_order: list[str] | None = None,
) -> dict:
    """Injeta duração/tamanho a partir dos dados brutos e garante 100% de cobertura."""
    video_by_id: dict[str, dict] = {str(v["msg_id"]): v for v in videos}
    seen_ids: set[str] = set()
    guide_map = guide_map or {}
    guide_order = guide_order or []

    out_modules: list[dict] = []
    for module in ai_json.get("modules", []):
        title = (module.get("moduleTitle") or "Geral").strip()

        # Aceita tanto lessonIds (formato compacto preferido) quanto lessons[].fileId (legado)
        candidate_ids = _extract_lesson_ids(module)
        out_lessons: list[dict] = []

        for raw_id in candidate_ids:
            file_id = str(raw_id).strip().lstrip("#")
            # Algumas vezes o AI vem com 'F0001' — normaliza para o msg_id puro
            if file_id.upper().startswith("F") and file_id[1:].isdigit():
                logger.warning("AI usou fcode %r ao invés de msg_id — descartando.", file_id)
                continue
            if not file_id.isdigit():
                logger.warning("AI retornou id inválido %r — ignorando.", file_id)
                continue
            if file_id not in video_by_id:
                logger.warning("AI referenciou msg_id %s inexistente — ignorando.", file_id)
                continue
            if file_id in seen_ids:
                logger.warning("AI duplicou msg_id %s — mantendo primeira ocorrência.", file_id)
                continue
            seen_ids.add(file_id)

            out_lessons.append(_build_lesson_dict(
                msg_id=file_id,
                video=video_by_id[file_id],
                order=len(out_lessons) + 1,
            ))

        if not out_lessons:
            continue

        out_modules.append({
            "moduleTitle": title,
            "order": len(out_modules) + 1,
            "lessons": out_lessons,
        })

    # Vídeos que o AI omitiu — primeiro tenta resgatar via guia determinístico
    orphans = [v for v in videos if str(v["msg_id"]) not in seen_ids]
    rescued = 0
    leftover_orphans: list[dict] = []

    for v in orphans:
        rescued_module = _lookup_module_in_guide(v, guide_map)
        if not rescued_module:
            leftover_orphans.append(v)
            continue

        seen_ids.add(str(v["msg_id"]))
        rescued += 1

        # Anexa ao módulo correspondente (cria se necessário, mas não deveria)
        target = next(
            (m for m in out_modules if m["moduleTitle"] == rescued_module),
            None,
        )
        if target is None:
            target = {
                "moduleTitle": rescued_module,
                "order": len(out_modules) + 1,
                "lessons": [],
            }
            out_modules.append(target)

        target["lessons"].append(_build_lesson_dict(
            msg_id=str(v["msg_id"]),
            video=v,
            order=len(target["lessons"]) + 1,
        ))

    if rescued:
        logger.info(
            "Resgatados %d/%d órfãos via guia determinístico.",
            rescued, len(orphans),
        )

    if guide_map:
        out_modules = _apply_guide_overrides(
            out_modules=out_modules,
            video_by_id=video_by_id,
            guide_map=guide_map,
            guide_order=guide_order if isinstance(guide_order, list) else [],
        )

    # Reordena cada módulo por msg_id após os resgates
    for m in out_modules:
        m["lessons"].sort(key=lambda l: int(l["fileId"]))
        for i, l in enumerate(m["lessons"], 1):
            l["order"] = i

    # O que sobrar mesmo após o resgate vai para "Geral"
    if leftover_orphans:
        logger.warning(
            "AI omitiu %d vídeo(s) que o guia não cobre — caindo em 'Geral'.",
            len(leftover_orphans),
        )
        geral_lessons = [
            _build_lesson_dict(
                msg_id=str(v["msg_id"]),
                video=v,
                order=i + 1,
            )
            for i, v in enumerate(leftover_orphans)
        ]
        existing = next(
            (m for m in out_modules if m["moduleTitle"].lower() == "geral"), None,
        )
        if existing:
            base = len(existing["lessons"])
            for j, lesson in enumerate(geral_lessons, 1):
                lesson["order"] = base + j
            existing["lessons"].extend(geral_lessons)
        else:
            out_modules.append({
                "moduleTitle": "Geral",
                "order": len(out_modules) + 1,
                "lessons": geral_lessons,
            })

    course_title = (ai_json.get("courseTitle") or channel_name).strip()
    description = (ai_json.get("description") or "").strip()

    total_lessons = sum(len(m["lessons"]) for m in out_modules)
    total_duration = sum(
        l["durationSeconds"] for m in out_modules for l in m["lessons"]
    )
    logger.info(
        "JSON final: curso='%s', %d módulos, %d aulas, duração total=%s",
        course_title, len(out_modules), total_lessons, _fmt_duration(total_duration),
    )

    return {
        "sourceName": channel_name,
        "courseTitle": course_title,
        "description": description,
        "modules": out_modules,
    }


def _apply_guide_overrides(
    out_modules: list[dict],
    video_by_id: dict[str, dict],
    guide_map: dict[str, str],
    guide_order: list[str],
) -> list[dict]:
    module_titles_in_order: list[str] = []
    lessons_by_title: dict[str, list[dict]] = {}

    for m in out_modules:
        title = (m.get("moduleTitle") or "Geral").strip()
        if title not in lessons_by_title:
            lessons_by_title[title] = []
            module_titles_in_order.append(title)
        lessons_by_title[title].extend(m.get("lessons") or [])

    corrected = 0
    final_lessons_by_title: dict[str, list[dict]] = {t: [] for t in module_titles_in_order}
    final_titles_in_order = list(module_titles_in_order)

    for current_title in module_titles_in_order:
        for lesson in lessons_by_title.get(current_title, []):
            file_id = str(lesson.get("fileId") or "").strip()
            video = video_by_id.get(file_id)
            expected = _lookup_module_in_guide(video, guide_map) if video else None
            final_title = (expected or current_title).strip() or "Geral"
            if expected and expected.strip() != current_title:
                corrected += 1
            if final_title not in final_lessons_by_title:
                final_lessons_by_title[final_title] = []
                final_titles_in_order.append(final_title)
            final_lessons_by_title[final_title].append(lesson)

    if corrected:
        logger.info("Guia sobrepôs a classificação do AI para %d aula(s).", corrected)

    ordered_titles: list[str] = []
    for t in guide_order:
        if t in final_lessons_by_title and final_lessons_by_title[t]:
            ordered_titles.append(t)
    for t in final_titles_in_order:
        if t not in ordered_titles and final_lessons_by_title.get(t):
            ordered_titles.append(t)

    rebuilt: list[dict] = []
    for t in ordered_titles:
        lessons = final_lessons_by_title.get(t) or []
        if not lessons:
            continue
        rebuilt.append({
            "moduleTitle": t,
            "order": len(rebuilt) + 1,
            "lessons": lessons,
        })
    return rebuilt


def _lookup_module_in_guide(video: dict, guide_map: dict[str, str]) -> str | None:
    """Procura o fcode no caption do vídeo e devolve o módulo do guia, se houver."""
    if not guide_map:
        return None
    caption = video.get("caption", "") or ""
    fcodes = _FCODE_RE.findall(caption)
    for fc in fcodes:
        module = guide_map.get(fc.upper())
        if module:
            return module
    return None


def _extract_lesson_ids(module: dict) -> list:
    """Aceita schema compacto (lessonIds) ou legado (lessons[].fileId)."""
    if isinstance(module.get("lessonIds"), list):
        return module["lessonIds"]
    if isinstance(module.get("lessons"), list):
        return [
            l.get("fileId") if isinstance(l, dict) else l
            for l in module["lessons"]
        ]
    return []


def _build_lesson_dict(msg_id: str, video: dict, order: int) -> dict:
    duration = int(video.get("duration_seconds") or 0)
    file_size = video.get("file_size_bytes")
    caption = video.get("caption", "")
    title = _clean_title_from_caption(caption, msg_id)
    fcodes = _FCODE_RE.findall(caption)
    fcode = fcodes[0].upper() if fcodes else None
    media_type = (video.get("media_type") or "video").strip().lower()
    mime_type = video.get("mime_type")
    original_filename = video.get("original_filename")
    file_ext = None
    if original_filename:
        m = re.search(r"(\.[A-Za-z0-9]{1,10})\b", str(original_filename))
        file_ext = m.group(1) if m else None
    if not file_ext and mime_type:
        file_ext = mimetypes.guess_extension(str(mime_type)) or None
    if media_type == "file" and original_filename:
        title = str(original_filename)

    return {
        "lessonTitle": title,
        "fileId": msg_id,
        "fcode": fcode,
        "mediaType": media_type,
        "mimeType": mime_type,
        "originalFilename": original_filename,
        "fileExt": file_ext,
        "order": order,
        "durationSeconds": duration,
        "durationStr": _fmt_duration(duration),
        "fileSize": file_size,
        "fileSizeMB": round(file_size / (1024 * 1024), 1) if file_size else None,
    }


def _clean_title_from_caption(caption: str, msg_id: str) -> str:
    """
    Deriva o título da aula a partir do caption bruto do Telegram.

    Heurística (cobre o formato '#FXXXX 01 - Título -  - By @autor ❤️‍🔥.\\n\\nMódulo'):
      1. Pega só a primeira linha (antes de qualquer '\\n').
      2. Remove '#FXXXX' do início.
      3. Remove ' - - By @qualquercoisa' e tudo após.
      4. Remove '.mp4' final e pontuação solta.
      5. Colapsa espaços.
    """
    text = (caption or "").strip()
    if not text:
        return f"Aula {msg_id}"

    first_line = text.splitlines()[0]
    first_line = _FCODE_RE.sub("", first_line)
    first_line = _WATERMARK_RE.sub("", first_line)
    first_line = re.sub(r"\.mp4\b", "", first_line, flags=re.IGNORECASE)
    first_line = re.sub(r"\s+", " ", first_line).strip(" -•·.\t")

    return first_line or f"Aula {msg_id}"


def _fmt_duration(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return ""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _empty_course(channel_name: str) -> dict:
    return {
        "sourceName": channel_name,
        "courseTitle": channel_name,
        "description": "",
        "modules": [],
    }
