"""
Dashboard — queries agregadas para o painel principal.

Todas as funções recebem (user_id, db) e devolvem o shape final esperado
pelo frontend, sem necessidade de pós-processamento no router.

Modelo de "horas estudadas" usado por todos os charts temporais:
  - Cada linha de WatchHistory representa o progresso atual em um vídeo.
  - Atribuímos `progress_seconds` ao timestamp `watched_at` (última atualização).
  - É uma aproximação — se o usuário voltou a uma aula em vários dias o tempo
    fica concentrado no último dia. Para tracking mais preciso seria preciso
    armazenar deltas por sessão; isso fica fora de escopo aqui.
"""
from datetime import UTC, datetime, timedelta
import re

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import DownloadStatus
from app.infrastructure.models import (
    Course,
    DownloadJob,
    Video,
    WatchHistory,
)


_DAY_LABELS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _start_of_week(reference: datetime) -> datetime:
    """Segunda-feira 00:00 da semana de `reference`."""
    monday = reference - timedelta(days=reference.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


# --------------------------------------------------------------------------
# /dashboard/stats
# --------------------------------------------------------------------------

async def get_stats(user_id: int, db: AsyncSession, course_id: int | None = None) -> dict:
    now = _now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if course_id is not None:
        lessons_completed_q = (
            select(func.count(WatchHistory.id))
            .select_from(WatchHistory)
            .join(Video, WatchHistory.video_id == Video.id)
            .where(
                WatchHistory.user_id == user_id,
                WatchHistory.completed.is_(True),
                Video.course_id == course_id,
            )
        )
        lessons_completed = (await db.execute(lessons_completed_q)).scalar() or 0

        total_lessons_q = select(func.count(Video.id)).where(Video.course_id == course_id)
        total_lessons = (await db.execute(total_lessons_q)).scalar() or 0

        hours_month_q = (
            select(func.coalesce(func.sum(WatchHistory.progress_seconds), 0))
            .select_from(WatchHistory)
            .join(Video, WatchHistory.video_id == Video.id)
            .where(
                WatchHistory.user_id == user_id,
                WatchHistory.watched_at >= month_start,
                Video.course_id == course_id,
            )
        )
        seconds_this_month = (await db.execute(hours_month_q)).scalar() or 0

        queued_q = (
            select(func.count(DownloadJob.id))
            .select_from(DownloadJob)
            .join(Video, DownloadJob.video_id == Video.id)
            .where(
                Video.course_id == course_id,
                DownloadJob.status.in_([
                    DownloadStatus.PENDING,
                    DownloadStatus.RETRY_PENDING,
                    DownloadStatus.DOWNLOADING,
                ]),
            )
        )
        queued = (await db.execute(queued_q)).scalar() or 0

        progress_pct = round((lessons_completed / total_lessons) * 100) if total_lessons else 0
        return {
            "active_courses": 1,
            "lessons_completed": lessons_completed,
            "total_lessons": total_lessons,
            "hours_this_month": round(seconds_this_month / 3600, 2),
            "queued_downloads": queued,
            "progress_pct": progress_pct,
        }

    # Cursos ativos (com qualquer watch_history)
    active_courses_q = (
        select(func.count(func.distinct(Video.course_id)))
        .select_from(WatchHistory)
        .join(Video, WatchHistory.video_id == Video.id)
        .where(WatchHistory.user_id == user_id)
    )
    active_courses = (await db.execute(active_courses_q)).scalar() or 0

    # Aulas concluídas
    lessons_completed_q = select(func.count(WatchHistory.id)).where(
        WatchHistory.user_id == user_id,
        WatchHistory.completed.is_(True),
    )
    lessons_completed = (await db.execute(lessons_completed_q)).scalar() or 0

    # Total de aulas disponíveis (em todos os cursos)
    total_lessons = (await db.execute(select(func.count(Video.id)))).scalar() or 0

    # Horas estudadas no mês (sum progress_seconds das linhas com watched_at >= mês atual)
    hours_month_q = select(func.coalesce(func.sum(WatchHistory.progress_seconds), 0)).where(
        WatchHistory.user_id == user_id,
        WatchHistory.watched_at >= month_start,
    )
    seconds_this_month = (await db.execute(hours_month_q)).scalar() or 0

    # Downloads em andamento
    queued_q = select(func.count(DownloadJob.id)).where(
        DownloadJob.status.in_([
            DownloadStatus.PENDING,
            DownloadStatus.RETRY_PENDING,
            DownloadStatus.DOWNLOADING,
        ])
    )
    queued = (await db.execute(queued_q)).scalar() or 0

    return {
        "active_courses": active_courses,
        "lessons_completed": lessons_completed,
        "total_lessons": total_lessons,
        "hours_this_month": round(seconds_this_month / 3600, 2),
        "queued_downloads": queued,
    }


# --------------------------------------------------------------------------
# /dashboard/weekly  — últimas 8 semanas
# --------------------------------------------------------------------------

async def get_weekly(
    user_id: int, db: AsyncSession, weeks: int = 8, course_id: int | None = None
) -> list[dict]:
    now = _now()
    current_week_start = _start_of_week(now)
    oldest_week_start = current_week_start - timedelta(weeks=weeks - 1)

    week_bucket = func.date_trunc("week", WatchHistory.watched_at)
    q = (
        select(
            week_bucket.label("week_start"),
            func.coalesce(func.sum(WatchHistory.progress_seconds), 0).label("seconds"),
        )
        .select_from(WatchHistory)
        .join(Video, WatchHistory.video_id == Video.id)
        .where(WatchHistory.user_id == user_id, WatchHistory.watched_at >= oldest_week_start)
        .group_by(week_bucket)
    )
    if course_id is not None:
        q = q.where(Video.course_id == course_id)
    rows = (await db.execute(q)).all()
    seconds_by_week = {r.week_start.replace(tzinfo=None): r.seconds for r in rows}

    out: list[dict] = []
    for i in range(weeks):
        week_start = oldest_week_start + timedelta(weeks=i)
        seconds = seconds_by_week.get(week_start, 0)
        out.append({
            "week_start": week_start.date().isoformat(),
            "label": f"Sem {i + 1}",
            "hours": round(seconds / 3600, 2),
        })
    return out


# --------------------------------------------------------------------------
# /dashboard/streak  — semana atual (Seg→Dom)
# --------------------------------------------------------------------------

async def get_streak(user_id: int, db: AsyncSession, course_id: int | None = None) -> list[dict]:
    now = _now()
    week_start = _start_of_week(now)
    week_end = week_start + timedelta(days=7)

    day_bucket = func.date_trunc("day", WatchHistory.watched_at)
    q = (
        select(
            day_bucket.label("day"),
            func.coalesce(func.sum(WatchHistory.progress_seconds), 0).label("seconds"),
        )
        .select_from(WatchHistory)
        .join(Video, WatchHistory.video_id == Video.id)
        .where(WatchHistory.user_id == user_id, WatchHistory.watched_at >= week_start, WatchHistory.watched_at < week_end)
        .group_by(day_bucket)
    )
    if course_id is not None:
        q = q.where(Video.course_id == course_id)
    rows = (await db.execute(q)).all()
    seconds_by_day = {r.day.replace(tzinfo=None).date(): r.seconds for r in rows}

    out: list[dict] = []
    for i in range(7):
        day = (week_start + timedelta(days=i)).date()
        seconds = seconds_by_day.get(day, 0)
        out.append({
            "day": _DAY_LABELS_PT[i],
            "date": day.isoformat(),
            "min": round(seconds / 60),
        })
    return out


# --------------------------------------------------------------------------
# /dashboard/hourly  — minutos por hora do dia (todos os dias)
# --------------------------------------------------------------------------

async def get_hourly(user_id: int, db: AsyncSession, course_id: int | None = None) -> list[dict]:
    hour_bucket = func.extract("hour", WatchHistory.watched_at)
    q = (
        select(
            hour_bucket.label("hour"),
            func.coalesce(func.sum(WatchHistory.progress_seconds), 0).label("seconds"),
        )
        .select_from(WatchHistory)
        .join(Video, WatchHistory.video_id == Video.id)
        .where(WatchHistory.user_id == user_id)
        .group_by(hour_bucket)
    )
    if course_id is not None:
        q = q.where(Video.course_id == course_id)
    rows = (await db.execute(q)).all()
    seconds_by_hour = {int(r.hour): r.seconds for r in rows}

    out: list[dict] = []
    for h in range(24):
        seconds = seconds_by_hour.get(h, 0)
        out.append({
            "hour": f"{h:02d}h",
            "min": round(seconds / 60),
        })
    return out


# --------------------------------------------------------------------------
# /dashboard/recent  — últimas N aulas tocadas
# --------------------------------------------------------------------------

async def get_recent(user_id: int, db: AsyncSession, limit: int = 10) -> list[dict]:
    ranked = (
        select(
            WatchHistory.progress_seconds.label("progress_seconds"),
            WatchHistory.completed.label("completed"),
            WatchHistory.watched_at.label("watched_at"),
            Video.id.label("video_id"),
            Video.course_id.label("course_id"),
            Course.title.label("course_title"),
            Video.fcode.label("fcode"),
            Video.title.label("title"),
            Video.module_name.label("module_name"),
            Video.duration_seconds.label("duration_seconds"),
            func.row_number()
            .over(
                partition_by=Video.course_id,
                order_by=(WatchHistory.watched_at.desc(), WatchHistory.id.desc()),
            )
            .label("rn"),
        )
        .select_from(WatchHistory)
        .join(Video, WatchHistory.video_id == Video.id)
        .join(Course, Video.course_id == Course.id)
        .where(WatchHistory.user_id == user_id)
    ).subquery()

    q = (
        select(ranked)
        .where(ranked.c.rn == 1)
        .order_by(desc(ranked.c.watched_at))
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    return [
        {
            "video_id": r.video_id,
            "course_id": r.course_id,
            "course_title": r.course_title,
            "fcode": r.fcode,
            "title": r.title,
            "module_name": r.module_name,
            "duration_seconds": r.duration_seconds,
            "progress_seconds": r.progress_seconds,
            "progress_pct": (
                round(r.progress_seconds / r.duration_seconds * 100)
                if r.duration_seconds else 0
            ),
            "completed": r.completed,
            "watched_at": r.watched_at.isoformat() if r.watched_at else None,
        }
        for r in rows
    ]


# --------------------------------------------------------------------------
# /dashboard/modules  — % de conclusão por módulo (top 5)
# --------------------------------------------------------------------------

async def get_modules(user_id: int, db: AsyncSession, top: int = 5, course_id: int | None = None) -> list[dict]:
    """
    Retorna até `top` módulos, priorizando módulos próximos do módulo atual (último assistido).
    Cada item: { module_name, course_title, total, completed, percent }.
    """
    def module_order(name: str) -> int | None:
        m = re.match(r"^\s*(\d+)\s*-", name or "")
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    completed_q = (
        select(
            Course.id.label("course_id"),
            Course.title.label("course_title"),
            Video.module_name.label("module_name"),
            func.count(Video.id).label("total"),
            func.count(WatchHistory.id).filter(WatchHistory.completed.is_(True)).label("completed"),
            func.max(WatchHistory.watched_at).label("last_watched_at"),
        )
        .select_from(Video)
        .join(Course, Video.course_id == Course.id)
        .join(
            WatchHistory,
            (WatchHistory.video_id == Video.id) & (WatchHistory.user_id == user_id),
            isouter=True,
        )
        .group_by(Course.id, Course.title, Video.module_name)
    )
    if course_id is not None:
        completed_q = completed_q.where(Course.id == course_id)
    rows = (await db.execute(completed_q)).all()

    items = [
        {
            "course_id": r.course_id,
            "course_title": r.course_title,
            "module_name": r.module_name,
            "total": int(r.total or 0),
            "completed": int(r.completed or 0),
            "percent": (
                round((r.completed or 0) / r.total * 100) if r.total else 0
            ),
            "_order": module_order(r.module_name),
            "_last_watched_at": r.last_watched_at,
        }
        for r in rows
    ]
    # Âncora: último módulo assistido (por watched_at). Fallback: maior percent.
    anchor = None
    watched = [i for i in items if i["_last_watched_at"] is not None and i["_order"] is not None]
    if watched:
        watched.sort(key=lambda x: x["_last_watched_at"], reverse=True)
        anchor = watched[0]
    else:
        ranked = [i for i in items if i["_order"] is not None]
        ranked.sort(key=lambda x: (x["percent"], x["completed"]), reverse=True)
        anchor = ranked[0] if ranked else None

    out: list[dict] = []
    if anchor:
        course_items = [i for i in items if i["course_id"] == anchor["course_id"] and i["_order"] is not None]
        course_items.sort(key=lambda x: x["_order"])
        orders = [i["_order"] for i in course_items if i["_order"] is not None]
        order_to_item = {i["_order"]: i for i in course_items if i["_order"] is not None}

        anchor_order = anchor["_order"]
        if anchor_order is not None and orders:
            closest_order = min(orders, key=lambda o: abs(o - anchor_order))
            anchor_idx = orders.index(closest_order)

            selected_orders: list[int] = []
            selected_orders.append(closest_order)
            step = 1
            while len(selected_orders) < top and (anchor_idx - step >= 0 or anchor_idx + step < len(orders)):
                if anchor_idx - step >= 0:
                    selected_orders.append(orders[anchor_idx - step])
                    if len(selected_orders) >= top:
                        break
                if anchor_idx + step < len(orders):
                    selected_orders.append(orders[anchor_idx + step])
                step += 1

            selected_orders = sorted(set(selected_orders))
            out = [order_to_item[o] for o in selected_orders if o in order_to_item][:top]

    # Completa com outros módulos (em andamento primeiro) se não houver o suficiente no curso âncora.
    if len(out) < top:
        selected = {(i["course_id"], i["module_name"]) for i in out}
        remaining = [i for i in items if (i["course_id"], i["module_name"]) not in selected]
        remaining.sort(
            key=lambda x: (
                1 if 0 < x["percent"] < 100 else 0,
                x["percent"],
                x["completed"],
                x["_last_watched_at"] or datetime.min,
            ),
            reverse=True,
        )
        out.extend(remaining[: max(0, top - len(out))])

    for i in out:
        i.pop("_order", None)
        i.pop("_last_watched_at", None)
    return out


# --------------------------------------------------------------------------
# /dashboard/my-courses  — cursos do usuário com progresso geral
# --------------------------------------------------------------------------

async def get_my_courses(user_id: int, db: AsyncSession) -> list[dict]:
    q = (
        select(
            Course.id,
            Course.title,
            Course.total_videos,
            Course.total_duration_seconds,
            func.count(func.distinct(Video.module_name)).label("modules"),
            func.count(WatchHistory.id).filter(WatchHistory.completed.is_(True)).label("completed"),
        )
        .select_from(Course)
        .join(Video, Video.course_id == Course.id, isouter=True)
        .join(
            WatchHistory,
            (WatchHistory.video_id == Video.id) & (WatchHistory.user_id == user_id),
            isouter=True,
        )
        .group_by(Course.id, Course.title, Course.total_videos, Course.total_duration_seconds)
        .order_by(Course.created_at.desc())
    )
    rows = (await db.execute(q)).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "modules": int(r.modules or 0),
            "lessons": int(r.total_videos or 0),
            "hours": round((r.total_duration_seconds or 0) / 3600, 1),
            "completed": int(r.completed or 0),
            "progress_pct": (
                round((r.completed or 0) / r.total_videos * 100)
                if r.total_videos else 0
            ),
        }
        for r in rows
    ]
