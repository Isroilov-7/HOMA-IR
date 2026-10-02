FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/mpl \
    DB_PATH=/data/health.db \
    BACKUP_DIR=/data/backups \
    TZ=Asia/Tashkent

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Ilova root emas foydalanuvchi bilan ishlaydi
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin bot \
 && mkdir -p /data && chown bot:bot /data
COPY --chown=bot:bot . .

USER bot
VOLUME ["/data"]
CMD ["python", "bot.py"]
